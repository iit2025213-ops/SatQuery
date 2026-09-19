# app/api/v1/assets.py

from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Form
from typing import Optional
import logging
import uuid

from app.auth.dependencies import get_current_user_id
from app.api.v1.schemas import UploadAssetResponse, AssetMetadata

logger = logging.getLogger("satquery")
router = APIRouter(prefix="/api/v1", tags=["assets"])


import tempfile
import os

@router.post("/assets", response_model=UploadAssetResponse)
async def upload_asset(
    file: UploadFile = File(...),
    modality: str = Form("optical"),
    acquisition_date: Optional[str] = Form(None),
    user_id: str = Depends(get_current_user_id)
):
    """Upload satellite image asset"""

    from app.main import supabase_client, cloudinary_client

    asset_id = str(uuid.uuid4())

    try:
        # Read file
        contents = await file.read()

        # Save to temp file since Cloudinary SDK needs a real file path
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            temp_file.write(contents)
            temp_path = temp_file.name

        try:
            # Upload to Cloudinary
            result = await cloudinary_client.upload_artifact(
                file_path=temp_path,
                artifact_type="original_image",
                job_id="assets",
                metadata={"asset_id": asset_id}
            )
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)

        # Create asset record
        asset_data = {
            "asset_id": asset_id,
            "user_id": user_id,
            "filename": file.filename,
            "file_url": result["url"],
            "file_size_bytes": len(contents),
            "modality": modality,
            "acquisition_date": acquisition_date,
            "upload_status": "ready"
        }

        supabase_client.get_user_client().table("assets").insert(asset_data).execute()

        logger.info(f"Asset uploaded: {asset_id} by user {user_id}")

        return UploadAssetResponse(
            asset_id=asset_id,
            status="ready",
            metadata=AssetMetadata(
                modality=modality,
                acquisition_date=acquisition_date
            ),
            file_url=result["url"]
        )

    except Exception as e:
        logger.error(f"Error uploading asset: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload asset")


@router.get("/assets/{asset_id}")
async def get_asset(
    asset_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get asset details"""

    from app.main import supabase_client

    try:
        asset = supabase_client.get_user_client().table("assets").select("*").eq("asset_id", asset_id).eq("user_id", user_id).single().execute()

        if not asset.data:
            raise HTTPException(status_code=404, detail="Asset not found")

        return asset.data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting asset: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get asset")


@router.get("/assets")
async def list_assets(
    user_id: str = Depends(get_current_user_id),
    job_id: Optional[str] = None,
    status: Optional[str] = None
):
    """List user's assets"""

    from app.main import supabase_client

    try:
        query = supabase_client.get_user_client().table("assets").select("*").eq("user_id", user_id)

        if job_id:
            query = query.eq("job_id", job_id)
        if status:
            query = query.eq("upload_status", status)

        assets = query.order("created_at", desc=True).execute()

        return {
            "assets": assets.data,
            "count": len(assets.data)
        }

    except Exception as e:
        logger.error(f"Error listing assets: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list assets")


@router.delete("/assets/{asset_id}")
async def delete_asset(
    asset_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Delete an asset"""

    from app.main import supabase_client, cloudinary_client

    try:
        asset = supabase_client.get_user_client().table("assets").select("*").eq("asset_id", asset_id).eq("user_id", user_id).single().execute()

        if not asset.data:
            raise HTTPException(status_code=404, detail="Asset not found")

        # Delete from Cloudinary if applicable
        if asset.data.get("file_url"):
            try:
                await cloudinary_client.delete_artifact(asset.data["file_url"])
            except Exception:
                logger.warning(f"Failed to delete asset from Cloudinary: {asset_id}")

        # Delete from database
        supabase_client.get_user_client().table("assets").delete().eq("asset_id", asset_id).execute()

        logger.info(f"Asset deleted: {asset_id}")

        return {"message": "Deleted", "asset_id": asset_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting asset: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete asset")
