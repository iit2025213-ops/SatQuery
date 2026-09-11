# app/models/terrain_adapter.py

"""
Terrain Capability Adapter — Phase 8

Bridges AI Brain capability calls → TerrainProcessor.
Handles: generate_terrain_2d, generate_terrain_3d
"""

import logging
from typing import Optional

import numpy as np

from app.models.base import BaseAdapter
from app.agent.state import Observation
from app.terrain.processor import TerrainProcessor

logger = logging.getLogger("satquery")


class TerrainAdapter(BaseAdapter):
    """Adapter for terrain generation capabilities."""

    async def execute(self, arguments: dict, state, supabase_client) -> Observation:
        """
        Execute a terrain capability.

        Arguments:
        {
            "capability": "generate_terrain_2d" | "generate_terrain_3d",
            "mode": "2d" | "3d",
            "dem_data": [...],   # Elevation array (or retrieved from state)
            "aoi_bbox": [minx, miny, maxx, maxy],
            "options": {...}
        }
        """
        capability = arguments.get("capability", "generate_terrain_2d")
        mode = arguments.get("mode", "2d")

        if mode == "2d" or capability == "generate_terrain_2d":
            return await self._generate_2d(arguments, state, supabase_client)
        elif mode == "3d" or capability == "generate_terrain_3d":
            return await self._generate_3d(arguments, state, supabase_client)
        else:
            return Observation(
                step_number=state.current_step,
                source_capability=capability,
                status="failed",
                result={"error": f"Unknown terrain mode: {mode}"},
            )

    async def _generate_2d(self, arguments: dict, state, supabase_client) -> Observation:
        """Generate 2D terrain (hillshade + contours)."""
        try:
            dem_data = arguments.get("dem_data")
            if dem_data is not None:
                dem_data = np.array(dem_data, dtype=np.float32)
            else:
                return Observation(
                    step_number=state.current_step,
                    source_capability="generate_terrain_2d",
                    status="failed",
                    result={"error": "No DEM data provided"},
                )

            options = arguments.get("options", {})

            hillshade, contours, stats = await TerrainProcessor.generate_2d_terrain(
                dem_data, options
            )

            return Observation(
                step_number=state.current_step,
                source_capability="generate_terrain_2d",
                status="success",
                result={
                    "mode": "2d",
                    "hillshade_shape": list(hillshade.shape),
                    "contour_shape": list(contours.shape),
                    "elevation_stats": stats,
                },
                confidence=0.90,
            )

        except Exception as e:
            logger.error(f"Terrain 2D adapter error: {e}", exc_info=True)
            return Observation(
                step_number=state.current_step,
                source_capability="generate_terrain_2d",
                status="failed",
                result={"error": str(e)},
                confidence=0.0,
            )

    async def _generate_3d(self, arguments: dict, state, supabase_client) -> Observation:
        """Generate 3D terrain mesh."""
        try:
            dem_data = arguments.get("dem_data")
            if dem_data is not None:
                dem_data = np.array(dem_data, dtype=np.float32)
            else:
                return Observation(
                    step_number=state.current_step,
                    source_capability="generate_terrain_3d",
                    status="failed",
                    result={"error": "No DEM data provided"},
                )

            aoi_bbox = arguments.get("aoi_bbox", [0, 0, 1, 1])
            options = arguments.get("options", {})

            glb_bytes, metadata = await TerrainProcessor.generate_3d_terrain(
                dem_data, aoi_bbox, options=options
            )

            return Observation(
                step_number=state.current_step,
                source_capability="generate_terrain_3d",
                status="success",
                result={
                    "mode": "3d",
                    "mesh_metadata": metadata,
                    "glb_size_bytes": len(glb_bytes),
                },
                confidence=0.90,
            )

        except Exception as e:
            logger.error(f"Terrain 3D adapter error: {e}", exc_info=True)
            return Observation(
                step_number=state.current_step,
                source_capability="generate_terrain_3d",
                status="failed",
                result={"error": str(e)},
                confidence=0.0,
            )
