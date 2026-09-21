"""Tests for context builder."""

from app.agent.context import ContextBuilder
from app.agent.state import AgentState, AssetReference
from app.evidence.schema import (
    EvidenceSource,
    EvidenceType,
    Observation,
    ObservationStatus,
)


def test_context_includes_request():
    state = AgentState(request="Analyze image", current_goal="Analyze image")
    ctx = ContextBuilder().build(state)
    assert ctx["user_request"] == "Analyze image"
    assert ctx["current_goal"] == "Analyze image"


def test_context_includes_assets():
    state = AgentState(
        request="test",
        input_assets=[AssetReference(asset_id="a1", modality="optical")],
    )
    ctx = ContextBuilder().build(state)
    assert len(ctx["input_assets"]) == 1
    assert ctx["input_assets"][0]["asset_id"] == "a1"


def test_context_includes_observations():
    state = AgentState(request="test")
    obs = Observation(
        source=EvidenceSource(capability="val"),
        type=EvidenceType.VALIDATION,
        status=ObservationStatus.SUCCESS,
        result={"valid": True},
    )
    state.add_observation(obs)
    ctx = ContextBuilder().build(state)
    assert len(ctx["observations"]) == 1
    assert ctx["observations"][0]["capability"] == "val"


def test_context_bounded():
    """Context should include at most _MAX_RECENT_OBS observations."""
    state = AgentState(request="test")
    for i in range(25):
        state.add_observation(
            Observation(
                source=EvidenceSource(capability=f"cap_{i}"),
                type=EvidenceType.VALIDATION,
                status=ObservationStatus.SUCCESS,
            )
        )
    ctx = ContextBuilder().build(state)
    assert len(ctx["observations"]) <= 10


def test_context_no_binary_data():
    """Context observations should not contain raw binary data."""
    state = AgentState(request="test")
    obs = Observation(
        source=EvidenceSource(capability="test"),
        type=EvidenceType.VQA,
        status=ObservationStatus.SUCCESS,
        result={"text": "answer"},
    )
    state.add_observation(obs)
    ctx = ContextBuilder().build(state)
    # Observation summary should be a simple dict, not contain image bytes
    summary = ctx["observations"][0]
    assert isinstance(summary, dict)
    assert "evidence_id" in summary


def test_context_includes_capabilities():
    state = AgentState(request="test")
    ctx = ContextBuilder().build(
        state, available_capabilities=["interpret_scene", "validate_remote_sensing_input"]
    )
    assert any("interpret_scene" in cap for cap in ctx["available_capabilities"])
