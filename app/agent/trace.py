"""Execution trace recorder.

The trace is the *observable* record of what the agent did.  It records
steps, capabilities, latency and short rationale.  It **never** exposes
hidden chain-of-thought.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class TraceStep(BaseModel):
    """One step in the execution trace."""

    step_number: int
    action: str
    capability: str = ""
    model: str = ""
    backend: str = "mock"
    input_references: list[str] = Field(default_factory=list)
    output_references: list[str] = Field(default_factory=list)
    status: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    latency_s: float = 0.0
    confidence: float | None = None
    rationale: str = ""


class TraceRecorder:
    """Accumulates ``TraceStep`` entries for a single agent run."""

    def __init__(self) -> None:
        self.steps: list[TraceStep] = []
        self._timer_start: float | None = None

    def start_timer(self) -> None:
        self._timer_start = time.monotonic()

    def stop_timer(self) -> float:
        if self._timer_start is None:
            return 0.0
        elapsed = time.monotonic() - self._timer_start
        self._timer_start = None
        return round(elapsed, 4)

    def record(
        self,
        action: str,
        *,
        capability: str = "",
        model: str = "",
        backend: str = "mock",
        input_refs: list[str] | None = None,
        output_refs: list[str] | None = None,
        status: str = "",
        latency_s: float = 0.0,
        confidence: float | None = None,
        rationale: str = "",
    ) -> TraceStep:
        step = TraceStep(
            step_number=len(self.steps) + 1,
            action=action,
            capability=capability,
            model=model,
            backend=backend,
            input_references=input_refs or [],
            output_references=output_refs or [],
            status=status,
            latency_s=latency_s,
            confidence=confidence,
            rationale=rationale,
        )
        self.steps.append(step)
        return step

    def to_dicts(self) -> list[dict[str, Any]]:
        return [s.model_dump(mode="json") for s in self.steps]
