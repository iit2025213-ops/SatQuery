# app/gee/connector.py

"""
Google Earth Engine Connector — Phase 7

Authenticates via service account and queries satellite collections
(Sentinel-2, Landsat-8/9, MODIS) and DEM data (USGS 3DEP, SRTM).

Source of truth: 6-9.md Phase 7 architecture.
"""

import os
import json
import logging
import asyncio
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timezone

logger = logging.getLogger("satquery")

# GEE import is deferred — only loaded when authenticate() is called
# so the server starts even without earthengine-api installed
_ee = None


def _get_ee():
    """Lazy-import earthengine-api."""
    global _ee
    if _ee is None:
        import ee
        _ee = ee
    return _ee


class GEEConnector:
    """
    Google Earth Engine integration.

    Authenticates with a service account (not OAuth) for server-side
    automation, as specified in 6-9.md.
    """

    # Sentinel-2 band metadata
    SENTINEL2_BANDS = {
        "B2":  {"name": "Blue",  "wavelength_nm": 490,  "resolution_m": 10},
        "B3":  {"name": "Green", "wavelength_nm": 560,  "resolution_m": 10},
        "B4":  {"name": "Red",   "wavelength_nm": 665,  "resolution_m": 10},
        "B8":  {"name": "NIR",   "wavelength_nm": 842,  "resolution_m": 10},
        "B11": {"name": "SWIR1", "wavelength_nm": 1610, "resolution_m": 20},
        "B12": {"name": "SWIR2", "wavelength_nm": 2190, "resolution_m": 20},
    }

    # Landsat 8/9 band metadata
    LANDSAT_BANDS = {
        "SR_B2": {"name": "Blue",  "wavelength_nm": 482,  "resolution_m": 30},
        "SR_B3": {"name": "Green", "wavelength_nm": 562,  "resolution_m": 30},
        "SR_B4": {"name": "Red",   "wavelength_nm": 655,  "resolution_m": 30},
        "SR_B5": {"name": "NIR",   "wavelength_nm": 865,  "resolution_m": 30},
        "SR_B6": {"name": "SWIR1", "wavelength_nm": 1609, "resolution_m": 30},
        "SR_B7": {"name": "SWIR2", "wavelength_nm": 2201, "resolution_m": 30},
    }

    def __init__(self, service_account_key_path: Optional[str], project_id: Optional[str]):
        self.service_account_key_path = service_account_key_path
        self.project_id = project_id
        self.authenticated = False
        logger.info("GEEConnector initialised (auth pending)")

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    async def authenticate(self) -> bool:
        """
        Authenticate to GEE using a service account key file.

        Uses ee.ServiceAccountCredentials (server-side, not interactive OAuth).
        """
        ee = _get_ee()

        if self.authenticated:
            return True

        if not self.service_account_key_path or not os.path.exists(self.service_account_key_path):
            logger.error(
                f"GEE service account key not found at: {self.service_account_key_path}"
            )
            return False

        if not self.project_id:
            logger.error("GEE project ID not configured")
            return False

        try:
            # Read the key file to extract the service account email
            with open(self.service_account_key_path, "r") as f:
                key_data = json.load(f)

            service_account_email = key_data.get("client_email")
            if not service_account_email:
                logger.error("Service account key file missing 'client_email'")
                return False

            credentials = ee.ServiceAccountCredentials(
                service_account_email,
                self.service_account_key_path,
            )

            ee.Initialize(credentials=credentials, project=self.project_id)

            self.authenticated = True
            logger.info(f"✅ GEE authenticated — project: {self.project_id}")
            return True

        except Exception as e:
            logger.error(f"❌ GEE authentication failed: {e}")
            return False

    def _ensure_authenticated(self):
        """Raise if not authenticated."""
        if not self.authenticated:
            raise RuntimeError("GEE not authenticated. Call authenticate() first.")

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------

    @staticmethod
    def geojson_to_ee_geometry(geojson: dict):
        """Convert a GeoJSON Polygon dict to an ee.Geometry."""
        ee = _get_ee()
        coords = geojson["coordinates"][0]  # outer ring
        ee_coords = [[c[0], c[1]] for c in coords]
        return ee.Geometry.Polygon(ee_coords)

    # ------------------------------------------------------------------
    # Sentinel-2 queries
    # ------------------------------------------------------------------

    async def query_sentinel2(
        self,
        aoi_geojson: dict,
        date_start: str,
        date_end: str,
        cloud_cover_max: int = 20,
        max_results: int = 10,
    ) -> List[Dict]:
        """
        Query Sentinel-2 Level-2A (surface reflectance) imagery.

        Returns a list of scene metadata dicts sorted by cloud cover (ascending).
        """
        ee = _get_ee()
        self._ensure_authenticated()

        try:
            aoi_geom = self.geojson_to_ee_geometry(aoi_geojson)

            collection = (
                ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                .filterBounds(aoi_geom)
                .filterDate(date_start, date_end)
                .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_cover_max))
                .sort("CLOUDY_PIXEL_PERCENTAGE")
            )

            # Fetch metadata (capped)
            image_list = collection.toList(max_results).getInfo()

            if not image_list:
                logger.warning("No Sentinel-2 imagery found for AOI / date range")
                return []

            scenes: List[Dict] = []
            for img in image_list:
                try:
                    props = img["properties"]
                    ts = props.get("system:time_start", 0)
                    acq_date = datetime.fromtimestamp(ts / 1000, timezone.utc).strftime("%Y-%m-%d")

                    scenes.append({
                        "id": img["id"],
                        "source": "Sentinel-2",
                        "acquisition_date": acq_date,
                        "cloud_cover_percent": props.get("CLOUDY_PIXEL_PERCENTAGE", 0),
                        "bands": list(self.SENTINEL2_BANDS.keys()),
                        "band_wavelengths": {
                            b: info["wavelength_nm"]
                            for b, info in self.SENTINEL2_BANDS.items()
                        },
                        "resolution_m": 10,
                        "crs": props.get("EPSG", "EPSG:32643"),
                    })
                except Exception as exc:
                    logger.warning(f"Skipping Sentinel-2 scene: {exc}")

            logger.info(f"✅ Found {len(scenes)} Sentinel-2 scenes")
            return scenes

        except Exception as e:
            logger.error(f"❌ Sentinel-2 query error: {e}")
            return []

    # ------------------------------------------------------------------
    # Landsat 8/9 queries
    # ------------------------------------------------------------------

    async def query_landsat(
        self,
        aoi_geojson: dict,
        date_start: str,
        date_end: str,
        cloud_cover_max: int = 20,
        max_results: int = 10,
    ) -> List[Dict]:
        """Query Landsat 8/9 Collection 2 Level-2 imagery."""
        ee = _get_ee()
        self._ensure_authenticated()

        try:
            aoi_geom = self.geojson_to_ee_geometry(aoi_geojson)

            # Landsat 9
            l9 = (
                ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
                .filterBounds(aoi_geom)
                .filterDate(date_start, date_end)
                .filter(ee.Filter.lt("CLOUD_COVER", cloud_cover_max))
            )

            # Landsat 8
            l8 = (
                ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
                .filterBounds(aoi_geom)
                .filterDate(date_start, date_end)
                .filter(ee.Filter.lt("CLOUD_COVER", cloud_cover_max))
            )

            # Merge and sort
            merged = l9.merge(l8).sort("CLOUD_COVER")
            image_list = merged.toList(max_results).getInfo()

            if not image_list:
                logger.warning("No Landsat imagery found for AOI / date range")
                return []

            scenes: List[Dict] = []
            for img in image_list:
                try:
                    props = img["properties"]
                    ts = props.get("system:time_start", 0)
                    acq_date = datetime.fromtimestamp(ts / 1000, timezone.utc).strftime("%Y-%m-%d")
                    spacecraft = props.get("SPACECRAFT_ID", "LANDSAT_9")
                    source = "Landsat-9" if "9" in spacecraft else "Landsat-8"

                    scenes.append({
                        "id": img["id"],
                        "source": source,
                        "acquisition_date": acq_date,
                        "cloud_cover_percent": props.get("CLOUD_COVER", 0),
                        "bands": list(self.LANDSAT_BANDS.keys()),
                        "band_wavelengths": {
                            b: info["wavelength_nm"]
                            for b, info in self.LANDSAT_BANDS.items()
                        },
                        "resolution_m": 30,
                        "crs": props.get("EPSG", "EPSG:32643"),
                    })
                except Exception as exc:
                    logger.warning(f"Skipping Landsat scene: {exc}")

            logger.info(f"✅ Found {len(scenes)} Landsat scenes")
            return scenes

        except Exception as e:
            logger.error(f"❌ Landsat query error: {e}")
            return []

    # ------------------------------------------------------------------
    # DEM retrieval
    # ------------------------------------------------------------------

    async def retrieve_dem(
        self,
        aoi_geojson: dict,
        resolution_m: int = 30,
    ) -> Optional[Dict]:
        """
        Retrieve DEM metadata + elevation statistics.

        Uses USGS 3DEP (10 m) for high-res or SRTM (30 m) as fallback.
        """
        ee = _get_ee()
        self._ensure_authenticated()

        try:
            aoi_geom = self.geojson_to_ee_geometry(aoi_geojson)

            # Choose DEM source
            if resolution_m <= 10:
                dem_image = ee.Image("USGS/3DEP/10m")
                source = "USGS-3DEP"
                band_name = "elevation"
            else:
                dem_image = ee.Image("USGS/SRTMGL1_003")
                source = "SRTM"
                band_name = "elevation"

            dem = dem_image.select(band_name).clip(aoi_geom)

            # Compute stats
            stats = dem.reduceRegion(
                reducer=(
                    ee.Reducer.min()
                    .combine(ee.Reducer.max(), None, True)
                    .combine(ee.Reducer.mean(), None, True)
                    .combine(ee.Reducer.stdDev(), None, True)
                ),
                geometry=aoi_geom,
                scale=resolution_m,
                maxPixels=1e9,
            ).getInfo()

            elevation_stats = {
                "min_m": stats.get(f"{band_name}_min", 0),
                "max_m": stats.get(f"{band_name}_max", 0),
                "mean_m": stats.get(f"{band_name}_mean", 0),
                "std_m": stats.get(f"{band_name}_stdDev", 0),
            }

            logger.info(f"✅ DEM retrieved ({source}): {elevation_stats}")

            return {
                "source": source,
                "resolution_m": resolution_m,
                "elevation_stats": elevation_stats,
                "crs": "EPSG:4326",
            }

        except Exception as e:
            logger.error(f"❌ DEM retrieval error: {e}")
            return None

    # ------------------------------------------------------------------
    # Cloud masking
    # ------------------------------------------------------------------

    @staticmethod
    def apply_sentinel2_cloud_mask(image):
        """
        Apply SCL-based cloud mask to a Sentinel-2 image.

        Masks out: clouds (high/medium probability), cirrus, cloud shadows.
        """
        ee = _get_ee()
        scl = image.select("SCL")
        # SCL classes to mask: 3=cloud_shadow, 8=cloud_medium, 9=cloud_high, 10=cirrus
        mask = (
            scl.neq(3)
            .And(scl.neq(8))
            .And(scl.neq(9))
            .And(scl.neq(10))
        )
        return image.updateMask(mask)

    @staticmethod
    def apply_landsat_cloud_mask(image):
        """Apply QA_PIXEL-based cloud mask to a Landsat image."""
        ee = _get_ee()
        qa = image.select("QA_PIXEL")
        # Bit 3 = cloud, Bit 4 = cloud shadow
        cloud_mask = qa.bitwiseAnd(1 << 3).eq(0)
        shadow_mask = qa.bitwiseAnd(1 << 4).eq(0)
        return image.updateMask(cloud_mask).updateMask(shadow_mask)

    # ------------------------------------------------------------------
    # Download & process (for future Cloudinary upload)
    # ------------------------------------------------------------------

    async def download_and_process(
        self,
        scene_id: str,
        aoi_geojson: dict,
        bands: List[str],
        apply_cloud_mask: bool = True,
    ) -> Optional[Dict]:
        """
        Process a GEE scene: select bands, clip to AOI, cloud-mask.

        Returns the processed ee.Image metadata.

        NOTE: Actual file export to GCS/Cloudinary will be added when
        Cloud Storage bucket is configured. For now, this prepares the
        image and returns metadata.
        """
        ee = _get_ee()
        self._ensure_authenticated()

        try:
            aoi_geom = self.geojson_to_ee_geometry(aoi_geojson)
            image = ee.Image(scene_id)

            # Select bands
            image = image.select(bands)

            # Cloud mask
            if apply_cloud_mask:
                if "S2" in scene_id or "COPERNICUS" in scene_id:
                    # Need SCL band for masking — re-load full image
                    full_image = ee.Image(scene_id)
                    image = self.apply_sentinel2_cloud_mask(full_image).select(bands)
                elif "LANDSAT" in scene_id:
                    full_image = ee.Image(scene_id)
                    image = self.apply_landsat_cloud_mask(full_image).select(bands)

            # Clip to AOI
            image = image.clip(aoi_geom)

            # Get properties
            info = image.getInfo()
            props = info.get("properties", {}) if info else {}

            logger.info(f"✅ Processed scene: {scene_id}")

            return {
                "scene_id": scene_id,
                "bands": bands,
                "processed": True,
                "properties": props,
            }

        except Exception as e:
            logger.error(f"❌ Error processing scene {scene_id}: {e}")
            return None

    # ------------------------------------------------------------------
    # Thumbnail generation (getThumbURL)
    # ------------------------------------------------------------------

    async def get_thumbnail_url(
        self,
        scene_id: str,
        aoi_geojson: dict,
        bands: List[str] = None,
        vis_min: int = 0,
        vis_max: int = 3000,
        dimensions: int = 1024,
    ) -> Optional[str]:
        """
        Generate a signed PNG thumbnail URL for an RGB true-color view.

        Uses GEE's getThumbURL() — renders the image server-side and
        returns a direct download link. No Cloud Storage bucket required.
        """
        ee = _get_ee()
        self._ensure_authenticated()

        if bands is None:
            # Sentinel-2 RGB default
            if "COPERNICUS" in scene_id or "S2" in scene_id:
                bands = ["B4", "B3", "B2"]
            else:
                # Landsat
                bands = ["SR_B4", "SR_B3", "SR_B2"]

        try:
            aoi_geom = self.geojson_to_ee_geometry(aoi_geojson)
            image = ee.Image(scene_id).select(bands).clip(aoi_geom)

            thumb_url = image.getThumbURL({
                "bands": bands,
                "region": aoi_geom,
                "dimensions": dimensions,
                "format": "png",
                "min": vis_min,
                "max": vis_max,
            })

            logger.info(f"✅ Thumbnail URL generated for scene: {scene_id}")
            return thumb_url

        except Exception as e:
            logger.error(f"❌ Failed to generate thumbnail URL for {scene_id}: {e}")
            return None

    async def compute_index_thumbnail_url(
        self,
        scene_id: str,
        aoi_geojson: dict,
        index_name: str,
        dimensions: int = 1024,
    ) -> Optional[str]:
        """
        Compute an index (NDVI, NDWI, NDBI, NBR) and return a signed PNG thumbnail URL 
        with an appropriate color palette.
        """
        ee = _get_ee()
        self._ensure_authenticated()

        try:
            aoi_geom = self.geojson_to_ee_geometry(aoi_geojson)
            image = ee.Image(scene_id)

            if "COPERNICUS" in scene_id or "S2" in scene_id:
                green, red, nir = "B3", "B4", "B8"
                swir1, swir2 = "B11", "B12"
            else:
                green, red, nir = "SR_B3", "SR_B4", "SR_B5"
                swir1, swir2 = "SR_B6", "SR_B7"

            index_name = index_name.upper()
            if index_name == "NDVI":
                bands_to_use = [nir, red]
                palette = ["#d73027", "#fc8d59", "#fee08b", "#91cf60", "#1a9850"] # Red -> Green
            elif index_name == "NDWI":
                bands_to_use = [green, nir]
                palette = ["#ffffcc", "#a1dab4", "#41b6c4", "#2c7fb8", "#253494"] # White -> Blue
            elif index_name == "NDBI":
                bands_to_use = [swir1, nir]
                palette = ["#fef0d9", "#fdcc8a", "#fc8d59", "#e34a33", "#b30000"] # White -> Red
            elif index_name == "NBR":
                bands_to_use = [nir, swir2]
                palette = ["#ffffcc", "#ffeda0", "#fed976", "#feb24c", "#fd8d3c", "#fc4e2a", "#e31a1c", "#000000"] # Yellow -> Black
            else:
                logger.error(f"Unknown index requested: {index_name}")
                return None

            # Clip to the bounding box so the output image is rectangular (like Mapbox)
            # rather than an irregular clipped polygon which might get squashed in DOCX.
            index_img = image.normalizedDifference(bands_to_use).rename(index_name).clip(aoi_geom.bounds())

            thumb_url = index_img.getThumbURL({
                "bands": [index_name],
                "region": aoi_geom.bounds(),
                "dimensions": dimensions,
                "format": "png",
                "min": -0.2,
                "max": 0.8,
                "palette": palette,
            })

            logger.info(f"✅ {index_name} thumbnail URL generated for scene: {scene_id}")
            return thumb_url

        except Exception as e:
            logger.error(f"❌ Failed to compute {index_name} thumbnail for {scene_id}: {e}")
            return None

    async def get_spatial_stats(
        self,
        scene_id: str,
        aoi_geojson: dict,
    ) -> Optional[Dict]:
        """Compute mean values for multiple indices (NDVI, NDWI, NDBI, NBR) over the AOI."""
        ee = _get_ee()
        self._ensure_authenticated()

        try:
            aoi_geom = self.geojson_to_ee_geometry(aoi_geojson)
            image = ee.Image(scene_id)

            if "COPERNICUS" in scene_id or "S2" in scene_id:
                green, red, nir = "B3", "B4", "B8"
                swir1, swir2 = "B11", "B12"
            else:
                green, red, nir = "SR_B3", "SR_B4", "SR_B5"
                swir1, swir2 = "SR_B6", "SR_B7"

            # Compute indices
            ndvi = image.normalizedDifference([nir, red]).rename("NDVI")
            ndwi = image.normalizedDifference([green, nir]).rename("NDWI")
            ndbi = image.normalizedDifference([swir1, nir]).rename("NDBI")
            nbr = image.normalizedDifference([nir, swir2]).rename("NBR")
            
            multi_index = ee.Image([ndvi, ndwi, ndbi, nbr]).clip(aoi_geom)

            combined_reducer = ee.Reducer.mean().combine(
                reducer2=ee.Reducer.minMax(),
                sharedInputs=True
            ).combine(
                reducer2=ee.Reducer.stdDev(),
                sharedInputs=True
            )

            stats = multi_index.reduceRegion(
                reducer=combined_reducer,
                geometry=aoi_geom,
                scale=100,
                maxPixels=1e8,
            ).getInfo()

            return {
                "ndvi_mean": round(stats.get("NDVI_mean", 0) or 0, 3),
                "ndvi_min": round(stats.get("NDVI_min", 0) or 0, 3),
                "ndvi_max": round(stats.get("NDVI_max", 0) or 0, 3),
                "ndvi_std": round(stats.get("NDVI_stdDev", 0) or 0, 3),
                "ndwi_mean": round(stats.get("NDWI_mean", 0) or 0, 3),
                "ndwi_min": round(stats.get("NDWI_min", 0) or 0, 3),
                "ndwi_max": round(stats.get("NDWI_max", 0) or 0, 3),
                "ndwi_std": round(stats.get("NDWI_stdDev", 0) or 0, 3),
                "ndbi_mean": round(stats.get("NDBI_mean", 0) or 0, 3),
                "ndbi_min": round(stats.get("NDBI_min", 0) or 0, 3),
                "ndbi_max": round(stats.get("NDBI_max", 0) or 0, 3),
                "ndbi_std": round(stats.get("NDBI_stdDev", 0) or 0, 3),
                "nbr_mean": round(stats.get("NBR_mean", 0) or 0, 3),
                "nbr_min": round(stats.get("NBR_min", 0) or 0, 3),
                "nbr_max": round(stats.get("NBR_max", 0) or 0, 3),
                "nbr_std": round(stats.get("NBR_stdDev", 0) or 0, 3),
            }

        except Exception as e:
            logger.error(f"❌ Failed to compute spatial stats for {scene_id}: {e}")
            return None

    # ------------------------------------------------------------------
    # Timeline & Time-Series Data
    # ------------------------------------------------------------------

    async def get_timeline_data(
        self,
        aoi_geojson: dict,
        start_date: str = None,
        end_date: str = None,
        interval_months: int = 3,
    ) -> Optional[Dict]:
        """
        Generate time-series imagery and stats for a given period.
        Returns a list of frames with exact acquisition dates, and the AOI bounds.
        """
        import asyncio
        from datetime import datetime, timezone
        from dateutil.relativedelta import relativedelta
        
        self._ensure_authenticated()

        try:
            frames = []
            now = datetime.now(timezone.utc)
            
            if not end_date:
                end_dt = now
            else:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                
            if not start_date:
                start_dt = end_dt - relativedelta(months=36)
            else:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            
            # 1. Fetch best scene for each interval
            scene_tasks = []
            
            # Calculate total months difference
            total_months = (end_dt.year - start_dt.year) * 12 + (end_dt.month - start_dt.month)
            num_steps = max(1, total_months // interval_months)
            
            current_dt = start_dt
            for i in range(num_steps):
                step_end = current_dt + relativedelta(months=interval_months)
                if step_end > end_dt and i == num_steps - 1:
                    step_end = end_dt
                
                # We want the single least cloudy image for this month interval
                scene_tasks.append(
                    self.query_sentinel2(
                        aoi_geojson=aoi_geojson,
                        date_start=current_dt.strftime("%Y-%m-%d"),
                        date_end=step_end.strftime("%Y-%m-%d"),
                        cloud_cover_max=30,
                        max_results=1
                    )
                )
                current_dt = step_end
                
            monthly_scenes = await asyncio.gather(*scene_tasks)
            
            # 2. For each valid scene, fetch thumbnail and NDVI stats concurrently
            process_tasks = []
            valid_scenes = []
            
            for scenes in monthly_scenes:
                if not scenes:
                    continue
                    
                scene = scenes[0]
                valid_scenes.append(scene)
                
                process_tasks.append(
                    asyncio.gather(
                        self.get_thumbnail_url(scene["id"], aoi_geojson),
                        self.get_spatial_stats(scene["id"], aoi_geojson)
                    )
                )
                
            if not process_tasks:
                return None
                
            results = await asyncio.gather(*process_tasks)
            
            for i, (thumb_url, stats) in enumerate(results):
                scene = valid_scenes[i]
                frames.append({
                    "date": scene.get("acquisition_date"),
                    "scene_id": scene.get("id"),
                    "cloud_cover": scene.get("cloud_cover_percent"),
                    "source": "Sentinel-2",
                    "thumbnail_url": thumb_url,
                    "ndvi_mean": stats.get("ndvi_mean") if stats else None,
                    "ndwi_mean": stats.get("ndwi_mean") if stats else None,
                    "ndbi_mean": stats.get("ndbi_mean") if stats else None,
                    "nbr_mean": stats.get("nbr_mean") if stats else None,
                    "quality": "acceptable" if stats else "unknown"
                })
                
            # 3. Calculate bounding box of AOI to overlay the image on the map
            ee = _get_ee()
            aoi_geom = self.geojson_to_ee_geometry(aoi_geojson)
            bbox = aoi_geom.bounds().coordinates().getInfo()[0]
            lons = [c[0] for c in bbox]
            lats = [c[1] for c in bbox]
            bounds = [min(lons), min(lats), max(lons), max(lats)]
            
            # Generate Time-Lapse Video URL
            video_url = None
            scene_ids = [f["scene_id"] for f in frames]
            if scene_ids:
                try:
                    # Create an ImageCollection from ONLY the explicitly selected best scenes
                    images = [ee.Image(sid) for sid in scene_ids]
                    collection = ee.ImageCollection(images).select(['B4', 'B3', 'B2'])
                    
                    def apply_scaling(image):
                        return image.visualize(min=0, max=3000, gamma=1.4).clip(aoi_geom)
                    
                    scaled_collection = collection.map(apply_scaling)
                    
                    video_url = scaled_collection.getVideoThumbURL({
                        'dimensions': 256,
                        'framesPerSecond': 2,
                        'region': aoi_geom,
                        'format': 'gif'
                    })
                    logger.info(f"✅ Generated timelapse video URL from GEE: {video_url}")
                except Exception as vid_err:
                    logger.error(f"Failed to generate video thumbnail: {vid_err}")

            return {
                "frames": frames,
                "video_url": video_url,
                "bbox": bounds,
                "aoi": aoi_geojson
            }

        except Exception as e:
            logger.error(f"❌ Failed to generate timeline data: {e}")
            return None

    async def generate_timelapse_url(self, scene_ids: list, aoi_geojson: dict) -> str:
        """Generate a GEE timelapse GIF URL from a list of specific scene IDs."""
        ee = _get_ee()
        try:
            aoi_geom = self.geojson_to_ee_geometry(aoi_geojson)
            images = [ee.Image(sid) for sid in scene_ids]
            collection = ee.ImageCollection(images).select(['B4', 'B3', 'B2'])

            def apply_scaling(image):
                return image.visualize(min=0, max=3000, gamma=1.4).clip(aoi_geom)

            scaled_collection = collection.map(apply_scaling)
            video_url = scaled_collection.getVideoThumbURL({
                'dimensions': 320,
                'framesPerSecond': 2,
                'region': aoi_geom,
                'format': 'gif'
            })
            logger.info(f"✅ Generated timelapse URL from {len(scene_ids)} scenes: {video_url}")
            return video_url
        except Exception as e:
            logger.error(f"Failed to generate timelapse URL: {e}")
            return None

    # ------------------------------------------------------------------
    # Phase 5: Advanced Geospatial Analytics
    # ------------------------------------------------------------------

    def _get_index_image(self, scene_id: str, index_name: str):
        ee = _get_ee()
        image = ee.Image(scene_id)
        if "COPERNICUS" in scene_id or "S2" in scene_id:
            green, red, nir = "B3", "B4", "B8"
            swir1, swir2 = "B11", "B12"
        else:
            green, red, nir = "SR_B3", "SR_B4", "SR_B5"
            swir1, swir2 = "SR_B6", "SR_B7"
            
        index_name = index_name.upper()
        if index_name == "NDVI":
            return image.normalizedDifference([nir, red]).rename(index_name)
        elif index_name == "NDWI":
            return image.normalizedDifference([green, nir]).rename(index_name)
        elif index_name == "NDBI":
            return image.normalizedDifference([swir1, nir]).rename(index_name)
        elif index_name == "NBR":
            return image.normalizedDifference([nir, swir2]).rename(index_name)
        else:
            raise ValueError(f"Unknown index: {index_name}")

    async def compute_change_area(self, aoi_geojson: dict, scene_id_1: str, scene_id_2: str, index_name: str, threshold: float, direction: str) -> dict:
        ee = _get_ee()
        self._ensure_authenticated()
        
        aoi_geom = self.geojson_to_ee_geometry(aoi_geojson)
        img1 = self._get_index_image(scene_id_1, index_name)
        img2 = self._get_index_image(scene_id_2, index_name)
        
        diff = img2.subtract(img1)
        if direction == "decrease":
            mask = diff.lte(threshold)
        else:
            mask = diff.gte(threshold)
            
        pixel_area = ee.Image.pixelArea().updateMask(mask)
        area_dict = pixel_area.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=aoi_geom,
            scale=10,
            maxPixels=1e9
        ).getInfo()
        
        total_area_dict = ee.Image.pixelArea().reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=aoi_geom,
            scale=10,
            maxPixels=1e9
        ).getInfo()
        
        area_sq_m = area_dict.get('area') or 0
        total_sq_m = total_area_dict.get('area') or 1  # prevent div by zero
        
        area_km2 = area_sq_m / 1e6
        total_km2 = total_sq_m / 1e6
        
        return {
            "changed_area_km2": round(area_km2, 4),
            "aoi_area_km2": round(total_km2, 4),
            "percentage_of_aoi": round((area_km2 / total_km2) * 100, 2),
            "crs": "EPSG:4326",
            "scale": 10,
            "methodology": f"|{index_name}_2 - {index_name}_1| {direction} threshold {threshold}"
        }

    async def compute_overlap(self, aoi_geojson: dict, scene_id_1: str, scene_id_2: str, index_1: str, threshold_1: float, dir_1: str, index_2: str, threshold_2: float, dir_2: str) -> dict:
        ee = _get_ee()
        self._ensure_authenticated()
        
        aoi_geom = self.geojson_to_ee_geometry(aoi_geojson)
        
        i1_t1 = self._get_index_image(scene_id_1, index_1)
        i1_t2 = self._get_index_image(scene_id_2, index_1)
        diff_1 = i1_t2.subtract(i1_t1)
        mask_1 = diff_1.lte(threshold_1) if dir_1 == "decrease" else diff_1.gte(threshold_1)
        
        i2_t1 = self._get_index_image(scene_id_1, index_2)
        i2_t2 = self._get_index_image(scene_id_2, index_2)
        diff_2 = i2_t2.subtract(i2_t1)
        mask_2 = diff_2.lte(threshold_2) if dir_2 == "decrease" else diff_2.gte(threshold_2)
        
        overlap_mask = mask_1.And(mask_2)
        
        pixel_area = ee.Image.pixelArea().updateMask(overlap_mask)
        area_dict = pixel_area.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=aoi_geom,
            scale=10,
            maxPixels=1e9
        ).getInfo()
        
        total_area_dict = ee.Image.pixelArea().reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=aoi_geom,
            scale=10,
            maxPixels=1e9
        ).getInfo()
        
        area_sq_m = area_dict.get('area') or 0
        total_sq_m = total_area_dict.get('area') or 1
        
        return {
            "overlap_area_km2": round(area_sq_m / 1e6, 4),
            "aoi_area_km2": round(total_sq_m / 1e6, 4),
            "overlap_percentage": round((area_sq_m / total_sq_m) * 100, 2),
            "crs": "EPSG:4326",
            "scale": 10,
            "methodology": "Logical AND intersection of two temporal change masks"
        }

    async def compute_subregion_statistics(self, aoi_geojson: dict, scene_id: str, index_name: str, grid_size_deg: float = 0.05) -> dict:
        ee = _get_ee()
        self._ensure_authenticated()
        
        aoi_geom = self.geojson_to_ee_geometry(aoi_geojson)
        img = self._get_index_image(scene_id, index_name)
        
        grid = ee.Geometry(aoi_geom).coveringGrid("EPSG:4326", grid_size_deg)
        grid_clipped = grid.map(lambda f: ee.Feature(ee.Feature(f).intersection(aoi_geom, 10)))
        
        stats = img.reduceRegions(
            collection=grid_clipped,
            reducer=ee.Reducer.mean().combine(ee.Reducer.count(), None, True),
            scale=10
        ).getInfo()
        
        regions = []
        for feature in stats.get('features', []):
            props = feature.get('properties', {})
            mean_val = props.get('mean')
            count_val = props.get('count')
            if mean_val is not None and count_val is not None and count_val > 0:
                regions.append({
                    "id": feature.get('id'),
                    f"{index_name}_mean": round(mean_val, 3),
                    "valid_pixels": count_val
                })
                
        return {
            "regions": regions,
            "crs": "EPSG:4326",
            "grid_size_deg": grid_size_deg,
            "methodology": "Configurable regular rectangular grid clipped to AOI"
        }

    async def compute_anomalies(self, aoi_geojson: dict, target_scene_id: str, index_name: str, threshold: float, hist_start: str, hist_end: str) -> dict:
        ee = _get_ee()
        self._ensure_authenticated()
        
        aoi_geom = self.geojson_to_ee_geometry(aoi_geojson)
        
        # Historical collection
        collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(aoi_geom)
            .filterDate(hist_start, hist_end)
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
        )
        
        def calc_idx(img):
            idx = index_name.upper()
            if idx == "NDVI": return img.normalizedDifference(["B8", "B4"]).rename(idx)
            elif idx == "NDWI": return img.normalizedDifference(["B3", "B8"]).rename(idx)
            elif idx == "NDBI": return img.normalizedDifference(["B11", "B8"]).rename(idx)
            elif idx == "NBR": return img.normalizedDifference(["B8", "B12"]).rename(idx)
            return img.select("B8")
            
        index_col = collection.map(calc_idx)
        
        # Minimum-observation check
        count_img = index_col.count()
        obs_count_dict = count_img.reduceRegion(ee.Reducer.median(), aoi_geom, 100, maxPixels=1e9).getInfo()
        obs_count = obs_count_dict.get(index_name.upper()) or 0
        
        if obs_count < 3:
            return {"success": False, "errors": [{"code": "INSUFFICIENT_OBSERVATIONS", "message": f"Only {obs_count} median valid historical observations found."}]}
            
        mean_img = index_col.mean()
        std_img = index_col.reduce(ee.Reducer.stdDev())
        
        hist_stats = mean_img.addBands(std_img).reduceRegion(ee.Reducer.mean(), aoi_geom, 100, maxPixels=1e9).getInfo()
        hist_mean = hist_stats.get(index_name.upper()) or 0
        hist_std = hist_stats.get(f"{index_name.upper()}_stdDev") or 0
        
        if hist_std == 0:
            return {"success": False, "errors": [{"code": "INSUFFICIENT_OBSERVATIONS", "message": "Historical standard deviation is 0."}]}
            
        target_img = self._get_index_image(target_scene_id, index_name)
        
        diff = target_img.subtract(mean_img).abs()
        z_score = diff.divide(std_img)
        anomaly_mask = z_score.gte(threshold)
        
        anomaly_area_dict = ee.Image.pixelArea().updateMask(anomaly_mask).reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=aoi_geom,
            scale=10,
            maxPixels=1e9
        ).getInfo()
        
        anomaly_area_km2 = (anomaly_area_dict.get('area') or 0) / 1e6
        
        return {
            "success": True,
            "anomaly_area_km2": round(anomaly_area_km2, 4),
            "historical_mean": round(hist_mean, 3),
            "historical_stdDev": round(hist_std, 3),
            "threshold": threshold,
            "valid_observation_count": int(obs_count),
            "methodology": "|value - historical_mean| / historical_stdDev >= threshold"
        }

    async def compare_indices(self, aoi_geojson: dict, scene_id: str, index_1: str, index_2: str, operation: str) -> dict:
        ee = _get_ee()
        self._ensure_authenticated()
        
        aoi_geom = self.geojson_to_ee_geometry(aoi_geojson)
        img1 = self._get_index_image(scene_id, index_1)
        img2 = self._get_index_image(scene_id, index_2)
        
        if operation == "spatial correlation":
            combined = img1.addBands(img2)
            corr = combined.reduceRegion(
                reducer=ee.Reducer.pearsonsCorrelation(),
                geometry=aoi_geom,
                scale=100,
                maxPixels=1e9
            ).getInfo()
            return {
                "correlation": round(corr.get('correlation') or 0, 3),
                "p_value": round(corr.get('p-value') or 0, 4),
                "operation": operation,
                "methodology": "Pearson spatial correlation coefficient between indices"
            }
        elif operation == "difference":
            diff = img1.subtract(img2)
            stats = diff.reduceRegion(ee.Reducer.mean().combine(ee.Reducer.stdDev(), None, True), aoi_geom, 100, maxPixels=1e9).getInfo()
            return {
                "difference_mean": round(stats.get(f"{index_1.upper()}_mean") or 0, 3),
                "difference_std": round(stats.get(f"{index_1.upper()}_stdDev") or 0, 3),
                "operation": operation,
                "methodology": f"Spatial mean of ({index_1} - {index_2})"
            }
        elif operation == "ratio":
            ratio = img1.divide(img2)
            stats = ratio.reduceRegion(ee.Reducer.mean(), aoi_geom, 100, maxPixels=1e9).getInfo()
            return {
                "ratio_mean": round(stats.get(f"{index_1.upper()}") or 0, 3),
                "operation": operation,
                "methodology": f"Spatial mean of ({index_1} / {index_2})"
            }
        else:
            raise ValueError(f"Unsupported operation: {operation}")

    async def compute_hotspots(self, aoi_geojson: dict, scene_id_1: str, scene_id_2: str, index_name: str, threshold: float, direction: str) -> dict:
        ee = _get_ee()
        self._ensure_authenticated()
        
        aoi_geom = self.geojson_to_ee_geometry(aoi_geojson)
        img1 = self._get_index_image(scene_id_1, index_name)
        img2 = self._get_index_image(scene_id_2, index_name)
        
        diff = img2.subtract(img1)
        if direction == "decrease":
            mask = diff.lte(threshold)
        else:
            mask = diff.gte(threshold)
            
        # Neighborhood density/convolution
        kernel = ee.Kernel.circle(radius=200, units='meters')
        density = mask.reduceNeighborhood(ee.Reducer.mean(), kernel)
        
        # Minimum cluster criterion (>50% of the neighborhood must be changed)
        hotspot_mask = density.gt(0.5).And(mask)
        
        pixel_area = ee.Image.pixelArea().updateMask(hotspot_mask)
        area_dict = pixel_area.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=aoi_geom,
            scale=10,
            maxPixels=1e9
        ).getInfo()
        
        area_sq_m = area_dict.get('area') or 0
        area_km2 = area_sq_m / 1e6
        
        return {
            "hotspot_area_km2": round(area_km2, 4),
            "crs": "EPSG:4326",
            "scale": 10,
            "methodology": "input change raster -> threshold mask -> 200m circular neighborhood density -> minimum 50% cluster criterion -> hotspot mask"
        }

    # ------------------------------------------------------------------
    # Phase 6: Temporal Intelligence
    # ------------------------------------------------------------------

    async def compute_trend(self, aoi_geojson: dict, index_name: str, start_date: str, end_date: str) -> dict:
        ee = _get_ee()
        self._ensure_authenticated()
        
        aoi_geom = self.geojson_to_ee_geometry(aoi_geojson)
        collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(aoi_geom)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
        )
        
        def add_time_band(img):
            date = ee.Date(img.get('system:time_start'))
            years = date.difference(ee.Date('1970-01-01'), 'year')
            time_img = ee.Image(years).rename('time').float()
            
            idx_name = index_name.upper()
            if idx_name == "NDVI": idx_img = img.normalizedDifference(["B8", "B4"]).rename(idx_name)
            elif idx_name == "NDWI": idx_img = img.normalizedDifference(["B3", "B8"]).rename(idx_name)
            elif idx_name == "NDBI": idx_img = img.normalizedDifference(["B11", "B8"]).rename(idx_name)
            elif idx_name == "NBR": idx_img = img.normalizedDifference(["B8", "B12"]).rename(idx_name)
            else: idx_img = img.select("B8")
            
            return time_img.addBands(idx_img)
            
        trend_col = collection.map(add_time_band)
        
        obs_count = trend_col.count().select(0).reduceRegion(ee.Reducer.median(), aoi_geom, 100).getInfo()
        if not obs_count or list(obs_count.values())[0] < 5:
            return {"success": False, "errors": [{"code": "INSUFFICIENT_OBSERVATIONS", "message": "Not enough images for trend."}]}
            
        linear_fit = trend_col.reduce(ee.Reducer.linearFit())
        stats = linear_fit.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=aoi_geom,
            scale=100,
            maxPixels=1e9
        ).getInfo()
        
        return {
            "success": True,
            "slope": round(stats.get('scale') or 0, 5),
            "offset": round(stats.get('offset') or 0, 5),
            "valid_observation_count": int(list(obs_count.values())[0]),
            "period": {"start": start_date, "end": end_date},
            "methodology": "ee.Reducer.linearFit() on fractional years. NOTE: Measures linear trend; does not strictly test monotonicity."
        }

    async def compute_seasonality(self, aoi_geojson: dict, index_name: str, start_date: str, end_date: str) -> dict:
        ee = _get_ee()
        self._ensure_authenticated()
        
        aoi_geom = self.geojson_to_ee_geometry(aoi_geojson)
        collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(aoi_geom)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
        )
        
        def calc_idx(img):
            idx_name = index_name.upper()
            if idx_name == "NDVI": idx_img = img.normalizedDifference(["B8", "B4"]).rename(idx_name)
            elif idx_name == "NDWI": idx_img = img.normalizedDifference(["B3", "B8"]).rename(idx_name)
            elif idx_name == "NDBI": idx_img = img.normalizedDifference(["B11", "B8"]).rename(idx_name)
            elif idx_name == "NBR": idx_img = img.normalizedDifference(["B8", "B12"]).rename(idx_name)
            else: idx_img = img.select("B8")
            return idx_img.copyProperties(img, ["system:time_start"])
            
        index_col = collection.map(calc_idx)
        
        months = ee.List.sequence(1, 12)
        def get_monthly_mean(m):
            monthly_col = index_col.filter(ee.Filter.calendarRange(m, m, 'month'))
            mean_img = monthly_col.mean()
            obs_img = monthly_col.count().rename([f"{index_name.upper()}_count"])
            
            stats = mean_img.addBands(obs_img).reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=aoi_geom,
                scale=100,
                maxPixels=1e9
            )
            return ee.Feature(None, {
                'month': m,
                'mean': stats.get(index_name.upper()),
                'obs_count': stats.get(f"{index_name.upper()}_count")
            })
            
        monthly_stats = ee.FeatureCollection(months.map(get_monthly_mean)).getInfo()['features']
        
        seasonality = []
        for feature in monthly_stats:
            props = feature.get('properties', {})
            seasonality.append({
                "month": props.get('month'),
                "mean": round(props.get('mean') or 0, 4) if props.get('mean') is not None else None,
                "obs_count": round(props.get('obs_count') or 0, 1) if props.get('obs_count') is not None else 0
            })
            
        valid_months = [m for m in seasonality if m['mean'] is not None and m['obs_count'] >= 1]
        if len(valid_months) < 10:
            return {"success": False, "errors": [{"code": "INSUFFICIENT_OBSERVATIONS", "message": "Monthly coverage is too sparse to conclude seasonality."}]}
            
        max_month = max(valid_months, key=lambda x: x['mean'])
        min_month = min(valid_months, key=lambda x: x['mean'])
        amplitude = max_month['mean'] - min_month['mean']
        
        return {
            "success": True,
            "monthly_profile": seasonality,
            "amplitude": round(amplitude, 4),
            "peak_month": max_month['month'],
            "trough_month": min_month['month'],
            "period": {"start": start_date, "end": end_date},
            "methodology": "Monthly mean aggregation across years."
        }

    async def compute_temporal_breaks(self, aoi_geojson: dict, index_name: str, start_date: str, end_date: str, threshold: float = 2.0) -> dict:
        import math
        ee = _get_ee()
        self._ensure_authenticated()
        
        aoi_geom = self.geojson_to_ee_geometry(aoi_geojson)
        collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(aoi_geom)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
        )
        
        def get_mean_val(img):
            idx_name = index_name.upper()
            if idx_name == "NDVI": idx_img = img.normalizedDifference(["B8", "B4"]).rename(idx_name)
            elif idx_name == "NDWI": idx_img = img.normalizedDifference(["B3", "B8"]).rename(idx_name)
            elif idx_name == "NDBI": idx_img = img.normalizedDifference(["B11", "B8"]).rename(idx_name)
            elif idx_name == "NBR": idx_img = img.normalizedDifference(["B8", "B12"]).rename(idx_name)
            else: idx_img = img.select("B8")
            
            # Using scale=500 to prevent GEE from hanging when mapping reduceRegion over hundreds of images
            stats = idx_img.reduceRegion(ee.Reducer.mean(), aoi_geom, 500, maxPixels=1e9)
            return ee.Feature(None, {
                'system:time_start': img.get('system:time_start'),
                'mean_val': stats.get(idx_name)
            })
            
        fc = ee.FeatureCollection(collection.map(get_mean_val)).getInfo()['features']
        
        values = []
        for feature in fc:
            props = feature.get('properties', {})
            ts = props.get('system:time_start')
            v = props.get('mean_val')
            if ts and v is not None:
                values.append({
                    "date": ee.Date(ts).format('YYYY-MM-dd').getInfo(),
                    "val": v
                })
                
        if len(values) < 5:
            return {"success": False, "errors": [{"code": "INSUFFICIENT_OBSERVATIONS", "message": "Not enough images for break detection."}]}
            
        # Calculate mean and std in python
        mean = sum(x['val'] for x in values) / len(values)
        variance = sum((x['val'] - mean) ** 2 for x in values) / len(values)
        std_dev = math.sqrt(variance)
        
        if std_dev == 0:
            return {"success": False, "errors": [{"code": "ZERO_VARIANCE", "message": "Standard deviation is 0."}]}
            
        deviations = []
        for x in values:
            z_score = abs(x['val'] - mean) / std_dev
            deviations.append({
                "date": x['date'],
                "deviation_magnitude": round(z_score, 3)
            })
                
        significant = [d for d in deviations if d['deviation_magnitude'] >= threshold]
        
        if not significant:
            return {
                "success": True,
                "break_detected": False,
                "message": "No candidate breaks detected above threshold.",
                "methodology": "Candidate deviation detection via absolute z-score of spatial mean from period mean."
            }
            
        max_dev = max(significant, key=lambda x: x['deviation_magnitude'])
        
        return {
            "success": True,
            "break_detected": True,
            "candidate_break_date": max_dev['date'],
            "magnitude": max_dev['deviation_magnitude'],
            "all_significant_deviations": len(significant),
            "period": {"start": start_date, "end": end_date},
            "methodology": "Candidate deviation detection via absolute z-score of spatial mean from period mean (not a formal structural change-point test)."
        }

    async def compute_change_persistence(self, aoi_geojson: dict, index_name: str, pre_start: str, pre_end: str, post_start: str, post_end: str, threshold: float, direction: str) -> dict:
        ee = _get_ee()
        self._ensure_authenticated()
        
        aoi_geom = self.geojson_to_ee_geometry(aoi_geojson)
        
        pre_col = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(aoi_geom)
            .filterDate(pre_start, pre_end)
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
        )
        
        def calc_idx(img):
            idx_name = index_name.upper()
            if idx_name == "NDVI": return img.normalizedDifference(["B8", "B4"]).rename(idx_name)
            elif idx_name == "NDWI": return img.normalizedDifference(["B3", "B8"]).rename(idx_name)
            elif idx_name == "NDBI": return img.normalizedDifference(["B11", "B8"]).rename(idx_name)
            elif idx_name == "NBR": return img.normalizedDifference(["B8", "B12"]).rename(idx_name)
            return img.select("B8")
            
        pre_mean = pre_col.map(calc_idx).mean()
        
        post_col = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(aoi_geom)
            .filterDate(post_start, post_end)
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
        ).map(calc_idx)
        
        post_obs_count = post_col.count().reduceRegion(ee.Reducer.median(), aoi_geom, 100).getInfo().get(index_name.upper()) or 0
        if post_obs_count < 3:
            return {"success": False, "errors": [{"code": "INSUFFICIENT_OBSERVATIONS", "message": f"Requires minimum 3 post-event observations, found {post_obs_count}."}]}
            
        def check_anomaly(img):
            diff = img.subtract(pre_mean)
            if direction == "decrease":
                is_anom = diff.lte(threshold)
            else:
                is_anom = diff.gte(threshold)
            return is_anom.rename('anomaly').float()
            
        anomaly_col = post_col.map(check_anomaly)
        
        persistence_img = anomaly_col.sum().divide(anomaly_col.count())
        
        persistence_score = persistence_img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=aoi_geom,
            scale=100,
            maxPixels=1e9
        ).getInfo().get('anomaly') or 0
        
        return {
            "success": True,
            "persistence_score": round(persistence_score, 4),
            "post_event_observations": int(post_obs_count),
            "pre_period": {"start": pre_start, "end": pre_end},
            "post_period": {"start": post_start, "end": post_end},
            "methodology": f"Explicit pre-event baseline mean compared against each post-event observation. Persistence = fraction of post-event observations passing the {direction} threshold."
        }

    async def compute_event_window(self, aoi_geojson: dict, index_name: str, event_date: str, pre_days: int = 90, post_days: int = 90) -> dict:
        import datetime
        ee = _get_ee()
        self._ensure_authenticated()
        
        aoi_geom = self.geojson_to_ee_geometry(aoi_geojson)
        
        evt_dt = datetime.datetime.strptime(event_date, "%Y-%m-%d")
        pre_start = (evt_dt - datetime.timedelta(days=pre_days)).strftime("%Y-%m-%d")
        pre_end = event_date
        post_start = event_date
        post_end = (evt_dt + datetime.timedelta(days=post_days)).strftime("%Y-%m-%d")
        
        def get_window_mean(start, end):
            col = (
                ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                .filterBounds(aoi_geom)
                .filterDate(start, end)
                .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
            )
            def calc_idx(img):
                idx_name = index_name.upper()
                if idx_name == "NDVI": return img.normalizedDifference(["B8", "B4"]).rename(idx_name)
                elif idx_name == "NDWI": return img.normalizedDifference(["B3", "B8"]).rename(idx_name)
                elif idx_name == "NDBI": return img.normalizedDifference(["B11", "B8"]).rename(idx_name)
                elif idx_name == "NBR": return img.normalizedDifference(["B8", "B12"]).rename(idx_name)
                return img.select("B8")
            idx_col = col.map(calc_idx)
            obs_count = idx_col.count().reduceRegion(ee.Reducer.median(), aoi_geom, 100).getInfo().get(index_name.upper()) or 0
            mean_val = idx_col.mean().reduceRegion(ee.Reducer.mean(), aoi_geom, 100).getInfo().get(index_name.upper())
            return mean_val, obs_count

        pre_val, pre_obs = get_window_mean(pre_start, pre_end)
        post_val, post_obs = get_window_mean(post_start, post_end)
        
        if pre_obs < 1 or post_obs < 1:
            return {"success": False, "errors": [{"code": "INSUFFICIENT_OBSERVATIONS", "message": "Need at least 1 observation in both pre and post windows."}]}
            
        delta = post_val - pre_val if pre_val and post_val else 0
        
        return {
            "success": True,
            "pre_event_mean": round(pre_val, 4) if pre_val else None,
            "post_event_mean": round(post_val, 4) if post_val else None,
            "delta": round(delta, 4) if delta else None,
            "pre_observations": int(pre_obs),
            "post_observations": int(post_obs),
            "event_date": event_date,
            "windows": {"pre_days": pre_days, "post_days": post_days},
            "methodology": "Spatial mean reduction over exact temporal windows before and after the event date."
        }
