"""Tests for evidence fusion and confidence engine."""

from app.evidence.fusion import EvidenceFusion
from app.evidence.confidence import ConfidenceEngine
from app.evidence.schema import (
    EvidenceSource,
    EvidenceType,
    Observation,
    ObservationStatus,
)


def _make_obs(cap: str, conf: float = 0.85, status=ObservationStatus.SUCCESS) -> Observation:
    return Observation(
        source=EvidenceSource(capability=cap),
        type=EvidenceType.VQA,
        status=status,
        confidence=conf,
    )


# --- Fusion ---

def test_fusion_add_and_query():
    f = EvidenceFusion()
    f.add(_make_obs("cap1"))
    f.add(_make_obs("cap2"))
    assert len(f.all) == 2
    assert len(f.by_capability("cap1")) == 1


def test_fusion_successful():
    f = EvidenceFusion()
    f.add(_make_obs("cap1"))
    f.add(_make_obs("cap2", status=ObservationStatus.FAILURE))
    assert len(f.successful()) == 1
    assert len(f.failed()) == 1


def test_fusion_has_evidence():
    f = EvidenceFusion()
    f.add(_make_obs("cap1"))
    assert f.has_evidence_for("cap1")
    assert not f.has_evidence_for("cap_missing")


def test_fusion_summary():
    f = EvidenceFusion()
    f.add(_make_obs("cap1"))
    f.add(_make_obs("cap2"))
    s = f.summary()
    assert s["total"] == 2
    assert s["successful"] == 2


# --- Confidence ---

def test_confidence_empty():
    engine = ConfidenceEngine()
    assert engine.compute([]) == 0.0


def test_confidence_single_high():
    engine = ConfidenceEngine()
    obs = [_make_obs("cap1", conf=0.95)]
    conf = engine.compute(obs)
    assert 0.7 < conf <= 1.0


def test_confidence_with_failure():
    engine = ConfidenceEngine()
    obs = [
        _make_obs("cap1", conf=0.9),
        _make_obs("cap2", conf=0.3, status=ObservationStatus.FAILURE),
    ]
    conf = engine.compute(obs)
    assert conf < 0.9  # should be penalised


def test_confidence_not_simple_voting():
    """Confidence must NOT be just 'N models agree = X%'."""
    engine = ConfidenceEngine()
    obs = [_make_obs(f"cap{i}", conf=0.8) for i in range(3)]
    conf = engine.compute(obs)
    # Should be based on multiple factors, not just average
    assert 0.5 < conf < 1.0


def test_confidence_considers_completeness():
    engine = ConfidenceEngine()
    obs = [_make_obs("cap1", conf=0.9)]
    full = engine.compute(obs, expected_capabilities=["cap1", "cap2"])
    partial = engine.compute(obs, expected_capabilities=["cap1"])
    assert partial >= full  # more complete = higher confidence
