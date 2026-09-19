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

        # Generate report
        from app.services.document_generator import DocumentGenerator
        from app.main import cloudinary_client
        
        generator = DocumentGenerator(supabase_client, cloudinary_client)
        doc_metadata = await generator.generate_markdown_report(job_id, user_id)
        
        # Insert into documents table
        new_doc = {
            "job_id": job_id,
            "doc_type": "analysis_report",
            "format": "md",
            "cloudinary_public_id": doc_metadata["cloudinary_public_id"],
            "url": doc_metadata["url"]
        }
        
        # Insert and return
        result = supabase_client.get_user_client().table("documents").insert(new_doc).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to save document metadata")
            
        doc = result.data[0]
        
        return {
            "document_id": doc.get("document_id"),
            "type": doc.get("doc_type"),
            "format": doc.get("format"),
            "url": f"/api/v1/documents/{doc.get('document_id')}",
            "created_at": doc.get("created_at")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


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
