"""Tests for observation schema."""

from app.evidence.schema import (
    EvidenceSource,
    EvidenceType,
    Observation,
    ObservationStatus,
    SpatialMetadata,
    TemporalMetadata,
)


def test_observation_creation():
    obs = Observation(
        source=EvidenceSource(capability="test", model="TestModel"),
        type=EvidenceType.VQA,
        status=ObservationStatus.SUCCESS,
        result={"text": "Urban area"},
        confidence=0.9,
    )
    assert obs.type == EvidenceType.VQA
    assert obs.confidence == 0.9
    assert obs.evidence_id.startswith("ev_")


def test_observation_auto_id():
    o1 = Observation(
        source=EvidenceSource(capability="a"),
        type=EvidenceType.VALIDATION,
        status=ObservationStatus.SUCCESS,
    )
    o2 = Observation(
        source=EvidenceSource(capability="b"),
        type=EvidenceType.CAPTION,
        status=ObservationStatus.SUCCESS,
    )
    assert o1.evidence_id != o2.evidence_id


def test_observation_with_spatial():
    obs = Observation(
        source=EvidenceSource(capability="test"),
        type=EvidenceType.BITEMPORAL_CHANGE,
        status=ObservationStatus.SUCCESS,
        spatial=SpatialMetadata(bbox=[1.0, 2.0, 3.0, 4.0], crs="EPSG:32643"),
    )
    assert obs.spatial.crs == "EPSG:32643"


def test_observation_with_temporal():
    obs = Observation(
        source=EvidenceSource(capability="test"),
        type=EvidenceType.BITEMPORAL_CHANGE,
        status=ObservationStatus.SUCCESS,
        temporal=TemporalMetadata(before="2018-01-01", after="2024-01-01"),
    )
    assert obs.temporal.before == "2018-01-01"


def test_observation_failure():
    obs = Observation(
        source=EvidenceSource(capability="test"),
        type=EvidenceType.ERROR,
        status=ObservationStatus.FAILURE,
        error_message="Model crashed",
    )
    assert obs.status == ObservationStatus.FAILURE
    assert obs.error_message == "Model crashed"


def test_observation_serialization():
    obs = Observation(
        source=EvidenceSource(capability="cap1", model="M1"),
        type=EvidenceType.GROUNDING,
        status=ObservationStatus.SUCCESS,
        result={"regions": [{"label": "urban"}]},
    )
    data = obs.model_dump(mode="json")
    assert data["source"]["capability"] == "cap1"
    restored = Observation.model_validate(data)
    assert restored.type == EvidenceType.GROUNDING
