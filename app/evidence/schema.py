"""Observation / evidence schema.

Every model or tool result is normalised into an ``Observation`` before
it enters the agent state.  This guarantees a uniform interface for the
LLM context builder, the critic, and the confidence engine.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ------------------------------------------------------------------
# Enums
# ------------------------------------------------------------------

class ObservationStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    TIMEOUT = "timeout"
    INVALID_INPUT = "invalid_input"


class EvidenceType(str, Enum):
    VALIDATION = "validation"
    VQA = "vqa"
    CAPTION = "caption"
    GROUNDING = "grounding"
    SCENE_INTERPRETATION = "scene_interpretation"
    BITEMPORAL_CHANGE = "bitemporal_change"
    MULTISPECTRAL = "multispectral"
    SAR = "sar"
    MULTIMODAL = "multimodal"
    AREA_CALCULATION = "area_calculation"
    CHANGE_MAP = "change_map"
    TIMELAPSE = "timelapse"
    RETRIEVAL = "retrieval"
    GEOSPATIAL = "geospatial"
    IMAGE_PROCESSING = "image_processing"
    ERROR = "error"


# ------------------------------------------------------------------
# Sub-models
# ------------------------------------------------------------------

class EvidenceSource(BaseModel):
    """Provenance of a single observation."""
    capability: str
    model: str = ""
    version: str = ""
    backend: str = "mock"


class SpatialMetadata(BaseModel):
    """Spatial context attached to an observation."""
    bbox: list[float] = Field(default_factory=list)
    crs: str = ""
    resolution_m: float | None = None


class TemporalMetadata(BaseModel):
    """Temporal context attached to an observation."""
    timestamp: str = ""
    before: str = ""
    after: str = ""


# ------------------------------------------------------------------
# Core observation
# ------------------------------------------------------------------

class Observation(BaseModel):
    """Standardised output of any capability execution.

    Every model adapter and deterministic tool **must** produce an
    ``Observation`` so that the agent loop has a uniform contract.
    """

    evidence_id: str = Field(default_factory=lambda: f"ev_{uuid.uuid4().hex[:8]}")
    source: EvidenceSource
    type: EvidenceType
    status: ObservationStatus
    result: dict[str, Any] = Field(default_factory=dict)
    spatial: SpatialMetadata = Field(default_factory=SpatialMetadata)
    temporal: TemporalMetadata = Field(default_factory=TemporalMetadata)
    artifacts: list[str] = Field(
        default_factory=list, description="Artifact IDs produced by this observation"
    )
    confidence: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Model-reported confidence"
    )
    error_message: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
