# app/storage/cloudinary_client.py

import cloudinary
import cloudinary.uploader
import cloudinary.api
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("satquery")

class CloudinaryClient:
    """Wrapper for Cloudinary API"""
    
    def __init__(self, cloud_name: str, api_key: str, api_secret: str, upload_folder: str = "satquery-ai"):
        """Initialize Cloudinary"""
        self.cloud_name = cloud_name
        self.api_key = api_key
        self.api_secret = api_secret
        self.upload_folder = upload_folder
        
        # Configure cloudinary
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret
        )
        
        logger.info(f"Cloudinary initialized (folder: {upload_folder})")
    
    async def upload_artifact(self, file_path: str, artifact_type: str, job_id: str, metadata: dict = None) -> dict:
        """Upload artifact to Cloudinary"""
        try:
            public_id = f"{self.upload_folder}/{job_id}/{artifact_type}/{datetime.now().timestamp()}"
            
            # Determine resource type
            if artifact_type in ["change_mask", "change_map", "visualization"]:
                resource_type = "image"
                format_override = "png" if artifact_type in ["change_map", "visualization"] else "tif"
            elif artifact_type in ["geojson", "statistics", "analysis_json"]:
                resource_type = "raw"
                format_override = "json"
            else:
                resource_type = "auto"
                format_override = None
            
            # Upload file
            response = cloudinary.uploader.upload(
                file_path,
                public_id=public_id,
                resource_type=resource_type,
                overwrite=True,
                tags=[job_id, artifact_type],
                metadata=metadata or {}
            )
            
            logger.info(f"Uploaded artifact: {artifact_type} to {public_id}")
            
            return {
                "artifact_id": response.get("public_id"),
                "url": response.get("secure_url"),
                "cloudinary_public_id": response.get("public_id"),
                "file_size_bytes": response.get("bytes"),
                "format": response.get("format")
            }
        
        except Exception as e:
            logger.error(f"Failed to upload artifact: {e}")
            raise
    
    def get_signed_url(self, public_id: str, expiration_minutes: int = 60) -> str:
        """Generate signed URL for artifact"""
        expiration_time = datetime.utcnow() + timedelta(minutes=expiration_minutes)
        
        signed_url = cloudinary.utils.cloudinary_url(
            public_id,
            sign_url=True,
            type="authenticated",
            expires_at=int(expiration_time.timestamp())
        )
        
        return signed_url[0]
    
    async def delete_artifact(self, public_id: str) -> bool:
        """Delete artifact from Cloudinary"""
        try:
            cloudinary.uploader.destroy(public_id)
            logger.info(f"Deleted artifact: {public_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete artifact: {e}")
            raise
