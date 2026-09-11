# app/models/gee_adapter.py

"""
GEE Capability Adapter — Phase 7

Bridges AI Brain capability calls → GEEConnector.
Handles: retrieve_satellite_imagery, retrieve_dem
"""

import logging
from typing import Optional

from app.models.base import BaseAdapter
from app.agent.state import Observation
from app.config import settings

logger = logging.getLogger("satquery")


class GEEAdapter(BaseAdapter):
    """Adapter for GEE satellite imagery retrieval capabilities."""

    def __init__(self):
        self._connector = None
        self._processor = None

    def _get_connector(self):
        if self._connector is None:
            from app.gee.connector import GEEConnector

            self._connector = GEEConnector(
                service_account_key_path=settings.gee_service_account_key_path,
                project_id=settings.gee_project_id,
            )
        return self._connector

    def _get_processor(self):
        if self._processor is None:
            from app.gee.processor import GEEProcessor

            self._processor = GEEProcessor(cloudinary_client=None)
        return self._processor

    async def execute(self, arguments: dict, state, supabase_client) -> Observation:
        """
        Execute a GEE capability.

        The Brain calls this with arguments like:
        {
            "capability": "retrieve_satellite_imagery" | "retrieve_dem",
            "aoi": {GeoJSON Polygon},
            "date_start": "2024-01-01",
            "date_end": "2024-12-31",
            "collections": ["Sentinel-2", "Landsat-8"],
            "cloud_cover_max": 20,
            "resolution_m": 30
        }
        """
        capability = arguments.get("capability", "retrieve_satellite_imagery")

        if capability == "retrieve_satellite_imagery":
            return await self._retrieve_imagery(arguments, state, supabase_client)
        elif capability == "retrieve_dem":
            return await self._retrieve_dem(arguments, state, supabase_client)
        else:
            return Observation(
                step_number=state.current_step,
                source_capability=capability,
                status="failed",
                result={"error": f"Unknown GEE capability: {capability}"},
            )

    async def _retrieve_imagery(self, arguments: dict, state, supabase_client) -> Observation:
        """Query GEE for satellite imagery."""
        connector = self._get_connector()
        processor = self._get_processor()

        # Get AOI — from arguments or from agent state
        aoi = arguments.get("aoi") or getattr(state, "aoi", None)
        if not aoi:
            return Observation(
                step_number=state.current_step,
                source_capability="retrieve_satellite_imagery",
                status="failed",
                result={"error": "No AOI provided in arguments or agent state"},
            )

        date_start = arguments.get("date_start", "2024-01-01")
        date_end = arguments.get("date_end", "2024-12-31")
        collections = arguments.get("collections", ["Sentinel-2"])
        cloud_cover_max = arguments.get("cloud_cover_max", 20)

        try:
            # Authenticate
            auth_ok = await connector.authenticate()
            if not auth_ok:
                return Observation(
                    step_number=state.current_step,
                    source_capability="retrieve_satellite_imagery",
                    status="failed",
                    result={"error": "GEE authentication failed"},
                )

            # Create collection record
            collection_id = await processor.create_collection(
                job_id=state.job_id,
                user_id="system",  # Brain-initiated
                query_params={
                    "aoi": aoi,
                    "date_start": date_start,
                    "date_end": date_end,
                    "collections": collections,
                    "cloud_cover_max": cloud_cover_max,
                },
                collection_name=", ".join(collections),
                supabase_client=supabase_client,
            )

            # Query
            all_scenes = []

            if "Sentinel-2" in collections:
                scenes = await connector.query_sentinel2(
                    aoi, date_start, date_end, cloud_cover_max
                )
                all_scenes.extend(scenes)

            if "Landsat-8" in collections or "Landsat-9" in collections:
                scenes = await connector.query_landsat(
                    aoi, date_start, date_end, cloud_cover_max
                )
                all_scenes.extend(scenes)

            # Store scenes
            asset_ids = await processor.store_scenes(
                all_scenes, collection_id, state.job_id, supabase_client
            )

            # Retrieve DEM alongside
            dem_info = await connector.retrieve_dem(aoi)
            if dem_info:
                from app.geospatial.aoi import AOIValidator
                bbox = AOIValidator.extract_bounds(aoi)
                await processor.store_dem(
                    dem_info, collection_id, state.job_id, supabase_client, bbox=bbox
                )

            # Mark complete
            await processor.update_collection_status(
                collection_id, "completed", supabase_client,
                progress_percent=100,
                results_count=len(all_scenes),
                scenes_retrieved=len(asset_ids),
            )

            return Observation(
                step_number=state.current_step,
                source_capability="retrieve_satellite_imagery",
                status="success",
                result={
                    "collection_id": collection_id,
                    "imagery_count": len(all_scenes),
                    "scenes": all_scenes,
                    "dem": dem_info,
                    "date_range": {"start": date_start, "end": date_end},
                },
                confidence=0.95,
            )

        except Exception as e:
            logger.error(f"GEE adapter imagery error: {e}", exc_info=True)
            return Observation(
                step_number=state.current_step,
                source_capability="retrieve_satellite_imagery",
                status="failed",
                result={"error": str(e)},
                confidence=0.0,
            )

    async def _retrieve_dem(self, arguments: dict, state, supabase_client) -> Observation:
        """Retrieve DEM data for an AOI."""
        connector = self._get_connector()

        aoi = arguments.get("aoi") or getattr(state, "aoi", None)
        if not aoi:
            return Observation(
                step_number=state.current_step,
                source_capability="retrieve_dem",
                status="failed",
                result={"error": "No AOI provided"},
            )

        resolution_m = arguments.get("resolution_m", 30)

        try:
            auth_ok = await connector.authenticate()
            if not auth_ok:
                return Observation(
                    step_number=state.current_step,
                    source_capability="retrieve_dem",
                    status="failed",
                    result={"error": "GEE authentication failed"},
                )

            dem_info = await connector.retrieve_dem(aoi, resolution_m)

            if not dem_info:
                return Observation(
                    step_number=state.current_step,
                    source_capability="retrieve_dem",
                    status="failed",
                    result={"error": "DEM data not available for this AOI"},
                )

            return Observation(
                step_number=state.current_step,
                source_capability="retrieve_dem",
                status="success",
                result={
                    "dem": dem_info,
                    "elevation_stats": dem_info.get("elevation_stats"),
                },
                confidence=0.95,
            )

        except Exception as e:
            logger.error(f"GEE adapter DEM error: {e}", exc_info=True)
            return Observation(
                step_number=state.current_step,
                source_capability="retrieve_dem",
                status="failed",
                result={"error": str(e)},
                confidence=0.0,
            )
