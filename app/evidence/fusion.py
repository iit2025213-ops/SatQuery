"""Evidence fusion.

Collects, indexes, and queries observations.  Supports querying by
capability, type, and status.
"""

from __future__ import annotations

from app.evidence.schema import EvidenceType, Observation, ObservationStatus


class EvidenceFusion:
    """Aggregate and query collected observations."""

    def __init__(self) -> None:
        self._observations: list[Observation] = []

    def add(self, obs: Observation) -> None:
        self._observations.append(obs)

    @property
    def all(self) -> list[Observation]:
        return list(self._observations)

    def by_capability(self, capability: str) -> list[Observation]:
        return [o for o in self._observations if o.source.capability == capability]

    def by_type(self, etype: EvidenceType) -> list[Observation]:
        return [o for o in self._observations if o.type == etype]

    def successful(self) -> list[Observation]:
        return [
            o for o in self._observations
            if o.status == ObservationStatus.SUCCESS
        ]

    def failed(self) -> list[Observation]:
        return [
            o for o in self._observations
            if o.status in (ObservationStatus.FAILURE, ObservationStatus.TIMEOUT)
        ]

    def has_evidence_for(self, capability: str) -> bool:
        return any(
            o.source.capability == capability
            and o.status == ObservationStatus.SUCCESS
            for o in self._observations
        )

    def summary(self) -> dict:
        """Return a compact summary for context building."""
        return {
            "total": len(self._observations),
            "successful": len(self.successful()),
            "failed": len(self.failed()),
            "capabilities_covered": list(
                {o.source.capability for o in self.successful()}
            ),
        }
