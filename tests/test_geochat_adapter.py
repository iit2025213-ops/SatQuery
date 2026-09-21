import pytest
from unittest.mock import patch, MagicMock
from app.config import get_settings
from app.models.geochat.adapter import GeoChatAdapter
from app.evidence.schema import EvidenceType, ObservationStatus
import httpx

@pytest.fixture
def configure_endpoint():
    settings = get_settings()
    settings.geochat_endpoint = "http://mock-geochat"
    yield
    settings.geochat_endpoint = ""

@pytest.mark.asyncio
async def test_geochat_adapter_mock_predict(configure_endpoint):
    """Verify that the GeoChat adapter successfully calls the remote client."""
    adapter = GeoChatAdapter()
    
    # Valid input for interpret_scene
    valid_args = {
        "_capability": "interpret_scene",
        "asset": "asset_123",
        "prompt": "What is visible?"
    }
    
    # Check input validation
    is_valid, err = adapter.validate_input(valid_args)
    assert is_valid is True
    
    # Check predict
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "text": "A simulated scene.",
        "model": "GeoChat",
        "version": "1.0",
        "inference_time_seconds": 0.5
    }

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        raw_output = await adapter.predict(valid_args)

    assert "text" in raw_output
    assert raw_output["model"] == "GeoChat"
    assert raw_output["version"] == "1.0"
    
    # Check normalization
    obs = adapter.normalize_output(raw_output, valid_args)
    assert obs.status == ObservationStatus.SUCCESS
    assert obs.type == EvidenceType.SCENE_INTERPRETATION
    assert obs.source.capability == "interpret_scene"
    assert "text" in obs.result

@pytest.mark.asyncio
async def test_geochat_adapter_endpoint_not_configured():
    """Verify adapter handles unconfigured endpoint gracefully."""
    settings = get_settings()
    settings.geochat_endpoint = ""
    
    adapter = GeoChatAdapter()
    valid_args = {
        "_capability": "interpret_scene",
        "asset": "asset_123"
    }
    
    raw_output = await adapter.predict(valid_args)
    obs = adapter.normalize_output(raw_output, valid_args)
    
    assert obs.status == ObservationStatus.FAILURE
    assert obs.type == EvidenceType.ERROR
    assert "endpoint is not configured" in obs.error_message.lower()

@pytest.mark.asyncio
async def test_geochat_adapter_malformed_output():
    """Verify adapter gracefully handles malformed output from model."""
    adapter = GeoChatAdapter()
    valid_args = {
        "_capability": "interpret_scene",
        "asset": "asset_123",
        "prompt": "What is visible?"
    }
    
    # Simulating a model that returns entirely broken output missing required fields
    malformed_raw = {"unexpected": "data"}
    
    obs = adapter.normalize_output(malformed_raw, valid_args)
    assert obs.status == ObservationStatus.FAILURE
    assert obs.type == EvidenceType.ERROR
    assert "validation error" in obs.error_message.lower()
