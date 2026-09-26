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
    """Build a registry pre-loaded with all built-in mock adapters."""
    from app.models.geochat.adapter import GeoChatAdapter
    from app.models.change_detection.adapter import ChangeDetectionAdapter
    from app.models.prithvi.adapter import PrithviAdapter
    from app.models.sarmae.adapter import SARMAEAdapter
    from app.models.terramind.adapter import TerraMindAdapter
    from app.geospatial.validation import ValidationAdapter
    from app.geospatial.processing import VisualPreviewAdapter
    from app.tools.area import AreaCalculationAdapter

    registry = CapabilityRegistry()

    # Validation capabilities — use the validation adapter
    for cap_name in (
        "validate_remote_sensing_input",
        "validate_temporal_pair",
        "validate_spatial_alignment",
    ):
        registry.register(BUILTIN_CAPABILITIES[cap_name], ValidationAdapter)

    # Retrieval
    registry.register(
        BUILTIN_CAPABILITIES["retrieve_satellite_imagery"], ValidationAdapter
    )

    # GeoChat capabilities
    for cap_name in (
        "answer_remote_sensing_vqa",
        "generate_caption",
        "ground_region",
        "interpret_scene",
        "answer_change_vqa",
    ):
        registry.register(BUILTIN_CAPABILITIES[cap_name], GeoChatAdapter)

    # ChangeDetection
    registry.register(
        BUILTIN_CAPABILITIES["detect_bitemporal_change"], ChangeDetectionAdapter
    )

    # Prithvi
    registry.register(
        BUILTIN_CAPABILITIES["analyze_multispectral_image"], PrithviAdapter
    )

    # SARMAE
    registry.register(
        BUILTIN_CAPABILITIES["analyze_sar_image"], SARMAEAdapter
    )

    # TerraMind
    for cap_name in (
        "terramind_embedding",
        "terramind_tim",
        "terramind_generate",
        "terramind_coordinate_tokenizer",
    ):
        registry.register(BUILTIN_CAPABILITIES[cap_name], TerraMindAdapter)

    # Geospatial tools
    registry.register(
        BUILTIN_CAPABILITIES["create_visual_preview"], VisualPreviewAdapter
    )
    registry.register(
        BUILTIN_CAPABILITIES["calculate_changed_area"], AreaCalculationAdapter
    )
    registry.register(
        BUILTIN_CAPABILITIES["generate_change_map"], ValidationAdapter
    )
    registry.register(
        BUILTIN_CAPABILITIES["generate_timelapse"], ValidationAdapter
    )

    return registry