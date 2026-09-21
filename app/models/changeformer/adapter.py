"""ChangeFormer Adapter.

Bi-temporal change detection on same-domain optical imagery.

BOUNDARY CONSTRAINT:
Phase 3 guarantees the inputs are georeferenced and exactly co-registered.
This adapter strictly owns all model-specific ML preprocessing.
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
    SpatialMetadata,
    TemporalMetadata,
)
from app.models.base import BaseModelAdapter
from app.models.client import (
    EndpointNotConfiguredError,
    RemoteModelError,
)
from app.models.changeformer.client import ChangeFormerClient

logger = logging.getLogger(__name__)


class ChangeFormerAdapter(BaseModelAdapter):
    """Adapter for ChangeFormer bi-temporal change detection."""

    def validate_input(self, arguments: dict[str, Any]) -> tuple[bool, str]:
        if not arguments.get("before_asset") or not arguments.get("after_asset"):
            return False, "ChangeFormer requires 'before_asset' and 'after_asset'."
        return True, ""

    async def predict(self, arguments: dict[str, Any]) -> dict[str, Any]:
        settings = get_settings()
        client = ChangeFormerClient(
            endpoint=settings.changeformer_endpoint,
            api_key=settings.changeformer_api_key,
            timeout_seconds=settings.changeformer_timeout_seconds,
        )

        state = arguments.get("_state")
        before_id = arguments.get("before_asset", "")
        after_id = arguments.get("after_asset", "")
        before_uri = ""
        after_uri = ""
        if state:
            for a in state.input_assets:
                if a.asset_id == before_id:
                    before_uri = a.uri
                if a.asset_id == after_id:
                    after_uri = a.uri

        try:
            return await client.infer({
                "before_asset_uri": before_uri,
                "after_asset_uri": after_uri,
                "before_asset_id": before_id,
                "after_asset_id": after_id,
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
        capability = arguments.get("_capability", "detect_bitemporal_change")

        if "_error" in raw:
            return Observation(
                source=EvidenceSource(capability=capability, model="ChangeFormer", backend="remote"),
                type=EvidenceType.ERROR,
                status=ObservationStatus.FAILURE,
                result={
                    "error": raw["_error"],
                    "error_type": raw.get("_error_type", "unknown"),
                    "retryable": raw.get("_retryable", False),
                },
                error_message=raw["_error"],
            )

        return Observation(
            source=EvidenceSource(
                capability=capability,
                model=raw.get("model", "ChangeFormer"),
                version=raw.get("version", ""),
                backend="remote",
            ),
            type=EvidenceType.BITEMPORAL_CHANGE,
            status=ObservationStatus.SUCCESS,
            result={
                "changed_pixels": raw.get("changed_pixels", 0),
                "total_pixels": raw.get("total_pixels", 0),
                "change_mask_uri": raw.get("change_mask_uri", ""),
            },
            artifacts=[raw.get("change_mask_uri", "")] if raw.get("change_mask_uri") else [],
            confidence=None,  # ChangeFormer does not produce calibrated confidence
        )
