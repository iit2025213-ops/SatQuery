"""Closed-loop integration tests with the deterministic geospatial layer."""

import os
import tempfile
import pytest

from app.agent.controller import AgentController
from app.config import Settings
from app.executor.executor import DefaultExecutor
from app.llm.mock import MockLLM
from app.registry.registry import build_default_registry
from unittest.mock import patch, MagicMock

from tests.test_geospatial import create_synthetic_raster


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture(autouse=True)
def mock_http():
    """Mock HTTP POST for all specialist clients."""
    async def mock_post(url, json, headers, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        
        if "geochat" in url.lower() or "interpret" in json.get("prompt", ""):
            resp.json.return_value = {"text": "A simulated scene.", "model": "GeoChat", "version": "1.0"}
        elif "sarmae" in url.lower():
            resp.json.return_value = {"result": {"modality": "sar", "objects": []}, "model": "SARMAE"}
        else:
            resp.json.return_value = {"result": {}, "model": "Mock"}
            
        return resp
        
    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        yield

def _controller() -> AgentController:
    registry = build_default_registry()
    executor = DefaultExecutor(registry)
    
    settings = Settings(
        max_steps=10,
        geochat_endpoint="http://mock",
        sarmae_endpoint="http://mock",
    )
    
    from app.config import get_settings
    get_settings.cache_clear()
    global _mock_settings
    _mock_settings = settings
    
    return AgentController(
        llm=MockLLM(),
        executor=executor,
        registry=registry,
        settings=settings,
    )

@pytest.fixture(autouse=True)
def patch_get_settings():
    with patch("app.models.geochat.adapter.get_settings", lambda: _mock_settings), \
         patch("app.models.sarmae.adapter.get_settings", lambda: _mock_settings):
        yield


@pytest.mark.asyncio
async def test_geospatial_valid_optical_routing(temp_dir):
    """Test that a valid optical synthetic raster routes to interpret_scene."""
    path = os.path.join(temp_dir, "optical.tif")
    create_synthetic_raster(path, width=50, height=50, count=3, tags={"modality": "optical"})

    ctrl = _controller()
    
    result = await ctrl.run(
        "Analyze this image.",
        input_assets=[
            {"asset_id": "asset_001", "uri": path, "format": "geotiff", "modality": "optical"}
        ],
    )
    
    assert result["status"] == "complete"
    capabilities = [e["capability"] for e in result["evidence"]]
    
    # It must have validated the input deterministically
    assert "validate_remote_sensing_input" in capabilities
    
    # And because it was optical and valid, the next step in the MockLLM is interpret_scene
    assert "interpret_scene" in capabilities


@pytest.mark.asyncio
async def test_geospatial_invalid_raster_halts():
    """Test that an unreadable raster returns an error observation and halts correctly."""
    ctrl = _controller()
    
    result = await ctrl.run(
        "Analyze this image.",
        input_assets=[
            {"asset_id": "asset_001", "uri": "does_not_exist.tif", "format": "geotiff", "modality": "optical"}
        ],
    )
    
    capabilities = [e["capability"] for e in result["evidence"]]
    
    # The validation should have failed, producing an ERROR observation or INVALID_INPUT
    assert "validate_remote_sensing_input" in capabilities
    
    # Because validation failed, the LLM should replan or retry, but NOT blindly interpret_scene
    assert "interpret_scene" not in capabilities


@pytest.mark.asyncio
async def test_geospatial_sar_routing(temp_dir):
    """Test that a synthetic SAR raster routes to analyze_sar_image."""
    path = os.path.join(temp_dir, "sar.tif")
    # 2 bands often heuristically determined as SAR if no tag, but we tag it anyway
    create_synthetic_raster(path, width=50, height=50, count=2, tags={"modality": "sar"})

    ctrl = _controller()
    
    result = await ctrl.run(
        "Analyze this SAR image.",
        input_assets=[
            {"asset_id": "asset_001", "uri": path, "format": "geotiff", "modality": "sar"}
        ],
    )
    
    assert result["status"] == "complete"
    capabilities = [e["capability"] for e in result["evidence"]]
    
    assert "validate_remote_sensing_input" in capabilities
    
    # The MockLLM sees "modality": "sar" in the validation observation and routes appropriately
    assert "analyze_sar_image" in capabilities
    assert "interpret_scene" not in capabilities
