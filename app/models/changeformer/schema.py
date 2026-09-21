"""ChangeFormer schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChangeFormerRequest(BaseModel):
    """Internal request for ChangeFormer bi-temporal change detection."""

    before_asset_uri: str = Field(..., description="URI of the 'before' image")
    after_asset_uri: str = Field(..., description="URI of the 'after' image")
    before_asset_id: str = Field(default="", description="Before asset ID for provenance")
    after_asset_id: str = Field(default="", description="After asset ID for provenance")


class ChangeFormerResponse(BaseModel):
    """Structured response from the ChangeFormer inference service."""

    changed_pixels: int = Field(..., description="Number of changed pixels")
    total_pixels: int = Field(..., description="Total pixels in the image")
    change_mask_uri: str = Field(default="", description="URI to the output change mask")
    model: str = Field(default="ChangeFormer", description="Model name")
    version: str = Field(default="", description="Model version")
    inference_time_seconds: float | None = Field(default=None)
