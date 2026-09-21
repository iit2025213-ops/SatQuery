"""Prithvi schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PrithviRequest(BaseModel):
    """Internal request for Prithvi multispectral analysis."""

    asset_uri: str = Field(..., description="URI of the multispectral image")
    asset_id: str = Field(default="", description="Asset ID for provenance")
    task: str = Field(default="land_cover", description="Analysis task (land_cover, segmentation, etc.)")


class PrithviResponse(BaseModel):
    """Structured response from the Prithvi inference service."""

    result: dict = Field(default_factory=dict, description="Analysis results (e.g. land cover fractions)")
    model: str = Field(default="Prithvi", description="Model name")
    version: str = Field(default="", description="Model version")
    inference_time_seconds: float | None = Field(default=None)
