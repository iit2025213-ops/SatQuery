"""SARMAE remote client."""

from __future__ import annotations

import base64
import os
from typing import Any

from app.models.client import RemoteModelClient, RemoteModelError
from app.models.sarmae.schema import SARMAEResponse


class SARMAEClient(RemoteModelClient):
    """HTTP client for the hosted SARMAE service."""

    def __init__(self, *, endpoint: str, api_key: str = "", timeout_seconds: float = 90) -> None:
        super().__init__(
            model_name="SARMAE",
            endpoint=endpoint,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
        )
        
    async def infer(self, payload: dict[str, Any]) -> dict[str, Any]:
        asset_uri = payload.get("asset_uri", "")
        if not asset_uri or not os.path.exists(asset_uri):
            raise RemoteModelError(
                model="SARMAE",
                message=f"Local asset not found for base64 encoding: {asset_uri}",
                retryable=False
            )
            
        with open(asset_uri, "rb") as f:
            img_bytes = f.read()
            
        payload["image_b64"] = base64.b64encode(img_bytes).decode("utf-8")
        return await super().infer(payload)

    def _build_request(
        self, payload: dict[str, Any]
    ) -> tuple[str, dict[str, str], dict[str, Any]]:
        url = f"{self.endpoint}/v1/analyze"
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        body = {
            "image_b64": payload.get("image_b64", ""),
            "task": "representation",
            "metadata": {"asset_id": payload.get("asset_id", "")},
        }
        return url, headers, body

    def _parse_response(self, raw: dict[str, Any]) -> dict[str, Any]:
        response = SARMAEResponse(
            result=raw.get("result", raw),
            model=raw.get("model", "SARMAE-ViT-B"),
            version=raw.get("version", "1.0"),
            inference_time_seconds=raw.get("inference_time_seconds", 0.0),
        )
        return response.model_dump()
