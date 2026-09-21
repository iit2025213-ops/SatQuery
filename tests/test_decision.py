"""Tests for decision schema and validation."""

import pytest
from app.agent.decision import (
    ActionType,
    Decision,
    DecisionValidationError,
    validate_decision,
)


def test_call_capability_requires_capability():
    with pytest.raises(ValueError, match="CALL_CAPABILITY requires"):
        Decision(action=ActionType.CALL_CAPABILITY, capability="")


def test_retry_requires_capability():
    with pytest.raises(ValueError, match="RETRY requires"):
        Decision(action=ActionType.RETRY, capability="")


def test_parallel_requires_entries():
    with pytest.raises(ValueError, match="PARALLEL requires"):
        Decision(action=ActionType.PARALLEL, parallel_capabilities=[])


def test_final_requires_answer():
    with pytest.raises(ValueError, match="FINAL requires"):
        Decision(action=ActionType.FINAL, final_answer="")


def test_valid_call_capability():
    d = Decision(
        action=ActionType.CALL_CAPABILITY,
        capability="interpret_scene",
        arguments={"asset": "asset_001"},
        reason="Test",
    )
    assert d.capability == "interpret_scene"


def test_valid_final():
    d = Decision(
        action=ActionType.FINAL,
        final_answer="Analysis complete.",
        final_confidence=0.9,
    )
    assert d.final_confidence == 0.9


def test_validate_unknown_capability():
    d = Decision(
        action=ActionType.CALL_CAPABILITY,
        capability="nonexistent",
        reason="Test",
    )
    with pytest.raises(DecisionValidationError, match="Unknown capability"):
        validate_decision(d, {"interpret_scene"}, set())


def test_validate_unknown_asset():
    d = Decision(
        action=ActionType.CALL_CAPABILITY,
        capability="interpret_scene",
        arguments={"before_asset": "ghost"},
        reason="Test",
    )
    with pytest.raises(DecisionValidationError, match="not found"):
        validate_decision(d, {"interpret_scene"}, {"asset_001"})


def test_validate_parallel_unknown_capability():
    d = Decision(
        action=ActionType.PARALLEL,
        parallel_capabilities=[
            {"capability": "nonexistent", "arguments": {}},
        ],
    )
    with pytest.raises(DecisionValidationError, match="Unknown capability"):
        validate_decision(d, {"interpret_scene"}, set())


def test_validate_valid_decision():
    d = Decision(
        action=ActionType.CALL_CAPABILITY,
        capability="interpret_scene",
        arguments={"asset": "asset_001"},
        reason="Test",
    )
    # Should not raise
    validate_decision(d, {"interpret_scene"}, {"asset_001"})


def test_replan_action():
    d = Decision(action=ActionType.REPLAN, reason="Need more evidence")
    assert d.action == ActionType.REPLAN


def test_request_input_action():
    d = Decision(action=ActionType.REQUEST_INPUT, reason="Need user clarification")
    assert d.action == ActionType.REQUEST_INPUT
