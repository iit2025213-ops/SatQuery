"""Request / response schemas for the public API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ------------------------------------------------------------------
# Request
# ------------------------------------------------------------------

class AssetInput(BaseModel):
    asset_id: str
    uri: str = ""
    modality: str = ""
    format: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalyzeRequest(BaseModel):
    """POST /api/v1/analyze body."""
    query: str
    assets: list[AssetInput] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ------------------------------------------------------------------
# Response
# ------------------------------------------------------------------

class EvidenceSummary(BaseModel):
    evidence_id: str
    capability: str
    type: str
    status: str
    confidence: float | None = None


class JobResult(BaseModel):
    """Final result embedded in a job response."""
    answer: str = ""
    confidence: float = 0.0
    status: str = "pending"
    evidence: list[EvidenceSummary] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    verification: dict[str, Any] | None = None
    trace: list[dict[str, Any]] = Field(default_factory=list)
    step_count: int = 0
    replans: int = 0


class AnalyzeResponse(BaseModel):
    """POST /api/v1/analyze response."""
    job_id: str
    status: str = "accepted"


class JobStatusResponse(BaseModel):
    """GET /api/v1/jobs/{job_id} response."""
    job_id: str
    status: str
    result: JobResult | None = None


class JobReportResponse(BaseModel):
    """GET /api/v1/jobs/{job_id}/report response."""
    job_id: str
    report_markdown: str
