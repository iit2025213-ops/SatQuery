"""OpenAI LLM provider — production implementation.

The ``OpenAIProvider`` converts the agent context into structured
OpenAI chat-completion requests and parses the response back into
the canonical ``Decision`` schema.  It handles:

- structured JSON output generation (strict schema, with fallback)
- response validation
- API errors (timeout, rate-limit, network) with backoff
- malformed responses (with retry)
- latency recording
- provider metadata

The provider NEVER exposes hidden chain-of-thought.

The API key is loaded from the environment and is **never** hardcoded
or committed.
"""

from __future__ import annotations

import io
import json
import logging
import time
from typing import Any

from app.agent.decision import ActionType, Decision
from app.llm.base import LLMProvider

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Exceptions
# ------------------------------------------------------------------

class OpenAIConfigError(Exception):
    """Raised when OpenAI is invoked without valid configuration."""


class OpenAIResponseError(Exception):
    """Raised when an OpenAI response cannot be parsed into a Decision."""


# ------------------------------------------------------------------
# Decision JSON schema for structured output (strict mode)
# ------------------------------------------------------------------
#
# OpenAI's strict json_schema mode requires every object to list ALL
# its keys in "required" (optional fields become nullable types, not
# omitted) and forbids free-form dicts (no arbitrary-key objects).
# Because "arguments", "parallel_capabilities" and
# "specialist_evaluations" all have dynamic/arbitrary keys, they are
# encoded as JSON strings here and decoded back into real objects in
# _normalize_response() before Decision validation.

_DECISION_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": [
                "CALL_CAPABILITY",
                "PARALLEL",
                "RETRY",
                "REPLAN",
                "REQUEST_INPUT",
                "CONVERSATIONAL",
                "FINAL",
            ],
        },
        "capability": {"type": ["string", "null"]},
        "arguments_json": {
            "type": ["string", "null"],
            "description": (
                "JSON-encoded object of capability arguments, e.g. "
                '\'{"asset": "asset_001"}\'. Null if not applicable.'
            ),
        },
        "reason": {"type": ["string", "null"]},
        "parallel_capabilities_json": {
            "type": ["string", "null"],
            "description": (
                "JSON-encoded array of {capability, arguments} objects. "
                "Only used when action is PARALLEL."
            ),
        },
        "final_answer": {"type": ["string", "null"]},
        "final_confidence": {"type": ["number", "null"]},
        "specialist_evaluations_json": {
            "type": ["string", "null"],
            "description": (
                "JSON-encoded object mapping evidence_id to a 0.0-1.0 score."
            ),
        },
    },
    "required": [
        "action",
        "capability",
        "arguments_json",
        "reason",
        "parallel_capabilities_json",
        "final_answer",
        "final_confidence",
        "specialist_evaluations_json",
    ],
    "additionalProperties": False,
}

# Fields that arrive as JSON-encoded strings under strict mode and need
# to be decoded back into python objects, mapped to their real Decision
# field name.
_JSON_STRING_FIELDS: dict[str, str] = {
    "arguments_json": "arguments",
    "parallel_capabilities_json": "parallel_capabilities",
    "specialist_evaluations_json": "specialist_evaluations",
}


# ------------------------------------------------------------------
# Provider
# ------------------------------------------------------------------

class OpenAIProvider(LLMProvider):
    """Production LLM backend powered by the OpenAI API.

    Parameters
    ----------
    api_key:
        OpenAI API key — loaded from environment, never hardcoded.
    model:
        Model identifier (e.g. ``gpt-4.1-mini``).
    base_url:
        Custom OpenAI-compatible endpoint.  Empty string uses the
        official endpoint.
    temperature:
        Sampling temperature for decision generation.
    max_retries:
        Maximum number of retries on transient API errors.
    max_tokens_decide:
        Output token cap for decide() calls.
    max_tokens_synthesize:
        Output token cap for synthesize() calls.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "",
        base_url: str = "",
        temperature: float = 0.1,
        max_retries: int = 2,
        max_tokens_decide: int = 2000,
        max_tokens_synthesize: int = 2000,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url or None
        self._temperature = temperature
        self._max_retries = max_retries
        self._max_tokens_decide = max_tokens_decide
        self._max_tokens_synthesize = max_tokens_synthesize
        self._client: Any = None

        # Once a strict-schema call fails with a non-retryable error
        # (e.g. the configured model doesn't support json_schema mode),
        # stop retrying strict mode for the rest of this provider's
        # lifetime and fall back to plain json_object mode.
        self._strict_schema_supported = True

        # Deferred client creation — only when actually needed.
        # This ensures imports and Settings construction never fail
        # merely because the key is empty.

    # ------------------------------------------------------------------
    # LLMProvider interface
    # ------------------------------------------------------------------

    async def decide(self, context: dict[str, Any]) -> Decision:
        """Ask the LLM for the next structured Decision."""
        self._ensure_client()

        system_prompt = self._build_system_prompt(context)
        user_prompt = await self._build_user_prompt(context)

        raw_json = await self._call_api(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            purpose="decide",
            json_mode=True,
            max_tokens=self._max_tokens_decide,
        )

        return self._parse_decision(raw_json)

    async def synthesize(self, context: dict[str, Any]) -> str:
        """Produce a natural-language summary from accumulated evidence."""
        self._ensure_client()

        system_prompt = (
            "You are a remote-sensing analysis assistant. "
            "Produce a concise, evidence-grounded answer based on the "
            "observations collected during the analysis. "
            "Do NOT fabricate results that were not observed. "
            "Reference only evidence that exists in the observations."
        )
        user_prompt = (
            "Synthesize a clear answer from these observations:\n\n"
            + json.dumps(context, default=str, indent=2)
        )

        raw_text = await self._call_api(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            purpose="synthesize",
            json_mode=False,
            max_tokens=self._max_tokens_synthesize,
        )
        return raw_text

    # ------------------------------------------------------------------
    # Client management
    # ------------------------------------------------------------------

    def _ensure_client(self) -> None:
        """Lazily create the OpenAI client; raise a clear error if
        the API key is missing or the SDK is not installed."""
        if self._client is not None:
            return

        if not self._api_key:
            raise OpenAIConfigError(
                "OpenAI API key is not configured. "
                "Set the OPENAI_API_KEY environment variable."
            )

        if not self._model:
            raise OpenAIConfigError(
                "OpenAI model is not configured. "
                "Set the OPENAI_MODEL environment variable."
            )

        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise OpenAIConfigError(
                "The 'openai' package is not installed. "
                "Run: pip install openai"
            )

        kwargs: dict[str, Any] = {"api_key": self._api_key}
        if self._base_url:
            kwargs["base_url"] = self._base_url

        self._client = AsyncOpenAI(**kwargs)
        logger.info(
            "OpenAI client created: model=%s base_url=%s",
            self._model,
            self._base_url or "default",
        )

    # ------------------------------------------------------------------
    # API call with retry + backoff
    # ------------------------------------------------------------------

    async def _call_api(
        self,
        *,
        system_prompt: str,
        user_prompt: str | list[dict[str, Any]],
        purpose: str,
        json_mode: bool = True,
        max_tokens: int | None = None,
    ) -> str:
        """Call the OpenAI API with retry + backoff on transient errors.

        Returns the raw response content string.
        """
        # Lazy imports so openai errors only surface at call time
        from openai import (
            APIConnectionError,
            APITimeoutError,
            RateLimitError,
            APIStatusError,
        )

        last_error: Exception | None = None
        attempts = self._max_retries + 1

        for attempt in range(1, attempts + 1):
            t0 = time.monotonic()
            try:
                kwargs: dict[str, Any] = {
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": self._temperature,
                }
                if max_tokens is not None:
                    kwargs["max_tokens"] = max_tokens

                if json_mode:
                    if self._strict_schema_supported:
                        kwargs["response_format"] = {
                            "type": "json_schema",
                            "json_schema": {
                                "name": "agent_decision",
                                "strict": True,
                                "schema": _DECISION_JSON_SCHEMA,
                            },
                        }
                    else:
                        kwargs["response_format"] = {"type": "json_object"}

                response = await self._client.chat.completions.create(**kwargs)
                elapsed = time.monotonic() - t0

                content = response.choices[0].message.content or ""
                logger.info(
                    "OpenAI %s response: model=%s attempt=%d/%d "
                    "latency=%.2fs tokens=%s strict_schema=%s",
                    purpose,
                    self._model,
                    attempt,
                    attempts,
                    elapsed,
                    getattr(response.usage, "total_tokens", "?"),
                    json_mode and self._strict_schema_supported,
                )
                return content

            except (APITimeoutError, APIConnectionError) as exc:
                elapsed = time.monotonic() - t0
                last_error = exc
                logger.warning(
                    "OpenAI %s transient error (attempt %d/%d, %.2fs): %s",
                    purpose, attempt, attempts, elapsed, exc,
                )
                if attempt == attempts:
                    break
                import asyncio
                await asyncio.sleep(min(2 ** attempt, 8))
                continue

            except RateLimitError as exc:
                elapsed = time.monotonic() - t0
                last_error = exc
                logger.warning(
                    "OpenAI rate limit hit (attempt %d/%d, %.2fs): %s",
                    attempt, attempts, elapsed, exc,
                )
                if attempt == attempts:
                    break
                import asyncio
                await asyncio.sleep(min(2 ** attempt, 8))
                continue

            except APIStatusError as exc:
                elapsed = time.monotonic() - t0

                # If strict json_schema mode itself is the problem (e.g.
                # the configured model doesn't support it), fall back to
                # plain json_object mode and retry immediately — this is
                # not a transient error, so it doesn't count against the
                # normal retry budget's backoff.
                if (
                    json_mode
                    and self._strict_schema_supported
                    and exc.status_code in (400, 404, 422)
                ):
                    logger.warning(
                        "OpenAI rejected strict json_schema mode "
                        "(status=%s): %s — falling back to json_object "
                        "mode for model=%s.",
                        exc.status_code, exc, self._model,
                    )
                    self._strict_schema_supported = False
                    continue

                logger.error(
                    "OpenAI API error (attempt %d/%d, %.2fs): status=%s %s",
                    attempt, attempts, elapsed, exc.status_code, exc,
                )
                raise OpenAIResponseError(
                    f"OpenAI API error {exc.status_code}: {exc}"
                ) from exc

            except Exception as exc:
                elapsed = time.monotonic() - t0
                logger.error(
                    "Unexpected OpenAI error (%.2fs): %s", elapsed, exc,
                )
                raise OpenAIResponseError(
                    f"Unexpected OpenAI error: {exc}"
                ) from exc

        # All retries exhausted
        raise OpenAIResponseError(
            f"OpenAI {purpose} failed after {attempts} attempts: {last_error}"
        )

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_decision(self, raw: str) -> Decision:
        """Parse raw JSON string into a validated ``Decision``.

        Handles malformed JSON, missing fields, and invalid values.
        """
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.error("OpenAI returned invalid JSON: %s", raw[:500])
            raise OpenAIResponseError(
                f"Invalid JSON from OpenAI: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise OpenAIResponseError(
                f"Expected JSON object, got {type(data).__name__}"
            )

        data = self._normalize_response(data)

        try:
            decision = Decision.model_validate(data)
        except Exception as exc:
            logger.error(
                "OpenAI response failed Decision validation: %s — raw: %s",
                exc, data,
            )
            raise OpenAIResponseError(
                f"Decision validation failed: {exc}"
            ) from exc

        return decision

    @staticmethod
    def _normalize_response(data: dict[str, Any]) -> dict[str, Any]:
        """Fix common LLM output quirks before Pydantic validation.

        - Strict-mode *_json string fields decoded back into real objects
        - Lowered action → uppercased
        - ``tool`` / ``tool_name`` → ``capability``
        - ``rationale`` / ``reasoning`` → ``reason``
        - ``answer`` → ``final_answer``
        - ``confidence`` at top level → ``final_confidence``
        """
        # Decode strict-mode JSON-string fields back into python objects.
        for json_field, target_field in _JSON_STRING_FIELDS.items():
            if json_field in data:
                raw_val = data.pop(json_field)
                if target_field in data and data[target_field] is not None:
                    # Already provided directly (legacy/non-strict path) —
                    # don't overwrite.
                    continue
                if raw_val in (None, ""):
                    continue
                if isinstance(raw_val, str):
                    try:
                        data[target_field] = json.loads(raw_val)
                    except json.JSONDecodeError:
                        logger.warning(
                            "Failed to decode %s as JSON: %r",
                            json_field, raw_val[:300],
                        )
                else:
                    # Model already returned a native object (non-strict
                    # path) — use as-is.
                    data[target_field] = raw_val

        # action casing
        if "action" in data and isinstance(data["action"], str):
            data["action"] = data["action"].upper()

        # capability aliases
        for alias in ("tool", "tool_name"):
            if alias in data and "capability" not in data:
                data["capability"] = data.pop(alias)

        # reason aliases
        for alias in ("rationale", "reasoning", "reasoning_summary"):
            if alias in data and "reason" not in data:
                data["reason"] = data.pop(alias)

        # final answer aliases
        if "answer" in data and "final_answer" not in data:
            data["final_answer"] = data.pop("answer")

        # top-level confidence → final_confidence for FINAL
        if (
            data.get("action") == "FINAL"
            and "confidence" in data
            and "final_confidence" not in data
        ):
            data["final_confidence"] = data.pop("confidence")

        # Ensure arguments is a dict
        if "arguments" in data and data["arguments"] is None:
            data["arguments"] = {}

        # Ensure parallel_capabilities is a list
        if "parallel_capabilities" in data and data["parallel_capabilities"] is None:
            data["parallel_capabilities"] = []

        return data

    # ------------------------------------------------------------------
    # System prompt
    # ------------------------------------------------------------------

    @staticmethod
    def _build_system_prompt(context: dict[str, Any]) -> str:
        """Construct the system prompt that establishes the LLM's role
        as a continuous controller."""

        capabilities = context.get("available_capabilities", [])
        cap_block = "\n".join(f"  - {c}" for c in capabilities) if capabilities else "  (none registered)"

        prompt_parts = []
        prompt_parts.append(
            "You are the SatQuery AI Core -- an elite, fully autonomous Master "
            "Geospatial Intelligence Director. You orchestrate a distributed swarm "
            "of specialized remote-sensing AI models to solve complex geospatial "
            "intelligence problems with surgical precision."
        )

        # Section 1: Conversational vs Analysis mode
        prompt_parts.append(
            "\n\n## 1. CONVERSATIONAL MODE vs ANALYSIS MODE\n\n"
            "**CONVERSATIONAL MODE (DEFAULT):**\n"
            "When the user sends a simple greeting, question, or chat message "
            "WITHOUT satellite imagery or analysis requests, you MUST respond using "
            "the CONVERSATIONAL action. Do NOT invoke any specialist models. Simply "
            "have a friendly, intelligent conversation. Examples:\n"
            "- 'Hello' -> CONVERSATIONAL (reply with a warm greeting and explain your capabilities)\n"
            "- 'What can you do?' -> CONVERSATIONAL (describe your multi-model analysis pipeline)\n"
            "- 'Tell me about SAR imagery' -> CONVERSATIONAL (answer with your domain expertise)\n\n"
            "**ANALYSIS MODE (TRIGGERED BY IMAGERY + QUESTION):**\n"
            "When the user provides satellite images AND asks a question about them "
            "(e.g., 'analyze this image', 'what changed?', 'classify land use'), "
            "you MUST switch to full analysis mode and begin orchestrating specialist "
            "models. Only then should you use CALL_CAPABILITY, PARALLEL, RETRY, REPLAN, "
            "or FINAL actions.\n\n"
            "**TRANSITION RULE:** If input_assets is empty or contains no imagery, stay "
            "in CONVERSATIONAL mode. The moment imagery appears with an analytical query, "
            "engage full pipeline orchestration."
        )

        # Section 2: Core Operating Paradigm
        prompt_parts.append(
            "\n\n## 2. CORE OPERATING PARADIGM\n"
            "You operate on a rigorous ReAct (Reason + Act) loop. You NEVER formulate a "
            "rigid upfront plan. Instead:\n"
            "1. Evaluate the current intelligence state (what observations exist so far)\n"
            "2. Dispatch the optimal specialist model for the NEXT piece of missing evidence\n"
            "3. Interpret the returning telemetry (text, images, tensors)\n"
            "4. Visually cross-verify all generated artifacts against your own visual cortex\n"
            "5. Dynamically calculate your next optimal move based on ALL accumulated evidence\n"
            "6. Repeat until sufficient evidence exists to produce a comprehensive FINAL briefing"
        )

        # Section 3: Rock-solid model I/O reference
        prompt_parts.append(
            "\n\n## 3. SPECIALIST MODEL REFERENCE (ROCK-SOLID I/O)\n\n"
            "### 3a. GeoChat (Visual Question Answering)\n"
            "- Capability Name: geochat_analyze\n"
            "- What it does: Takes a satellite image and a natural-language question, "
            "returns a textual description of visual contents (buildings, roads, water, "
            "vegetation, terrain types).\n"
            "- Input: {asset: '<asset_id>', question: '<your question>'}\n"
            "- Output: A text observation with scene description.\n"
            "- Best for: Initial scene understanding, identifying object types.\n"
            "- Limitation: Text-only output. No masks, no math. Must be cross-verified visually.\n\n"

            "### 3b. TerraMind (Foundation Model)\n"
            "- Capability Names: terramind_tim (classification), terramind_generate "
            "(cross-modal generation), terramind_embedding (feature vector)\n"
            "- What it does: Processes satellite imagery through a massive foundation "
            "model to produce land-use classification (LULC), vegetation indices (NDVI), "
            "synthetic radar (S1GRD), elevation (DEM), or dense embeddings.\n"
            "- Input for terramind_tim: {\"asset\": \"<asset_id>\", \"modality\": \"RGB\", \"tim_modalities\": \"LULC\"}\n"
            "- Input for terramind_generate: {\"asset\": \"<asset_id>\", \"modality\": \"RGB\", "
            "\"output_modalities\": \"S1GRD\", \"include_png\": true}\n"
            "- Input for terramind_embedding: {\"asset\": \"<asset_id>\", \"modality\": \"RGB\"}\n"
            "- CRITICAL: The 'asset' key is MANDATORY for all terramind_* capabilities. "
            "You MUST set \"asset\": \"<the exact asset_id from input_assets>\". "
            "Omitting it will cause a precondition failure.\n"
            "- Output: Classification labels, generated cross-modal images (PNG), or "
            "dense feature embeddings.\n"
            "- DYNAMIC MODALITY SELECTION -- YOU MUST REASON ABOUT WHICH TO REQUEST:\n"
            "  * S1GRD -- Synthetic Aperture Radar. Use for structures, buildings, vessels, cloud-obscured areas.\n"
            "  * LULC -- Land Use / Land Cover. Use for terrain classification (urban, forest, water, agricultural).\n"
            "  * NDVI -- Normalized Difference Vegetation Index. Use for vegetation health, deforestation. "
            "TerraMind CAN generate NDVI from ANY image including plain RGB PNG -- no multispectral bands required. Use terramind_generate with modality=RGB and output_modalities=NDVI and include_png=true.\n"
            "  * DEM -- Digital Elevation Model. Use when elevation or topography is relevant.\n\n"

            "### 3e. GPT-4 Vision (Grounding + Captioning)\n"
            "- Capability Names: ground_region, generate_caption\n"
            "- What it does: Detects and draws bounding boxes around ALL objects in an image "
            "(buildings, roads, vegetation, vehicles, structures) and generates detailed captions.\n"
            "- Input for ground_region: {\"asset\": \"<asset_id>\"}\n"
            "- Input for generate_caption: {\"asset\": \"<asset_id>\"}\n"
            "- CRITICAL: The 'asset' key is MANDATORY. Set \"asset\": \"<the exact asset_id from input_assets>\".\n"
            "- Output: A Cloudinary URL of the image with bounding boxes drawn on it, plus a scene caption.\n"
            "- Best for: Object detection, feature identification, scene description with visual artifacts.\n"
            "- Works with: Any image format (PNG, JPEG, GeoTIFF). Accepts Cloudinary URLs directly.\n\n"

            "### 3c. Change Detection (U-Net Binary Change Mask)\n"
            "- Capability Name: change_detection\n"
            "- What it does: Takes TWO temporally different satellite images and produces "
            "a binary change mask (red overlay) highlighting changed pixels.\n"
            "- Input: {before_asset: '<id_1>', after_asset: '<id_2>'}\n"
            "- Output: Binary mask PNG + pixel stats (changed_pixels, total_pixels, change_percentage).\n"
            "- CRITICAL CAVEAT: This is a custom handmade U-Net model prone to pixel bleed, "
            "edge artifacts, and margin overestimation. Treat pixel counts as a CEILING ESTIMATE. "
            "In your final report, explicitly contextualize this margin of error.\n\n"

            "### 3d. Area Calculation (Deterministic Math)\n"
            "- Capability Name: calculate_changed_area\n"
            "- What it does: Takes a change mask and computes precise area in km2 and m2.\n"
            "- Output: area_km2, area_m2, changed_pixels, total_pixels.\n"
            "- Always prefer this tool over making your own area estimates."
        )

        # Section 4: Available capabilities
        prompt_parts.append(
            f"\n\n## 4. AVAILABLE CAPABILITIES\n{cap_block}"
        )

        # Section 5: Decision schema
        prompt_parts.append(
            "\n\n## 5. STRICT DECISION JSON SCHEMA\n"
            "Return a strict JSON object with EXACTLY these fields:\n"
            "- 'action': One of CALL_CAPABILITY, PARALLEL, RETRY, REPLAN, REQUEST_INPUT, CONVERSATIONAL, FINAL\n"
            "- 'capability': Exact capability name (for CALL_CAPABILITY/RETRY), else null.\n"
            "- 'arguments_json': JSON-ENCODED STRING of arguments, else null.\n"
            "- 'reason': Dense, professional intelligence rationale (1-2 sentences).\n"
            "- 'parallel_capabilities_json': JSON-ENCODED STRING array (PARALLEL only), else null.\n"
            "- 'final_answer': For FINAL: exhaustive analytical briefing. For CONVERSATIONAL: "
            "your friendly chat response. Else null.\n"
            "- 'final_confidence': Float 0.0-1.0 (FINAL only), else null.\n"
            "- 'specialist_evaluations_json': JSON-ENCODED STRING mapping evidence_id to score (0.0-1.0), else null."
        )

        # Section 6: Visual verification
        prompt_parts.append(
            "\n\n## 6. CLOSED-LOOP VISUAL VERIFICATION\n"
            "You have direct native visual access to all attached imagery and generated "
            "artifacts (masks, radar generations, overlays).\n"
            "When a specialist returns an Observation:\n"
            "- Cross-reference its output against your own visual understanding.\n"
            "- If hallucinated or geometrically wrong: score 0.1-0.4, trigger RETRY/REPLAN.\n"
            "- If accurate: score 0.8-1.0."
        )

        # Section 7: Final briefing requirements
        prompt_parts.append(
            "\n\n## 7. FINAL BRIEFING REQUIREMENTS\n"
            "When issuing FINAL, your final_answer MUST be:\n"
            "- Deeply analytical -- not a summary. Provide strategic insight and conclusions.\n"
            "- Evidence-grounded -- cite observations, evidence IDs, and mathematical figures.\n"
            "- Quantitatively rigorous -- include area calculations, change percentages, confidence-adjusted estimates.\n"
            "- Visually informed -- describe what you see in attached masks and generated images.\n"
            "- Uncertainty-aware -- state limitations, known model biases, confidence intervals.\n"
            "- Structured -- use sections: Executive Summary, Scene Analysis, Change Assessment, "
            "Quantitative Metrics, Model Cross-Verification, Strategic Conclusions."
        )

        # Section 8: Execution directives
        prompt_parts.append(
            "\n\n## 8. EXECUTION DIRECTIVES\n"
            "- Zero Hallucination Tolerance: NEVER fabricate outputs, scores, or metadata.\n"
            "- Deterministic Math: Always route numerical calculations to deterministic tools.\n"
            "- PARALLEL IS MANDATORY for multi-task queries: When user asks for 2+ independent things "
            "(e.g. NDVI AND grounding, LULC AND caption), use ONE PARALLEL action -- NOT sequential steps.\n"
            "  PARALLEL example for NDVI+grounding: parallel_capabilities_json = "
            '[{\"capability\":\"terramind_generate\",\"arguments\":{\"asset\":\"<id>\",\"modality\":\"RGB\",\"output_modalities\":\"NDVI\",\"include_png\":true}},'  "
            '{\"capability\":\"ground_region\",\"arguments\":{\"asset\":\"<id>\"}}]'\n"
            "- Sequential ONLY when step B requires output from step A.\n"
            "- Modality Constraints: Never call optical-only capabilities on SAR data.\n"
            "- Asset References: Always reference the exact asset_id from input_assets."
        )

        return "".join(prompt_parts)


    # ------------------------------------------------------------------
    # User prompt + image attachment (with GeoTIFF conversion)
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_band_array(arr: Any) -> Any:
        """2%-98% percentile stretch to 8-bit, for non-uint8 (e.g. 16-bit
        GeoTIFF) imagery. Keeps only the first 3 bands for RGB display.

        NOTE: this duplicates a slice of app.geospatial.processing's
        percentile-stretch logic (used by the create_visual_preview
        capability). If/when that module's stretch function is exposed
        as an importable utility, replace this with a direct call to it
        so there is a single source of truth for the stretch parameters.
        """
        import numpy as np

        if arr.dtype != np.uint8:
            arr = arr.astype("float32")
            lo = float(np.percentile(arr, 2))
            hi = float(np.percentile(arr, 98))
            if hi <= lo:
                hi = lo + 1.0
            arr = ((arr - lo) / (hi - lo) * 255.0).clip(0, 255).astype("uint8")
        if arr.ndim == 3 and arr.shape[-1] > 3:
            arr = arr[..., :3]
        return arr

    @classmethod
    def _load_image_bytes_for_llm(cls, uri: str) -> tuple[bytes, str] | None:
        """Return (png_bytes, mime) for any supported asset, converting
        GeoTIFF/TIFF (and any non-8-bit imagery) to a normalized PNG.
        Returns None if the file can't be read or converted."""
        try:
            from PIL import Image
        except ImportError:
            logger.warning("Pillow not installed; cannot attach imagery to LLM calls.")
            return None

        lower = uri.lower()
        try:
            # Handle HTTP/Cloudinary URLs
            if uri.startswith("http"):
                import httpx as _httpx
                with _httpx.Client(timeout=30) as _client:
                    resp = _client.get(uri)
                    resp.raise_for_status()
                    raw = resp.content
                
                # Assume standard image formats for HTTP unless it looks like tiff
                if "tif" not in lower:
                    mime = "image/jpeg" if "jpg" in lower or "jpeg" in lower else "image/png"
                    return raw, mime
                else:
                    # It's a TIFF from URL, load it into PIL
                    import io
                    import numpy as np
                    img = Image.open(io.BytesIO(raw))
                    arr = np.array(img)
                    arr = cls._normalize_band_array(arr)
                    out_img = Image.fromarray(arr).convert("RGB")
                    buf = io.BytesIO()
                    out_img.save(buf, format="PNG")
                    return buf.getvalue(), "image/png"

            # Handle Local Files
            if lower.endswith((".png", ".jpg", ".jpeg")):
                with open(uri, "rb") as f:
                    raw = f.read()
                mime = "image/png" if lower.endswith(".png") else "image/jpeg"
                return raw, mime

            if lower.endswith((".tif", ".tiff")):
                try:
                    import numpy as np
                except ImportError:
                    logger.warning("numpy not installed; cannot normalize GeoTIFF for LLM vision.")
                    return None

                img = Image.open(uri)
                arr = np.array(img)
                arr = cls._normalize_band_array(arr)
                out_img = Image.fromarray(arr).convert("RGB")
                buf = io.BytesIO()
                out_img.save(buf, format="PNG")
                return buf.getvalue(), "image/png"

            # Unsupported extension
            return None

        except Exception as exc:
            logger.warning(
                "Failed to load/convert image %s for LLM vision: %s",
                uri, exc,
            )
            return None

    @classmethod
    async def _build_user_prompt(
        cls, context: dict[str, Any]
    ) -> list[dict[str, Any]] | str:
        """Construct the user message containing the current agent state
        and any images (including GeoTIFF assets, auto-converted)."""
        import base64
        import os

        text_content = json.dumps(context, default=str, indent=2)
        content_blocks: list[dict[str, Any]] = [{"type": "text", "text": text_content}]

        # Extract images from input assets
        image_uris = []
        for asset in context.get("input_assets", []):
            uri = asset.get("uri")
            if uri:
                if uri.startswith("http") or os.path.exists(uri):
                    image_uris.append(uri)

        # Extract images from observation artifacts
        for obs in context.get("observations", []):
            if "artifacts" in obs and obs["artifacts"]:
                for uri in obs["artifacts"]:
                    if uri and isinstance(uri, str):
                        if (uri.startswith("http") or os.path.exists(uri)) and uri not in image_uris:
                            image_uris.append(uri)

        for uri in image_uris:
            loaded = cls._load_image_bytes_for_llm(uri)
            if loaded is None:
                continue

            raw_bytes, mime = loaded
            b64 = base64.b64encode(raw_bytes).decode("utf-8")
            content_blocks.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "high"},
            })

        if len(content_blocks) == 1:
            return text_content
        return content_blocks