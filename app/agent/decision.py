"""Structured decision schema.

The LLM **must** return a ``Decision`` that conforms to this schema.
Unknown actions, missing required fields, and invalid references are
rejected before anything is executed.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


# ------------------------------------------------------------------
# Action enum
# ------------------------------------------------------------------

class ActionType(str, Enum):
    CALL_CAPABILITY = "CALL_CAPABILITY"
    PARALLEL = "PARALLEL"
    RETRY = "RETRY"
    REPLAN = "REPLAN"
    REQUEST_INPUT = "REQUEST_INPUT"
    CONVERSATIONAL = "CONVERSATIONAL"
    FINAL = "FINAL"


# ------------------------------------------------------------------
# Decision
# ------------------------------------------------------------------

class Decision(BaseModel):
    """A single structured decision produced by the LLM."""

    action: ActionType
    capability: str | None = Field(
        default="",
        description="Capability name — required for CALL_CAPABILITY / RETRY",
    )
    arguments: dict[str, Any] = Field(default_factory=dict)
    reason: str = Field(
        default="",
        description="Short observable rationale (NOT chain-of-thought)",
    )
    parallel_capabilities: list[dict[str, Any]] = Field(
        default_factory=list,
        description="For PARALLEL action — list of {capability, arguments}",
    )
    final_answer: str = Field(
        default="",
        description="Synthesised answer when action is FINAL",
    )
    final_confidence: float | None = Field(
        default=None, ge=0.0, le=1.0,
    )
    specialist_evaluations: dict[str, float] = Field(
        default_factory=dict,
        description="Mapping of evidence_id to a confidence score (0.0-1.0) assigned by the LLM.",
    )

    @model_validator(mode="after")
    def _validate_action_fields(self) -> "Decision":
        if self.action == ActionType.CALL_CAPABILITY and not self.capability:
            raise ValueError("CALL_CAPABILITY requires a non-empty 'capability'")
        if self.action == ActionType.RETRY and not self.capability:
            raise ValueError("RETRY requires a non-empty 'capability'")
        if self.action == ActionType.PARALLEL and not self.parallel_capabilities:
            raise ValueError("PARALLEL requires at least one entry in 'parallel_capabilities'")
        if self.action == ActionType.FINAL and not self.final_answer:
            raise ValueError("FINAL requires a non-empty 'final_answer'")
        return self


# ------------------------------------------------------------------
# Validation helpers
# ------------------------------------------------------------------

class DecisionValidationError(Exception):
    """Raised when a decision fails schema or semantic validation."""


def validate_decision(
    decision: Decision,
    known_capabilities: set[str],
    available_asset_ids: set[str],
) -> None:
    """Raise ``DecisionValidationError`` if the decision is invalid.

    Checks performed:
    - capability exists in registry
    - referenced assets exist in state
    - parallel entries are individually valid
    """
    if decision.action in (ActionType.CALL_CAPABILITY, ActionType.RETRY):
        if decision.capability not in known_capabilities:
            raise DecisionValidationError(
                f"Unknown capability: {decision.capability!r}"
            )
        _check_asset_refs(decision.arguments, available_asset_ids)

    if decision.action == ActionType.PARALLEL:
        for entry in decision.parallel_capabilities:
            cap = entry.get("capability", "")
            if cap not in known_capabilities:
                raise DecisionValidationError(
                    f"Unknown capability in parallel list: {cap!r}"
                )
            _check_asset_refs(entry.get("arguments", {}), available_asset_ids)


def _check_asset_refs(args: dict[str, Any], available: set[str]) -> None:
    """Ensure any argument ending in ``_asset`` references a known asset."""
    for key, value in args.items():
        if key.endswith("_asset") and isinstance(value, str) and value:
            if value not in available:
                raise DecisionValidationError(
                    f"Referenced asset {value!r} (argument {key!r}) not found"
                )
