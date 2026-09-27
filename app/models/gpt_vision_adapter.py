"""GPT-4 Vision adapter for grounding and captioning."""

from __future__ import annotations

import base64
import json
import logging
import os
from typing import Any

from app.config import get_settings
from app.evidence.schema import (
    EvidenceSource,
    EvidenceType,
    Observation,
    ObservationStatus,
)
from app.models.base import BaseModelAdapter

logger = logging.getLogger(__name__)

# Try to import AzureOpenAI; if it fails, it will fail at predict time.
try:
    from openai import AzureOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class GPTVisionAdapter(BaseModelAdapter):
    """Adapter that uses GPT-4 Vision for grounding and captioning."""

    def validate_input(self, arguments: dict[str, Any]) -> tuple[bool, str]:
        if "asset_uri" not in arguments and "assets" not in arguments and "asset" not in arguments:
            return False, "GPT Vision requires an 'asset' or 'asset_uri'."
        return True, ""

    async def predict(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if not OPENAI_AVAILABLE:
            return {
                "_error": "OpenAI python package is not installed.",
                "_error_type": "ImportError",
                "_retryable": False,
            }

        settings = get_settings()
        api_key = settings.openai_api_key
        base_url = settings.openai_base_url
        model_name = settings.openai_model or "gpt-4.1-mini"

        if not api_key:
            return {
                "_error": "OpenAI API key not configured.",
                "_error_type": "ConfigurationError",
                "_retryable": False,
            }

        # Resolve asset URI
        asset_uri = arguments.get("asset_uri")
        if not asset_uri:
            asset_id = arguments.get("asset")
            state = arguments.get("_state")
            if state and asset_id:
                for a in state.input_assets:
                    if a.asset_id == asset_id:
                        asset_uri = a.uri
                        break

        # --- Load image bytes (supports both http URLs and local files) ---
        image_bytes: bytes | None = None
        if asset_uri and asset_uri.startswith("http"):
            import httpx
            try:
                async with httpx.AsyncClient(timeout=30) as http_client:
                    resp = await http_client.get(asset_uri)
                    resp.raise_for_status()
                    image_bytes = resp.content
            except Exception as e:
                return {
                    "_error": f"Failed to download image from {asset_uri}: {e}",
                    "_error_type": "DownloadError",
                    "_retryable": False,
                }
        else:
            if not asset_uri or not os.path.exists(asset_uri):
                return {
                    "_error": f"Asset URI not found or invalid: {asset_uri}",
                    "_error_type": "AssetNotFound",
                    "_retryable": False,
                }

            try:
                with open(asset_uri, "rb") as f:
                    image_bytes = f.read()
            except Exception as e:
                return {
                    "_error": f"Failed to read image: {e}",
                    "_error_type": "FileReadError",
                    "_retryable": False,
                }

        # --- Auto-convert TIFF/GeoTIFF to PNG for OpenAI Vision API ---
        # OpenAI Vision only accepts PNG/JPEG/GIF/WEBP. If the image is
        # a TIFF (common for satellite imagery), convert it to PNG first.
        try:
            from PIL import Image as _PILImage
            import io as _io
            _probe = _PILImage.open(_io.BytesIO(image_bytes))
            if _probe.format in ("TIFF", "MPO") or (
                asset_uri and any(ext in asset_uri.lower() for ext in (".tif", ".tiff"))
            ):
                logger.info("GPT Vision: auto-converting %s to PNG for API compatibility", _probe.format)
                import numpy as np
                arr = np.array(_probe)
                # Percentile stretch for 16-bit imagery
                if arr.dtype != np.uint8:
                    arr = arr.astype("float32")
                    lo = float(np.percentile(arr, 2))
                    hi = float(np.percentile(arr, 98))
                    if hi <= lo:
                        hi = lo + 1.0
                    arr = ((arr - lo) / (hi - lo) * 255.0).clip(0, 255).astype("uint8")
                if arr.ndim == 3 and arr.shape[-1] > 3:
                    arr = arr[..., :3]
                out_img = _PILImage.fromarray(arr).convert("RGB")
                buf = _io.BytesIO()
                out_img.save(buf, format="PNG")
                image_bytes = buf.getvalue()
        except Exception as conv_err:
            logger.warning("TIFF auto-conversion check failed (non-fatal): %s", conv_err)

        b64 = base64.b64encode(image_bytes).decode("utf-8")


        prompt = ""
        cap = arguments.get("_capability", "")
        
        if cap == "ground_region":
            prompt = (
                "You are an expert satellite/aerial image analyst.\n\n"
                "1. **Caption** – Write a rich, detailed caption describing the scene.\n"
                "2. **Object detection** – Identify ALL distinct buildings, structures, roads, "
                "and vegetation patches visible in the image. For each object return a "
                "bounding box as [ymin, xmin, ymax, xmax] where every coordinate is an "
                "integer on a 0-1000 scale (0 = top/left edge, 1000 = bottom/right edge).\n\n"
                "Return ONLY a JSON object – no markdown fences – with this schema:\n"
                "{\n"
                '  "caption": "...",\n'
                '  "objects": [\n'
                '    {"label": "large blue-roof warehouse", "box": [ymin, xmin, ymax, xmax]},\n'
                "    ...\n"
                "  ]\n"
                "}"
            )
        else:
            prompt = (
                "You are an expert satellite/aerial image analyst.\n"
                "Provide a detailed description of this image."
            )

        try:
            # Azure client (assuming base_url includes /openai/v1 or needs it stripped)
            azure_endpoint = base_url.replace("/openai/v1", "") if base_url else ""
            client_args = {"api_key": api_key}
            if azure_endpoint:
                client_args["azure_endpoint"] = azure_endpoint
                client_args["api_version"] = "2025-01-01-preview"
                client = AzureOpenAI(**client_args)
            else:
                from openai import OpenAI
                client = OpenAI(api_key=api_key)

            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{b64}"},
                            },
                        ],
                    }
                ],
                max_tokens=2000,
                temperature=0.2,
            )

            raw_text = response.choices[0].message.content.strip()
            
            # Clean markdown JSON block
            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[1]
                if raw_text.endswith("```"):
                    raw_text = raw_text[:-3]
            
            if cap == "ground_region":
                try:
                    data = json.loads(raw_text)
                    # Store raw bytes (not URL) so normalize_output can draw boxes synchronously
                    return {
                        "result": data,
                        "original_image": asset_uri,
                        "_image_bytes": image_bytes,  # raw bytes for PIL drawing
                    }
                except json.JSONDecodeError:
                    return {
                        "_error": f"Failed to parse GPT JSON output: {raw_text}",
                        "_error_type": "JSONDecodeError",
                        "_retryable": False,
                    }
            else:
                return {"result": {"caption": raw_text}}

        except Exception as e:
            return {
                "_error": str(e),
                "_error_type": type(e).__name__,
                "_retryable": True,
            }

    def normalize_output(
        self, raw: dict[str, Any], arguments: dict[str, Any]
    ) -> Observation:
        cap = arguments.get("_capability", "gpt_vision")

        if "_error" in raw:
            return Observation(
                source=EvidenceSource(capability=cap, model="GPT-4-Vision", backend="openai"),
                type=EvidenceType.ERROR,
                status=ObservationStatus.FAILURE,
                result={
                    "error": raw["_error"],
                    "error_type": raw.get("_error_type", "unknown"),
                    "retryable": raw.get("_retryable", False),
                },
                error_message=raw["_error"],
            )

        artifacts = []
        result = raw.get("result", {})
        
        if cap == "ground_region" and "objects" in result:
            from PIL import Image, ImageDraw, ImageFont
            from app.utils.upload import upload_image_base64
            import io
            
            try:
                # Draw boxes — use pre-loaded bytes if available (avoids opening URL as file path)
                import io as _io
                _img_bytes = raw.get("_image_bytes")
                if _img_bytes:
                    img = Image.open(_io.BytesIO(_img_bytes)).convert("RGB")
                elif raw.get("original_image", "").startswith("http"):
                    import httpx as _httpx
                    _resp = _httpx.get(raw["original_image"], timeout=30)
                    _resp.raise_for_status()
                    img = Image.open(_io.BytesIO(_resp.content)).convert("RGB")
                else:
                    img = Image.open(raw["original_image"]).convert("RGB")
                W, H = img.size
                draw = ImageDraw.Draw(img)
                
                COLORS = [
                    "#FF3B30", "#34C759", "#00C7BE", "#FF9500", "#AF52DE",
                    "#FF2D55", "#5AC8FA", "#FFCC00", "#30D158", "#64D2FF",
                ]
                
                for idx, obj in enumerate(result["objects"]):
                    ymin, xmin, ymax, xmax = obj.get("box", [0, 0, 0, 0])
                    px = (
                        int(xmin / 1000 * W),
                        int(ymin / 1000 * H),
                        int(xmax / 1000 * W),
                        int(ymax / 1000 * H),
                    )
                    color = COLORS[idx % len(COLORS)]
                    lw = max(2, int(min(W, H) * 0.006))
                    draw.rectangle(px, outline=color, width=lw)
                
                    label = obj.get("label", "")
                    try:
                        font = ImageFont.truetype("arial.ttf", max(10, int(min(W, H) * 0.025)))
                    except OSError:
                        font = ImageFont.load_default()
                
                    text_bbox = draw.textbbox((0, 0), label, font=font)
                    tw, th = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
                    tx, ty = px[0], max(0, px[1] - th - 4)
                    draw.rectangle([tx, ty, tx + tw + 4, ty + th + 4], fill=color)
                    draw.text((tx + 2, ty + 2), label, fill="white", font=font)
                
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                b64_img = base64.b64encode(buf.getvalue()).decode("utf-8")
                url = upload_image_base64(b64_img, "gpt_grounded")
                if url:
                    artifacts.append(url)
                    result["grounded_image_uri"] = url
            except Exception as e:
                logger.error(f"Failed to draw GPT grounding boxes: {e}")

        return Observation(
            source=EvidenceSource(
                capability=cap,
                model="GPT-4-Vision",
                version="latest",
                backend="openai",
            ),
            type=EvidenceType.GROUNDING if cap == "ground_region" else EvidenceType.CAPTION,
            status=ObservationStatus.SUCCESS,
            result=result,
            artifacts=artifacts,
        )
