"""GeoChat schemas.

Input/output contracts for the GeoChat vision-language model.
These schemas define what the adapter expects and what it normalizes
before producing an Observation.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class GeoChatRequest(BaseModel):
    """Internal request sent to the GeoChat client."""

    asset_uri: str = Field(default="", description="URI/path of the primary input image asset")
    asset_uris: list[str] = Field(
        default_factory=list,
        description="One or two image URIs. Two enables CDVQA change-VQA. Overrides asset_uri if set.",
    )
    prompt: str = Field(
        default="Describe the major objects, land-cover characteristics, and spatial patterns visible in this satellite image.",
        description="The prompt to send to GeoChat",
    )
    asset_id: str = Field(default="", description="Asset ID for provenance tracking")
    max_new_tokens: int = Field(default=256, ge=1, le=1024)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)


class GeoChatResponse(BaseModel):
    """Structured response from the GeoChat inference service."""

    text: str = Field(..., description="The textual response from GeoChat")
    model: str = Field(default="GeoChat", description="Model name")
    version: str = Field(default="", description="Model version or checkpoint")
    inference_time_seconds: float | None = Field(
        default=None, description="Model inference latency"
    )
    is_cdvqa: bool = Field(default=False, description="Whether this was a two-image CDVQA change-VQA call")