# app/evidence/confidence.py

from typing import List
from app.evidence.schema import EvidenceItem


class ConfidenceEngine:
    """Calculate evidence confidence"""

    @staticmethod
    def calculate_confidence(
        observations: List,
        evidence_items: List[EvidenceItem]
    ) -> float:
        """Calculate overall confidence"""

        if not observations:
            return 0.0

        # Weight by observation confidence
        confidences = [obs.confidence or 0.5 for obs in observations if obs.status == "success"]

        if not confidences:
            return 0.0

        # Average with slight boost for multiple observations
        avg_confidence = sum(confidences) / len(confidences)
        observation_bonus = min(0.05, len(confidences) * 0.01)

        final_confidence = min(0.99, avg_confidence + observation_bonus)

        return final_confidence
