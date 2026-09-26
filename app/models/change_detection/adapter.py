"""Change_detection Adapter.

Bi-temporal change detection on same-domain optical imagery (Siamese U-Net, multi-scale fused).

BOUNDARY CONSTRAINT:
Phase 3 guarantees the inputs are georeferenced and exactly co-registered.
This adapter strictly owns all model-specific ML preprocessing (see preprocess.py: any input is turned into
an 8-bit RGB PNG before it is sent to the service).

The service works on pixels. The returned mask/overlay have size (mask_width x mask_height) and lie on the SAME
pixel grid as the inputs (which Phase 3 guarantees are identical), so map coordinates can be recovered with the
asset's own geotransform. (If the two inputs ever differed in size, the service resizes 'after' to match 'before'.)
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
from app.models.change_detection.client import MODEL_NAME, MODEL_VERSION, ChangeDetectionClient

logger = logging.getLogger(__name__)

# Optional tuning arguments that are forwarded to the service when present (see deploy/server.py).
_OPTIONAL_ARGS = ("scales", "quorum", "threshold", "min_area", "tta")


class ChangeDetectionAdapter(BaseModelAdapter):
    """Adapter for Change_detection bi-temporal change detection."""

    def validate_input(self, arguments: dict[str, Any]) -> tuple[bool, str]:
        if not arguments.get("before_asset") or not arguments.get("after_asset"):
            return False, "Change_detection requires 'before_asset' and 'after_asset'."
        return True, ""

    async def predict(self, arguments: dict[str, Any]) -> dict[str, Any]:
        settings = get_settings()
        client = ChangeDetectionClient(
            endpoint=settings.change_detection_endpoint,
            api_key=settings.change_detection_api_key,
            timeout_seconds=settings.change_detection_timeout_seconds,
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

        if not before_uri or not after_uri:
            missing = [n for n, u in (("before_asset", before_uri), ("after_asset", after_uri)) if not u]
            return {
                "_error": f"Could not resolve {' and '.join(missing)} to an input asset URI.",
                "_error_type": "AssetNotFound",
                "_retryable": False,
            }

        payload: dict[str, Any] = {
            "before_asset_uri": before_uri,
            "after_asset_uri": after_uri,
            "before_asset_id": before_id,
            "after_asset_id": after_id,
        }
        for key in _OPTIONAL_ARGS:
            if arguments.get(key) is not None:
                payload[key] = arguments[key]

        try:
            return await client.infer(payload)
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
                source=EvidenceSource(capability=capability, model=MODEL_NAME, backend="remote"),
                type=EvidenceType.ERROR,
                status=ObservationStatus.FAILURE,
                result={
                    "error": raw["_error"],
                    "error_type": raw.get("_error_type", "unknown"),
                    "retryable": raw.get("_retryable", False),
                },
                error_message=raw["_error"],
            )

        artifacts = [u for u in (raw.get("change_mask_uri", ""), raw.get("change_overlay_uri", "")) if u]
        
        # Compute mean agreement across scales as initial confidence signal
        agreements = list(raw.get("agreement_per_scale", {}).values())
        initial_confidence = sum(agreements) / len(agreements) if agreements else 0.5
        
        return Observation(
            source=EvidenceSource(
                capability=capability,
                model=raw.get("model", MODEL_NAME),
                version=raw.get("version", MODEL_VERSION),
                backend="remote",
            ),
            type=EvidenceType.BITEMPORAL_CHANGE,
            status=ObservationStatus.SUCCESS,
            result={
                "changed_pixels": raw.get("changed_pixels", 0),
                "total_pixels": raw.get("total_pixels", 0),
                "changed_percent": raw.get("changed_percent", 0.0),
                "n_regions": raw.get("n_regions", 0),
                "verdict": raw.get("verdict", ""),
                "agreement_per_scale": raw.get("agreement_per_scale", {}),
                "change_mask_uri": raw.get("change_mask_uri", ""),
                "change_overlay_uri": raw.get("change_overlay_uri", ""),
                "mask_width": raw.get("mask_width", 0),
                "mask_height": raw.get("mask_height", 0),
                "inference_time_seconds": raw.get("inference_time_seconds"),
            },
            artifacts=artifacts,
            confidence=initial_confidence,
        )
