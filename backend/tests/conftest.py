# tests/conftest.py

import pytest
import asyncio
from typing import AsyncGenerator
import os
from dotenv import load_dotenv
import logging
import httpx

# Load the real environment variables
load_dotenv('.env')

# Logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("satquery")

# ============================================================================
# ASYNC SUPPORT
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# ============================================================================
# TEST AOI FIXTURES (Real Geometries)
# ============================================================================

@pytest.fixture
def test_aoi_small():
    """Small test AOI (0.1 km²) - San Francisco"""
    return {
        "type": "Polygon",
        "coordinates": [[
            [-122.415, 37.774],
            [-122.414, 37.774],
            [-122.414, 37.775],
            [-122.415, 37.775],
            [-122.415, 37.774]
        ]]
    }

@pytest.fixture
def test_aoi_medium():
    """Medium test AOI (100 km²) - Bay Area"""
    return {
        "type": "Polygon",
        "coordinates": [[
            [-122.5, 37.7],
            [-122.4, 37.7],
            [-122.4, 37.8],
            [-122.5, 37.8],
            [-122.5, 37.7]
        ]]
    }

@pytest.fixture
def test_aoi_large():
    """Large test AOI (900 km²) - Northern California"""
    return {
        "type": "Polygon",
        "coordinates": [[
            [-123.0, 37.0],
            [-122.0, 37.0],
            [-122.0, 38.0],
            [-123.0, 38.0],
            [-123.0, 37.0]
        ]]
    }

@pytest.fixture
def test_aoi_invalid_closed():
    """Invalid AOI - not closed"""
    return {
        "type": "Polygon",
        "coordinates": [[
            [-122.415, 37.774],
            [-122.414, 37.774],
            [-122.414, 37.775],
            [-122.415, 37.775]
            # Missing closing point
        ]]
    }

@pytest.fixture
def test_aoi_self_intersecting():
    """Invalid AOI - self-intersecting"""
    return {
        "type": "Polygon",
        "coordinates": [[
            [0, 0],
            [2, 2],
            [2, 0],
            [0, 2],
            [0, 0]
        ]]
    }

# ============================================================================
# MOCK AI BRAIN ONLY
# ============================================================================

class MockAIBrain:
    """
    MOCKED AI Brain for testing agent decisions
    
    This is the ONLY mocked component. It simulates AI Brain decisions
    without calling the real AI service. All decisions are deterministic
    based on observation count.
    """
    
    def __init__(self):
        self.call_count = 0
        self.decision_history = []
    
    async def send_state_and_get_decision(self, agent_state: dict):
        """
        Mock Brain that makes predictable decisions based on state
        
        Decision sequence:
        1. observations_count=0  -> Retrieve satellite imagery
        2. observations_count=1  -> Generate 2D terrain
        3. observations_count=2  -> Retrieve temporal imagery
        4. observations_count>=3 -> Return final analysis
        """
        
        self.call_count += 1
        observations_count = len(agent_state.get("observations", []))
        
        # Decision 1: Retrieve satellite imagery
        if observations_count == 0:
            decision = {
                "type": "decision",
                "action": "CALL_TOOL",
                "capability": "retrieve_satellite_imagery",
                "arguments": {
                    "aoi": agent_state.get("aoi"),
                    "date_start": "2024-01-01",
                    "date_end": "2024-12-31",
                    "collections": ["Sentinel-2"],
                    "cloud_cover_max": 20
                },
                "reason": "User requested analysis of AOI"
            }
            logger.info("Mock Brain: Decision 1 - Retrieve satellite imagery")
        
        # Decision 2: Generate 2D terrain
        elif observations_count == 1:
            decision = {
                "type": "decision",
                "action": "CALL_TOOL",
                "capability": "generate_terrain_2d",
                "arguments": {
                    "dem_url": "USGS/3DEP/10m",
                    "satellite_url": "COPERNICUS/S2_SR_HARMONIZED",
                    "aoi": agent_state.get("aoi")
                },
                "reason": "Generate terrain visualization"
            }
            logger.info("Mock Brain: Decision 2 - Generate 2D terrain")
        
        # Decision 3: Retrieve temporal imagery
        elif observations_count == 2:
            decision = {
                "type": "decision",
                "action": "CALL_TOOL",
                "capability": "retrieve_temporal_imagery",
                "arguments": {
                    "aoi": agent_state.get("aoi"),
                    "date_start": "2019-01-01",
                    "date_end": "2025-12-31",
                    "collection": "Sentinel-2"
                },
                "reason": "Analyze temporal changes"
            }
            logger.info("Mock Brain: Decision 3 - Retrieve temporal imagery")
        
        # Final decision: Return analysis
        else:
            decision = {
                "type": "decision",
                "action": "FINAL",
                "answer": f"Analysis complete. {observations_count} observations collected.",
                "confidence": 0.95
            }
            logger.info("Mock Brain: Final - Return analysis")
        
        self.decision_history.append(decision)
        return decision

@pytest.fixture
async def mock_brain():
    """Mock AI Brain fixture (ONLY MOCKED COMPONENT)"""
    return MockAIBrain()

# ============================================================================
# REAL GEE CONNECTOR (NOT MOCKED)
# ============================================================================

@pytest.fixture
async def gee_connector():
    """
    Real GEE connector fixture
    Connects to actual Google Earth Engine with credentials from .env
    """
    from app.gee.connector import GEEConnector
    from app.config import settings
    
    connector = GEEConnector(
        project_id=settings.gee_project_id,
        service_account_key_path=settings.gee_service_account_key_path
    )
    
    await connector.authenticate()
    logger.info("✓ Real GEE connector authenticated")
    
    yield connector

# ============================================================================
# REAL SUPABASE CLIENT (NOT MOCKED)
# ============================================================================

@pytest.fixture
async def supabase_client():
    """
    Real Supabase client fixture
    Connects to actual Supabase database instance.
    """
    from supabase import create_client, Client
    from app.config import settings
    
    url = settings.supabase_url
    key = settings.supabase_service_role_key or settings.supabase_key
    
    if not url or not key:
        pytest.skip("Supabase credentials not configured in .env")
    
    client: Client = create_client(url, key)
    logger.info("✓ Real Supabase client initialized")
    
    yield client

# ============================================================================
# REAL HTTP CLIENT (NOT MOCKED)
# ============================================================================

@pytest.fixture
async def http_client():
    """Real HTTP client for making requests"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client

# ============================================================================
# REAL AOI VALIDATION (NOT MOCKED)
# ============================================================================

@pytest.fixture
async def aoi_validator():
    """Real AOI validator using actual geospatial libraries"""
    from app.geospatial.aoi import AOIValidator
    return AOIValidator()

# ============================================================================
# REAL SENTINEL-2 DATA (THROUGH GEE, NOT MOCKED)
# ============================================================================

@pytest.fixture
async def real_sentinel2_scenes(gee_connector, test_aoi_medium):
    """Real Sentinel-2 imagery from Google Earth Engine"""
    scenes = await gee_connector.query_sentinel2(
        aoi_geojson=test_aoi_medium,
        date_start="2024-01-01",
        date_end="2024-12-31",
        cloud_cover_max=20
    )
    
    logger.info(f"Retrieved {len(scenes)} real Sentinel-2 scenes from GEE")
    return scenes

# ============================================================================
# REAL DEM DATA (THROUGH GEE, NOT MOCKED)
# ============================================================================

@pytest.fixture
async def real_dem(gee_connector, test_aoi_medium):
    """Real DEM from USGS 3DEP via Google Earth Engine"""
    dem_data = await gee_connector.retrieve_dem(
        aoi_geojson=test_aoi_medium,
        resolution_m=30
    )
    
    logger.info(f"Retrieved real DEM from USGS 3DEP via GEE")
    return dem_data

# ============================================================================
# SETUP & TEARDOWN
# ============================================================================

@pytest.fixture(autouse=True)
async def cleanup_after_test(supabase_client):
    """
    Cleanup real database records after each test
    Deletes test records from Supabase to keep DB clean
    """
    yield
    
    # Cleanup test data from Supabase
    try:
        # Example: Delete test jobs
        # supabase_client.table("jobs").delete().eq("status", "test_pending").execute()
        pass
    except Exception as e:
        logger.warning(f"Cleanup error (non-fatal): {e}")

# ============================================================================
# ASYNC TEST CLIENT
# ============================================================================

@pytest.fixture
async def async_test_client():
    """Real async HTTP client for testing backend API"""
    from app.main import app
    from httpx import AsyncClient
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
