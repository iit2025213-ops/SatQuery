"""Confidence engine.

Calculates composite confidence from multiple factors — NOT simple
model voting.
"""

from __future__ import annotations

from app.evidence.schema import Observation, ObservationStatus


class ConfidenceEngine:
    """Computes an aggregate confidence score for a set of observations."""

    # Weights for the confidence factors (sum = 1.0)
    WEIGHT_MODEL = 0.35
    WEIGHT_COMPLETENESS = 0.25
    WEIGHT_CONSISTENCY = 0.20
    WEIGHT_DATA_QUALITY = 0.20

    def compute(
        self,
        observations: list[Observation],
        *,
        expected_capabilities: list[str] | None = None,
    ) -> float:
        """Return a composite confidence in [0, 1]."""
        if not observations:
            return 0.0

        model_conf = self._model_confidence(observations)
        completeness = self._evidence_completeness(
            observations, expected_capabilities or []
        )
        consistency = self._cross_consistency(observations)
        quality = self._data_quality(observations)

        composite = (
            self.WEIGHT_MODEL * model_conf
            + self.WEIGHT_COMPLETENESS * completeness
            + self.WEIGHT_CONSISTENCY * consistency
            + self.WEIGHT_DATA_QUALITY * quality
        )
        return round(min(max(composite, 0.0), 1.0), 3)

    # ------------------------------------------------------------------
    # Sub-scores
    # ------------------------------------------------------------------

    @staticmethod
    def _model_confidence(observations: list[Observation]) -> float:
        confs = [o.confidence for o in observations if o.confidence is not None]
        return sum(confs) / len(confs) if confs else 0.5

    @staticmethod
    def _evidence_completeness(
        observations: list[Observation],
        expected: list[str],
    ) -> float:
        if not expected:
            return 1.0
        covered = {
            o.source.capability
            for o in observations
            if o.status == ObservationStatus.SUCCESS
        }
        return len(covered & set(expected)) / len(expected)

    @staticmethod
    def _cross_consistency(observations: list[Observation]) -> float:
        """Simple heuristic: if all successful observations have confidence
        within 0.3 of each other, consistency is high."""
        confs = [
            o.confidence
            for o in observations
            if o.confidence is not None and o.status == ObservationStatus.SUCCESS
        ]
        if len(confs) < 2:
            return 0.8  # not enough to assess
        spread = max(confs) - min(confs)
        return max(0.0, 1.0 - spread)

    @staticmethod
    def _data_quality(observations: list[Observation]) -> float:
        """Penalise failed or partial observations."""
        if not observations:
            return 0.0
        ok = sum(
            1
            for o in observations
            if o.status in (ObservationStatus.SUCCESS, ObservationStatus.PARTIAL)
        )
        return ok / len(observations)
