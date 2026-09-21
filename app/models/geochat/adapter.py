"""GeoChat Adapter.

Connects the generic Executor to the hosted GeoChat inference service.
The AgentController never directly imports or depends on GeoChat internals.
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
from app.models.client import (
    EndpointNotConfiguredError,
    ModelAuthError,
    ModelConnectionError,
    ModelResponseError,
    ModelTimeoutError,
    RemoteModelError,
)
from app.models.geochat.client import GeoChatClient
from app.models.geochat.schema import GeoChatResponse

logger = logging.getLogger(__name__)


class GeoChatAdapter(BaseModelAdapter):
    """Adapter for the GeoChat vision-language model."""

    def validate_input(self, arguments: dict[str, Any]) -> tuple[bool, str]:
        """Validate input arguments."""
        if not arguments.get("asset"):
            return False, "GeoChat requires an 'asset' argument."
        return True, ""

    async def predict(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call the remote GeoChat service."""
        settings = get_settings()
        client = GeoChatClient(
            endpoint=settings.geochat_endpoint,
            api_key=settings.geochat_api_key,
            timeout_seconds=settings.geochat_timeout_seconds,
        )

        # Resolve asset URI from state if available
        state = arguments.get("_state")
        asset_id = arguments.get("asset", "")
        asset_uri = ""
        if state:
            for a in state.input_assets:
                if a.asset_id == asset_id:
                    asset_uri = a.uri
                    break

        prompt = arguments.get("prompt", "Describe the major objects, land-cover characteristics, and spatial patterns visible in this satellite image.")

        try:
            result = await client.infer({
                "asset_uri": asset_uri,
                "prompt": prompt,
                "asset_id": asset_id,
            })
            return result
        except EndpointNotConfiguredError as exc:
            return {"_error": str(exc), "_error_type": "endpoint_not_configured", "_retryable": False}
        except ModelTimeoutError as exc:
            return {"_error": str(exc), "_error_type": "timeout", "_retryable": True}
        except ModelConnectionError as exc:
            return {"_error": str(exc), "_error_type": "connection_error", "_retryable": True}
        except ModelAuthError as exc:
            return {"_error": str(exc), "_error_type": "auth_error", "_retryable": False}
        except ModelResponseError as exc:
            return {"_error": str(exc), "_error_type": "response_error", "_retryable": exc.retryable}
        except RemoteModelError as exc:
            return {"_error": str(exc), "_error_type": "remote_error", "_retryable": exc.retryable}

    def normalize_output(
        self, raw: dict[str, Any], arguments: dict[str, Any]
    ) -> Observation:
        """Convert GeoChat response into a normalized Observation."""
        capability = arguments.get("_capability", "interpret_scene")

        # Handle error responses from predict()
        if "_error" in raw:
            return Observation(
                source=EvidenceSource(
                    capability=capability,
                    model="GeoChat",
                    backend="remote",
                ),
                type=EvidenceType.ERROR,
                status=ObservationStatus.FAILURE,
                result={
                    "error": raw["_error"],
                    "error_type": raw.get("_error_type", "unknown"),
                    "retryable": raw.get("_retryable", False),
                },
                error_message=raw["_error"],
            )

        # Parse successful response
        try:
            response = GeoChatResponse(**raw)
        except Exception as exc:
            return Observation(
                source=EvidenceSource(
                    capability=capability,
                    model="GeoChat",
                    backend="remote",
                ),
                type=EvidenceType.ERROR,
                status=ObservationStatus.FAILURE,
                result={"error": f"Failed to parse GeoChat response: {exc}"},
                error_message=str(exc),
            )
            
        # Optional: Parse Bounding Boxes and Annotate Image
        artifacts = []
        result_payload = {
            "text": response.text,
            "model": response.model,
            "version": response.version,
        }
        
        # Check if the text contains coordinate patterns [ymin, xmin, ymax, xmax]
        if "[" in response.text and "]" in response.text:
            from app.models.geochat.parser import annotate_image
            
            # Resolve asset URI
            state = arguments.get("_state")
            asset_id = arguments.get("asset", "")
            asset_uri = ""
            if state:
                for a in state.input_assets:
                    if a.asset_id == asset_id:
                        asset_uri = a.uri
                        break
                        
            if asset_uri:
                annotated_uri = annotate_image(asset_uri, response.text)
                if annotated_uri:
                    artifacts.append(annotated_uri)
                    result_payload["annotated_image_uri"] = annotated_uri

        return Observation(
            source=EvidenceSource(
                capability=capability,
                model=response.model,
                version=response.version,
                backend="remote",
            ),
            type=EvidenceType.SCENE_INTERPRETATION,
            status=ObservationStatus.SUCCESS,
            result=result_payload,
            artifacts=artifacts,
            confidence=None,  # GeoChat does not produce calibrated confidence
        )

