"""Prithvi adapter.

EO / multispectral foundation model for representation and downstream tasks.
"""

from __future__ import annotations

import logging
from typing import Any

from app.config import get_settings
from app.evidence.schema import (
    EvidenceSource,
    EvidenceType,
    Observation,
    ObservationStatus,
)
from app.models.base import BaseModelAdapter
from app.models.client import RemoteModelError
from app.models.prithvi.client import PrithviClient

logger = logging.getLogger(__name__)


class PrithviAdapter(BaseModelAdapter):
    """Adapter for Prithvi multispectral foundation model."""

    def validate_input(self, arguments: dict[str, Any]) -> tuple[bool, str]:
        if not arguments.get("asset") and not arguments.get("image_uri"):
            return False, "Prithvi requires an 'asset' or 'image_uri'."
        return True, ""

    async def predict(self, arguments: dict[str, Any]) -> dict[str, Any]:
        settings = get_settings()
        client = PrithviClient(
            endpoint=settings.prithvi_endpoint,
            api_key=settings.prithvi_api_key,
            timeout_seconds=settings.prithvi_timeout_seconds,
        )

        state = arguments.get("_state")
        asset_id = arguments.get("asset", "")
        asset_uri = arguments.get("image_uri", "")
        
        if not asset_uri and state:
            for a in state.input_assets:
                if a.asset_id == asset_id:
                    asset_uri = a.uri
                    break

        try:
            return await client.infer({
                "asset_uri": asset_uri,
                "asset_id": asset_id,
                "task": "land_cover",
            })
        except RemoteModelError as exc:
            return {
                "_error": str(exc),
                "_error_type": type(exc).__name__,
                "_retryable": exc.retryable,
            }

    def normalize_output(
        self, raw: dict[str, Any], arguments: dict[str, Any]
    ) -> Observation:
        cap = arguments.get("_capability", "analyze_multispectral_image")

        if "_error" in raw:
            return Observation(
                source=EvidenceSource(capability=cap, model="Prithvi", backend="remote"),
                type=EvidenceType.ERROR,
                status=ObservationStatus.FAILURE,
                result={
                    "error": raw["_error"],
                    "error_type": raw.get("_error_type", "unknown"),
                    "retryable": raw.get("_retryable", False),
                },
                error_message=raw["_error"],
            )

        is_image = "mask_base64" in raw.get("result", raw)
        
        return Observation(
            source=EvidenceSource(
                capability=cap,
                model=raw.get("model", "Prithvi"),
                version=raw.get("version", ""),
                backend="remote"
            ),
            type=EvidenceType.IMAGE_BASE64 if is_image else EvidenceType.MULTISPECTRAL,
            status=ObservationStatus.SUCCESS,
            result=raw.get("result", raw),
            confidence=raw.get("result", {}).get("confidence"),
        )
