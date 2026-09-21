"""Spatial alignment and co-registration.

Ensures two independent rasters refer exactly to the same geographic locations.
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
    from rasterio.warp import reproject, Resampling
except ImportError:
    np = None
    rasterio = None


def align_rasters(reference_uri: str, target_uri: str, is_mask: bool = False) -> dict[str, Any]:
    """Deterministically align a target raster to match a reference raster's exact grid.

    Checks CRS, resolution, and affine transform.
    If they do not perfectly match, it resamples the target raster.
    Returns the provenance of the operation and the new aligned URI.
    """
    if rasterio is None or np is None:
        return {"error": "rasterio or numpy not installed"}

    if not os.path.exists(reference_uri) or not os.path.exists(target_uri):
        if not reference_uri.startswith("mock://") and not target_uri.startswith("mock://"):
            return {"error": "One or both input files not found."}
        
    if reference_uri.startswith("mock://") or target_uri.startswith("mock://"):
        return {
            "aligned": True,
            "aligned_uri": f"mock://aligned_{os.path.basename(target_uri)}",
            "provenance": "mock_alignment"
        }

    try:
        with rasterio.open(reference_uri) as ref_src, rasterio.open(target_uri) as tgt_src:
            
            if not ref_src.crs or not tgt_src.crs:
                return {"error": "Both rasters must have a valid CRS for alignment."}
                
            if not ref_src.transform or not tgt_src.transform:
                return {"error": "Both rasters must have a valid affine transform."}

            # Check if they already align perfectly
            same_crs = (ref_src.crs == tgt_src.crs)
            same_transform = (ref_src.transform == tgt_src.transform)
            same_shape = (ref_src.height == tgt_src.height and ref_src.width == tgt_src.width)
            
            if same_crs and same_transform and same_shape:
                return {
                    "aligned": True,
                    "aligned_uri": target_uri,
                    "provenance": "perfect_match",
                    "crs": ref_src.crs.to_string(),
                    "transform": [
                        ref_src.transform.a, ref_src.transform.b, ref_src.transform.c,
                        ref_src.transform.d, ref_src.transform.e, ref_src.transform.f
                    ]
                }
                
            # Need to reproject / resample
            logger.info("Aligning %s to reference %s", target_uri, reference_uri)
            
            fd, aligned_uri = tempfile.mkstemp(suffix=".tif")
            os.close(fd)
            
            meta = ref_src.meta.copy()
            # The target might have different number of bands or dtype, but we match the grid
            meta.update({
                'count': tgt_src.count,
                'dtype': tgt_src.dtypes[0]
            })

            resampling_method = Resampling.nearest if is_mask else Resampling.bilinear
            
            with rasterio.open(aligned_uri, 'w', **meta) as dst:
                for i in range(1, tgt_src.count + 1):
                    reproject(
                        source=rasterio.band(tgt_src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=tgt_src.transform,
                        src_crs=tgt_src.crs,
                        dst_transform=ref_src.transform,
                        dst_crs=ref_src.crs,
                        resampling=resampling_method
                    )
                    
            return {
                "aligned": True,
                "aligned_uri": aligned_uri,
                "provenance": f"resampled_to_reference ({resampling_method.name})",
                "crs": ref_src.crs.to_string(),
                "transform": [
                    ref_src.transform.a, ref_src.transform.b, ref_src.transform.c,
                    ref_src.transform.d, ref_src.transform.e, ref_src.transform.f
                ]
            }

    except Exception as exc:
        logger.error("Failed to align rasters: %s", exc)
        return {"error": f"Alignment failed: {exc}"}
