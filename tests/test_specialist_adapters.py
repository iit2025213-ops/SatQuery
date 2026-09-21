"""Contract tests for specialist adapters."""

import pytest
from unittest.mock import patch, MagicMock

from app.config import get_settings
from app.evidence.schema import ObservationStatus
from app.models.changeformer.adapter import ChangeFormerAdapter
from app.models.prithvi.adapter import PrithviAdapter
from app.models.sarmae.adapter import SARMAEAdapter
from app.models.terramind.adapter import TerraMindAdapter

@pytest.fixture(autouse=True)
def configure_endpoints():
    settings = get_settings()
    settings.changeformer_endpoint = "http://mock"
    settings.prithvi_endpoint = "http://mock"
    settings.sarmae_endpoint = "http://mock"
    settings.terramind_endpoint = "http://mock"
    yield
    settings.changeformer_endpoint = ""
    settings.prithvi_endpoint = ""
    settings.sarmae_endpoint = ""
    settings.terramind_endpoint = ""

@pytest.mark.asyncio
async def test_changeformer_adapter():
    adapter = ChangeFormerAdapter()
    args = {"before_asset": "b1", "after_asset": "a1", "_capability": "detect_bitemporal_change"}
    
    ok, err = adapter.validate_input(args)
    assert ok is True
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "statistics": {
            "changed_pixels": 500,
            "total_pixels": 10000
        },
        "change_mask": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
        "model": "ChangeFormer"
    }
    
    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        raw = await adapter.predict(args)
        
    obs = adapter.normalize_output(raw, args)
    assert obs.status == ObservationStatus.SUCCESS
    assert obs.result["changed_pixels"] == 500
    assert len(obs.artifacts) > 0

@pytest.mark.asyncio
async def test_prithvi_adapter():
    adapter = PrithviAdapter()
    args = {"asset": "a1", "_capability": "analyze_multispectral_image"}
    
    ok, err = adapter.validate_input(args)
    assert ok is True
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "result": {"water": 0.5, "urban": 0.5},
        "model": "Prithvi"
    }
    
    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        raw = await adapter.predict(args)
        
    obs = adapter.normalize_output(raw, args)
    assert obs.status == ObservationStatus.SUCCESS
    assert obs.result["water"] == 0.5

@pytest.mark.asyncio
async def test_sarmae_adapter():
    from app.models.sarmae.adapter import SARMAEAdapter
    import tempfile
    import os
    
    adapter = SARMAEAdapter()
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tf:
        tf.write(b"dummy_image_data")
        temp_path = tf.name
        
    try:
        args = {"asset": "a1", "image_uri": temp_path, "_capability": "analyze_sar_image"}
        
        ok, err = adapter.validate_input(args)
        assert ok is True
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "result": {"ships": 5},
            "model": "SARMAE"
        }
        
        with patch("app.geospatial.processing.create_visual_preview") as mock_cvp:
            mock_cvp.return_value = {"preview_uri": temp_path}
            with patch("httpx.AsyncClient.post", return_value=mock_resp):
                raw = await adapter.predict(args)
                
        obs = adapter.normalize_output(raw, args)
        assert obs.status == ObservationStatus.SUCCESS
        assert obs.result["ships"] == 5
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@pytest.mark.asyncio
async def test_terramind_adapter():
    adapter = TerraMindAdapter()
    args = {"asset_uri": "mock.tif", "_capability": "perform_multimodal_analysis"}

    ok, err = adapter.validate_input(args)
    assert ok is True
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "result": {"analysis": "ok"},
        "model": "TerraMind++"
    }
    
    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        raw = await adapter.predict(args)
        
    obs = adapter.normalize_output(raw, args)
    assert obs.status == ObservationStatus.SUCCESS
    assert obs.result["analysis"] == "ok"
