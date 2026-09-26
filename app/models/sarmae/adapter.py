"""SARMAE adapter.

SAR representation model for SAR-specific analysis.
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
from app.models.sarmae.client import SARMAEClient

logger = logging.getLogger(__name__)


class SARMAEAdapter(BaseModelAdapter):
    """Adapter for SAR-MAE SAR analysis model."""

    def validate_input(self, arguments: dict[str, Any]) -> tuple[bool, str]:
        if not arguments.get("asset") and not arguments.get("image_uri"):
            return False, "SARMAE requires an 'asset' or 'image_uri'."
        return True, ""

    async def predict(self, arguments: dict[str, Any]) -> dict[str, Any]:
        settings = get_settings()
        client = SARMAEClient(
            endpoint=settings.sarmae_endpoint,
            api_key=settings.sarmae_api_key,
            timeout_seconds=settings.sarmae_timeout_seconds,
        )

        state = arguments.get("_state")
        asset_id = arguments.get("asset", "")
        asset_uri = arguments.get("image_uri", "")

        if not asset_uri and state:
            for a in state.input_assets:
                if a.asset_id == asset_id:
                    asset_uri = a.uri
                    break

        if not asset_uri:
            return {
                "_error": "No asset_uri provided or found in state.",
                "_error_type": "ValueError",
                "_retryable": False,
            }

        import os
        from app.geospatial.processing import create_visual_preview
        
        preview_res = create_visual_preview(input_uri=asset_uri)
        if "error" in preview_res:
            return {
                "_error": preview_res["error"],
                "_error_type": "GeospatialProcessingError",
                "_retryable": False,
            }
            
        visual_uri = preview_res.get("preview_uri", "")

        try:
            res = await client.infer({
                "asset_uri": visual_uri,
                "asset_id": asset_id,
            })
            # Only clean up local temp files, not cloud URLs
            if visual_uri and not visual_uri.startswith("http") and not visual_uri.startswith("mock://") and os.path.exists(visual_uri):
                os.remove(visual_uri)
            return res
        except RemoteModelError as exc:
            if visual_uri and not visual_uri.startswith("http") and not visual_uri.startswith("mock://") and os.path.exists(visual_uri):
                os.remove(visual_uri)
            return {
                "_error": str(exc),
                "_error_type": type(exc).__name__,
                "_retryable": exc.retryable,
            }

    def normalize_output(
        self, raw: dict[str, Any], arguments: dict[str, Any]
    ) -> Observation:
        cap = arguments.get("_capability", "analyze_sar_image")

        if "_error" in raw:
            return Observation(
                source=EvidenceSource(capability=cap, model="SARMAE", backend="remote"),
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
                capability=cap,
                model=raw.get("model", "SARMAE"),
                version=raw.get("version", ""),
                backend="remote",
            ),
            type=EvidenceType.SAR,
            status=ObservationStatus.SUCCESS,
            result=raw.get("result", raw),
            confidence=raw.get("result", {}).get("confidence"),
        )
