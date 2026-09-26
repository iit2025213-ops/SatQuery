"""Change_detection schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChangeDetectionRequest(BaseModel):
    """Internal request for Change_detection bi-temporal change detection."""

    before_asset_uri: str = Field(..., description="URI of the 'before' image")
    after_asset_uri: str = Field(..., description="URI of the 'after' image")
    before_asset_id: str = Field(default="", description="Before asset ID for provenance")
    after_asset_id: str = Field(default="", description="After asset ID for provenance")


class ChangeDetectionResponse(BaseModel):
    """Structured response from the Change_detection inference service."""

    changed_pixels: int = Field(..., description="Number of changed pixels")
    total_pixels: int = Field(..., description="Total pixels in the image")
    changed_percent: float = Field(default=0.0, description="Share of the image marked as changed (0-100)")
    n_regions: int = Field(default=0, description="Number of separate changed regions in the mask")
    verdict: str = Field(
        default="",
        description="'ok', or 'check_by_eye' when the model's scales disagree (a consistency flag, not accuracy)",
    )
    agreement_per_scale: dict[str, float] = Field(
        default_factory=dict, description="Overlap (IoU 0-1) between each scale's mask and the final mask"
    )
    change_mask_uri: str = Field(default="", description="URI to the output change mask (PNG, 255 = changed)")
    change_overlay_uri: str = Field(default="", description="URI to the 'after' image with changes outlined in red")
    mask_width: int = Field(default=0, description="Width in pixels of the mask / overlay images")
    mask_height: int = Field(default=0, description="Height in pixels of the mask / overlay images")
    model: str = Field(default="Change_detection", description="Model name")
    version: str = Field(default="", description="Model version")
    inference_time_seconds: float | None = Field(default=None)
