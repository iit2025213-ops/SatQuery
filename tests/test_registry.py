"""Tests for capability registry."""

import pytest
from app.registry.registry import build_default_registry


def test_registry_has_all_builtins(registry):
    expected = [
        "validate_remote_sensing_input",
        "validate_temporal_pair",
        "validate_spatial_alignment",
        "retrieve_satellite_imagery",
        "answer_remote_sensing_vqa",
        "generate_caption",
        "ground_region",
        "interpret_scene",
        "detect_bitemporal_change",
        "analyze_multispectral_image",
        "analyze_sar_image",
        "perform_multimodal_analysis",
        "calculate_changed_area",
        "generate_change_map",
        "generate_timelapse",
    ]
    for cap in expected:
        assert registry.has(cap), f"Missing capability: {cap}"


def test_resolve_valid_capability(registry):
    defn, adapter = registry.resolve("interpret_scene")
    assert defn.name == "interpret_scene"
    assert adapter is not None


def test_resolve_unknown_raises(registry):
    with pytest.raises(KeyError, match="Unknown capability"):
        registry.resolve("nonexistent_capability")


def test_list_capabilities(registry):
    caps = registry.list_capabilities()
    assert "interpret_scene" in caps
    assert len(caps) >= 15


def test_get_definition(registry):
    defn = registry.get_definition("detect_bitemporal_change")
    assert defn.requires_temporal_pair is True
    assert defn.required_asset_count == 2


def test_capability_isolation():
    """Registry creates new adapter instances on each resolve."""
    reg = build_default_registry()
    _, a1 = reg.resolve("interpret_scene")
    _, a2 = reg.resolve("interpret_scene")
    assert a1 is not a2
