"""Capability definitions.

Each capability declares what it needs (inputs, modality, format, …)
so that the precondition-validation gate can reject invalid requests
before any specialist model is called.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Modality(str, Enum):
    OPTICAL = "optical"
    SAR = "sar"
    MULTISPECTRAL = "multispectral"
    ANY = "any"


class CapabilityDefinition(BaseModel):
    """Declarative spec for a single capability."""

    name: str
    description: str = ""
    required_asset_count: int = Field(default=1, ge=0)
    accepted_modalities: list[Modality] = Field(
        default_factory=lambda: [Modality.ANY]
    )
    accepted_formats: list[str] = Field(
        default_factory=lambda: ["geotiff", "png", "jpeg", "tif", "tiff"]
    )
    requires_temporal_pair: bool = False
    requires_spatial_overlap: bool = False
    requires_metadata: list[str] = Field(default_factory=list)
    output_type: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)


# ------------------------------------------------------------------
# Built-in definitions
# ------------------------------------------------------------------

BUILTIN_CAPABILITIES: dict[str, CapabilityDefinition] = {
    # --- Validation ---
    "validate_remote_sensing_input": CapabilityDefinition(
        name="validate_remote_sensing_input",
        description="Validate a single remote-sensing image (format, modality, metadata).",
        required_asset_count=1,
        output_type="validation",
    ),
    "validate_temporal_pair": CapabilityDefinition(
        name="validate_temporal_pair",
        description="Validate that two images form a valid temporal pair.",
        required_asset_count=2,
        requires_temporal_pair=True,
        requires_spatial_overlap=True,
        output_type="validation",
    ),
    "validate_spatial_alignment": CapabilityDefinition(
        name="validate_spatial_alignment",
        description="Check spatial alignment / co-registration of two images.",
        required_asset_count=2,
        requires_spatial_overlap=True,
        output_type="validation",
    ),

    # --- Retrieval ---
    "retrieve_satellite_imagery": CapabilityDefinition(
        name="retrieve_satellite_imagery",
        description="Search and retrieve satellite imagery for an AOI / time range.",
        required_asset_count=0,
        output_type="retrieval",
    ),

    # --- VLM / interpretation ---
    "answer_remote_sensing_vqa": CapabilityDefinition(
        name="answer_remote_sensing_vqa",
        description="Answer a natural-language question about a satellite image.",
        required_asset_count=1,
        accepted_modalities=[Modality.OPTICAL],
        output_type="vqa",
    ),
    "generate_caption": CapabilityDefinition(
        name="generate_caption",
        description="Generate a descriptive caption for a satellite image.",
        required_asset_count=1,
        accepted_modalities=[Modality.OPTICAL],
        output_type="caption",
    ),
    "ground_region": CapabilityDefinition(
        name="ground_region",
        description="Locate a described region or object in a satellite image.",
        required_asset_count=1,
        accepted_modalities=[Modality.OPTICAL],
        output_type="grounding",
    ),
    "interpret_scene": CapabilityDefinition(
        name="interpret_scene",
        description="Provide a high-level scene interpretation.",
        required_asset_count=1,
        accepted_modalities=[Modality.OPTICAL],
        output_type="scene_interpretation",
    ),

    # --- Change detection ---
    "detect_bitemporal_change": CapabilityDefinition(
        name="detect_bitemporal_change",
        description="Detect pixel-level change between two temporal images.",
        required_asset_count=2,
        accepted_modalities=[Modality.OPTICAL],
        requires_temporal_pair=True,
        requires_spatial_overlap=True,
        output_type="bitemporal_change",
    ),

    # --- Specialist analysis ---
    "analyze_multispectral_image": CapabilityDefinition(
        name="analyze_multispectral_image",
        description="Analyse a multispectral image (land cover, indices, etc.).",
        required_asset_count=1,
        accepted_modalities=[Modality.MULTISPECTRAL, Modality.OPTICAL],
        output_type="multispectral",
    ),
    "analyze_sar_image": CapabilityDefinition(
        name="analyze_sar_image",
        description="Analyse a SAR image (backscatter, structures, etc.).",
        required_asset_count=1,
        accepted_modalities=[Modality.SAR],
        output_type="sar",
    ),
    "perform_multimodal_analysis": CapabilityDefinition(
        name="perform_multimodal_analysis",
        description="Cross-modal analysis combining optical and SAR. Can perform unsupervised segmentation. Provide 'num_classes' in arguments if the user requests a specific number of clusters/classes.",
        required_asset_count=1,
        accepted_modalities=[Modality.ANY],
        output_type="multimodal",
    ),

    # --- Geospatial tools ---
    "create_visual_preview": CapabilityDefinition(
        name="create_visual_preview",
        description="Deterministically generate an 8-bit visual preview of a raster using percentile stretching. For visualization only. NOT for ML preprocessing.",
        required_asset_count=1,
        output_type="image_processing",
    ),
    "calculate_changed_area": CapabilityDefinition(
        name="calculate_changed_area",
        description="Compute the changed area from a change mask.",
        required_asset_count=0,
        output_type="area_calculation",
    ),
    "generate_change_map": CapabilityDefinition(
        name="generate_change_map",
        description="Produce a visual change map from detection results.",
        required_asset_count=0,
        output_type="change_map",
    ),
    "generate_timelapse": CapabilityDefinition(
        name="generate_timelapse",
        description="Create a timelapse from a temporal image sequence.",
        required_asset_count=0,
        output_type="timelapse",
    ),
}
