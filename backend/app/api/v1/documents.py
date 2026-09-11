# app/api/v1/documents.py

from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime
import logging
import uuid

from app.auth.dependencies import get_current_user_id

logger = logging.getLogger("satquery")
router = APIRouter(prefix="/api/v1", tags=["documents"])


@router.post("/jobs/{job_id}/generate-report")
async def generate_report(
    job_id: str,
    format: str = "pdf",  # pdf, docx, json
    user_id: str = Depends(get_current_user_id)
):
    """Generate report from job results"""

    from app.main import supabase_client

    try:
        # Verify user owns job
        job = supabase_client.get_user_client().table("jobs").select("*").eq("job_id", job_id).eq("user_id", user_id).single().execute()

        if not job.data:
            raise HTTPException(status_code=404, detail="Job not found")

        # TODO: Generate report (implement in MEGAPROMPT 10)

        return {
            "document_id": str(uuid.uuid4()),
            "type": "analysis_report",
            "format": format,
            "url": f"/api/v1/documents/{uuid.uuid4()}",
            "created_at": datetime.utcnow()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate report")


@router.get("/jobs/{job_id}/documents")
async def list_job_documents(
    job_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """List all documents for a job"""

    from app.main import supabase_client

    try:
        # Verify user owns job
        job = supabase_client.get_user_client().table("jobs").select("user_id").eq("job_id", job_id).single().execute()

        if not job.data or job.data["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        documents = supabase_client.get_user_client().table("documents").select("*").eq("job_id", job_id).execute()

        return {
            "job_id": job_id,
            "documents": documents.data,
            "count": len(documents.data)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list documents")


@router.get("/documents/{document_id}")
async def get_document(
    document_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get a document with signed URL"""

    from app.main import supabase_client, cloudinary_client

    try:
        document = supabase_client.get_user_client().table("documents").select("*, jobs(user_id)").eq("document_id", document_id).single().execute()

        if not document.data or document.data["jobs"]["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        doc_data = document.data

        # Generate signed URL
        signed_url = cloudinary_client.get_signed_url(
            doc_data["cloudinary_public_id"],
            expiration_minutes=60
        )

        return {
            "document_id": document_id,
            "type": doc_data["doc_type"],
            "format": doc_data["format"],
            "url": signed_url,
            "created_at": doc_data["created_at"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get document")
