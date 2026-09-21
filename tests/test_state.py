"""Tests for AgentState."""

import pytest
from app.agent.state import AgentState, AssetReference, TaskRecord
from app.evidence.schema import (
    EvidenceSource,
    EvidenceType,
    Observation,
    ObservationStatus,
)


def test_state_creation():
    state = AgentState(request="Analyze image", current_goal="Analyze image")
    assert state.request == "Analyze image"
    assert state.step_count == 0
    assert state.observations == []
    assert state.replans == 0


def test_add_observation():
    state = AgentState(request="test")
    obs = Observation(
        source=EvidenceSource(capability="test_cap"),
        type=EvidenceType.VALIDATION,
        status=ObservationStatus.SUCCESS,
        result={"valid": True},
    )
    state.add_observation(obs)
    assert len(state.observations) == 1
    assert obs.evidence_id in state.evidence


def test_record_task_success():
    state = AgentState(request="test")
    record = TaskRecord(
        task_id="t1", capability="test_cap", status="success", evidence_id="ev1"
    )
    state.record_task(record)
    assert len(state.executed_tasks) == 1
    assert len(state.failed_tasks) == 0


def test_record_task_failure():
    state = AgentState(request="test")
    record = TaskRecord(
        task_id="t1", capability="test_cap", status="failure", error="boom"
    )
    state.record_task(record)
    assert len(state.failed_tasks) == 1
    assert len(state.executed_tasks) == 0


def test_last_observation_empty():
    state = AgentState(request="test")
    assert state.last_observation() is None


def test_last_observation():
    state = AgentState(request="test")
    obs = Observation(
        source=EvidenceSource(capability="cap1"),
        type=EvidenceType.VQA,
        status=ObservationStatus.SUCCESS,
    )
    state.add_observation(obs)
    assert state.last_observation() == obs


def test_observations_by_capability():
    state = AgentState(request="test")
    obs1 = Observation(
        source=EvidenceSource(capability="cap1"),
        type=EvidenceType.VQA,
        status=ObservationStatus.SUCCESS,
    )
    obs2 = Observation(
        source=EvidenceSource(capability="cap2"),
        type=EvidenceType.CAPTION,
        status=ObservationStatus.SUCCESS,
    )
    state.add_observation(obs1)
    state.add_observation(obs2)
    assert len(state.observations_by_capability("cap1")) == 1


def test_has_evidence_for():
    state = AgentState(request="test")
    obs = Observation(
        source=EvidenceSource(capability="cap1"),
        type=EvidenceType.VQA,
        status=ObservationStatus.SUCCESS,
    )
    state.add_observation(obs)
    assert state.has_evidence_for("cap1")
    assert not state.has_evidence_for("cap2")


def test_asset_reference():
    asset = AssetReference(
        asset_id="a1", uri="s3://bucket/img.tif", modality="optical", format="geotiff"
    )
    assert asset.asset_id == "a1"
    assert asset.modality == "optical"


def test_state_serialization():
    state = AgentState(request="test", step_count=5)
    data = state.model_dump()
    assert data["step_count"] == 5
    restored = AgentState.model_validate(data)
    assert restored.request == "test"
