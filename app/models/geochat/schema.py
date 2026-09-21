"""GeoChat schemas.

Input/output contracts for the GeoChat vision-language model.
These schemas define what the adapter expects and what it normalizes
before producing an Observation.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class GeoChatRequest(BaseModel):
    """Internal request sent to the GeoChat client."""

    asset_uri: str = Field(..., description="URI/path of the input image asset")
    prompt: str = Field(
        default="Describe the major objects, land-cover characteristics, and spatial patterns visible in this satellite image.",
        description="The prompt to send to GeoChat",
    )
    asset_id: str = Field(default="", description="Asset ID for provenance tracking")


class GeoChatResponse(BaseModel):
    """Structured response from the GeoChat inference service."""

    text: str = Field(..., description="The textual response from GeoChat")
    model: str = Field(default="GeoChat", description="Model name")
    version: str = Field(default="", description="Model version or checkpoint")
    inference_time_seconds: float | None = Field(
        default=None, description="Model inference latency"
    )
