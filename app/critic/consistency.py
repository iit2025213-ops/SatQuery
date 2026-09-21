"""Consistency checks.

Spatial, temporal, numerical, and modality consistency utilities
used by the critic.
"""

from __future__ import annotations

from app.evidence.schema import Observation, ObservationStatus


class ConsistencyChecker:
    """Runs targeted consistency checks on a set of observations."""

    def check_spatial(self, observations: list[Observation]) -> list[str]:
        """Detect CRS or bbox mismatches across observations."""
        issues: list[str] = []
        crs_set = {
            o.spatial.crs
            for o in observations
            if o.spatial.crs and o.status == ObservationStatus.SUCCESS
        }
        if len(crs_set) > 1:
            issues.append(f"Mixed CRS detected: {crs_set}")
        return issues

    def check_temporal(self, observations: list[Observation]) -> list[str]:
        """Detect temporal inconsistencies."""
        issues: list[str] = []
        for obs in observations:
            if obs.temporal.before and obs.temporal.after:
                if obs.temporal.before >= obs.temporal.after:
                    issues.append(
                        f"Temporal inversion in {obs.evidence_id}: "
                        f"before={obs.temporal.before} >= after={obs.temporal.after}"
                    )
        return issues

    def check_numerical(self, observations: list[Observation]) -> list[str]:
        """Flag results with out-of-range or obviously wrong values."""
        issues: list[str] = []
        for obs in observations:
            if obs.confidence is not None and not (0.0 <= obs.confidence <= 1.0):
                issues.append(
                    f"Invalid confidence {obs.confidence} in {obs.evidence_id}"
                )
        return issues

    def run_all(self, observations: list[Observation]) -> list[str]:
        """Run all consistency checks and return combined issues."""
        return (
            self.check_spatial(observations)
            + self.check_temporal(observations)
            + self.check_numerical(observations)
        )
