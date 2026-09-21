"""Tests for executor and precondition validation."""

import pytest
from app.agent.state import AgentState, AssetReference
from app.evidence.schema import ObservationStatus
from app.executor.executor import DefaultExecutor
from app.registry.registry import build_default_registry


@pytest.fixture
def executor():
    return DefaultExecutor(build_default_registry())


@pytest.mark.asyncio
async def test_executor_success(executor, optical_state):
    obs = await executor.run(
        "validate_remote_sensing_input",
        {"asset": "asset_001"},
        optical_state,
    )
    assert obs.status == ObservationStatus.SUCCESS


@pytest.mark.asyncio
async def test_executor_unknown_capability(executor, empty_state):
    obs = await executor.run("nonexistent", {}, empty_state)
    assert obs.status == ObservationStatus.FAILURE
    assert "Unknown capability" in obs.error_message


@pytest.mark.asyncio
async def test_precondition_rejects_missing_temporal_pair(executor):
    state = AgentState(
        request="test",
        input_assets=[
            AssetReference(asset_id="a1", modality="optical"),
        ],
    )
    # detect_bitemporal_change requires before_asset + after_asset
    obs = await executor.run(
        "detect_bitemporal_change",
        {"asset": "a1"},  # missing before/after
        state,
    )
    assert obs.status == ObservationStatus.INVALID_INPUT


@pytest.mark.asyncio
async def test_precondition_rejects_wrong_modality(executor):
    """SAR image should not pass modality check for optical-only capability."""
    state = AgentState(
        request="test",
        input_assets=[
            AssetReference(asset_id="a1", modality="sar"),
        ],
    )
    obs = await executor.run(
        "interpret_scene",
        {"asset": "a1"},
        state,
    )
    assert obs.status == ObservationStatus.INVALID_INPUT
    assert "modality" in obs.error_message.lower()
