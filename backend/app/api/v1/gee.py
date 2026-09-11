# app/api/v1/gee.py

"""
GEE API endpoints — Phase 7

Endpoints (per 6-9.md source of truth):
  POST  /api/v1/gee/query-imagery
  GET   /api/v1/gee/collections/{collection_id}
  GET   /api/v1/gee/imagery/{imagery_id}
  GET   /api/v1/gee/query-status/{collection_id}
  POST  /api/v1/gee/retrieve-dem
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
import uuid

from app.auth.dependencies import get_current_user_id
from app.config import settings

logger = logging.getLogger("satquery")
router = APIRouter(prefix="/api/v1/gee", tags=["gee"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class QueryImageryRequest(BaseModel):
    aoi: dict  # GeoJSON Polygon
    date_start: str  # YYYY-MM-DD
    date_end: str
    collections: List[str] = ["Sentinel-2"]
    cloud_cover_max: int = Field(default=20, ge=0, le=100)
    resolution_m: Optional[int] = None


class RetrieveDEMRequest(BaseModel):
    aoi: dict  # GeoJSON Polygon
    resolution_m: int = Field(default=30, ge=10, le=90)


# ---------------------------------------------------------------------------
# Lazy GEE connector singleton
# ---------------------------------------------------------------------------

_gee_connector = None
_gee_processor = None


def _get_gee_connector():
    """Get or create the GEEConnector singleton."""
    global _gee_connector
    if _gee_connector is None:
        from app.gee.connector import GEEConnector

        _gee_connector = GEEConnector(
            service_account_key_path=settings.gee_service_account_key_path,
            project_id=settings.gee_project_id,
        )
    return _gee_connector


def _get_gee_processor():
    """Get or create the GEEProcessor singleton."""
    global _gee_processor
    if _gee_processor is None:
        from app.gee.processor import GEEProcessor
        from app.main import cloudinary_client

        _gee_processor = GEEProcessor(cloudinary_client=cloudinary_client)
    return _gee_processor


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/query-imagery")
async def query_imagery(
    request: QueryImageryRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Query GEE for satellite imagery matching AOI, date range, and cloud cover.

    Maps to: POST /api/v1/gee/query-imagery (6-9.md)
    """
    from app.main import supabase_client

    connector = _get_gee_connector()
    processor = _get_gee_processor()

    # Authenticate if needed
    auth_ok = await connector.authenticate()
    if not auth_ok:
        raise HTTPException(
            status_code=503,
            detail="GEE authentication failed. Check service account credentials.",
        )

    try:
        # Create a collection record
        query_params = {
            "aoi": request.aoi,
            "date_start": request.date_start,
            "date_end": request.date_end,
            "collections": request.collections,
            "cloud_cover_max": request.cloud_cover_max,
        }

        collection_name = ", ".join(request.collections)
        job_id = str(uuid.uuid4())  # standalone query — no parent job

        collection_id = await processor.create_collection(
            job_id=job_id,
            user_id=user_id,
            query_params=query_params,
            collection_name=collection_name,
            supabase_client=supabase_client,
        )

        # Update status → querying
        await processor.update_collection_status(
            collection_id, "querying", supabase_client, progress_percent=10
        )

        # Query each requested collection
        all_scenes: List[dict] = []

        if "Sentinel-2" in request.collections:
            scenes = await connector.query_sentinel2(
                request.aoi, request.date_start, request.date_end,
                request.cloud_cover_max,
            )
            all_scenes.extend(scenes)

        if "Landsat-8" in request.collections or "Landsat-9" in request.collections:
            scenes = await connector.query_landsat(
                request.aoi, request.date_start, request.date_end,
                request.cloud_cover_max,
            )
            all_scenes.extend(scenes)

        # Store scene metadata
        await processor.update_collection_status(
            collection_id, "processing", supabase_client, progress_percent=50
        )

        asset_ids = await processor.store_scenes(
            all_scenes, collection_id, job_id, supabase_client
        )

        # Retrieve DEM
        dem_info = await connector.retrieve_dem(request.aoi, request.resolution_m or 30)
        dem_id = None
        if dem_info:
            from app.geospatial.aoi import AOIValidator
            bbox = AOIValidator.extract_bounds(request.aoi)
            dem_id = await processor.store_dem(
                dem_info, collection_id, job_id, supabase_client, bbox=bbox
            )

        # Mark complete
        await processor.update_collection_status(
            collection_id, "completed", supabase_client,
            progress_percent=100,
            results_count=len(all_scenes),
            scenes_retrieved=len(asset_ids),
        )

        logger.info(
            f"GEE query complete: {len(all_scenes)} scenes, "
            f"collection {collection_id}"
        )

        return {
            "collection_id": collection_id,
            "job_id": job_id,
            "status": "completed",
            "scenes_count": len(all_scenes),
            "scenes": all_scenes,
            "dem": dem_info,
            "dem_id": dem_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying imagery: {e}", exc_info=True)
        # Try to mark collection as failed
        try:
            await processor.update_collection_status(
                collection_id, "failed", supabase_client,
                error_message=str(e),
            )
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Failed to query imagery: {str(e)}")


@router.get("/collections/{collection_id}")
async def get_collection(
    collection_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """
    Get a GEE collection with its scenes and DEM.

    Maps to: GET /api/v1/gee/collections/{collection_id} (6-9.md)
    """
    from app.main import supabase_client

    try:
        # Get collection
        col = (
            supabase_client.get_admin_client()
            .table("gee_collections")
            .select("*")
            .eq("collection_id", collection_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        if not col.data:
            raise HTTPException(status_code=404, detail="Collection not found")

        # Get scenes
        scenes = (
            supabase_client.get_admin_client()
            .table("gee_assets")
            .select("*")
            .eq("collection_id", collection_id)
            .order("acquisition_date")
            .execute()
        )

        # Get DEM
        dem = (
            supabase_client.get_admin_client()
            .table("dem_assets")
            .select("*")
            .eq("collection_id", collection_id)
            .execute()
        )

        return {
            "collection": col.data,
            "imagery": scenes.data or [],
            "dem": dem.data[0] if dem.data else None,
            "metadata": {
                "total_scenes": len(scenes.data) if scenes.data else 0,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting collection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get collection")


@router.get("/imagery/{imagery_id}")
async def get_imagery(
    imagery_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """
    Get a single GEE imagery asset.

    Maps to: GET /api/v1/gee/imagery/{imagery_id} (6-9.md)
    """
    from app.main import supabase_client

    try:
        asset = (
            supabase_client.get_admin_client()
            .table("gee_assets")
            .select("*")
            .eq("gee_asset_id", imagery_id)
            .single()
            .execute()
        )

        if not asset.data:
            raise HTTPException(status_code=404, detail="Imagery not found")

        return {
            "imagery": asset.data,
            "bands": asset.data.get("bands"),
            "url": asset.data.get("cloudinary_url"),
            "metadata": {
                "source": asset.data.get("source"),
                "acquisition_date": asset.data.get("acquisition_date"),
                "cloud_cover_percent": asset.data.get("cloud_cover_percent"),
                "resolution_m": asset.data.get("resolution_m"),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting imagery: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get imagery")


@router.get("/query-status/{collection_id}")
async def query_status(
    collection_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """
    Get status of a GEE query collection.

    Maps to: GET /api/v1/gee/query-status/{collection_id} (6-9.md)
    """
    from app.main import supabase_client

    try:
        col = (
            supabase_client.get_admin_client()
            .table("gee_collections")
            .select("collection_id, status, progress_percent, results_count, scenes_retrieved, error_message")
            .eq("collection_id", collection_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )

        if not col.data:
            raise HTTPException(status_code=404, detail="Collection not found")

        return {
            "status": col.data.get("status"),
            "progress_percent": col.data.get("progress_percent"),
            "results_count": col.data.get("results_count"),
            "scenes_retrieved": col.data.get("scenes_retrieved"),
            "error": col.data.get("error_message"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get query status")


@router.post("/retrieve-dem")
async def retrieve_dem(
    request: RetrieveDEMRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Retrieve DEM for a given AOI.

    Maps to: POST /api/v1/gee/retrieve-dem (6-9.md)
    """
    from app.main import supabase_client

    connector = _get_gee_connector()

    auth_ok = await connector.authenticate()
    if not auth_ok:
        raise HTTPException(
            status_code=503,
            detail="GEE authentication failed. Check service account credentials.",
        )

    try:
        dem_info = await connector.retrieve_dem(request.aoi, request.resolution_m)

        if not dem_info:
            raise HTTPException(status_code=404, detail="DEM data not available for this AOI")

        return {
            "dem": dem_info,
            "status": "success",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving DEM: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve DEM")
