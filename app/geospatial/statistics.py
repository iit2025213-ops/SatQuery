"""Deterministic raster statistics.

Computes basic band-level statistics from a raster file.
Uses rasterio for efficient access — avoids loading entire arrays
when only metadata-level information is needed.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    import numpy as np
    import rasterio
except ImportError:
    np = None
    rasterio = None


def compute_raster_stats(raster_uri: str) -> dict[str, Any]:
    """Compute per-band statistics for a raster.

    Returns min, max, mean, std, nodata_count, valid_count per band,
    plus overall totals.
    """
    if rasterio is None or np is None:
        return {"error": "rasterio or numpy not installed"}

    import os
    if not os.path.exists(raster_uri):
        return {"error": f"File not found: {raster_uri}"}

    try:
        with rasterio.open(raster_uri) as src:
            band_stats = []
            total_pixels = src.width * src.height
            overall_nodata = 0

            for band_idx in range(1, src.count + 1):
                data = src.read(band_idx)

                if src.nodata is not None:
                    valid_mask = data != src.nodata
                    valid_data = data[valid_mask]
                    nodata_count = int(np.sum(~valid_mask))
                else:
                    valid_data = data.flatten()
                    nodata_count = 0

                valid_count = valid_data.size
                overall_nodata += nodata_count

                if valid_count == 0:
                    band_stats.append({
                        "band": band_idx,
                        "min": None,
                        "max": None,
                        "mean": None,
                        "std": None,
                        "valid_count": 0,
                        "nodata_count": nodata_count,
                    })
                    continue

                band_stats.append({
                    "band": band_idx,
                    "min": float(np.min(valid_data)),
                    "max": float(np.max(valid_data)),
                    "mean": float(np.mean(valid_data)),
                    "std": float(np.std(valid_data)),
                    "valid_count": valid_count,
                    "nodata_count": nodata_count,
                })

            return {
                "valid": True,
                "band_count": src.count,
                "total_pixels_per_band": total_pixels,
                "overall_nodata_pixels": overall_nodata,
                "nodata_fraction": round(
                    overall_nodata / (total_pixels * src.count), 4
                ) if total_pixels > 0 else 0.0,
                "bands": band_stats,
            }

    except Exception as exc:
        logger.error("Failed to compute stats for %s: %s", raster_uri, exc)
        return {"error": f"Statistics computation failed: {exc}"}
