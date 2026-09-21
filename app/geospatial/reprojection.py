"""Deterministic CRS reprojection utilities.

Reprojects rasters and bounding boxes between coordinate reference systems.
Uses rasterio.warp for raster reprojection — never overwrites source data.
"""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Any

logger = logging.getLogger(__name__)

try:
    import rasterio
    from rasterio.warp import calculate_default_transform, reproject, Resampling
except ImportError:
    rasterio = None


def reproject_raster(
    input_uri: str,
    target_crs: str,
    resampling: str = "bilinear",
) -> dict[str, Any]:
    """Reproject a raster to a new CRS.

    Creates a NEW derived raster — the source is never overwritten.
    Returns metadata about the operation including the new URI and provenance.

    Parameters
    ----------
    input_uri:
        Path to the source raster.
    target_crs:
        Target CRS string (e.g. ``"EPSG:32643"``).
    resampling:
        Resampling method name: ``"nearest"``, ``"bilinear"``, ``"cubic"``, etc.
    """
    if rasterio is None:
        return {"error": "rasterio not installed"}

    if not os.path.exists(input_uri):
        return {"error": f"Input file not found: {input_uri}"}

    # Map string to rasterio Resampling enum
    try:
        resamp = Resampling[resampling]
    except KeyError:
        return {"error": f"Unknown resampling method: {resampling}"}

    try:
        with rasterio.open(input_uri) as src:
            if not src.crs:
                return {"error": "Source raster has no CRS — cannot reproject."}

            source_crs = src.crs.to_string()

            # If already in the target CRS, no work needed
            if src.crs == rasterio.crs.CRS.from_user_input(target_crs):
                return {
                    "reprojected": False,
                    "output_uri": input_uri,
                    "provenance": "already_in_target_crs",
                    "source_crs": source_crs,
                    "target_crs": target_crs,
                }

            # Calculate the optimal transform for the target CRS
            transform, width, height = calculate_default_transform(
                src.crs, target_crs, src.width, src.height, *src.bounds
            )

            meta = src.meta.copy()
            meta.update({
                "crs": target_crs,
                "transform": transform,
                "width": width,
                "height": height,
            })

            fd, output_uri = tempfile.mkstemp(suffix=".tif")
            os.close(fd)

            with rasterio.open(output_uri, "w", **meta) as dst:
                for i in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=target_crs,
                        resampling=resamp,
                    )

            return {
                "reprojected": True,
                "output_uri": output_uri,
                "provenance": f"reprojected ({resampling})",
                "source_crs": source_crs,
                "target_crs": target_crs,
                "source_resolution": list(src.res),
                "output_width": width,
                "output_height": height,
                "resampling": resampling,
            }

    except Exception as exc:
        logger.error("Reprojection failed for %s: %s", input_uri, exc)
        return {"error": f"Reprojection failed: {exc}"}
