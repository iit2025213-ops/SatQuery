"""Cloudinary upload utility."""

import logging
import base64
import os
import uuid
from typing import Optional

try:
    import cloudinary
    import cloudinary.uploader
    CLOUDINARY_AVAILABLE = True
except ImportError:
    CLOUDINARY_AVAILABLE = False

from app.config import get_settings

logger = logging.getLogger(__name__)

_cloudinary_configured = False


def _ensure_cloudinary_configured():
    global _cloudinary_configured
    if _cloudinary_configured:
        return

    settings = get_settings()
    if not settings.cloudinary_cloud_name:
        return

    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
    )
    _cloudinary_configured = True


def upload_image_base64(b64_data: str, prefix: str = "img") -> Optional[str]:
    """Upload a base64 encoded image to Cloudinary and return the secure URL.
    
    If Cloudinary is not configured or not installed, returns None.
    """
    if not CLOUDINARY_AVAILABLE:
        logger.warning("Cloudinary not installed. Cannot upload image.")
        return None

    settings = get_settings()
    if not settings.cloudinary_cloud_name:
        logger.warning("Cloudinary cloud_name not set. Cannot upload image.")
        return None

    _ensure_cloudinary_configured()

    try:
        # Generate a unique public ID
        public_id = f"{prefix}_{uuid.uuid4().hex[:8]}"
        
        # Ensure base64 string is formatted as data URI if it's not already
        if not b64_data.startswith("data:image"):
            b64_data = f"data:image/png;base64,{b64_data}"
            
        logger.info(f"Uploading image {public_id} to Cloudinary...")
        
        upload_kwargs = {
            "public_id": public_id,
            "folder": settings.cloudinary_upload_folder,
        }
        if settings.cloudinary_upload_preset:
            upload_kwargs["upload_preset"] = settings.cloudinary_upload_preset
            
        result = cloudinary.uploader.upload(b64_data, **upload_kwargs)
        
        url = result.get("secure_url")
        logger.info(f"Image uploaded successfully: {url}")
        return url
    except Exception as e:
        logger.error(f"Failed to upload image to Cloudinary: {e}", exc_info=True)
        return None


def upload_image_file(file_path: str, prefix: str = "img") -> Optional[str]:
    """Upload a local file to Cloudinary and return the secure URL."""
    if not os.path.exists(file_path):
        logger.warning(f"File {file_path} does not exist.")
        return None
        
    try:
        with open(file_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return upload_image_base64(b64, prefix)
    except Exception as e:
        logger.error(f"Failed to read file for Cloudinary upload: {e}")
        return None
