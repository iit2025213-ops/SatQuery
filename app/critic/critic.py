"""Critic — evaluates evidence sufficiency and quality.

Verification is conditional: simple queries may not need it, while
multi-step analyses benefit from consistency checks.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.evidence.schema import Observation, ObservationStatus


class VerificationResult(BaseModel):
    """Output of a critic evaluation."""

    sufficient: bool = True
    contradictions: list[str] = []
    warnings: list[str] = []
    recommendation: str = ""


class Critic:
    """Evaluates collected evidence for a single agent run."""

    def evaluate(self, observations: list[Observation]) -> VerificationResult:
        contradictions = self._detect_contradictions(observations)
        warnings = self._detect_warnings(observations)
        sufficient = self._is_sufficient(observations)

        recommendation = ""
        if contradictions:
            recommendation = "Contradictory evidence detected — consider verification."
        elif not sufficient:
            recommendation = "Insufficient evidence — consider additional analysis."

        return VerificationResult(
            sufficient=sufficient and not contradictions,
            contradictions=contradictions,
            warnings=warnings,
            recommendation=recommendation,
        )

    # ------------------------------------------------------------------
    # Internal checks
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_contradictions(observations: list[Observation]) -> list[str]:
        """Look for conflicting evidence across observations."""
        contradictions: list[str] = []
        successes = [o for o in observations if o.status == ObservationStatus.SUCCESS]

        # Example: if change detection says "large change" but scene
        # interpretation says "no change", flag it.
        change_obs = [o for o in successes if o.type.value == "bitemporal_change"]
        scene_obs = [o for o in successes if o.type.value == "scene_interpretation"]

        for co in change_obs:
            change_pct = co.result.get("mean_probability", 0)
            for so in scene_obs:
                text = so.result.get("text", "").lower()
                if change_pct > 0.7 and "no change" in text:
                    contradictions.append(
                        f"Change detection ({change_pct:.0%}) contradicts "
                        f"scene interpretation ('no change')."
                    )
        return contradictions

    @staticmethod
    def _detect_warnings(observations: list[Observation]) -> list[str]:
        warnings: list[str] = []
        for obs in observations:
            if obs.confidence is not None and obs.confidence < 0.5:
                warnings.append(
                    f"Low confidence ({obs.confidence:.2f}) from "
                    f"{obs.source.capability}."
                )
            if obs.status == ObservationStatus.PARTIAL:
                warnings.append(
                    f"Partial result from {obs.source.capability}."
                )
        return warnings

    @staticmethod
    def _is_sufficient(observations: list[Observation]) -> bool:
        """At least one successful observation is required."""
        return any(o.status == ObservationStatus.SUCCESS for o in observations)
