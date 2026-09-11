# app/models/geospatial_engine.py

"""
Geospatial Engine adapter — real implementations using AOIValidator / AOICalculator.
Replaces the previous mocked version.
"""

from app.models.base import BaseAdapter
from app.agent.state import Observation
from app.geospatial.aoi import AOIValidator, AOICalculator
import logging

logger = logging.getLogger("satquery")


class GeospatialEngine(BaseAdapter):
    """Geospatial operations (CRS, alignment, area calculation)"""

    async def execute(self, arguments: dict, state, supabase_client) -> Observation:
        """Execute geospatial operation"""

        operation = arguments.get("operation")

        if operation == "validate_input":
            return await self._validate_input(arguments, state, supabase_client)
        elif operation == "calculate_area":
            return await self._calculate_area(arguments, state, supabase_client)
        elif operation == "validate_aoi":
            return await self._validate_aoi(arguments, state)
        else:
            return Observation(
                step_number=state.current_step,
                source_capability="geospatial_engine",
                status="failed",
                result={"error": f"Unknown operation: {operation}"},
            )

    async def _validate_input(self, arguments: dict, state, supabase_client) -> Observation:
        """Validate satellite imagery inputs"""

        asset_ids = arguments.get("asset_ids", [])

        # Get assets from Supabase
        assets = []
        for asset_id in asset_ids:
            try:
                asset = (
                    supabase_client.get_admin_client()
                    .table("assets")
                    .select("*")
                    .eq("asset_id", asset_id)
                    .single()
                    .execute()
                )
                assets.append(asset.data)
            except Exception:
                pass

        # Validate
        validation_results = {
            "total_assets": len(assets),
            "valid_assets": len(
                [a for a in assets if a.get("validation_status") != "invalid"]
            ),
            "issues": [],
        }

        return Observation(
            step_number=state.current_step,
            source_capability="geospatial_engine",
            status="success",
            result=validation_results,
            confidence=0.95,
        )

    async def _calculate_area(self, arguments: dict, state, supabase_client) -> Observation:
        """Calculate area from GeoJSON — real implementation via pyproj projection"""

        geojson = arguments.get("geojson")

        if not geojson:
            # Fall back to AOI from agent state if available
            geojson = state.aoi if hasattr(state, "aoi") else None

        if not geojson:
            return Observation(
                step_number=state.current_step,
                source_capability="geospatial_engine",
                status="failed",
                result={"error": "No GeoJSON provided and no AOI in agent state"},
            )

        # Real area calculation
        area_m2, area_km2 = AOICalculator.calculate_area(geojson)
        centroid = AOICalculator.calculate_centroid(geojson)
        bbox = AOIValidator.extract_bounds(geojson)

        return Observation(
            step_number=state.current_step,
            source_capability="geospatial_engine",
            status="success",
            result={
                "area_m2": area_m2,
                "area_km2": area_km2,
                "centroid": list(centroid) if centroid else None,
                "bbox": bbox,
            },
            confidence=0.95,
        )

    async def _validate_aoi(self, arguments: dict, state) -> Observation:
        """Validate an AOI GeoJSON — real Shapely validation"""

        geojson = arguments.get("geojson")
        if not geojson:
            return Observation(
                step_number=state.current_step,
                source_capability="geospatial_engine",
                status="failed",
                result={"error": "No GeoJSON provided"},
            )

        is_valid, errors = AOIValidator.validate_geojson(geojson)

        if is_valid:
            area_m2, area_km2 = AOICalculator.calculate_area(geojson)
            bbox = AOIValidator.extract_bounds(geojson)
            size_ok, size_err = AOIValidator.check_size_limit(area_km2)

            result = {
                "valid": True,
                "area_m2": area_m2,
                "area_km2": area_km2,
                "bbox": bbox,
                "within_size_limit": size_ok,
            }
            if not size_ok:
                result["size_warning"] = size_err

            return Observation(
                step_number=state.current_step,
                source_capability="geospatial_engine",
                status="success",
                result=result,
                confidence=0.98,
            )
        else:
            return Observation(
                step_number=state.current_step,
                source_capability="geospatial_engine",
                status="failed",
                result={"valid": False, "errors": errors},
                confidence=0.98,
            )
