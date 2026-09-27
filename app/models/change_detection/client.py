"""Change_detection remote client."""

from __future__ import annotations

import base64
import os
import tempfile
import time
from typing import Any

import httpx

from app.models.client import RemoteModelClient, ModelConnectionError
from app.models.change_detection.preprocess import ImagePreparationError, to_rgb8_png, coregister_pair
from app.models.change_detection.schema import ChangeDetectionResponse

MODEL_NAME = "Change_detection"
MODEL_VERSION = "mix_v1"

# Optional tuning knobs the service understands; they are forwarded only when the caller sets them.
_OPTIONAL_PARAMS = ("scales", "quorum", "threshold", "min_area", "tta")


class ChangeDetectionClient(RemoteModelClient):
    """HTTP client for the hosted Change_detection service (LitServe on Lightning AI)."""

    def __init__(self, *, endpoint: str, api_key: str = "", timeout_seconds: float = 600) -> None:
        super().__init__(
            model_name=MODEL_NAME,
            endpoint=endpoint,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
        )

    async def _fetch_as_bytes(self, uri: str) -> bytes:
        """Fetch a remote or local URI and return raw bytes."""
        if not uri:
            return b""
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
        return data

    async def infer(self, payload: dict[str, Any]) -> dict[str, Any]:
        # Fetch assets as bytes
        before_bytes = await self._fetch_as_bytes(payload.get("before_asset_uri", ""))
        after_bytes = await self._fetch_as_bytes(payload.get("after_asset_uri", ""))

        if payload.get("before_asset_uri", "").startswith("mock://") or payload.get("after_asset_uri", "").startswith("mock://"):
            before_b64 = base64.b64encode(before_bytes).decode("utf-8")
            after_b64 = base64.b64encode(after_bytes).decode("utf-8")
        else:
            try:
                # Co-register pairs to exact optimal resolution
                before_bytes, after_bytes = coregister_pair(before_bytes, after_bytes)
                
                # Convert to PNG safely via to_rgb8_png (though coregister_pair already returns PNGs)
                before_bytes = to_rgb8_png(before_bytes)
                after_bytes = to_rgb8_png(after_bytes)
                
                before_b64 = base64.b64encode(before_bytes).decode("utf-8")
                after_b64 = base64.b64encode(after_bytes).decode("utf-8")
            except Exception as exc:
                raise ModelConnectionError(self.model_name, f"Cannot prepare image pair: {exc}")

        # Override payload to pass base64 directly to _build_request
        payload["before_b64"] = before_b64
        payload["after_b64"] = after_b64

        started = time.perf_counter()
        result = await super().infer(payload)
        result["inference_time_seconds"] = round(time.perf_counter() - started, 3)
        return result

    def _build_request(
        self, payload: dict[str, Any]
    ) -> tuple[str, dict[str, str], dict[str, Any]]:
        url = f"{self.endpoint}/predict"
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        body: dict[str, Any] = {
            "before": payload.get("before_b64", ""),
            "after": payload.get("after_b64", ""),
        }
        for key in _OPTIONAL_PARAMS:
            if payload.get(key) is not None:
                body[key] = payload[key]
        return url, headers, body

    @staticmethod
    def _write_png(b64: str, prefix: str) -> str:
        if not b64:
            return ""
        fd, path = tempfile.mkstemp(prefix=prefix, suffix=".png")
        os.close(fd)
        with open(path, "wb") as f:
            f.write(base64.b64decode(b64))
        return path

    def _parse_response(self, raw: dict[str, Any]) -> dict[str, Any]:
        from app.utils.upload import upload_image_base64
        mask_uri = ""
        overlay_uri = ""
        
        mask_b64 = raw.get("mask_png_base64", "")
        if mask_b64:
            mask_uri = upload_image_base64(mask_b64, "changedet_mask") or self._write_png(mask_b64, "changedet_mask_")
            
        overlay_b64 = raw.get("overlay_png_base64", "")
        if overlay_b64:
            overlay_uri = upload_image_base64(overlay_b64, "changedet_overlay") or self._write_png(overlay_b64, "changedet_overlay_")

        width, height = int(raw.get("width", 0) or 0), int(raw.get("height", 0) or 0)
        total = int(raw.get("total_pixels") or width * height)
        changed = raw.get("changed_pixels")
        if changed is None:  # older service versions only report a percentage
            changed = round(float(raw.get("changed_percent", 0.0)) / 100.0 * total)

        response = ChangeDetectionResponse(
            changed_pixels=int(changed),
            total_pixels=total,
            changed_percent=float(raw.get("changed_percent", 0.0)),
            n_regions=int(raw.get("n_regions", 0)),
            verdict=str(raw.get("verdict", "")),
            agreement_per_scale={str(k): float(v) for k, v in (raw.get("agreement_per_scale") or {}).items()},
            change_mask_uri=mask_uri,
            change_overlay_uri=overlay_uri,
            mask_width=width,
            mask_height=height,
            model=MODEL_NAME,
            version=MODEL_VERSION,
        )
        return response.model_dump()
