"""Artifact schema and manager.

Artifacts are the persistent outputs of capability executions — GeoTIFFs,
masks, PNGs, JSON statistics, etc.  They are referenced by ID inside the
agent state and can become inputs to downstream capabilities.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ------------------------------------------------------------------
# Types
# ------------------------------------------------------------------

class ArtifactType(str, Enum):
    GEOTIFF = "geotiff"
    PNG = "png"
    JPEG = "jpeg"
    MASK = "mask"
    POLYGON = "polygon"
    BBOX = "bbox"
    EMBEDDING = "embedding"
    CAPTION = "caption"
    JSON_STATS = "json_stats"
    CHANGE_MAP = "change_map"
    TIMELAPSE_FRAME = "timelapse_frame"
    OTHER = "other"


# ------------------------------------------------------------------
# Schema
# ------------------------------------------------------------------

class Artifact(BaseModel):
    """A single artifact produced or consumed during an agent run."""

    artifact_id: str = Field(
        default_factory=lambda: f"art_{uuid.uuid4().hex[:8]}"
    )
    type: ArtifactType
    uri: str = Field(
        default="", description="File path, URL, or object-store key"
    )
    source_task: str = Field(
        default="", description="Evidence ID or capability name that produced this"
    )
    metadata: dict[str, Any] = Field(default_factory=dict)
    spatial_metadata: dict[str, Any] = Field(default_factory=dict)
    temporal_metadata: dict[str, Any] = Field(default_factory=dict)


# ------------------------------------------------------------------
# Manager
# ------------------------------------------------------------------

class ArtifactManager:
    """In-memory registry of artifacts for a single agent run."""

    def __init__(self) -> None:
        self._store: dict[str, Artifact] = {}

    def register(self, artifact: Artifact) -> str:
        """Store an artifact and return its ID."""
        self._store[artifact.artifact_id] = artifact
        return artifact.artifact_id

    def get(self, artifact_id: str) -> Artifact | None:
        return self._store.get(artifact_id)

    def exists(self, artifact_id: str) -> bool:
        return artifact_id in self._store

    def list_ids(self) -> list[str]:
        return list(self._store.keys())

    def get_by_source(self, source_task: str) -> list[Artifact]:
        return [a for a in self._store.values() if a.source_task == source_task]

    def validate_dependency(self, artifact_id: str) -> bool:
        """Return True if the artifact exists and is available."""
        return self.exists(artifact_id)
