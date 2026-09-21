"""Spatial compatibility and bounds checking.

Deterministic checks for overlap, containment, and CRS compatibility.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    import pyproj
    from shapely.geometry import box
except ImportError:
    pyproj = None
    box = None


def reproject_bounds(bounds: list[float], source_crs: str, target_crs: str) -> list[float] | None:
    """Reproject bounding box from source CRS to target CRS."""
    if pyproj is None:
        logger.warning("pyproj not installed — cannot reproject bounds.")
        return None
        
    try:
        transformer = pyproj.Transformer.from_crs(source_crs, target_crs, always_xy=True)
        # Bounding box coordinates: [minx, miny, maxx, maxy]
        minx, miny, maxx, maxy = bounds
        
        # Transform the 4 corners
        corners = [
            transformer.transform(minx, miny),
            transformer.transform(minx, maxy),
            transformer.transform(maxx, miny),
            transformer.transform(maxx, maxy),
        ]
        
        xs = [c[0] for c in corners if c[0] is not float('inf')]
        ys = [c[1] for c in corners if c[1] is not float('inf')]
        
        if not xs or not ys:
            return None
            
        return [min(xs), min(ys), max(xs), max(ys)]
    except Exception as exc:
        logger.error("Failed to reproject bounds from %s to %s: %s", source_crs, target_crs, exc)
        return None


def calculate_spatial_compatibility(
    bounds1: list[float], crs1: str,
    bounds2: list[float], crs2: str
) -> dict[str, Any]:
    """Deterministically calculate spatial compatibility between two assets."""
    if box is None:
        return {"compatible": False, "error": "shapely not installed"}
        
    if not crs1 or not crs2:
        return {"compatible": False, "error": "Missing CRS for one or both assets"}
        
    # If CRSs differ, reproject bounds2 to crs1
    if crs1 != crs2:
        bounds2_reproj = reproject_bounds(bounds2, crs2, crs1)
        if not bounds2_reproj:
            return {"compatible": False, "error": "Reprojection failed for compatibility check"}
        b2 = bounds2_reproj
    else:
        b2 = bounds2
        
    try:
        geom1 = box(*bounds1)
        geom2 = box(*b2)
        
        intersection = geom1.intersection(geom2)
        overlap_area = intersection.area
        area1 = geom1.area
        area2 = geom2.area
        
        if overlap_area <= 0:
            return {
                "compatible": False,
                "overlap_percentage": 0.0,
                "reason": "No spatial overlap"
            }
            
        # Calculate overlap percentage relative to the smallest bounds
        min_area = min(area1, area2)
        overlap_percentage = (overlap_area / min_area) * 100
        
        return {
            "compatible": overlap_percentage > 5.0,  # Arbitrary 5% threshold for basic overlap
            "overlap_percentage": round(overlap_percentage, 2),
            "intersection_bounds": [intersection.bounds[0], intersection.bounds[1], intersection.bounds[2], intersection.bounds[3]] if intersection.bounds else None,
            "crs": crs1
        }
    except Exception as exc:
        logger.error("Spatial compatibility check failed: %s", exc)
        return {"compatible": False, "error": str(exc)}
