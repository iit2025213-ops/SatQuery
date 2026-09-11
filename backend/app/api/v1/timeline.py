# app/api/v1/timeline.py

"""
Timeline API endpoints — Phase 9

Endpoints:
  POST  /api/v1/timeline/retrieve
  GET   /api/v1/timeline/{timeline_id}
  GET   /api/v1/timeline/animation/{timeline_id}
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
import uuid

from app.auth.dependencies import get_current_user_id
from app.config import settings

logger = logging.getLogger("satquery")
router = APIRouter(prefix="/api/v1/timeline", tags=["timeline"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class RetrieveTimelineRequest(BaseModel):
    aoi_geojson: dict  # GeoJSON Polygon
    date_start: str  # YYYY-MM-DD
    date_end: str
    collection: str = "Sentinel-2"
    cloud_cover_max: int = Field(default=20, ge=0, le=100)
    job_id: Optional[str] = None
    aoi_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/retrieve")
async def retrieve_timeline(
    request: RetrieveTimelineRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Retrieve multi-year satellite imagery timeline.

    Queries GEE for the best scene per year across the date range.
    """
    from app.main import supabase_client
    from app.gee.connector import GEEConnector
    from app.timeline.processor import TimelineProcessor

    try:
        # Authenticate GEE
        connector = GEEConnector(
            service_account_key_path=settings.gee_service_account_key_path,
            project_id=settings.gee_project_id,
        )
        auth_ok = await connector.authenticate()
        if not auth_ok:
            raise HTTPException(status_code=503, detail="GEE authentication failed")

        # Create timeline record
        timeline_id = str(uuid.uuid4())
        job_id = request.job_id or str(uuid.uuid4())
        aoi_id = request.aoi_id or str(uuid.uuid4())

        supabase_client.get_admin_client().table("timeline_collections").insert({
            "timeline_id": timeline_id,
            "job_id": job_id,
            "aoi_id": aoi_id,
            "date_start": request.date_start,
            "date_end": request.date_end,
            "collection_name": request.collection,
            "cloud_cover_max": request.cloud_cover_max,
            "status": "processing",
            "progress_percent": 10,
        }).execute()

        # Retrieve timeline
        scenes_by_year, ref_year = await TimelineProcessor.retrieve_timeline(
            connector,
            request.aoi_geojson,
            request.date_start,
            request.date_end,
            request.collection,
            request.cloud_cover_max,
        )

        # Store per-year imagery records
        for year, scene in scenes_by_year.items():
            supabase_client.get_admin_client().table("timeline_imagery").insert({
                "timeline_imagery_id": str(uuid.uuid4()),
                "timeline_id": timeline_id,
                "year": year,
                "acquisition_date": scene.get("acquisition_date"),
                "scene_id": scene.get("id"),
                "cloud_cover_percent": scene.get("cloud_cover_percent"),
                "status": "metadata_stored",
            }).execute()

        # Update collection
        supabase_client.get_admin_client().table("timeline_collections").update({
            "year_count": len(scenes_by_year),
            "reference_year": ref_year,
            "status": "completed",
            "progress_percent": 100,
        }).eq("timeline_id", timeline_id).execute()

        logger.info(f"Timeline created: {timeline_id} — {len(scenes_by_year)} years")

        return {
            "timeline_id": timeline_id,
            "years_count": len(scenes_by_year),
            "years": sorted(scenes_by_year.keys()),
            "reference_year": ref_year,
            "scenes": {str(y): s for y, s in scenes_by_year.items()},
            "status": "completed",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving timeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve timeline: {str(e)}")


@router.get("/{timeline_id}")
async def get_timeline(
    timeline_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Get a timeline collection with its per-year imagery."""
    from app.main import supabase_client

    try:
        col = (
            supabase_client.get_admin_client()
            .table("timeline_collections")
            .select("*")
            .eq("timeline_id", timeline_id)
            .single()
            .execute()
        )
        if not col.data:
            raise HTTPException(status_code=404, detail="Timeline not found")

        imagery = (
            supabase_client.get_admin_client()
            .table("timeline_imagery")
            .select("*")
            .eq("timeline_id", timeline_id)
            .order("year")
            .execute()
        )

        return {
            "timeline": col.data,
            "imagery": imagery.data or [],
            "metadata": {
                "total_years": len(imagery.data) if imagery.data else 0,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting timeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get timeline")


@router.get("/animation/{timeline_id}")
async def get_animation(
    timeline_id: str,
    format: str = "gif",
    user_id: str = Depends(get_current_user_id),
):
    """Get animation for a timeline."""
    from app.main import supabase_client

    try:
        anim = (
            supabase_client.get_admin_client()
            .table("timeline_animations")
            .select("*")
            .eq("timeline_id", timeline_id)
            .eq("format", format)
            .execute()
        )

        if not anim.data:
            raise HTTPException(status_code=404, detail="Animation not found")

        return {
            "animation_url": anim.data[0].get("cloudinary_url"),
            "format": format,
            "duration_seconds": anim.data[0].get("duration_seconds"),
            "frame_count": anim.data[0].get("frame_count"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting animation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get animation")
