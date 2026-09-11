# app/api/v1/terrain.py

"""
Terrain API endpoints — Phase 8

Endpoints:
  POST  /api/v1/terrain/generate-2d
  POST  /api/v1/terrain/generate-3d
  GET   /api/v1/terrain/statistics/{terrain_id}
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
import uuid

import numpy as np

from app.auth.dependencies import get_current_user_id
from app.terrain.processor import TerrainProcessor

logger = logging.getLogger("satquery")
router = APIRouter(prefix="/api/v1/terrain", tags=["terrain"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class Generate2DRequest(BaseModel):
    dem_data: List[List[float]]  # 2D array of elevation values
    job_id: Optional[str] = None
    dem_id: Optional[str] = None
    options: Optional[dict] = Field(
        default=None,
        description="Options: hillshade_azimuth, hillshade_altitude, hillshade_contrast, contour_interval",
    )


class Generate3DRequest(BaseModel):
    dem_data: List[List[float]]  # 2D array of elevation values
    aoi_bbox: List[float] = Field(..., min_length=4, max_length=4)
    texture_rgb: Optional[List[List[List[int]]]] = None  # (H, W, 3) RGB
    job_id: Optional[str] = None
    dem_id: Optional[str] = None
    options: Optional[dict] = Field(
        default=None,
        description="Options: elevation_exaggeration, mesh_resolution",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/generate-2d")
async def generate_2d_terrain(
    request: Generate2DRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Generate 2D terrain visualization (hillshade + contours).

    Accepts a 2D DEM array and returns statistics + terrain_id.
    """
    from app.main import supabase_client

    try:
        dem_array = np.array(request.dem_data, dtype=np.float32)

        hillshade, contours, stats = await TerrainProcessor.generate_2d_terrain(
            dem_array, request.options or {}
        )

        if hillshade.size == 0:
            raise HTTPException(status_code=500, detail="Hillshade generation failed")

        # Save to database
        terrain_id = str(uuid.uuid4())
        job_id = request.job_id or str(uuid.uuid4())

        record = {
            "terrain_id": terrain_id,
            "job_id": job_id,
            "dem_id": request.dem_id or str(uuid.uuid4()),
            "mode": "2d",
            "elevation_stats": stats,
            "processing_params": request.options or {},
            "status": "completed",
            "progress_percent": 100,
        }

        supabase_client.get_admin_client().table("terrain_assets").insert(record).execute()

        logger.info(f"2D terrain generated: {terrain_id}")

        return {
            "terrain_id": terrain_id,
            "mode": "2d",
            "hillshade_shape": list(hillshade.shape),
            "contour_shape": list(contours.shape),
            "statistics": stats,
            "status": "completed",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating 2D terrain: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate 2D terrain: {str(e)}")


@router.post("/generate-3d")
async def generate_3d_terrain(
    request: Generate3DRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Generate 3D terrain mesh (GLB).

    Accepts a 2D DEM array + optional RGB texture and returns mesh metadata.
    """
    from app.main import supabase_client

    try:
        dem_array = np.array(request.dem_data, dtype=np.float32)

        texture = None
        if request.texture_rgb:
            texture = np.array(request.texture_rgb, dtype=np.uint8)

        glb_bytes, metadata = await TerrainProcessor.generate_3d_terrain(
            dem_array, request.aoi_bbox, texture_rgb=texture, options=request.options or {}
        )

        if not glb_bytes:
            raise HTTPException(status_code=500, detail="Mesh generation failed")

        # Save to database
        terrain_id = str(uuid.uuid4())
        job_id = request.job_id or str(uuid.uuid4())

        record = {
            "terrain_id": terrain_id,
            "job_id": job_id,
            "dem_id": request.dem_id or str(uuid.uuid4()),
            "mode": "3d",
            "mesh_metadata": metadata,
            "bounds": metadata.get("bounds"),
            "elevation_stats": metadata.get("elevation_range_m"),
            "processing_params": request.options or {},
            "status": "completed",
            "progress_percent": 100,
        }

        supabase_client.get_admin_client().table("terrain_assets").insert(record).execute()

        logger.info(f"3D terrain generated: {terrain_id}")

        return {
            "terrain_id": terrain_id,
            "mode": "3d",
            "mesh_metadata": metadata,
            "status": "completed",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating 3D terrain: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate 3D terrain: {str(e)}")


@router.get("/statistics/{terrain_id}")
async def get_terrain_statistics(
    terrain_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Get terrain asset statistics."""
    from app.main import supabase_client

    try:
        result = (
            supabase_client.get_admin_client()
            .table("terrain_assets")
            .select("*")
            .eq("terrain_id", terrain_id)
            .single()
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Terrain asset not found")

        return {
            "terrain_id": terrain_id,
            "mode": result.data.get("mode"),
            "status": result.data.get("status"),
            "elevation_stats": result.data.get("elevation_stats"),
            "mesh_metadata": result.data.get("mesh_metadata"),
            "bounds": result.data.get("bounds"),
            "processing_params": result.data.get("processing_params"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting terrain statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get terrain statistics")
