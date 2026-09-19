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

    async def compute_ndvi_thumbnail_url(
        self,
        scene_id: str,
        aoi_geojson: dict,
        dimensions: int = 1024,
    ) -> Optional[str]:
        """
        Compute NDVI and return a signed PNG thumbnail URL with
        a red→yellow→green color palette (dead→sparse→healthy vegetation).
        """
        ee = _get_ee()
        self._ensure_authenticated()

        try:
            aoi_geom = self.geojson_to_ee_geometry(aoi_geojson)
            image = ee.Image(scene_id)

            # Determine NIR and Red bands
            if "COPERNICUS" in scene_id or "S2" in scene_id:
                nir_band, red_band = "B8", "B4"
            else:
                nir_band, red_band = "SR_B5", "SR_B4"

            ndvi = image.normalizedDifference([nir_band, red_band]).rename("NDVI").clip(aoi_geom)

            thumb_url = ndvi.getThumbURL({
                "bands": ["NDVI"],
                "region": aoi_geom,
                "dimensions": dimensions,
                "format": "png",
                "min": -0.2,
                "max": 0.8,
                "palette": ["#d73027", "#fc8d59", "#fee08b", "#91cf60", "#1a9850"],
            })

            logger.info(f"✅ NDVI thumbnail URL generated for scene: {scene_id}")
            return thumb_url

        except Exception as e:
            logger.error(f"❌ Failed to compute NDVI thumbnail for {scene_id}: {e}")
            return None

    async def get_ndvi_stats(
        self,
        scene_id: str,
        aoi_geojson: dict,
    ) -> Optional[Dict]:
        """Compute mean NDVI value over the AOI for a health summary."""
        ee = _get_ee()
        self._ensure_authenticated()

        try:
            aoi_geom = self.geojson_to_ee_geometry(aoi_geojson)
            image = ee.Image(scene_id)

            if "COPERNICUS" in scene_id or "S2" in scene_id:
                nir_band, red_band = "B8", "B4"
            else:
                nir_band, red_band = "SR_B5", "SR_B4"

            ndvi = image.normalizedDifference([nir_band, red_band]).rename("NDVI").clip(aoi_geom)

            stats = ndvi.reduceRegion(
                reducer=ee.Reducer.mean().combine(ee.Reducer.min(), None, True).combine(ee.Reducer.max(), None, True),
                geometry=aoi_geom,
                scale=100,
                maxPixels=1e8,
            ).getInfo()

            return {
                "mean": round(stats.get("NDVI_mean", 0), 3),
                "min": round(stats.get("NDVI_min", 0), 3),
                "max": round(stats.get("NDVI_max", 0), 3),
            }

        except Exception as e:
            logger.error(f"❌ Failed to compute NDVI stats for {scene_id}: {e}")
            return None
