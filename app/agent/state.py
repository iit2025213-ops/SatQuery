"""Agent state.

``AgentState`` is the single mutable record that persists across the
entire agent loop.  It accumulates observations, decisions, artifacts,
and metadata.  Large binary data is **never** stored inline — only
IDs / references are kept.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.evidence.schema import Observation


# ------------------------------------------------------------------
# Supporting types
# ------------------------------------------------------------------

class AssetReference(BaseModel):
    """Lightweight reference to an input asset (image, GeoTIFF, …)."""

    asset_id: str
    uri: str = ""
    modality: str = ""  # "optical", "sar", "multispectral", …
    format: str = ""    # "geotiff", "png", "jpeg", …
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskRecord(BaseModel):
    """Minimal record of an executed or failed task."""

    task_id: str
    capability: str
    status: str  # "success" | "failure" | "timeout" | …
    evidence_id: str = ""
    error: str = ""
    retries: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ------------------------------------------------------------------
# Agent state
# ------------------------------------------------------------------

class AgentState(BaseModel):
    """Complete state of a single agent run.

    The controller reads and writes this after every loop iteration.
    """

    # --- Request ---
    request: str = ""
    input_assets: list[AssetReference] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    current_goal: str = ""

    # --- Evidence ---
    observations: list[Observation] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
    artifact_ids: list[str] = Field(
        default_factory=list,
        description="Artifact IDs (actual artifacts live in ArtifactManager)",
    )

    # --- Task tracking ---
    executed_tasks: list[TaskRecord] = Field(default_factory=list)
    failed_tasks: list[TaskRecord] = Field(default_factory=list)

    # --- Decision tracking ---
    current_decision: dict[str, Any] | None = None
    decision_history: list[dict[str, Any]] = Field(default_factory=list)

    # --- Replanning / verification ---
    replans: int = 0
    verification_status: str = ""  # "" | "pending" | "passed" | "failed"
    confidence: float | None = None

    # --- Result ---
    final_result: dict[str, Any] | None = None
    step_count: int = 0

    # ---- helpers ----

    def add_observation(self, obs: Observation) -> None:
        """Append an observation and index its evidence_id."""
        self.observations.append(obs)
        self.evidence[obs.evidence_id] = obs.model_dump(
            exclude={"timestamp"}, mode="json"
        )
        if obs.artifacts:
            for artifact in obs.artifacts:
                if artifact not in self.artifact_ids:
                    self.artifact_ids.append(artifact)

    def record_task(self, record: TaskRecord) -> None:
        if record.status == "success":
            self.executed_tasks.append(record)
        else:
            self.failed_tasks.append(record)

    def last_observation(self) -> Observation | None:
        return self.observations[-1] if self.observations else None

    def observations_by_capability(self, capability: str) -> list[Observation]:
        return [
            o for o in self.observations if o.source.capability == capability
        ]

    def has_evidence_for(self, capability: str) -> bool:
        return any(
            o.source.capability == capability
            for o in self.observations
            if o.status.value == "success"
        )
