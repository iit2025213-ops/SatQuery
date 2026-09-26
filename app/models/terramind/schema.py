"""TerraMind schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional


class AssetInput(BaseModel):
    uri: str = Field(..., description="Path or URL to GeoTIFF file")
    modality: str = Field(default="S2L2A", description="Modality (S2L2A, S1GRD, RGB, etc.)")
