# app/api/v1/jobs.py

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional
import logging

from app.auth.dependencies import get_current_user_id
from app.api.v1.schemas import JobStatusResponse, JobProgress

logger = logging.getLogger("satquery")
router = APIRouter(prefix="/api/v1", tags=["jobs"])


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get status of a job"""

    from app.main import supabase_client

    try:
        job = supabase_client.get_user_client().table("jobs").select("*").eq("job_id", job_id).eq("user_id", user_id).single().execute()

        if not job.data:
            raise HTTPException(status_code=404, detail="Job not found")

        job_data = job.data

        return JobStatusResponse(
            job_id=job_data["job_id"],
            status=job_data["status"],
            query=job_data["query"],
            progress=JobProgress(
                completed_steps=job_data.get("current_step", 0),
                total_steps=None
            ),
            final_answer=job_data.get("final_answer"),
            confidence=job_data.get("confidence"),
            created_at=job_data["created_at"],
            updated_at=job_data["updated_at"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get job")


@router.get("/jobs")
async def list_jobs(
    user_id: str = Depends(get_current_user_id),
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """List user's jobs"""

    from app.main import supabase_client

    try:
        query = supabase_client.get_user_client().table("jobs").select("*").eq("user_id", user_id)

        if status:
            query = query.eq("status", status)

        jobs = query.order("created_at", desc=True).range(offset, offset + limit).execute()

        return {
            "jobs": jobs.data,
            "total": len(jobs.data),
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error listing jobs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list jobs")


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Cancel a running job"""

    from app.main import supabase_client

    try:
        job = supabase_client.get_user_client().table("jobs").select("*").eq("job_id", job_id).eq("user_id", user_id).single().execute()

        if not job.data:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.data["status"] not in ["queued", "running"]:
            raise HTTPException(status_code=400, detail="Job cannot be cancelled")

        supabase_client.get_user_client().table("jobs").update({"status": "cancelled"}).eq("job_id", job_id).execute()

        logger.info(f"Job cancelled: {job_id}")

        return {"status": "cancelled", "job_id": job_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling job: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cancel job")


@router.get("/jobs/{job_id}/evidence")
async def get_job_evidence(
    job_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get evidence trail for a job"""

    from app.main import supabase_client

    try:
        # Verify user owns job
        job = supabase_client.get_user_client().table("jobs").select("user_id").eq("job_id", job_id).single().execute()

        if not job.data or job.data["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        evidence = supabase_client.get_user_client().table("evidence").select("*").eq("job_id", job_id).execute()
        observations = supabase_client.get_user_client().table("observations").select("*").eq("job_id", job_id).execute()

        return {
            "job_id": job_id,
            "evidence": evidence.data,
            "observations": observations.data,
            "observations_count": len(observations.data)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting evidence: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get evidence")
