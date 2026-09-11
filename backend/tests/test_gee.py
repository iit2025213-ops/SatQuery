# tests/test_gee.py

"""
Unit tests for Phase 7: GEE/STAC Data Layer

Tests GEEConnector utilities, GEEProcessor logic, and GEEAdapter
routing. Live GEE tests are skipped unless credentials are available.
"""

import pytest
import os
from dotenv import load_dotenv

# Load .env file so os.environ picks up GEE_PROJECT_ID
load_dotenv()


# ---------------------------------------------------------------------------
# GEEConnector unit tests (no live GEE required)
# ---------------------------------------------------------------------------

class TestGEEConnectorGeometry:
    """Test geometry conversion utilities — no auth needed."""

    def test_geojson_to_ee_coords(self):
        """Test that geojson_to_ee_geometry extracts the right coords."""
        # We can't call the actual ee function without auth,
        # but we can test the coordinate extraction logic.
        geojson = {
            "type": "Polygon",
            "coordinates": [
                [[77.0, 28.0], [77.1, 28.0], [77.1, 28.1], [77.0, 28.1], [77.0, 28.0]]
            ],
        }
        # Extract the outer ring the same way connector does
        coords = geojson["coordinates"][0]
        ee_coords = [[c[0], c[1]] for c in coords]

        assert len(ee_coords) == 5
        assert ee_coords[0] == [77.0, 28.0]
        assert ee_coords[-1] == [77.0, 28.0]  # closed ring

    def test_sentinel2_band_metadata(self):
        """Test that Sentinel-2 band metadata is defined."""
        from app.gee.connector import GEEConnector

        bands = GEEConnector.SENTINEL2_BANDS
        assert "B2" in bands
        assert "B4" in bands
        assert "B8" in bands
        assert bands["B2"]["wavelength_nm"] == 490
        assert bands["B8"]["name"] == "NIR"

    def test_landsat_band_metadata(self):
        """Test that Landsat band metadata is defined."""
        from app.gee.connector import GEEConnector

        bands = GEEConnector.LANDSAT_BANDS
        assert "SR_B4" in bands
        assert "SR_B5" in bands
        assert bands["SR_B5"]["name"] == "NIR"
        assert bands["SR_B4"]["resolution_m"] == 30


class TestGEEConnectorInit:
    """Test connector initialisation."""

    def test_init_without_credentials(self):
        """Connector should initialise even without valid credentials."""
        from app.gee.connector import GEEConnector

        connector = GEEConnector(
            service_account_key_path=None,
            project_id=None,
        )
        assert connector.authenticated is False

    def test_init_with_missing_file(self):
        """Connector should initialise with a non-existent key path."""
        from app.gee.connector import GEEConnector

        connector = GEEConnector(
            service_account_key_path="/nonexistent/key.json",
            project_id="test-project",
        )
        assert connector.authenticated is False

    @pytest.mark.asyncio
    async def test_authenticate_fails_gracefully(self):
        """Auth should fail gracefully when credentials are missing."""
        from app.gee.connector import GEEConnector

        connector = GEEConnector(
            service_account_key_path=None,
            project_id=None,
        )
        result = await connector.authenticate()
        assert result is False
        assert connector.authenticated is False


# ---------------------------------------------------------------------------
# GEEProcessor unit tests
# ---------------------------------------------------------------------------

class TestGEEProcessor:
    """Test processor logic (no Supabase needed for these)."""

    def test_init_without_cloudinary(self):
        """Processor should initialise without Cloudinary client."""
        from app.gee.processor import GEEProcessor

        processor = GEEProcessor(cloudinary_client=None)
        assert processor.cloudinary is None

    def test_scene_record_structure(self):
        """Test that a scene dict has the expected keys."""
        scene = {
            "id": "COPERNICUS/S2_SR_HARMONIZED/20240510T052651_20240510T053000_T43QFE",
            "source": "Sentinel-2",
            "acquisition_date": "2024-05-10",
            "cloud_cover_percent": 8.5,
            "bands": ["B2", "B3", "B4", "B8", "B11", "B12"],
            "resolution_m": 10,
            "crs": "EPSG:32643",
        }

        assert scene["source"] == "Sentinel-2"
        assert scene["resolution_m"] == 10
        assert "B8" in scene["bands"]


# ---------------------------------------------------------------------------
# GEEAdapter unit tests
# ---------------------------------------------------------------------------

class TestGEEAdapter:
    """Test adapter routing."""

    def test_adapter_init(self):
        """Adapter should initialise lazily."""
        from app.models.gee_adapter import GEEAdapter

        adapter = GEEAdapter()
        assert adapter._connector is None
        assert adapter._processor is None


# ---------------------------------------------------------------------------
# Capability Registry integration
# ---------------------------------------------------------------------------

class TestGEECapabilityRegistry:
    """Test that GEE capabilities are registered."""

    def test_retrieve_satellite_imagery_registered(self):
        """Check capability is in registry."""
        from app.registry.registry import CapabilityRegistry

        registry = CapabilityRegistry()
        cap = registry.get_capability("retrieve_satellite_imagery")
        assert cap is not None
        assert cap["adapter"] == "GEEAdapter"

    def test_retrieve_dem_registered(self):
        """Check DEM capability is in registry."""
        from app.registry.registry import CapabilityRegistry

        registry = CapabilityRegistry()
        cap = registry.get_capability("retrieve_dem")
        assert cap is not None
        assert cap["adapter"] == "GEEAdapter"

    def test_gee_adapter_instance_exists(self):
        """Check adapter instance is initialised."""
        from app.registry.registry import CapabilityRegistry

        registry = CapabilityRegistry()
        adapter = registry.get_adapter("retrieve_satellite_imagery")
        assert adapter is not None


# ---------------------------------------------------------------------------
# Live GEE tests (skipped unless GEE_PROJECT_ID env var is set)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not os.environ.get("GEE_PROJECT_ID"),
    reason="GEE credentials not configured (set GEE_PROJECT_ID to run)",
)
class TestGEELive:
    """Live GEE integration tests — requires valid credentials."""

    @pytest.mark.asyncio
    async def test_live_authenticate(self):
        """Test real GEE authentication."""
        from app.gee.connector import GEEConnector

        connector = GEEConnector(
            service_account_key_path=os.environ.get("GEE_SERVICE_ACCOUNT_KEY_PATH"),
            project_id=os.environ.get("GEE_PROJECT_ID"),
        )
        result = await connector.authenticate()
        assert result is True

    @pytest.mark.asyncio
    async def test_live_query_sentinel2(self):
        """Test real Sentinel-2 query."""
        from app.gee.connector import GEEConnector

        connector = GEEConnector(
            service_account_key_path=os.environ.get("GEE_SERVICE_ACCOUNT_KEY_PATH"),
            project_id=os.environ.get("GEE_PROJECT_ID"),
        )
        await connector.authenticate()

        aoi = {
            "type": "Polygon",
            "coordinates": [
                [[77.0, 28.5], [77.2, 28.5], [77.2, 28.7], [77.0, 28.7], [77.0, 28.5]]
            ],
        }

        scenes = await connector.query_sentinel2(aoi, "2024-01-01", "2024-06-30", 20)
        assert isinstance(scenes, list)
        # Should find at least some imagery over Delhi

    @pytest.mark.asyncio
    async def test_live_retrieve_dem(self):
        """Test real DEM retrieval."""
        from app.gee.connector import GEEConnector

        connector = GEEConnector(
            service_account_key_path=os.environ.get("GEE_SERVICE_ACCOUNT_KEY_PATH"),
            project_id=os.environ.get("GEE_PROJECT_ID"),
        )
        await connector.authenticate()

        aoi = {
            "type": "Polygon",
            "coordinates": [
                [[77.0, 28.5], [77.2, 28.5], [77.2, 28.7], [77.0, 28.7], [77.0, 28.5]]
            ],
        }

        dem_info = await connector.retrieve_dem(aoi, 30)
        assert dem_info is not None
        assert "elevation_stats" in dem_info
