# app/registry/registry.py

import logging
from typing import Optional

logger = logging.getLogger("satquery")


class CapabilityRegistry:
    """Central registry of all capabilities"""

    def __init__(self):
        self.capabilities = {
            "validate_remote_sensing_input": {
                "name": "validate_remote_sensing_input",
                "description": "Validate satellite imagery inputs",
                "adapter": "GeospatialValidator"
            },
            "detect_bitemporal_change": {
                "name": "detect_bitemporal_change",
                "description": "Detect changes between two images",
                "adapter": "ChangeFormerAdapter"
            },
            "interpret_scene": {
                "name": "interpret_scene",
                "description": "Interpret satellite image content",
                "adapter": "GeoChatAdapter"
            },
            "analyze_sar_image": {
                "name": "analyze_sar_image",
                "description": "Analyze SAR imagery",
                "adapter": "SARMAEAdapter"
            },
            "calculate_changed_area": {
                "name": "calculate_changed_area",
                "description": "Calculate area of detected changes",
                "adapter": "GeospatialEngine"
            },
            # Phase 7: GEE/STAC capabilities
            "retrieve_satellite_imagery": {
                "name": "retrieve_satellite_imagery",
                "description": "Query and retrieve satellite imagery from Google Earth Engine",
                "required_args": ["aoi", "date_start", "date_end"],
                "optional_args": ["collections", "cloud_cover_max"],
                "adapter": "GEEAdapter"
            },
            "retrieve_dem": {
                "name": "retrieve_dem",
                "description": "Retrieve Digital Elevation Model from USGS 3DEP or SRTM",
                "required_args": ["aoi"],
                "optional_args": ["resolution_m"],
                "adapter": "GEEAdapter"
            },
            # Phase 8: Terrain capabilities
            "generate_terrain_2d": {
                "name": "generate_terrain_2d",
                "description": "Generate 2D terrain visualization (hillshade + contours) from DEM",
                "required_args": ["dem_data"],
                "optional_args": ["options"],
                "adapter": "TerrainAdapter"
            },
            "generate_terrain_3d": {
                "name": "generate_terrain_3d",
                "description": "Generate 3D terrain mesh (GLB) from DEM with optional texture",
                "required_args": ["dem_data", "aoi_bbox"],
                "optional_args": ["texture_rgb", "options"],
                "adapter": "TerrainAdapter"
            },
            # Phase 9: Timeline capabilities
            "retrieve_temporal_imagery": {
                "name": "retrieve_temporal_imagery",
                "description": "Retrieve multi-year satellite imagery from GEE (best scene per year)",
                "required_args": ["aoi", "date_start", "date_end"],
                "optional_args": ["collection", "cloud_cover_max"],
                "adapter": "TimelineAdapter"
            },
            "generate_timeline_animation": {
                "name": "generate_timeline_animation",
                "description": "Generate GIF or MP4 animation from multi-year imagery frames",
                "required_args": ["frames"],
                "optional_args": ["labels", "format"],
                "adapter": "TimelineAdapter"
            },
        }

        self.adapters = {}
        self._init_adapters()

    def _init_adapters(self):
        """Initialize all adapters"""
        from app.models.geospatial_engine import GeospatialEngine
        from app.models.changeformer_adapter import ChangeFormerAdapter
        from app.models.gee_adapter import GEEAdapter
        from app.models.terrain_adapter import TerrainAdapter
        from app.models.timeline_adapter import TimelineAdapter

        self.adapters["GeospatialValidator"] = GeospatialEngine()
        self.adapters["GeospatialEngine"] = GeospatialEngine()
        self.adapters["ChangeFormerAdapter"] = ChangeFormerAdapter()
        self.adapters["GEEAdapter"] = GEEAdapter()
        self.adapters["TerrainAdapter"] = TerrainAdapter()
        self.adapters["TimelineAdapter"] = TimelineAdapter()
        # Initialize others as needed

    def get_capability(self, name: str) -> Optional[dict]:
        """Get capability definition"""
        return self.capabilities.get(name)

    def get_adapter(self, capability_name: str):
        """Get adapter for capability"""
        cap = self.get_capability(capability_name)
        if not cap:
            return None
        adapter_name = cap["adapter"]
        return self.adapters.get(adapter_name)

