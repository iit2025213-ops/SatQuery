"""TerraMind adapter.

Multimodal foundation model for EO tasks.
"""

from __future__ import annotations

import logging
from typing import Any

from app.config import get_settings
from app.evidence.schema import (
    EvidenceSource,
    EvidenceType,
    Observation,
    ObservationStatus,
)
from app.models.base import BaseModelAdapter
from app.models.client import RemoteModelError
from app.models.terramind.client import TerraMindClient

logger = logging.getLogger(__name__)


class TerraMindAdapter(BaseModelAdapter):
    """Adapter for IBM TerraMind multimodal foundation model."""

    def validate_input(self, arguments: dict[str, Any]) -> tuple[bool, str]:
        if "asset_uri" not in arguments and "assets" not in arguments:
            return False, "TerraMind requires an 'asset_uri' or 'assets' list."
        return True, ""

    async def predict(self, arguments: dict[str, Any]) -> dict[str, Any]:
        settings = get_settings()
        client = TerraMindClient(
            endpoint=settings.terramind_endpoint,
            api_key=settings.terramind_api_key,
            timeout_seconds=settings.terramind_timeout_seconds,
        )

        assets = []
        if "assets" in arguments:
            assets = arguments["assets"]
        elif "asset_uri" in arguments:
            assets.append({
                "uri": arguments["asset_uri"],
                "modality": arguments.get("modality", "S2L2A")
            })

        payload = {
            "assets": assets,
            "task": arguments.get("task", "segmentation"),
            "num_classes": int(arguments.get("num_classes", 3)),
            "clustering_method": arguments.get("clustering_method", "pca_kmeans"),
        }

        try:
            res = await client.infer(payload)
            
            # Post-process the mask to make it visible!
            result_data = res.get("result", {})
            mask_b64 = result_data.get("mask_base64")
            if mask_b64:
                import base64
                import io
                import numpy as np
                from PIL import Image

                try:
                    # Decode the black image
                    img_data = base64.b64decode(mask_b64)
                    img = Image.open(io.BytesIO(img_data))
                    arr = np.array(img)
                    
                    # Create a colorful palette for up to 10 clusters
                    palette = np.array([
                        [255, 99, 71],   # Tomato Red
                        [60, 179, 113],  # Medium Sea Green
                        [30, 144, 255],  # Dodger Blue
                        [255, 215, 0],   # Gold
                        [138, 43, 226],  # Blue Violet
                        [255, 140, 0],   # Dark Orange
                        [0, 206, 209],   # Dark Turquoise
                        [255, 105, 180], # Hot Pink
                        [139, 69, 19],   # Saddle Brown
                        [112, 128, 144], # Slate Gray
                    ], dtype=np.uint8)
                    
                    # Map cluster IDs to colors
                    color_arr = palette[arr % len(palette)]
                    
                    # Encode back to Base64
                    color_img = Image.fromarray(color_arr)
                    buf = io.BytesIO()
                    color_img.save(buf, format="PNG")
                    res["result"]["mask_base64"] = base64.b64encode(buf.getvalue()).decode("utf-8")
                except Exception as e:
                    logger.warning(f"Failed to colorize TerraMind mask: {e}")

            return res
        except RemoteModelError as exc:
            return {
                "_error": str(exc),
                "_error_type": type(exc).__name__,
                "_retryable": exc.retryable,
            }

    def normalize_output(
        self, raw: dict[str, Any], arguments: dict[str, Any]
    ) -> Observation:
        cap = arguments.get("_capability", "perform_multimodal_analysis")

        if "_error" in raw:
            return Observation(
                source=EvidenceSource(capability=cap, model="TerraMind", backend="remote"),
                type=EvidenceType.ERROR,
                status=ObservationStatus.FAILURE,
                result={
                    "error": raw["_error"],
                    "error_type": raw.get("_error_type", "unknown"),
                    "retryable": raw.get("_retryable", False),
                },
                error_message=raw["_error"],
            )

        return Observation(
            source=EvidenceSource(
                capability=cap,
                model=raw.get("model", "TerraMind"),
                version=raw.get("version", ""),
                backend="remote",
            ),
            type=EvidenceType.IMAGE_BASE64 if "mask_base64" in raw.get("result", {}) else EvidenceType.METADATA,
            status=ObservationStatus.SUCCESS,
            result=raw.get("result", raw),
            confidence=raw.get("confidence"),
        )
