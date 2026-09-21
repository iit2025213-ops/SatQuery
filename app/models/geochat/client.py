"""GeoChat remote client.

Calls the hosted GeoChat inference service via HTTP.
Translates between SatQuery's internal request contract and the
remote API contract.
"""

from __future__ import annotations

from typing import Any

from app.models.client import RemoteModelClient
from app.models.geochat.schema import GeoChatResponse


class GeoChatClient(RemoteModelClient):
    """HTTP client for the hosted GeoChat VLM service."""

    def __init__(self, *, endpoint: str, api_key: str = "", timeout_seconds: float = 60) -> None:
        super().__init__(
            model_name="GeoChat",
            endpoint=endpoint,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
        )

    def _build_request(
        self, payload: dict[str, Any]
    ) -> tuple[str, dict[str, str], dict[str, Any]]:
        """Translate internal payload to the hosted GeoChat API contract."""
        url = f"{self.endpoint}/predict"
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        body = {
            "image_uri": payload.get("asset_uri", ""),
            "prompt": payload.get("prompt", ""),
        }
        return url, headers, body

    def _parse_response(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Validate and extract the GeoChat response."""
        response = GeoChatResponse(
            text=raw.get("text", raw.get("output", "")),
            model=raw.get("model", "GeoChat"),
            version=raw.get("version", raw.get("checkpoint", "")),
            inference_time_seconds=raw.get("inference_time_seconds"),
        )
        return response.model_dump()
