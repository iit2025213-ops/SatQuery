# app/geospatial/aoi.py

"""
Area of Interest (AOI) — Validation, Calculation, Intersection

All geospatial operations use real Shapely + pyproj transformations.
Coordinates follow GeoJSON standard: [longitude, latitude] in WGS84 (EPSG:4326).
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Tuple
from shapely.geometry import Polygon, shape, mapping
from shapely.validation import make_valid
from pyproj import Transformer
import logging

logger = logging.getLogger("satquery")

# Reusable transformer: WGS84 → Web Mercator (metres)
_transformer_4326_to_3857 = Transformer.from_crs(
    "EPSG:4326",
    "EPSG:3857",
    always_xy=True,
)


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class AOICoordinate(BaseModel):
    """Single coordinate [longitude, latitude] (GeoJSON standard)"""
    lon: float = Field(..., ge=-180, le=180)
    lat: float = Field(..., ge=-90, le=90)


class AOIBounds(BaseModel):
    """Bounding box: [minx, miny, maxx, maxy]"""
    minx: float = Field(..., ge=-180, le=180)
    miny: float = Field(..., ge=-90, le=90)
    maxx: float = Field(..., ge=-180, le=180)
    maxy: float = Field(..., ge=-90, le=90)

    @field_validator("maxx")
    @classmethod
    def max_x_greater_than_min(cls, v, info):
        if "minx" in info.data and v <= info.data["minx"]:
            raise ValueError("maxx must be > minx")
        return v

    @field_validator("maxy")
    @classmethod
    def max_y_greater_than_min(cls, v, info):
        if "miny" in info.data and v <= info.data["miny"]:
            raise ValueError("maxy must be > miny")
        return v

    def to_array(self) -> List[float]:
        """Return as [minx, miny, maxx, maxy]"""
        return [self.minx, self.miny, self.maxx, self.maxy]


class AOIGeometry(BaseModel):
    """GeoJSON Polygon for AOI"""
    type: str = "Polygon"
    coordinates: List[List[List[float]]]

    @field_validator("coordinates")
    @classmethod
    def validate_polygon_coordinates(cls, v):
        """Validate polygon structure"""
        if not v:
            raise ValueError("Polygon must have at least one ring")

        # Outer ring must have ≥ 4 coordinates (first & last identical)
        if len(v[0]) < 4:
            raise ValueError("Outer ring must have at least 4 points")

        # Ring must be closed
        if v[0][0] != v[0][-1]:
            raise ValueError("Polygon ring must be closed (first point == last point)")

        # Validate each coordinate
        for ring in v:
            for coord in ring:
                if len(coord) < 2:
                    raise ValueError("Each coordinate must have [lon, lat]")
                if not (-180 <= coord[0] <= 180 and -90 <= coord[1] <= 90):
                    raise ValueError(f"Invalid coordinate: {coord}")
        return v


class AOI(BaseModel):
    """Area of Interest — full data model"""
    aoi_id: Optional[str] = None
    job_id: str
    user_id: str

    geojson: AOIGeometry
    bbox: List[float]  # [minx, miny, maxx, maxy]
    area_m2: Optional[float] = None
    area_km2: Optional[float] = None
    centroid: Optional[List[float]] = None  # [lon, lat]

    crs: str = "EPSG:4326"
    validation_status: str = "pending"
    validation_errors: Optional[List[str]] = None

    source: str = "drawn"  # drawn | uploaded | auto-generated
    description: Optional[str] = None


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

class AOIValidator:
    """Validate AOI geometries — real Shapely checks, no mocks."""

    @staticmethod
    def validate_geojson(geojson_dict: dict) -> Tuple[bool, Optional[List[str]]]:
        """
        Validate a GeoJSON geometry dict.

        Returns
        -------
        (is_valid, errors)   — errors is None when valid.
        """
        errors: List[str] = []

        # --- type check ---
        if geojson_dict.get("type") != "Polygon":
            errors.append("Only Polygon geometries are supported")
            return False, errors

        coords = geojson_dict.get("coordinates", [])

        if not coords:
            errors.append("Coordinates cannot be empty")
            return False, errors

        # --- outer ring closure + min point count ---
        outer = coords[0]
        if len(outer) < 4:
            errors.append("Outer ring must have at least 4 points (including closing point)")
            return False, errors

        if outer[0] != outer[-1]:
            errors.append("Polygon ring must be closed (first point == last point)")
            return False, errors

        # --- coordinate bounds ---
        for ring in coords:
            for point in ring:
                if len(point) < 2:
                    errors.append(f"Coordinate must have at least [lon, lat]: {point}")
                    continue
                lon, lat = point[0], point[1]
                if not (-180 <= lon <= 180):
                    errors.append(f"Longitude {lon} out of bounds [-180, 180]")
                if not (-90 <= lat <= 90):
                    errors.append(f"Latitude {lat} out of bounds [-90, 90]")

        if errors:
            return False, errors

        # --- Shapely validity (self-intersection, degenerate geometry) ---
        try:
            poly = shape(geojson_dict)

            if not poly.is_valid:
                errors.append("Polygon is self-intersecting or topologically invalid")

            if poly.is_empty or poly.area == 0:
                errors.append("Polygon has zero area")

        except Exception as e:
            errors.append(f"Geometry error: {str(e)}")

        return (len(errors) == 0), (errors if errors else None)

    @staticmethod
    def extract_bounds(geojson_dict: dict) -> Optional[List[float]]:
        """Extract [minx, miny, maxx, maxy] from GeoJSON."""
        try:
            poly = shape(geojson_dict)
            minx, miny, maxx, maxy = poly.bounds
            return [minx, miny, maxx, maxy]
        except Exception:
            return None

    @staticmethod
    def check_size_limit(
        area_km2: float, max_km2: float = 1000
    ) -> Tuple[bool, Optional[str]]:
        """Check if AOI exceeds the configurable size limit."""
        if area_km2 > max_km2:
            return False, f"AOI exceeds maximum size of {max_km2} km² (actual: {area_km2:.2f} km²)"
        return True, None

    @staticmethod
    def check_valid_bounds(
        bbox: List[float],
        valid_bounds: Optional[List[float]] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Check if bbox is within valid geographic bounds."""
        if valid_bounds is None:
            valid_bounds = [-180, -90, 180, 90]

        minx, miny, maxx, maxy = bbox
        vminx, vminy, vmaxx, vmaxy = valid_bounds

        if not (vminx <= minx <= vmaxx and vminy <= miny <= vmaxy):
            return False, "AOI bounds outside valid geographic area"
        if not (vminx <= maxx <= vmaxx and vminy <= maxy <= vmaxy):
            return False, "AOI bounds outside valid geographic area"

        return True, None


# ---------------------------------------------------------------------------
# Calculator
# ---------------------------------------------------------------------------

class AOICalculator:
    """Calculate AOI properties — real projections via pyproj."""

    @staticmethod
    def calculate_area(geojson_dict: dict) -> Tuple[float, float]:
        """
        Calculate area in m² and km².

        Projects from WGS84 (EPSG:4326) to Web Mercator (EPSG:3857) for
        metre-based area computation.

        Returns
        -------
        (area_m2, area_km2)
        """
        try:
            coords_3857 = []
            for ring in geojson_dict["coordinates"]:
                transformed_ring = []
                for point in ring:
                    lon, lat = point[0], point[1]
                    x, y = _transformer_4326_to_3857.transform(lon, lat)
                    transformed_ring.append((x, y))
                coords_3857.append(transformed_ring)

            poly_3857 = Polygon(
                coords_3857[0],
                holes=coords_3857[1:] if len(coords_3857) > 1 else None,
            )

            area_m2 = poly_3857.area
            area_km2 = area_m2 / 1_000_000
            return area_m2, area_km2

        except Exception as e:
            logger.error(f"Error calculating area: {e}")
            return 0.0, 0.0

    @staticmethod
    def calculate_centroid(geojson_dict: dict) -> Optional[Tuple[float, float]]:
        """Calculate centroid as (lon, lat) in WGS84."""
        try:
            poly = shape(geojson_dict)
            return (poly.centroid.x, poly.centroid.y)
        except Exception:
            return None

    @staticmethod
    def create_bbox_polygon(bbox: List[float]) -> dict:
        """Create a GeoJSON polygon from a [minx, miny, maxx, maxy] bbox."""
        minx, miny, maxx, maxy = bbox
        return {
            "type": "Polygon",
            "coordinates": [
                [
                    [minx, miny],
                    [maxx, miny],
                    [maxx, maxy],
                    [minx, maxy],
                    [minx, miny],  # close ring
                ]
            ],
        }


# ---------------------------------------------------------------------------
# Intersection / Overlap
# ---------------------------------------------------------------------------

class AOIIntersection:
    """Handle AOI intersection operations."""

    @staticmethod
    def intersection(geojson1: dict, geojson2: dict) -> Optional[dict]:
        """Calculate intersection of two polygons; returns GeoJSON or None."""
        try:
            poly1 = shape(geojson1)
            poly2 = shape(geojson2)

            result = poly1.intersection(poly2)

            if result.is_empty:
                return None

            return mapping(result)
        except Exception:
            return None

    @staticmethod
    def overlap_percentage(geojson1: dict, geojson2: dict) -> Optional[float]:
        """Return the percentage of geojson1 that overlaps with geojson2."""
        try:
            poly1 = shape(geojson1)
            poly2 = shape(geojson2)

            intersection_area = poly1.intersection(poly2).area
            poly1_area = poly1.area

            if poly1_area == 0:
                return 0.0

            return (intersection_area / poly1_area) * 100
        except Exception:
            return None
