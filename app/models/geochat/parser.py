"""GeoChat response parser and visualizer."""

import os
import re
import tempfile
from typing import Optional

from PIL import Image, ImageDraw


def annotate_image(image_uri: str, response_text: str) -> Optional[str]:
    """Parse bounding boxes [ymin, xmin, ymax, xmax] from text and draw them.
    
    Expects normalized coordinates on a 0-100 scale.
    Returns the path to the annotated temporary image, or None if no boxes found.
    """
    # Regex to find boxes formatted as [ymin, xmin, ymax, xmax] OR [ymin><xmin><ymax><xmax]
    import re
    # Match either format
    pattern = r"\[\s*(\d{1,3})\s*(?:,\|><)\s*(\d{1,3})\s*(?:,\|><)\s*(\d{1,3})\s*(?:,\|><)\s*(\d{1,3})\s*\]"
    # Wait, the above regex is slightly risky with literals. Let's make it simpler:
    pattern1 = r"\[(\d{1,3}),\s*(\d{1,3}),\s*(\d{1,3}),\s*(\d{1,3})\]"
    pattern2 = r"\[(\d{1,3})><(\d{1,3})><(\d{1,3})><(\d{1,3})\]"
    
    matches = re.findall(pattern1, response_text)
    if not matches:
        matches = re.findall(pattern2, response_text)
        
    if not matches:
        return None
        # Load the image
        if image_uri.startswith("http://") or image_uri.startswith("https://"):
            import requests
            from io import BytesIO
            resp = requests.get(image_uri, timeout=30)
            resp.raise_for_status()
            img = Image.open(BytesIO(resp.content)).convert("RGB")
        else:
            img = Image.open(image_uri).convert("RGB")
            
        width, height = img.size
        draw = ImageDraw.Draw(img)
        
        # We will cycle through a few vibrant colors for multiple boxes
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
            
            # Draw the rectangle (outline width scales with image size, min 2)
            line_width = max(2, int(min(width, height) * 0.005))
            draw.rectangle(
                [px_xmin, px_ymin, px_xmax, px_ymax],
                outline=color,
                width=line_width
            )
            
        # Save the annotated image to a temporary file
        fd, out_path = tempfile.mkstemp(suffix=".png", prefix="geochat_bbox_")
        os.close(fd)
        
        img.save(out_path, format="PNG")
        return out_path
        
    except Exception as e:
        print(f"[GeoChat Parser] Failed to annotate image: {e}")
        return None
