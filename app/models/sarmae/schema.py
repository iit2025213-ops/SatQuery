"""SARMAE schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SARMAERequest(BaseModel):
    """Internal request for SARMAE SAR analysis."""

    asset_uri: str = Field(..., description="URI of the SAR image")
    asset_id: str = Field(default="", description="Asset ID for provenance")


class SARMAEResponse(BaseModel):
    """Structured response from the SARMAE inference service."""

    result: dict = Field(default_factory=dict, description="Analysis results")
    model: str = Field(default="SARMAE", description="Model name")
    version: str = Field(default="", description="Model version")
    inference_time_seconds: float | None = Field(default=None)
