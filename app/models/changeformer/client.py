"""ChangeFormer remote client."""

from __future__ import annotations

import base64
import os
import tempfile
from typing import Any

import httpx

from app.models.client import RemoteModelClient, ModelConnectionError
from app.models.changeformer.schema import ChangeFormerResponse


class ChangeFormerClient(RemoteModelClient):
    """HTTP client for the hosted ChangeFormer service."""

    def __init__(self, *, endpoint: str, api_key: str = "", timeout_seconds: float = 120) -> None:
        super().__init__(
            model_name="ChangeFormer",
            endpoint=endpoint,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
        )

    async def _fetch_as_base64(self, uri: str) -> str:
        """Fetch a remote or local URI and return as base64 string."""
        if not uri:
            return ""
        if uri.startswith("http"):
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.get(uri)
                    resp.raise_for_status()
                    data = resp.content
            except Exception as exc:
                raise ModelConnectionError(self.model_name, f"Failed to fetch image {uri}: {exc}")
        elif uri.startswith("mock://"):
            data = b"mockdata"
        else:
            try:
                with open(uri, "rb") as f:
                    data = f.read()
            except Exception as exc:
                raise ModelConnectionError(self.model_name, f"Failed to read local image {uri}: {exc}")
                
        return base64.b64encode(data).decode("utf-8")

    async def infer(self, payload: dict[str, Any]) -> dict[str, Any]:
        # Encode assets to base64
        before_b64 = await self._fetch_as_base64(payload.get("before_asset_uri", ""))
        after_b64 = await self._fetch_as_base64(payload.get("after_asset_uri", ""))
        
        # Override payload to pass base64 directly to _build_request
        payload["before_b64"] = before_b64
        payload["after_b64"] = after_b64
        
        return await super().infer(payload)

    def _build_request(
        self, payload: dict[str, Any]
    ) -> tuple[str, dict[str, str], dict[str, Any]]:
        url = f"{self.endpoint}/predict"
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        body = {
            "before": payload.get("before_b64", ""),
            "after": payload.get("after_b64", ""),
        }
        return url, headers, body

    def _parse_response(self, raw: dict[str, Any]) -> dict[str, Any]:
        mask_uri = ""
        mask_b64 = raw.get("change_mask", "")
        if mask_b64:
            mask_data = base64.b64decode(mask_b64)
            fd, mask_uri = tempfile.mkstemp(suffix=".png")
            os.close(fd)
            with open(mask_uri, "wb") as f:
                f.write(mask_data)
                
        stats = raw.get("statistics", {})
        
        response = ChangeFormerResponse(
            changed_pixels=stats.get("changed_pixels", 0),
            total_pixels=stats.get("total_pixels", 0),
            change_mask_uri=mask_uri,
            model="ChangeFormer",
            version="1.0",
        )
        return response.model_dump()
