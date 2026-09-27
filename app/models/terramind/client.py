"""TerraMind remote client."""

from __future__ import annotations

import httpx
from typing import Any

from app.models.client import (
    RemoteModelClient, 
    EndpointNotConfiguredError, 
    ModelTimeoutError, 
    ModelConnectionError, 
    ModelAuthError, 
    ModelResponseError
)


class TerraMindClient(RemoteModelClient):
    """HTTP client for the hosted TerraMind foundation model service."""

    def __init__(self, *, endpoint: str, api_key: str = "", timeout_seconds: float = 1200) -> None:
        super().__init__(
            model_name="TerraMind",
            endpoint=endpoint,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
        )

    async def infer(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.endpoint:
            raise EndpointNotConfiguredError(self.model_name)

        operation = payload.get("operation")
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                if operation == "terramind_coordinate_tokenizer":
                    url = f"{self.endpoint}/v1/coords/encode-decode"
                    response = await client.post(url, json={"coords": payload["coords"]}, headers=headers)
                else:
                    if operation == "terramind_embedding":
                        url = f"{self.endpoint}/v1/file/embedding"
                    elif operation == "terramind_tim":
                        url = f"{self.endpoint}/v1/file/tim"
                    elif operation == "terramind_generate":
                        url = f"{self.endpoint}/v1/file/generate"
                    else:
                        raise ValueError(f"Unknown TerraMind operation: {operation}")

                    data = payload["data"]
                    file_path = payload["file_path"]

                    if file_path.startswith("http"):
                        img_resp = await client.get(file_path)
                        img_resp.raise_for_status()
                        raw_bytes = img_resp.content
                    else:
                        with open(file_path, "rb") as f:
                            raw_bytes = f.read()
                            
                    from app.models.change_detection.preprocess import to_rgb8_png
                    try:
                        raw_bytes = to_rgb8_png(raw_bytes, max_side=2048)
                        filename = "image.png"
                    except Exception:
                        import os
                        from urllib.parse import urlparse
                        parsed_url = urlparse(file_path)
                        filename = os.path.basename(parsed_url.path)
                        if not filename:
                            filename = "image.png"

                    files = {"file": (filename, raw_bytes, "application/octet-stream")}
                    response = await client.post(url, data=data, files=files, headers=headers)

            except httpx.TimeoutException:
                raise ModelTimeoutError(self.model_name, self.timeout_seconds)
            except (httpx.ConnectError, httpx.RequestError) as exc:
                raise ModelConnectionError(self.model_name, str(exc))

        if response.status_code in (401, 403):
            raise ModelAuthError(self.model_name)
        if response.status_code >= 400:
            detail = response.text[:500] if response.text else ""
            raise ModelResponseError(self.model_name, response.status_code, detail)

        try:
            return response.json()
        except Exception:
            raise ModelResponseError(self.model_name, response.status_code, "Response body is not valid JSON.")
