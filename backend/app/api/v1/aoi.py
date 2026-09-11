# app/api/v1/aoi.py

"""
AOI API endpoints — Phase 6

Endpoints (per 6-9.md source of truth):
  POST  /api/v1/aoi/validate
  POST  /api/v1/aoi/create
  GET   /api/v1/aoi/{aoi_id}
  POST  /api/v1/aoi/from-bounds
  POST  /api/v1/aoi/intersection
  POST  /api/v1/aoi/check-asset-overlap
"""

from fastapi import APIRouter, HTTPException, status, Depends, Body
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import logging
import uuid

from app.auth.dependencies import get_current_user_id
from app.geospatial.aoi import (
    AOIValidator,
    AOICalculator,
    AOIBounds,
    AOIIntersection,
)

logger = logging.getLogger("satquery")
router = APIRouter(prefix="/api/v1/aoi", tags=["aoi"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class ValidateAOIRequest(BaseModel):
    geojson: dict
    crs: Optional[str] = "EPSG:4326"


class ValidateAOIResponse(BaseModel):
    valid: bool
    errors: Optional[List[str]] = None
    area_km2: Optional[float] = None
    area_m2: Optional[float] = None
    bbox: Optional[List[float]] = None
    centroid: Optional[tuple] = None


class CreateAOIRequest(BaseModel):
    job_id: str
    geojson: dict
    source: str = "drawn"  # drawn | uploaded | auto-generated
    description: Optional[str] = None


class CreateAOIResponse(BaseModel):
    aoi_id: str
    area_km2: float
    bbox: List[float]
    centroid: Optional[tuple] = None
    created_at: datetime


class FromBoundsRequest(BaseModel):
    minx: float = Field(..., ge=-180, le=180)
    miny: float = Field(..., ge=-90, le=90)
    maxx: float = Field(..., ge=-180, le=180)
    maxy: float = Field(..., ge=-90, le=90)


class IntersectionRequest(BaseModel):
    aoi1: dict  # GeoJSON
    aoi2: dict  # GeoJSON


class AssetOverlapRequest(BaseModel):
    aoi_geojson: dict
    asset_ids: List[str]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/validate", response_model=ValidateAOIResponse)
async def validate_aoi(
    request: ValidateAOIRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Validate AOI GeoJSON polygon.

    Returns validation status, area, bbox, and any errors.
    """
    logger.info(f"Validating AOI for user {user_id}")

    try:
        # --- structural + geometric validation ---
        is_valid, errors = AOIValidator.validate_geojson(request.geojson)

        if not is_valid:
            return ValidateAOIResponse(
                valid=False,
                errors=errors,
            )

        # --- extract bounds ---
        bbox = AOIValidator.extract_bounds(request.geojson)
        if not bbox:
            raise HTTPException(status_code=400, detail="Could not extract bounding box")

        # --- bounds within valid range ---
        bounds_ok, bounds_err = AOIValidator.check_valid_bounds(bbox)
        if not bounds_ok:
            return ValidateAOIResponse(
                valid=False,
                errors=[bounds_err],
                bbox=bbox,
            )

        # --- area calculation ---
        area_m2, area_km2 = AOICalculator.calculate_area(request.geojson)

        # --- size limit ---
        size_ok, size_err = AOIValidator.check_size_limit(area_km2)
        if not size_ok:
            return ValidateAOIResponse(
                valid=False,
                errors=[size_err],
                area_km2=area_km2,
                bbox=bbox,
            )

        # --- centroid ---
        centroid = AOICalculator.calculate_centroid(request.geojson)

        return ValidateAOIResponse(
            valid=True,
            area_km2=area_km2,
            area_m2=area_m2,
            bbox=bbox,
            centroid=centroid,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating AOI: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to validate AOI")


@router.post("/create", response_model=CreateAOIResponse, status_code=status.HTTP_201_CREATED)
async def create_aoi(
    request: CreateAOIRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Validate, compute properties, and persist a new AOI to Supabase.
    """
    from app.main import supabase_client

    try:
        # Validate
        is_valid, errors = AOIValidator.validate_geojson(request.geojson)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid GeoJSON: {'; '.join(errors)}",
            )

        # Compute properties
        bbox = AOIValidator.extract_bounds(request.geojson)
        area_m2, area_km2 = AOICalculator.calculate_area(request.geojson)
        centroid = AOICalculator.calculate_centroid(request.geojson)

        # Size limit
        size_ok, size_err = AOIValidator.check_size_limit(area_km2)
        if not size_ok:
            raise HTTPException(status_code=400, detail=size_err)

        aoi_id = str(uuid.uuid4())

        aoi_record = {
            "aoi_id": aoi_id,
            "job_id": request.job_id,
            "user_id": user_id,
            "geojson": request.geojson,
            "bbox": bbox,
            "area_m2": area_m2,
            "area_km2": area_km2,
            "centroid": list(centroid) if centroid else None,
            "crs": "EPSG:4326",
            "validation_status": "valid",
            "source": request.source,
            "description": request.description,
        }

        supabase_client.get_admin_client().table("aois").insert(aoi_record).execute()

        logger.info(f"AOI created: {aoi_id} for job {request.job_id}")

        return CreateAOIResponse(
            aoi_id=aoi_id,
            area_km2=area_km2,
            bbox=bbox,
            centroid=centroid,
            created_at=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating AOI: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create AOI")


@router.get("/{aoi_id}")
async def get_aoi(
    aoi_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Get AOI details by ID."""
    from app.main import supabase_client

    try:
        result = (
            supabase_client.get_admin_client()
            .table("aois")
            .select("*")
            .eq("aoi_id", aoi_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="AOI not found")

        return result.data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting AOI: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get AOI")


@router.post("/from-bounds")
async def from_bounds(
    request: FromBoundsRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Convert a bounding box to a GeoJSON polygon and return its area.

    Maps to: POST /api/v1/aoi/from-bounds (6-9.md)
    """
    try:
        bbox = [request.minx, request.miny, request.maxx, request.maxy]
        polygon = AOICalculator.create_bbox_polygon(bbox)

        # Validate the resulting polygon
        is_valid, errors = AOIValidator.validate_geojson(polygon)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid bounds: {'; '.join(errors)}")

        area_m2, area_km2 = AOICalculator.calculate_area(polygon)

        return {
            "geojson": polygon,
            "area_km2": area_km2,
            "area_m2": area_m2,
            "bbox": bbox,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error converting bounds: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to convert bounds")


@router.post("/intersection")
async def intersection(
    request: IntersectionRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Compute the intersection of two GeoJSON polygons.

    Maps to: POST /api/v1/aoi/intersection (6-9.md)
    """
    try:
        # Validate both inputs
        for label, geojson in [("aoi1", request.aoi1), ("aoi2", request.aoi2)]:
            ok, errs = AOIValidator.validate_geojson(geojson)
            if not ok:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid {label}: {'; '.join(errs)}",
                )

        intersection_geojson = AOIIntersection.intersection(request.aoi1, request.aoi2)
        overlap_pct = AOIIntersection.overlap_percentage(request.aoi1, request.aoi2)

        return {
            "intersection_geojson": intersection_geojson,
            "overlap_percent": overlap_pct,
            "has_overlap": intersection_geojson is not None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error computing intersection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to compute intersection")


@router.post("/check-asset-overlap")
async def check_asset_overlap(
    request: AssetOverlapRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Check which uploaded assets overlap with the given AOI.

    Maps to: GET /api/v1/aoi/bounds-check (6-9.md)
    """
    from app.main import supabase_client

    try:
        # Validate AOI
        ok, errs = AOIValidator.validate_geojson(request.aoi_geojson)
        if not ok:
            raise HTTPException(status_code=400, detail=f"Invalid AOI: {'; '.join(errs)}")

        overlapping = []
        non_overlapping = []

        for asset_id in request.asset_ids:
            try:
                asset = (
                    supabase_client.get_admin_client()
                    .table("assets")
                    .select("asset_id, bbox")
                    .eq("asset_id", asset_id)
                    .eq("user_id", user_id)
                    .single()
                    .execute()
                )
            except Exception:
                non_overlapping.append(asset_id)
                continue

            if not asset.data:
                non_overlapping.append(asset_id)
                continue

            asset_bbox = asset.data.get("bbox")
            if not asset_bbox:
                non_overlapping.append(asset_id)
                continue

            # Create polygon from asset bbox and check overlap
            asset_geojson = AOICalculator.create_bbox_polygon(asset_bbox)
            overlap_pct = AOIIntersection.overlap_percentage(
                request.aoi_geojson, asset_geojson
            )

            if overlap_pct and overlap_pct > 0:
                overlapping.append({
                    "asset_id": asset_id,
                    "overlap_percent": round(overlap_pct, 2),
                })
            else:
                non_overlapping.append(asset_id)

        return {
            "overlapping_assets": overlapping,
            "non_overlapping": non_overlapping,
            "total_overlapping": len(overlapping),
            "total_non_overlapping": len(non_overlapping),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking overlap: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to check asset overlap")
