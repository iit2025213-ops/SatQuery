"""OpenAI LLM provider — production implementation.

The ``OpenAIProvider`` converts the agent context into structured
OpenAI chat-completion requests and parses the response back into
the canonical ``Decision`` schema.  It handles:

- structured JSON output generation
- response validation
- API errors (timeout, rate-limit, network)
- malformed responses (with retry)
- latency recording
- provider metadata

The provider NEVER exposes hidden chain-of-thought.

The API key is loaded from the environment and is **never** hardcoded
or committed.
"""

from __future__ import annotations

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
# Decision JSON schema for structured output
# ------------------------------------------------------------------

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
                "FINAL",
            ],
        },
        "capability": {"type": "string"},
        "arguments": {"type": "object"},
        "reason": {"type": "string"},
        "parallel_capabilities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "capability": {"type": "string"},
                    "arguments": {"type": "object"},
                },
                "required": ["capability"],
                "additionalProperties": False,
            },
        },
        "final_answer": {"type": "string"},
        "final_confidence": {"type": ["number", "null"]},
        "specialist_evaluations": {
            "type": "object",
            "additionalProperties": {"type": "number"}
        },
    },
    "required": ["action"],
    "additionalProperties": False,
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
        Model identifier (e.g. ``gpt-4o``).
    base_url:
        Custom OpenAI-compatible endpoint.  Empty string uses the
        official endpoint.
    temperature:
        Sampling temperature for decision generation.
    max_retries:
        Maximum number of retries on transient API errors.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "",
        base_url: str = "",
        temperature: float = 0.1,
        max_retries: int = 2,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url or None
        self._temperature = temperature
        self._max_retries = max_retries
        self._client: Any = None

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
        user_prompt = self._build_user_prompt(context)

        raw_json = await self._call_api(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            purpose="decide",
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
    # API call with retry
    # ------------------------------------------------------------------

    async def _call_api(
        self,
        *,
        system_prompt: str,
        user_prompt: str | list[dict[str, Any]],
        purpose: str,
        json_mode: bool = True,
    ) -> str:
        """Call the OpenAI API with retry on transient errors.

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
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}

                response = await self._client.chat.completions.create(**kwargs)
                elapsed = time.monotonic() - t0

                content = response.choices[0].message.content or ""
                logger.info(
                    "OpenAI %s response: model=%s attempt=%d/%d "
                    "latency=%.2fs tokens=%s",
                    purpose,
                    self._model,
                    attempt,
                    attempts,
                    elapsed,
                    getattr(response.usage, "total_tokens", "?"),
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
                # Brief back-off before retry
                import asyncio
                await asyncio.sleep(min(2 ** attempt, 8))
                continue

            except APIStatusError as exc:
                elapsed = time.monotonic() - t0
                logger.error(
                    "OpenAI API error (attempt %d/%d, %.2fs): status=%s %s",
                    attempt, attempts, elapsed, exc.status_code, exc,
                )
                # Non-retryable server errors
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
        # 1. Parse JSON
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

        # 2. Normalize common LLM quirks
        data = self._normalize_response(data)

        # 3. Validate against Decision schema
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

        - Lowered action → uppercased
        - ``tool`` / ``tool_name`` → ``capability``
        - ``rationale`` / ``reasoning`` → ``reason``
        - ``answer`` → ``final_answer``
        - ``confidence`` at top level → ``final_confidence``
        """
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

        return f"""You are the SatQuery AI reasoning engine — a continuous controller for remote-sensing analysis.

## Your Role
You are called REPEATEDLY after every tool/model execution. Each time, you receive the CURRENT state (including all observations collected so far) and must decide the SINGLE NEXT action.

You do NOT create a full plan upfront. You decide ONE step at a time based on current evidence.

## Available Capabilities
{cap_block}

## Decision Format
Return a JSON object with these fields:
- "action": One of CALL_CAPABILITY, PARALLEL, RETRY, REPLAN, REQUEST_INPUT, FINAL
- "capability": The capability name (required for CALL_CAPABILITY and RETRY)
- "arguments": Object with capability arguments (e.g. {{"asset": "asset_001"}})
- "reason": A SHORT observable rationale (1-2 sentences, NOT internal reasoning)
- "parallel_capabilities": Array of {{"capability": "...", "arguments": {{...}}}} (for PARALLEL only)
- "final_answer": Your synthesized answer (required for FINAL)
- "final_confidence": Confidence 0.0-1.0 (for FINAL)

## Rules
1. Select the MINIMUM capabilities needed — do not invoke every available model.
2. Always validate input before running specialist analysis.
3. Use observations to decide what to do next — previous results guide your choices.
4. If a capability failed, decide whether to RETRY, REPLAN, or try an alternative.
5. If evidence is sufficient, use FINAL to produce your answer.
6. NEVER fabricate tool outputs or claim a tool was executed when it was not.
7. NEVER assume satellite metadata that was not provided or observed.
8. For numerical/spatial calculations, prefer deterministic geospatial tools.
9. The "reason" field must be a short observable rationale, NOT chain-of-thought.
10. Respect modality constraints: do not call optical-only capabilities on SAR data.
11. When using CALL_CAPABILITY, reference asset IDs from the input_assets.
12. For FINAL, provide a complete evidence-grounded answer in "final_answer".
13. IMPORTANT: You have direct visual access to the satellite imagery. When a specialist model returns an observation, you MUST cross-reference their textual output against your own visual understanding of the image.
14. If the specialist's output is hallucinated, incorrect, or missing obvious features, assign it a low score (e.g. 0.1) in `specialist_evaluations` mapping their `evidence_id` to your score, and use RETRY or REPLAN.
15. If the specialist output is correct, assign it a high score (e.g. 0.9) in `specialist_evaluations`."""

    @staticmethod
    def _build_user_prompt(context: dict[str, Any]) -> list[dict[str, Any]] | str:
        """Construct the user message containing the current agent state and any images."""
        import base64
        import os
        
        text_content = json.dumps(context, default=str, indent=2)
        content_blocks = [{"type": "text", "text": text_content}]
        
        # Check for input assets to attach as images
        for asset in context.get("input_assets", []):
            uri = asset.get("uri")
            if uri and os.path.exists(uri) and uri.lower().endswith(('.png', '.jpg', '.jpeg')):
                try:
                    with open(uri, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")
                    mime = "image/png" if uri.lower().endswith(".png") else "image/jpeg"
                    content_blocks.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "high"}
                    })
                except Exception as e:
                    logger.warning("Failed to load image %s for LLM: %s", uri, e)
                    
        if len(content_blocks) == 1:
            return text_content
        return content_blocks
