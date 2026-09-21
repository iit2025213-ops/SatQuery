"""TerraMind remote client."""

from __future__ import annotations

from typing import Any

from app.models.client import RemoteModelClient
from app.models.terramind.schema import TerraMindResponse


class TerraMindClient(RemoteModelClient):
    """HTTP client for the hosted TerraMind foundation model service."""

    def __init__(self, *, endpoint: str, api_key: str = "", timeout_seconds: float = 1200) -> None:
        super().__init__(
            model_name="TerraMind",
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
            "assets": payload.get("assets", []),
            "task": payload.get("task", "segmentation"),
            "num_classes": payload.get("num_classes", 3),
            "clustering_method": payload.get("clustering_method", "pca_kmeans")
        }
        return url, headers, body

    def _parse_response(self, raw: dict[str, Any]) -> dict[str, Any]:
        response = TerraMindResponse(
            result=raw.get("result", raw),
            model=raw.get("model", "terramind_v1_large"),
            version=raw.get("version", "1.0"),
            inference_time_seconds=raw.get("inference_time_seconds"),
            confidence=raw.get("confidence")
        )
        return response.model_dump()
