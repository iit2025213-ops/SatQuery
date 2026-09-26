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
        """Translate internal payload to the fine-tuned GeoChat API contract."""
        url = f"{self.endpoint}/infer"
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        import base64
        import os
        from app.llm.openai import OpenAIProvider
        
        images: list[str] = []
        asset_uris = payload.get("asset_uris", [])
        for uri in asset_uris:
            if not uri:
                continue

            # Support HTTP/HTTPS URLs (e.g. Cloudinary links from frontend)
            if uri.startswith("http"):
                try:
                    import httpx as _httpx
                    with _httpx.Client(timeout=30) as _client:
                        resp = _client.get(uri)
                        resp.raise_for_status()
                        raw_bytes = resp.content
                        b64 = base64.b64encode(raw_bytes).decode("utf-8")
                        images.append(b64)
                        continue
                except Exception:
                    continue

            # Local file fallback
            if not os.path.exists(uri):
                continue
            loaded = OpenAIProvider._load_image_bytes_for_llm(uri)
            if loaded:
                raw_bytes, mime = loaded
                b64 = base64.b64encode(raw_bytes).decode("utf-8")
                images.append(b64)

        body = {
            "images": images,
            "question": payload.get("prompt", ""),
            "max_new_tokens": payload.get("max_new_tokens", 256),
            "temperature": payload.get("temperature", 0.0),
        }
        return url, headers, body

    def _parse_response(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Validate and extract the GeoChat response from custom schema."""
        response = GeoChatResponse(
            text=raw.get("answer", raw.get("output", "")),
            model="GeoChat",
            version=raw.get("model_version", "fine-tuned-7b"),
            inference_time_seconds=raw.get("latency_ms", 0) / 1000.0,
            is_cdvqa=raw.get("is_cdvqa", False),
        )
        return response.model_dump()
