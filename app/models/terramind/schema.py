"""TerraMind schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional


class AssetInput(BaseModel):
    uri: str = Field(..., description="Path or URL to GeoTIFF file")
    modality: str = Field(default="S2L2A", description="Modality (S2L2A, S1GRD, RGB, etc.)")


class TerraMindRequest(BaseModel):
    """Internal request for TerraMind multimodal analysis."""

    assets: List[AssetInput] = Field(..., description="List of input assets")
    task: str = Field(default="segmentation", description="Task (segmentation, features)")
    num_classes: int = Field(default=3, description="Number of K-Means clusters")
    clustering_method: str = Field(default="pca_kmeans", description="Clustering method")


class TerraMindResponse(BaseModel):
    """Structured response from the TerraMind inference service."""

    result: dict = Field(default_factory=dict, description="Segmentations or features")
    model: str = Field(default="terramind_v1_large", description="Model variant")
    version: str = Field(default="1.0", description="Model version")
    inference_time_seconds: Optional[float] = Field(default=None)
    confidence: Optional[float] = Field(default=None)
