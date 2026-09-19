# app/api/v1/queries.py

from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from datetime import datetime
from typing import Optional
import logging
import uuid

from app.auth.dependencies import get_current_user_id
from app.api.v1.schemas import SubmitQueryRequest, SubmitQueryResponse

logger = logging.getLogger("satquery")
router = APIRouter(prefix="/api/v1", tags=["queries"])


@router.post("/queries", response_model=SubmitQueryResponse, status_code=status.HTTP_201_CREATED)
async def submit_query(
    request: SubmitQueryRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id)
):
    """Submit a new satellite analysis query"""

    from app.main import supabase_client
    from app.geospatial.aoi import AOIValidator, AOICalculator

    job_id = str(uuid.uuid4())

    # AOI-related variables (populated if AOI is provided)
    aoi_bbox = None
    aoi_area_km2 = None

    try:
        # Validate assets exist and belong to user
        for asset_id in request.asset_ids:
            asset = supabase_client.get_user_client().table("assets").select("*").eq("asset_id", asset_id).eq("user_id", user_id).single().execute()
            if not asset.data:
                raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")

        # Validate AOI geometry first (no DB writes yet)
        if request.aoi:
            aoi_dict = request.aoi.model_dump()

            is_valid, errors = AOIValidator.validate_geojson(aoi_dict)
            if not is_valid:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid AOI: {'; '.join(errors)}"
                )

            aoi_bbox = AOIValidator.extract_bounds(aoi_dict)
            area_m2, aoi_area_km2 = AOICalculator.calculate_area(aoi_dict)
            centroid = AOICalculator.calculate_centroid(aoi_dict)

            size_ok, size_err = AOIValidator.check_size_limit(aoi_area_km2)
            if not size_ok:
                raise HTTPException(status_code=400, detail=size_err)

        # Create job FIRST so that job_id exists before the AOI FK reference
        job_data = {
            "job_id": job_id,
            "user_id": user_id,
            "query": request.query,
            "status": "queued",
            "aoi": request.aoi.model_dump() if request.aoi else None,
            "temporal_start": request.temporal.start if request.temporal else None,
            "temporal_end": request.temporal.end if request.temporal else None,
            "options": request.options.model_dump() if request.options else {},
            "agent_state": {
                "job_id": job_id,
                "user_request": request.query,
                "input_assets": request.asset_ids,
                "aoi": request.aoi.model_dump() if request.aoi else None,
                "aoi_area_km2": aoi_area_km2,
                "aoi_bbox": aoi_bbox,
                "observations": [],
                "evidence": [],
                "artifacts": []
            }
        }

        supabase_client.get_user_client().table("jobs").insert(job_data).execute()
        logger.info(f"Job created: {job_id} for user {user_id}")

        # NOW persist AOI to aois table (job_id already exists in jobs)
        if request.aoi:
            aoi_id = str(uuid.uuid4())
            supabase_client.get_admin_client().table("aois").insert({
                "aoi_id": aoi_id,
                "job_id": job_id,
                "user_id": user_id,
                "geojson": aoi_dict,
                "bbox": aoi_bbox,
                "area_m2": area_m2,
                "area_km2": aoi_area_km2,
                "centroid": list(centroid) if centroid else None,
                "validation_status": "valid",
                "source": "drawn",
            }).execute()
            logger.info(f"AOI saved: {aoi_id} for job {job_id}")

        # Fire the GEE background worker
        if request.aoi:
            from app.workers.gee_worker import run_gee_analysis
            from app.main import supabase_client as sc, cloudinary_client as cc
            background_tasks.add_task(
                run_gee_analysis,
                job_id=job_id,
                aoi_geojson=request.aoi.model_dump(),
                user_id=user_id,
                query_text=request.query,
                supabase_client=sc,
                cloudinary_client=cc,
            )
            logger.info(f"GEE worker queued for job {job_id}")

        return SubmitQueryResponse(
            job_id=job_id,
            status="queued",
            created_at=datetime.utcnow()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating job: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create job")

