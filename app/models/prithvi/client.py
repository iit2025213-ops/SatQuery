"""Prithvi remote client."""

from __future__ import annotations

from typing import Any

from app.models.client import RemoteModelClient
from app.models.prithvi.schema import PrithviResponse


class PrithviClient(RemoteModelClient):
    """HTTP client for the hosted Prithvi service."""

    def __init__(self, *, endpoint: str, api_key: str = "", timeout_seconds: float = 90) -> None:
        super().__init__(
            model_name="Prithvi",
            endpoint=endpoint,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
        )

    def _build_request(
        self, payload: dict[str, Any]
    ) -> tuple[str, dict[str, str], dict[str, Any]]:
        url = f"{self.endpoint}/v1/analyze"
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        body = {
            "asset_uri": payload.get("asset_uri", ""),
        }
        return url, headers, body

    def _parse_response(self, raw: dict[str, Any]) -> dict[str, Any]:
        response = PrithviResponse(
            result=raw.get("result", raw),
            model=raw.get("model", "Prithvi"),
            version=raw.get("version", ""),
            inference_time_seconds=raw.get("inference_time_seconds"),
        )
        return response.model_dump()
