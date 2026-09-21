"""Raster utility for deterministic inspection.

Reads raster metadata without loading full datasets into memory.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    import rasterio
    from rasterio.errors import RasterioIOError
except ImportError:
    rasterio = None
    RasterioIOError = Exception


def inspect_raster(uri: str) -> dict[str, Any]:
    """Inspect a raster file and return deterministic metadata.
    
    If the file is unreadable, returns {"valid": False, "error": ...}.
    """
    if rasterio is None:
        return {"valid": False, "error": "rasterio not installed"}

    try:
        with rasterio.open(uri) as src:
            # Safely extract CRS
            crs_str = None
            if src.crs:
                if src.crs.is_epsg_code:
                    crs_str = f"EPSG:{src.crs.to_epsg()}"
                else:
                    crs_str = src.crs.to_wkt()
                    
            # Resolution is typically a tuple of (x, y)
            res = src.res
            if len(res) == 2:
                resolution_x = abs(res[0])
                resolution_y = abs(res[1])
                resolution_m = resolution_x  # backward compatibility
            else:
                resolution_x = None
                resolution_y = None
                resolution_m = None

            bounds = src.bounds
            
            return {
                "valid": True,
                "width": src.width,
                "height": src.height,
                "count": src.count,
                "dtypes": [dtype for dtype in src.dtypes],
                "nodata": src.nodata,
                "crs": crs_str,
                "bounds": [bounds.left, bounds.bottom, bounds.right, bounds.top],
                "transform": [
                    src.transform.a, src.transform.b, src.transform.c,
                    src.transform.d, src.transform.e, src.transform.f,
                ],
                "resolution_m": resolution_m,
                "resolution_x": resolution_x,
                "resolution_y": resolution_y,
                "driver": src.driver,
                "tags": src.tags()
            }
            
    except RasterioIOError as exc:
        logger.warning("Raster inspection failed for %s: %s", uri, exc)
        return {"valid": False, "error": f"Failed to read raster: {exc}"}
    except Exception as exc:
        logger.error("Unexpected error reading raster %s: %s", uri, exc)
        return {"valid": False, "error": f"Unexpected error: {exc}"}

def determine_modality(tags: dict[str, Any], count: int) -> str:
    """Attempt to deterministically identify modality from raster metadata.
    
    Returns a string matching Modality enum (e.g. "optical", "sar", "multispectral"),
    or "unknown" if there is no reliable metadata.
    """
    # If the user or provider explicitly tagged it
    if "modality" in tags:
        return tags["modality"].lower()
        
    # Heuristics based on band count (these are fallbacks if metadata is missing)
    # Standard RGB
    if count == 3:
        return "optical"
        
    # Sentinel-2 often has 10, 12, or 13 bands
    if count in (10, 12, 13):
        return "multispectral"
        
    # Sentinel-1 SAR often has 2 bands (VV, VH)
    if count == 2:
        return "sar"
        
    return "unknown"
