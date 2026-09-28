"""Capability registry.

Maps capability names to their definitions **and** adapter factories.
The executor never instantiates adapters directly — it asks the
registry.
"""

from __future__ import annotations

import logging
from typing import Callable

from app.models.base import BaseModelAdapter
from app.registry.capabilities import (
    BUILTIN_CAPABILITIES,
    CapabilityDefinition,
)

logger = logging.getLogger(__name__)

# Type alias for adapter factory: () -> BaseModelAdapter
AdapterFactory = Callable[[], BaseModelAdapter]


class CapabilityRegistry:
    """Central registry of capabilities and their adapters."""

    def __init__(self) -> None:
        self._definitions: dict[str, CapabilityDefinition] = {}
        self._adapters: dict[str, AdapterFactory] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        definition: CapabilityDefinition,
        adapter_factory: AdapterFactory,
    ) -> None:
        self._definitions[definition.name] = definition
        self._adapters[definition.name] = adapter_factory
        logger.debug("Registered capability: %s", definition.name)

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def resolve(
        self, capability_name: str
    ) -> tuple[CapabilityDefinition, BaseModelAdapter]:
        """Return (definition, adapter_instance) or raise ``KeyError``."""
        if capability_name not in self._definitions:
            raise KeyError(f"Unknown capability: {capability_name!r}")
        defn = self._definitions[capability_name]
        adapter = self._adapters[capability_name]()
        return defn, adapter

    def has(self, capability_name: str) -> bool:
        return capability_name in self._definitions

    def list_capabilities(self) -> list[str]:
        return list(self._definitions.keys())

    def get_definition(self, capability_name: str) -> CapabilityDefinition:
        return self._definitions[capability_name]


# ------------------------------------------------------------------
# Default registry factory
# ------------------------------------------------------------------

def build_default_registry() -> CapabilityRegistry:
    """Build the production registry.

    Active specialist models (4 total):
      1. GeoChat          — VQA, scene interpretation, change-VQA
      2. GPT-4 Vision     — Grounding (bounding boxes) + captioning
      3. Change Detection — Bi-temporal pixel-level change mask (U-Net)
      4. TerraMind        — Foundation model: NDVI, LULC, SAR, DEM,
                            embeddings, coordinate tokenization,
                            SAR analysis and multispectral analysis.

    Prithvi and SARMAE have been retired. All their use-cases are
    covered by TerraMind's cross-modal generation capabilities.
    """
    from app.models.geochat.adapter import GeoChatAdapter
    from app.models.change_detection.adapter import ChangeDetectionAdapter
    from app.models.terramind.adapter import TerraMindAdapter
    from app.models.gpt_vision_adapter import GPTVisionAdapter
    from app.geospatial.validation import ValidationAdapter
    from app.geospatial.processing import VisualPreviewAdapter
    from app.tools.area import AreaCalculationAdapter

    registry = CapabilityRegistry()

    # ------------------------------------------------------------------
    # Validation (lightweight, no specialist model)
    # ------------------------------------------------------------------
    for cap_name in (
        "validate_remote_sensing_input",
        "validate_temporal_pair",
        "validate_spatial_alignment",
    ):
        registry.register(BUILTIN_CAPABILITIES[cap_name], ValidationAdapter)

    # Retrieval (stub)
    registry.register(
        BUILTIN_CAPABILITIES["retrieve_satellite_imagery"], ValidationAdapter
    )

    # ------------------------------------------------------------------
    # GeoChat — VQA + scene interpretation + change-VQA
    # ------------------------------------------------------------------
    for cap_name in (
        "answer_remote_sensing_vqa",
        "interpret_scene",
        "answer_change_vqa",
    ):
        registry.register(BUILTIN_CAPABILITIES[cap_name], GeoChatAdapter)

    # ------------------------------------------------------------------
    # GPT-4 Vision — Grounding (bounding boxes) + captioning
    # ------------------------------------------------------------------
    for cap_name in (
        "ground_region",
        "generate_caption",
    ):
        registry.register(BUILTIN_CAPABILITIES[cap_name], GPTVisionAdapter)

    # ------------------------------------------------------------------
    # Change Detection — Bi-temporal U-Net pixel-level change mask
    # ------------------------------------------------------------------
    registry.register(
        BUILTIN_CAPABILITIES["detect_bitemporal_change"], ChangeDetectionAdapter
    )

    # ------------------------------------------------------------------
    # TerraMind — Foundation model for ALL spectral / cross-modal work.
    # Covers: NDVI, LULC, SAR synthesis (S1GRD), DEM, multispectral
    # analysis, embeddings, and coordinate tokenisation.
    # SAR queries (previously SARMAE) and multispectral queries
    # (previously Prithvi) are now fully handled by TerraMind.
    # ------------------------------------------------------------------
    for cap_name in (
        "terramind_embedding",
        "terramind_tim",
        "terramind_generate",
        "terramind_coordinate_tokenizer",
        "analyze_sar_image",           # was SARMAE — now TerraMind
        "analyze_multispectral_image",  # was Prithvi — now TerraMind
    ):
        registry.register(BUILTIN_CAPABILITIES[cap_name], TerraMindAdapter)

    # ------------------------------------------------------------------
    # Geospatial deterministic tools
    # ------------------------------------------------------------------
    registry.register(
        BUILTIN_CAPABILITIES["create_visual_preview"], VisualPreviewAdapter
    )
    registry.register(
        BUILTIN_CAPABILITIES["calculate_changed_area"], AreaCalculationAdapter
    )
    # No stubs

    return registry