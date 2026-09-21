"""Tests for critic and consistency checker."""

from app.critic.critic import Critic
from app.critic.consistency import ConsistencyChecker
from app.evidence.schema import (
    EvidenceSource,
    EvidenceType,
    Observation,
    ObservationStatus,
    SpatialMetadata,
    TemporalMetadata,
)


def test_critic_sufficient_with_success():
    critic = Critic()
    obs = [
        Observation(
            source=EvidenceSource(capability="cap1"),
            type=EvidenceType.VQA,
            status=ObservationStatus.SUCCESS,
            result={"text": "urban"},
            confidence=0.9,
        )
    ]
    result = critic.evaluate(obs)
    assert result.sufficient is True
    assert result.contradictions == []


def test_critic_insufficient_no_success():
    critic = Critic()
    obs = [
        Observation(
            source=EvidenceSource(capability="cap1"),
            type=EvidenceType.ERROR,
            status=ObservationStatus.FAILURE,
            error_message="failed",
        )
    ]
    result = critic.evaluate(obs)
    assert result.sufficient is False


def test_critic_low_confidence_warning():
    critic = Critic()
    obs = [
        Observation(
            source=EvidenceSource(capability="cap1"),
            type=EvidenceType.VQA,
            status=ObservationStatus.SUCCESS,
            confidence=0.3,
        )
    ]
    result = critic.evaluate(obs)
    assert any("Low confidence" in w for w in result.warnings)


def test_critic_contradiction_detection():
    critic = Critic()
    obs = [
        Observation(
            source=EvidenceSource(capability="detect_bitemporal_change"),
            type=EvidenceType.BITEMPORAL_CHANGE,
            status=ObservationStatus.SUCCESS,
            result={"mean_probability": 0.9},
            confidence=0.9,
        ),
        Observation(
            source=EvidenceSource(capability="interpret_scene"),
            type=EvidenceType.SCENE_INTERPRETATION,
            status=ObservationStatus.SUCCESS,
            result={"text": "no change observed in the area"},
            confidence=0.8,
        ),
    ]
    result = critic.evaluate(obs)
    assert len(result.contradictions) > 0


# --- Consistency ---

def test_consistency_spatial_mixed_crs():
    checker = ConsistencyChecker()
    obs = [
        Observation(
            source=EvidenceSource(capability="a"),
            type=EvidenceType.VQA,
            status=ObservationStatus.SUCCESS,
            spatial=SpatialMetadata(crs="EPSG:4326"),
        ),
        Observation(
            source=EvidenceSource(capability="b"),
            type=EvidenceType.VQA,
            status=ObservationStatus.SUCCESS,
            spatial=SpatialMetadata(crs="EPSG:32643"),
        ),
    ]
    issues = checker.check_spatial(obs)
    assert any("Mixed CRS" in i for i in issues)


def test_consistency_temporal_inversion():
    checker = ConsistencyChecker()
    obs = [
        Observation(
            source=EvidenceSource(capability="cd"),
            type=EvidenceType.BITEMPORAL_CHANGE,
            status=ObservationStatus.SUCCESS,
            temporal=TemporalMetadata(before="2024-01-01", after="2018-01-01"),
        )
    ]
    issues = checker.check_temporal(obs)
    assert any("Temporal inversion" in i for i in issues)


def test_consistency_run_all():
    checker = ConsistencyChecker()
    obs = [
        Observation(
            source=EvidenceSource(capability="a"),
            type=EvidenceType.VQA,
            status=ObservationStatus.SUCCESS,
        )
    ]
    issues = checker.run_all(obs)
    assert isinstance(issues, list)
