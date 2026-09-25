import logging
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
import datetime

from app.gee.connector import GEEConnector

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------------
# Pydantic Schemas for Standardized Responses
# --------------------------------------------------------------------------------

class GEEToolResponse(BaseModel):
    success: bool = Field(..., description="Whether the tool execution was successful")
    tool: str = Field(..., description="The name of the tool executed")
    source: str = Field(default="GEE", description="The data source")
    data: Dict[str, Any] = Field(default_factory=dict, description="The primary scientific or queried data")
    visuals: List[str] = Field(default_factory=list, description="List of generated visual assets (URLs)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Provenance and processing metadata")
    quality: Dict[str, Any] = Field(default_factory=dict, description="Data quality indicators (e.g. cloud cover)")
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")


# --------------------------------------------------------------------------------
# GEEToolLayer: High-level Analytical Abstraction
# --------------------------------------------------------------------------------

class GEEToolLayer:
    """
    A stable, reusable service layer sitting above the GEEConnector.
    Exposes distinct analytical tools that return strictly structured GEEToolResponse objects.
    """
    
    def __init__(self, connector: GEEConnector = None):
        if connector:
            self.connector = connector
        else:
            from app.config import settings
            self.connector = GEEConnector(
                service_account_key_path=settings.gee_service_account_key_path,
                project_id=settings.gee_project_id
            )
        
    def _create_error_response(self, tool_name: str, error_msg: str) -> GEEToolResponse:
        """Helper to create a standard error response."""
        return GEEToolResponse(
            success=False,
            tool=tool_name,
            errors=[error_msg]
        )

    async def gee_search_imagery(
        self, 
        aoi: dict, 
        start_date: str, 
        end_date: str, 
        max_cloud_cover: int = 20
    ) -> GEEToolResponse:
        """Search for the best available imagery over an AOI within a date range."""
        tool_name = "gee_search_imagery"
        try:
            scenes = await self.connector.query_sentinel2(
                aoi_geojson=aoi,
                date_start=start_date,
                date_end=end_date,
                cloud_cover_max=max_cloud_cover,
                max_results=5
            )
            
            if not scenes:
                return self._create_error_response(tool_name, "No suitable imagery found for the specified period and cloud cover limit.")
                
            selected_scene = scenes[0]
            
            return GEEToolResponse(
                success=True,
                tool=tool_name,
                data={
                    "scenes": scenes,
                    "selected_scene": selected_scene
                },
                metadata={
                    "aoi": aoi,
                    "period": {"start": start_date, "end": end_date},
                    "collection": "COPERNICUS/S2_SR_HARMONIZED",
                    "provenance": "ESA / Google Earth Engine"
                },
                quality={
                    "cloud_cover_max": max_cloud_cover,
                    "selected_scene_cloud_cover": selected_scene.get("cloud_cover")
                }
            )
            
        except Exception as e:
            logger.error(f"gee_search_imagery failed: {e}")
            return self._create_error_response(tool_name, str(e))


    async def gee_calculate_indices(
        self,
        aoi: dict,
        scene_id: str,
        indices: List[str]
    ) -> GEEToolResponse:
        """Calculate specified remote sensing indices for a given scene and AOI."""
        tool_name = "gee_calculate_indices"
        try:
            stats = await self.connector.get_spatial_stats(scene_id, aoi)
            if not stats:
                return self._create_error_response(tool_name, "Failed to compute statistics. Data may be masked or invalid.")
                
            computed_indices = {}
            for idx in indices:
                idx_key = f"{idx.lower()}_mean"
                if idx_key in stats:
                    computed_indices[idx] = stats[idx_key]
                    
            return GEEToolResponse(
                success=True,
                tool=tool_name,
                data={
                    "indices": computed_indices,
                    "raw_stats": stats
                },
                metadata={
                    "aoi": aoi,
                    "scene_id": scene_id,
                    "processing": "Means calculated by Earth Engine Reducer"
                }
            )
        except Exception as e:
            logger.error(f"gee_calculate_indices failed: {e}")
            return self._create_error_response(tool_name, str(e))
            

    async def gee_get_zonal_statistics(
        self,
        aoi: dict,
        scene_id: str
    ) -> GEEToolResponse:
        """Get extended zonal statistics (mean, min, max, stdDev) for the AOI."""
        tool_name = "gee_get_zonal_statistics"
        try:
            stats = await self.connector.get_spatial_stats(scene_id, aoi)
            
            return GEEToolResponse(
                success=True,
                tool=tool_name,
                data={
                    "statistics": stats
                },
                metadata={
                    "aoi": aoi,
                    "scene_id": scene_id
                }
            )
        except Exception as e:
            logger.error(f"gee_get_zonal_statistics failed: {e}")
            return self._create_error_response(tool_name, str(e))


    async def gee_get_temporal_series(
        self,
        aoi: dict,
        start_date: str,
        end_date: str,
        indices: List[str] = None
    ) -> GEEToolResponse:
        """Retrieve a time series of index statistics across a date range."""
        tool_name = "gee_get_temporal_series"
        try:
            start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")
            
            # Calculate months between start and end
            delta = end_dt - start_dt
            months = max(1, int(delta.days / 30.44))
            
            # Dynamically determine interval based on total duration
            if months <= 3:
                interval_months = 1
            elif months <= 12:
                interval_months = 2
            elif months <= 36:
                interval_months = 3
            elif months <= 60:
                interval_months = 6
            else:
                interval_months = 12
            
            timeline = await self.connector.get_timeline_data(
                aoi_geojson=aoi, 
                start_date=start_date,
                end_date=end_date,
                interval_months=interval_months
            )
            if not timeline or "frames" not in timeline:
                return self._create_error_response(tool_name, "Failed to compute temporal series.")
                
            return GEEToolResponse(
                success=True,
                tool=tool_name,
                data={
                    "timeline": timeline["frames"],
                    "video_url": timeline.get("video_url")
                },
                metadata={
                    "aoi": aoi,
                    "period": {"start": start_date, "end": end_date},
                    "interval": f"approx {interval_months} months"
                }
            )
        except Exception as e:
            logger.error(f"gee_get_temporal_series failed: {e}")
            return self._create_error_response(tool_name, str(e))


    async def gee_compare_periods(
        self,
        aoi: dict,
        period_1: dict,
        period_2: dict,
        indices: List[str] = ["NDVI", "NDBI"]
    ) -> GEEToolResponse:
        """Compare statistics between two distinct periods for change detection."""
        tool_name = "gee_compare_periods"
        try:
            scenes_1 = await self.connector.query_sentinel2(
                aoi_geojson=aoi,
                date_start=period_1["start_date"],
                date_end=period_1["end_date"],
                max_results=1
            )
            
            scenes_2 = await self.connector.query_sentinel2(
                aoi_geojson=aoi,
                date_start=period_2["start_date"],
                date_end=period_2["end_date"],
                max_results=1
            )
            
            if not scenes_1 or not scenes_2:
                return self._create_error_response(tool_name, "Could not find valid imagery for both periods to compare.")
                
            scene_1 = scenes_1[0]["id"]
            scene_2 = scenes_2[0]["id"]
            
            stats_1 = await self.connector.get_spatial_stats(scene_1, aoi)
            stats_2 = await self.connector.get_spatial_stats(scene_2, aoi)
            
            changes = {}
            for idx in indices:
                idx_key = f"{idx.lower()}_mean"
                if idx_key in stats_1 and idx_key in stats_2:
                    val1 = stats_1[idx_key]
                    val2 = stats_2[idx_key]
                    if val1 is not None and val2 is not None:
                        changes[idx_key] = val2 - val1
                        
            return GEEToolResponse(
                success=True,
                tool=tool_name,
                data={
                    "period_1": {"scene_id": scene_1, "stats": stats_1},
                    "period_2": {"scene_id": scene_2, "stats": stats_2},
                    "changes": changes
                },
                metadata={
                    "aoi": aoi,
                    "comparison": f"{period_1} vs {period_2}"
                }
            )
        except Exception as e:
            logger.error(f"gee_compare_periods failed: {e}")
            return self._create_error_response(tool_name, str(e))


    async def gee_get_raster(
        self,
        aoi: dict,
        scene_id: str,
        index_name: str,
        dimensions: int = 1024
    ) -> GEEToolResponse:
        """Generate a visual raster (URL) for a specific index or RGB."""
        tool_name = "gee_get_raster"
        try:
            if index_name.upper() == "RGB":
                url = await self.connector.get_thumbnail_url(scene_id, aoi)
            else:
                url = await self.connector.compute_index_thumbnail_url(
                    scene_id=scene_id,
                    aoi_geojson=aoi,
                    index_name=index_name.upper(),
                    dimensions=dimensions
                )
                
            if not url:
                return self._create_error_response(tool_name, f"Failed to generate raster for {index_name}")
                
            # Extract date roughly from scene_id if possible
            import re
            date_match = re.search(r'/(\d{8})T', scene_id)
            scene_date = f"{date_match.group(1)[:4]}-{date_match.group(1)[4:6]}-{date_match.group(1)[6:8]}" if date_match else "unknown"
            
            return GEEToolResponse(
                success=True,
                tool=tool_name,
                data={
                    "type": f"{index_name.lower()}_raster",
                    "index": index_name.upper(),
                    "date": scene_date,
                    "aoi": aoi,
                    "url": url,
                    "visualization": {
                        "min": -1 if index_name.upper() != "RGB" else 0,
                        "max": 1 if index_name.upper() != "RGB" else 3000,
                        "palette": [] # Palette is handled by GEE connector internal styles
                    },
                    "source": "GEE"
                },
                visuals=[url],
                metadata={
                    "aoi": aoi,
                    "scene_id": scene_id,
                    "dimensions": dimensions
                }
            )
        except Exception as e:
            logger.error(f"gee_get_raster failed: {e}")
            return self._create_error_response(tool_name, str(e))

    async def gee_calculate_change_area(self, aoi: dict, scene_id_1: str, scene_id_2: str, index_name: str, threshold: float, direction: str) -> GEEToolResponse:
        tool_name = "gee_calculate_change_area"
        try:
            data = await self.connector.compute_change_area(aoi, scene_id_1, scene_id_2, index_name, threshold, direction)
            return GEEToolResponse(success=True, tool=tool_name, data=data, metadata={"aoi": aoi, "scene_1": scene_id_1, "scene_2": scene_id_2, "provenance": "Google Earth Engine spatial reduction"})
        except Exception as e:
            logger.error(f"{tool_name} failed: {e}")
            return self._create_error_response(tool_name, str(e))

    async def gee_detect_anomalies(self, aoi: dict, target_scene_id: str, index_name: str, threshold: float, hist_start: str, hist_end: str) -> GEEToolResponse:
        tool_name = "gee_detect_anomalies"
        try:
            data = await self.connector.compute_anomalies(aoi, target_scene_id, index_name, threshold, hist_start, hist_end)
            if not data.get("success", True):
                return self._create_error_response(tool_name, data.get("errors", [{}])[0].get("message", "Insufficient observations"))
            return GEEToolResponse(success=True, tool=tool_name, data=data, metadata={"aoi": aoi, "target_scene": target_scene_id, "provenance": "Google Earth Engine temporal z-score calculation"})
        except Exception as e:
            logger.error(f"{tool_name} failed: {e}")
            return self._create_error_response(tool_name, str(e))

    async def gee_get_subregion_statistics(self, aoi: dict, scene_id: str, index_name: str, grid_size_deg: float = 0.05) -> GEEToolResponse:
        tool_name = "gee_get_subregion_statistics"
        try:
            data = await self.connector.compute_subregion_statistics(aoi, scene_id, index_name, grid_size_deg)
            return GEEToolResponse(success=True, tool=tool_name, data=data, metadata={"aoi": aoi, "scene_id": scene_id, "provenance": "Google Earth Engine grid tessellation"})
        except Exception as e:
            logger.error(f"{tool_name} failed: {e}")
            return self._create_error_response(tool_name, str(e))

    async def gee_calculate_overlap(self, aoi: dict, scene_id_1: str, scene_id_2: str, index_1: str, threshold_1: float, dir_1: str, index_2: str, threshold_2: float, dir_2: str) -> GEEToolResponse:
        tool_name = "gee_calculate_overlap"
        try:
            data = await self.connector.compute_overlap(aoi, scene_id_1, scene_id_2, index_1, threshold_1, dir_1, index_2, threshold_2, dir_2)
            return GEEToolResponse(success=True, tool=tool_name, data=data, metadata={"aoi": aoi, "provenance": "Google Earth Engine logical intersection"})
        except Exception as e:
            logger.error(f"{tool_name} failed: {e}")
            return self._create_error_response(tool_name, str(e))

    async def gee_compare_indices(self, aoi: dict, scene_id: str, index_1: str, index_2: str, operation: str) -> GEEToolResponse:
        tool_name = "gee_compare_indices"
        try:
            data = await self.connector.compare_indices(aoi, scene_id, index_1, index_2, operation)
            return GEEToolResponse(success=True, tool=tool_name, data=data, metadata={"aoi": aoi, "scene_id": scene_id, "provenance": "Google Earth Engine spatial correlation/difference"})
        except Exception as e:
            logger.error(f"{tool_name} failed: {e}")
            return self._create_error_response(tool_name, str(e))

    async def gee_detect_hotspots(self, aoi: dict, scene_id_1: str, scene_id_2: str, index_name: str, threshold: float, direction: str) -> GEEToolResponse:
        tool_name = "gee_detect_hotspots"
        try:
            data = await self.connector.compute_hotspots(aoi, scene_id_1, scene_id_2, index_name, threshold, direction)
            return GEEToolResponse(success=True, tool=tool_name, data=data, metadata={"aoi": aoi, "provenance": "Google Earth Engine spatial convolution filter"})
        except Exception as e:
            logger.error(f"{tool_name} failed: {e}")
            return self._create_error_response(tool_name, str(e))

    # ------------------------------------------------------------------
    # Phase 6: Temporal Intelligence
    # ------------------------------------------------------------------

    async def gee_analyze_trend(self, aoi: dict, index_name: str, start_date: str, end_date: str) -> GEEToolResponse:
        tool_name = "gee_analyze_trend"
        try:
            data = await self.connector.compute_trend(aoi, index_name, start_date, end_date)
            if not data.get("success", True):
                return self._create_error_response(tool_name, data.get("errors", [{}])[0].get("message", "Trend failed"))
            return GEEToolResponse(success=True, tool=tool_name, data=data, metadata={"aoi": aoi, "provenance": "Google Earth Engine temporal linearFit"})
        except Exception as e:
            logger.error(f"{tool_name} failed: {e}")
            return self._create_error_response(tool_name, str(e))

    async def gee_analyze_seasonality(self, aoi: dict, index_name: str, start_date: str, end_date: str) -> GEEToolResponse:
        tool_name = "gee_analyze_seasonality"
        try:
            data = await self.connector.compute_seasonality(aoi, index_name, start_date, end_date)
            if not data.get("success", True):
                return self._create_error_response(tool_name, data.get("errors", [{}])[0].get("message", "Seasonality failed"))
            return GEEToolResponse(success=True, tool=tool_name, data=data, metadata={"aoi": aoi, "provenance": "Google Earth Engine monthly aggregation"})
        except Exception as e:
            logger.error(f"{tool_name} failed: {e}")
            return self._create_error_response(tool_name, str(e))

    async def gee_detect_temporal_breaks(self, aoi: dict, index_name: str, start_date: str, end_date: str, threshold: float = 2.0) -> GEEToolResponse:
        tool_name = "gee_detect_temporal_breaks"
        try:
            data = await self.connector.compute_temporal_breaks(aoi, index_name, start_date, end_date, threshold)
            return GEEToolResponse(success=True, tool=tool_name, data=data, metadata={"aoi": aoi, "provenance": "Google Earth Engine candidate deviation detection"})
        except Exception as e:
            logger.error(f"{tool_name} failed: {e}")
            return self._create_error_response(tool_name, str(e))

    async def gee_analyze_change_persistence(self, aoi: dict, index_name: str, pre_start: str, pre_end: str, post_start: str, post_end: str, threshold: float, direction: str) -> GEEToolResponse:
        tool_name = "gee_analyze_change_persistence"
        try:
            data = await self.connector.compute_change_persistence(aoi, index_name, pre_start, pre_end, post_start, post_end, threshold, direction)
            if not data.get("success", True):
                return self._create_error_response(tool_name, data.get("errors", [{}])[0].get("message", "Persistence failed"))
            return GEEToolResponse(success=True, tool=tool_name, data=data, metadata={"aoi": aoi, "provenance": "Google Earth Engine post-event fraction reduction"})
        except Exception as e:
            logger.error(f"{tool_name} failed: {e}")
            return self._create_error_response(tool_name, str(e))

    async def gee_analyze_event_window(self, aoi: dict, index_name: str, event_date: str, pre_days: int, post_days: int) -> GEEToolResponse:
        tool_name = "gee_analyze_event_window"
        try:
            data = await self.connector.compute_event_window(aoi, index_name, event_date, pre_days, post_days)
            if not data.get("success", True):
                return self._create_error_response(tool_name, data.get("errors", [{}])[0].get("message", "Event window failed"))
            return GEEToolResponse(success=True, tool=tool_name, data=data, metadata={"aoi": aoi, "provenance": "Google Earth Engine exact window reduction"})
        except Exception as e:
            logger.error(f"{tool_name} failed: {e}")
            return self._create_error_response(tool_name, str(e))

    async def gee_generate_timeline_artifact(
        self,
        aoi: dict,
        start_date: str,
        end_date: str,
        interval_months: int = 3,
        include_analytics: List[str] = None
    ) -> dict:
        """
        Generate a complete interactive timeline and timelapse visualization artifact.
        Returns a structured dictionary that the API routing will recognize and pass down 
        to the frontend UI as an interactive widget.
        """
        if include_analytics is None:
            include_analytics = []
            
        try:
            timeline_data = await self.connector.get_timeline_data(
                aoi_geojson=aoi,
                start_date=start_date,
                end_date=end_date,
                interval_months=interval_months
            )
            
            if not timeline_data or not timeline_data.get("frames"):
                return {"status": "error", "message": "No timeline data found for the given dates."}
                
            analytics_results = {}
            if "trend" in include_analytics:
                trend = await self.connector.compute_trend(aoi, "NDVI", start_date, end_date)
                if trend.get("success"):
                    analytics_results["trend"] = trend
            if "seasonality" in include_analytics:
                seasonality = await self.connector.compute_seasonality(aoi, "NDVI", start_date, end_date)
                if seasonality.get("success"):
                    analytics_results["seasonality"] = seasonality
            if "temporal_breaks" in include_analytics:
                breaks = await self.connector.compute_temporal_breaks(aoi, "NDVI", start_date, end_date)
                if breaks.get("success"):
                    analytics_results["temporal_breaks"] = breaks
                    
            if analytics_results:
                timeline_data["analytics"] = analytics_results
            
            return {
                "status": "success",
                "message": "Interactive timeline artifact generated successfully. Use this data to inform the user that the UI timeline has been generated.",
                "timeline_data": timeline_data
            }
            
        except Exception as e:
            logger.error(f"gee_generate_timeline_artifact failed: {e}")
            return {"status": "error", "message": str(e)}
