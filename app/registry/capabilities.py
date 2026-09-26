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
    "answer_change_vqa": CapabilityDefinition(
        name="answer_change_vqa",
        description=(
            "Answer a natural-language question about what changed between two "
            "temporal satellite images (GeoChat CDVQA: e.g. 'what changed here?', "
            "'did the building expand?')."
        ),
        required_asset_count=2,
        accepted_modalities=[Modality.OPTICAL],
        requires_temporal_pair=True,
        requires_spatial_overlap=True,
        output_type="change_vqa",
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
    "terramind_embedding": CapabilityDefinition(
        name="terramind_embedding",
        description="Extract feature embeddings from the TerraMind Large backbone. Provide 'merge_method' (mean, max, concat, dict, none) and 'modality' (e.g. S2L2A, S2L1C, S1GRD, S1RTC, RGB, DEM) in arguments.",
        required_asset_count=1,
        accepted_modalities=[Modality.ANY],
        output_type="multimodal",
    ),
    "terramind_tim": CapabilityDefinition(
        name="terramind_tim",
        description="Run TerraMind Thinking-in-Modalities (TiM) inference. Provide 'tim_modalities' (e.g. LULC, NDVI) and 'modality' in arguments.",
        required_asset_count=1,
        accepted_modalities=[Modality.ANY],
        output_type="multimodal",
    ),
    "terramind_generate": CapabilityDefinition(
        name="terramind_generate",
        description="Generate arbitrary modalities from input using TerraMind. Provide 'output_modalities' (e.g. S1GRD, LULC, DEM, NDVI), 'modality' of input, and 'timesteps' in arguments.",
        required_asset_count=1,
        accepted_modalities=[Modality.ANY],
        output_type="multimodal",
    ),
    "terramind_coordinate_tokenizer": CapabilityDefinition(
        name="terramind_coordinate_tokenizer",
        description="Encode or decode lon/lat coordinates using the TerraMind spatial tokenizer.",
        required_asset_count=0,
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
        description="Compute the exact geographical area (in square meters and km2) of the changed pixels. Provide the 'change_mask' argument with the URI of the mask returned by detect_bitemporal_change.",
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