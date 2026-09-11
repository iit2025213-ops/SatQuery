# app/models/timeline_adapter.py

"""
Timeline Capability Adapter — Phase 9

Bridges AI Brain capability calls → TimelineProcessor.
Handles: retrieve_temporal_imagery, generate_timeline_animation
"""

import logging

from app.models.base import BaseAdapter
from app.agent.state import Observation
from app.config import settings

logger = logging.getLogger("satquery")


class TimelineAdapter(BaseAdapter):
    """Adapter for temporal timeline capabilities."""

    async def execute(self, arguments: dict, state, supabase_client) -> Observation:
        """
        Execute a timeline capability.

        Arguments:
        {
            "capability": "retrieve_temporal_imagery" | "generate_timeline_animation",
            "aoi": {GeoJSON},
            "date_start": "2019-01-01",
            "date_end": "2025-12-31",
            "collection": "Sentinel-2",
            "cloud_cover_max": 20
        }
        """
        capability = arguments.get("capability", "retrieve_temporal_imagery")

        if capability == "retrieve_temporal_imagery":
            return await self._retrieve_timeline(arguments, state, supabase_client)
        elif capability == "generate_timeline_animation":
            return await self._generate_animation(arguments, state, supabase_client)
        else:
            return Observation(
                step_number=state.current_step,
                source_capability=capability,
                status="failed",
                result={"error": f"Unknown timeline capability: {capability}"},
            )

    async def _retrieve_timeline(self, arguments, state, supabase_client) -> Observation:
        """Retrieve multi-year imagery from GEE."""
        from app.gee.connector import GEEConnector
        from app.timeline.processor import TimelineProcessor

        try:
            aoi = arguments.get("aoi") or getattr(state, "aoi", None)
            if not aoi:
                return Observation(
                    step_number=state.current_step,
                    source_capability="retrieve_temporal_imagery",
                    status="failed",
                    result={"error": "No AOI provided"},
                )

            date_start = arguments.get("date_start", "2019-01-01")
            date_end = arguments.get("date_end", "2025-12-31")
            collection = arguments.get("collection", "Sentinel-2")
            cloud_cover_max = arguments.get("cloud_cover_max", 20)

            # Authenticate GEE
            connector = GEEConnector(
                service_account_key_path=settings.gee_service_account_key_path,
                project_id=settings.gee_project_id,
            )
            auth_ok = await connector.authenticate()
            if not auth_ok:
                return Observation(
                    step_number=state.current_step,
                    source_capability="retrieve_temporal_imagery",
                    status="failed",
                    result={"error": "GEE authentication failed"},
                )

            scenes_by_year, ref_year = await TimelineProcessor.retrieve_timeline(
                connector, aoi, date_start, date_end, collection, cloud_cover_max
            )

            if not scenes_by_year:
                return Observation(
                    step_number=state.current_step,
                    source_capability="retrieve_temporal_imagery",
                    status="failed",
                    result={"error": "No imagery found for date range"},
                    confidence=0.0,
                )

            return Observation(
                step_number=state.current_step,
                source_capability="retrieve_temporal_imagery",
                status="success",
                result={
                    "years_retrieved": len(scenes_by_year),
                    "years": sorted(scenes_by_year.keys()),
                    "reference_year": ref_year,
                    "scenes_metadata": {
                        str(y): s for y, s in scenes_by_year.items()
                    },
                    "collection": collection,
                },
                confidence=0.90,
            )

        except Exception as e:
            logger.error(f"Timeline adapter error: {e}", exc_info=True)
            return Observation(
                step_number=state.current_step,
                source_capability="retrieve_temporal_imagery",
                status="failed",
                result={"error": str(e)},
                confidence=0.0,
            )

    async def _generate_animation(self, arguments, state, supabase_client) -> Observation:
        """Generate GIF/MP4 animation from frames."""
        from app.timeline.processor import TimelineProcessor

        try:
            frames = arguments.get("frames")
            labels = arguments.get("labels")
            fmt = arguments.get("format", "gif")

            if not frames:
                return Observation(
                    step_number=state.current_step,
                    source_capability="generate_timeline_animation",
                    status="failed",
                    result={"error": "No frames provided"},
                )

            import numpy as np
            np_frames = [np.array(f, dtype=np.uint8) for f in frames]

            if fmt == "gif":
                data = await TimelineProcessor.generate_gif(np_frames, labels)
            else:
                data = await TimelineProcessor.generate_mp4(np_frames)

            return Observation(
                step_number=state.current_step,
                source_capability="generate_timeline_animation",
                status="success",
                result={
                    "format": fmt,
                    "frame_count": len(np_frames),
                    "size_bytes": len(data),
                },
                confidence=0.90,
            )

        except Exception as e:
            logger.error(f"Animation adapter error: {e}", exc_info=True)
            return Observation(
                step_number=state.current_step,
                source_capability="generate_timeline_animation",
                status="failed",
                result={"error": str(e)},
                confidence=0.0,
            )
