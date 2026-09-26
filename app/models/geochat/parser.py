"""GeoChat response parser and visualizer."""

import os
import re
import io
import base64
import tempfile
from typing import Optional
import logging

from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)


def annotate_image(image_uri: str, response_text: str) -> Optional[str]:
    """Parse bounding boxes [ymin, xmin, ymax, xmax] from text and draw them.
    
    Expects normalized coordinates on a 0-100 scale.
    Uploads annotated image to Cloudinary and returns the cloud URL.
    Returns None if no boxes found or annotation fails.
    """
    pattern1 = r"\[(\d{1,3}),\s*(\d{1,3}),\s*(\d{1,3}),\s*(\d{1,3})\]"
    pattern2 = r"\[(\d{1,3})<(\d{1,3})<(\d{1,3})<(\d{1,3})\]"
    pattern3 = r"\{<(\d{1,3})<(\d{1,3})<(\d{1,3})<(\d{1,3})>\|(?:[^}]+)\}"
    
    matches = re.findall(pattern1, response_text)
    if not matches:
        matches = re.findall(pattern2, response_text)
    if not matches:
        matches = re.findall(pattern3, response_text)
        
    if not matches:
        return None

    try:
        # Load the image from URL or local path
        if image_uri.startswith("http://") or image_uri.startswith("https://"):
            import httpx
            resp = httpx.get(image_uri, timeout=30)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        else:
            img = Image.open(image_uri).convert("RGB")
            
        width, height = img.size
        draw = ImageDraw.Draw(img)
        
        colors = ["red", "lime", "cyan", "magenta", "yellow"]
        
        for idx, match in enumerate(matches):
            ymin, xmin, ymax, xmax = map(int, match)
            
            # Convert 0-100 scale to actual pixel coordinates
            # GeoChat format is [ymin, xmin, ymax, xmax]
            px_ymin = int((ymin / 100.0) * height)
            px_xmin = int((xmin / 100.0) * width)
            px_ymax = int((ymax / 100.0) * height)
            px_xmax = int((xmax / 100.0) * width)
            
            color = colors[idx % len(colors)]
            line_width = max(2, int(min(width, height) * 0.005))
            draw.rectangle(
                [px_xmin, px_ymin, px_xmax, px_ymax],
                outline=color,
                width=line_width
            )

        # Save to bytes and upload to Cloudinary
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64_img = base64.b64encode(buf.getvalue()).decode("utf-8")
        
        try:
            from app.utils.upload import upload_image_base64
            cloud_url = upload_image_base64(b64_img, prefix="geochat_bbox")
            if cloud_url:
                return cloud_url
        except Exception as upload_err:
            logger.warning("Cloudinary upload failed for GeoChat annotation: %s", upload_err)

        # Fallback: write to temp file if Cloudinary fails
        fd, out_path = tempfile.mkstemp(suffix=".png", prefix="geochat_bbox_")
        os.close(fd)
        img.save(out_path, format="PNG")
        return out_path
        
    except Exception as e:
        logger.error("[GeoChat Parser] Failed to annotate image: %s", e)
        return None
