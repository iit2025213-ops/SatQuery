"""TerraMind adapter.

Multimodal foundation model for EO tasks.
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
from app.models.terramind.client import TerraMindClient

logger = logging.getLogger(__name__)


class TerraMindAdapter(BaseModelAdapter):
    """Adapter for IBM TerraMind multimodal foundation model."""

    def validate_input(self, arguments: dict[str, Any]) -> tuple[bool, str]:
        cap = arguments.get("_capability", "")
        if cap == "terramind_coordinate_tokenizer":
            if "coords" not in arguments:
                return False, "TerraMind coordinate tokenizer requires 'coords' list of [lon, lat]."
            return True, ""
        
        # Checking either 'asset_uri', 'assets', or 'asset' (common for agent capabilities)
        if "asset_uri" not in arguments and "assets" not in arguments and "asset" not in arguments:
            return False, "TerraMind requires an 'asset' or 'assets' parameter pointing to the image."
        return True, ""

    async def predict(self, arguments: dict[str, Any]) -> dict[str, Any]:
        settings = get_settings()
        client = TerraMindClient(
            endpoint=settings.terramind_endpoint,
            api_key=settings.terramind_api_key,
            timeout_seconds=settings.terramind_timeout_seconds,
        )

        cap = arguments.get("_capability", "")
        
        if cap == "terramind_coordinate_tokenizer":
            payload = {
                "operation": cap,
                "coords": arguments.get("coords")
            }
        else:
            asset_uri = ""
            
            # Resolve asset_id from arguments
            asset_id = arguments.get("asset")
            if not asset_id and "assets" in arguments and len(arguments["assets"]) > 0:
                 asset_id = arguments["assets"][0]

            # If arguments came from agent state input_assets, let's resolve it.
            if "_state" in arguments and asset_id:
                state = arguments["_state"]
                for a in state.input_assets:
                    if a.asset_id == asset_id:
                        asset_uri = a.uri
                        break

            # Fallback if directly passing asset_uri
            if not asset_uri and "asset_uri" in arguments:
                asset_uri = arguments["asset_uri"]

            if not asset_uri:
                 return {"_error": f"Could not resolve asset '{asset_id}'.", "_error_type": "ValueError", "_retryable": False}

            modality = arguments.get("modality", "S2L2A")
            data = {"modality": modality}

            if cap == "terramind_embedding":
                data["merge_method"] = arguments.get("merge_method", "mean")
                if "band_indices" in arguments:
                    data["band_indices"] = arguments["band_indices"]
            elif cap == "terramind_tim":
                data["tim_modalities"] = arguments.get("tim_modalities", "LULC")
                if "band_indices" in arguments:
                    data["band_indices"] = arguments["band_indices"]
            elif cap == "terramind_generate":
                data["output_modalities"] = arguments.get("output_modalities", "S1GRD,LULC")
                if "timesteps" in arguments:
                    data["timesteps"] = str(arguments["timesteps"])
                if "standardize" in arguments:
                    data["standardize"] = bool(arguments["standardize"])
                if "band_indices" in arguments:
                    data["band_indices"] = arguments["band_indices"]
                if "include_png" in arguments:
                    data["include_png"] = bool(arguments["include_png"])

            payload = {
                "operation": cap,
                "file_path": asset_uri,
                "data": data,
            }

        try:
            res = await client.infer(payload)
            return res
        except RemoteModelError as exc:
            return {
                "_error": str(exc),
                "_error_type": type(exc).__name__,
                "_retryable": exc.retryable,
            }
        except Exception as exc:
            return {
                "_error": str(exc),
                "_error_type": type(exc).__name__,
                "_retryable": False,
            }

    def normalize_output(
        self, raw: dict[str, Any], arguments: dict[str, Any]
    ) -> Observation:
        cap = arguments.get("_capability", "")

        if "_error" in raw:
            return Observation(
                source=EvidenceSource(capability=cap, model="TerraMind", backend="remote"),
                type=EvidenceType.ERROR,
                status=ObservationStatus.FAILURE,
                result={
                    "error": raw["_error"],
                    "error_type": raw.get("_error_type", "unknown"),
                    "retryable": raw.get("_retryable", False),
                },
                error_message=raw["_error"],
            )
            
        evidence_type = EvidenceType.MULTIMODAL
        artifacts = []
        
        # Check if there are generated PNGs and upload to Cloudinary
        if cap == "terramind_generate" and "outputs" in raw:
            from app.utils.upload import upload_image_base64
            for mod, data in raw["outputs"].items():
                if "png_base64" in data:
                    evidence_type = EvidenceType.IMAGE_PROCESSING
                    url = upload_image_base64(data["png_base64"], f"terramind_{mod}")
                    if url:
                        artifacts.append(url)
        
        # Remove massive raw tensors to avoid agent memory bloat, unless specifically needed
        result_clean = raw.copy()
        if "outputs" in result_clean:
             for k, v in result_clean["outputs"].items():
                  if isinstance(v, dict) and "data_b64_npy" in v:
                       del v["data_b64_npy"]
                  if isinstance(v, dict) and "png_base64" in v:
                       del v["png_base64"] # We uploaded it, no need to keep b64 in memory
        if "data_b64_npy" in result_clean:
             del result_clean["data_b64_npy"]
        if "final_layer_b64_npy" in result_clean:
             del result_clean["final_layer_b64_npy"]

        return Observation(
            source=EvidenceSource(
                capability=cap,
                model="TerraMind",
                version="large_v1",
                backend="remote",
            ),
            type=evidence_type,
            status=ObservationStatus.SUCCESS,
            result=result_clean,
            artifacts=artifacts,
        )
