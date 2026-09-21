"""Unit tests for the base RemoteModelClient."""

import pytest
import httpx
from unittest.mock import patch, MagicMock

from app.models.client import (
    RemoteModelClient,
    EndpointNotConfiguredError,
    ModelTimeoutError,
    ModelConnectionError,
    ModelAuthError,
    ModelResponseError,
)

@pytest.fixture
def client():
    return RemoteModelClient(
        model_name="TestModel",
        endpoint="http://api.test",
        api_key="test-key",
        timeout_seconds=5,
    )

@pytest.mark.asyncio
async def test_infer_success(client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"result": "success"}

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        res = await client.infer({"test": "data"})
    
    assert res == {"result": "success"}

@pytest.mark.asyncio
async def test_endpoint_not_configured():
    client = RemoteModelClient(model_name="TestModel", endpoint="")
    with pytest.raises(EndpointNotConfiguredError) as exc:
        await client.infer({})
    assert "not configured" in str(exc.value)

@pytest.mark.asyncio
async def test_timeout_error(client):
    with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("timeout")):
        with pytest.raises(ModelTimeoutError) as exc:
            await client.infer({})
    assert exc.value.retryable is True

@pytest.mark.asyncio
async def test_auth_error(client):
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        with pytest.raises(ModelAuthError) as exc:
            await client.infer({})
    assert exc.value.retryable is False

@pytest.mark.asyncio
async def test_response_error_500(client):
    mock_resp = MagicMock()
    mock_resp.status_code = 503
    mock_resp.text = "Service Unavailable"
    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        with pytest.raises(ModelResponseError) as exc:
            await client.infer({})
    assert exc.value.status_code == 503
    assert exc.value.retryable is True

@pytest.mark.asyncio
async def test_response_error_400(client):
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = "Bad Request"
    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        with pytest.raises(ModelResponseError) as exc:
            await client.infer({})
    assert exc.value.retryable is False

@pytest.mark.asyncio
async def test_invalid_json(client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.side_effect = ValueError("invalid json")
    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        with pytest.raises(ModelResponseError) as exc:
            await client.infer({})
    assert "not valid JSON" in str(exc.value)
