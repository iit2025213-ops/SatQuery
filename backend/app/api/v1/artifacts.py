# app/api/v1/artifacts.py

from fastapi import APIRouter, HTTPException, status, Depends
import logging

from app.auth.dependencies import get_current_user_id

logger = logging.getLogger("satquery")
router = APIRouter(prefix="/api/v1", tags=["artifacts"])


@router.get("/artifacts/{artifact_id}")
async def get_artifact(
    artifact_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get artifact with signed URL"""

    from app.main import supabase_client, cloudinary_client

    try:
        # Verify user owns this artifact via the parent job
        artifact = supabase_client.get_user_client().table("artifacts").select("*, jobs(user_id)").eq("artifact_id", artifact_id).single().execute()

        if not artifact.data or artifact.data["jobs"]["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        artifact_data = artifact.data

        # Generate signed URL
        signed_url = cloudinary_client.get_signed_url(
            artifact_data["cloudinary_public_id"],
            expiration_minutes=60
        )

        return {
            "artifact_id": artifact_id,
            "type": artifact_data["artifact_type"],
            "format": artifact_data["format"],
            "url": signed_url,
            "created_at": artifact_data["created_at"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting artifact: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get artifact")


@router.get("/jobs/{job_id}/artifacts")
async def list_job_artifacts(
    job_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """List all artifacts for a job"""

    from app.main import supabase_client

    try:
        # Verify user owns job
        job = supabase_client.get_user_client().table("jobs").select("user_id").eq("job_id", job_id).single().execute()

        if not job.data or job.data["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        artifacts = supabase_client.get_user_client().table("artifacts").select("*").eq("job_id", job_id).execute()

        return {
            "job_id": job_id,
            "artifacts": artifacts.data,
            "count": len(artifacts.data)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing artifacts: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list artifacts")


@router.delete("/artifacts/{artifact_id}")
async def delete_artifact(
    artifact_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Delete an artifact"""

    from app.main import supabase_client, cloudinary_client

    try:
        artifact = supabase_client.get_user_client().table("artifacts").select("*, jobs(user_id)").eq("artifact_id", artifact_id).single().execute()

        if not artifact.data or artifact.data["jobs"]["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        # Delete from Cloudinary
        if artifact.data.get("cloudinary_public_id"):
            await cloudinary_client.delete_artifact(artifact.data["cloudinary_public_id"])

        # Delete from database
        supabase_client.get_user_client().table("artifacts").delete().eq("artifact_id", artifact_id).execute()

        logger.info(f"Artifact deleted: {artifact_id}")

        return {"message": "Deleted", "artifact_id": artifact_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting artifact: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete artifact")
