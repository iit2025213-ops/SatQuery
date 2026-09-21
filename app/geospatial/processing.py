"""Image processing tools for deterministic operations.

Deterministic operations like image normalization.
"""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Any

logger = logging.getLogger(__name__)

try:
    import numpy as np
    import rasterio
except ImportError:
    np = None
    rasterio = None

from app.evidence.schema import (
    EvidenceSource,
    EvidenceType,
    Observation,
    ObservationStatus,
)
from app.models.base import BaseModelAdapter


def create_visual_preview(input_uri: str, output_uri: str | None = None) -> dict[str, Any]:
    """Deterministically generate an 8-bit visual preview using 2nd/98th percentiles.
    
    This is for visualization ONLY. It is NOT generic geospatial normalization.
    Model-specific ML preprocessing belongs inside specialist model adapters.
    
    If output_uri is not provided, writes to a temporary file. Never overwrites source.
    """
    if rasterio is None or np is None:
        return {"error": "rasterio or numpy not installed"}

    if not os.path.exists(input_uri) and not input_uri.startswith("mock://"):
        return {"error": f"Input file not found: {input_uri}"}
        
    if input_uri.startswith("mock://"):
        return {
            "preview_uri": f"mock://visual_{os.path.basename(input_uri)}",
            "percentiles": [0, 10000]
        }

    try:
        with rasterio.open(input_uri) as src:
            meta = src.meta.copy()
            
            # --- Dynamic Downsampling to prevent OOM ---
            max_dim = max(src.width, src.height)
            scale_factor = 1.0
            if max_dim > 2048:
                scale_factor = 2048.0 / max_dim
                
            # Ensure max 3 bands for PNG compatibility (RGB)
            out_bands = min(3, src.count)
            out_shape = (
                out_bands,
                int(src.height * scale_factor),
                int(src.width * scale_factor)
            )
            
            data = src.read(
                indexes=list(range(1, out_bands + 1)),
                out_shape=out_shape,
                resampling=rasterio.enums.Resampling.bilinear
            )
            
            # Normalize to 8-bit (0-255)
            transform = src.transform * src.transform.scale(
                (src.width / data.shape[-1]),
                (src.height / data.shape[-2])
            )
            
            meta.update(
                dtype=rasterio.uint8,
                driver="PNG",
                count=out_bands,
                height=data.shape[-2],
                width=data.shape[-1],
                transform=transform,
            )
            if 'nodata' in meta:
                del meta['nodata']
            
            normalized_data = np.zeros_like(data, dtype=np.uint8)
            
            percentiles = []
            
            for i in range(out_bands):
                band_data = data[i]
                # Ignore nodata if possible, simple approximation here
                valid_data = band_data[band_data > 0] if src.nodata else band_data
                
                if valid_data.size == 0:
                    percentiles.append((0, 0))
                    continue
                    
                p2, p98 = np.percentile(valid_data, (2, 98))
                percentiles.append((float(p2), float(p98)))
                
                # Stretch and clip
                with np.errstate(divide='ignore', invalid='ignore'):
                    stretched = (band_data - p2) / (p98 - p2)
                
                stretched = np.clip(stretched, 0, 1)
                normalized_data[i] = (stretched * 255).astype(np.uint8)

        if not output_uri:
            # Create a temp file
            fd, output_uri = tempfile.mkstemp(suffix=".png")
            os.close(fd)
            
        with rasterio.open(output_uri, 'w', **meta) as dst:
            dst.write(normalized_data)
            
        return {
            "preview_uri": output_uri,
            "percentiles": percentiles,
            "original_dtype": str(data.dtype),
            "new_dtype": "uint8"
        }
            
    except Exception as exc:
        logger.error("Failed to generate visual preview for %s: %s", input_uri, exc)
        return {"error": f"Preview generation failed: {exc}"}


class VisualPreviewAdapter(BaseModelAdapter):
    """Deterministic adapter for generating visual previews."""

    def validate_input(self, arguments: dict[str, Any]) -> tuple[bool, str]:
        if not arguments.get("asset"):
            return False, "Missing 'asset' argument"
        return True, ""

    async def predict(self, arguments: dict[str, Any]) -> dict[str, Any]:
        state = arguments.get("_state")
        asset_id = arguments.get("asset")
        
        uri = None
        if state:
            for a in state.input_assets:
                if a.asset_id == asset_id:
                    uri = a.uri
                    break
                    
        # Fallback to mock URI if none found or state missing
        if not uri:
            uri = f"mock://images/{asset_id}.tif"
            
        result = create_visual_preview(input_uri=uri)
        return result

    def normalize_output(
        self, raw: dict[str, Any], arguments: dict[str, Any]
    ) -> Observation:
        
        status = ObservationStatus.SUCCESS
        if "error" in raw:
            status = ObservationStatus.FAILURE
            
        return Observation(
            source=EvidenceSource(
                capability="create_visual_preview",
                model="deterministic_geospatial",
                backend="local",
            ),
            type=EvidenceType.IMAGE_PROCESSING, # Keep IMAGE_PROCESSING as visual operations fit here
            status=status,
            result=raw,
            error_message=raw.get("error") or "",
            confidence=1.0,
        )
