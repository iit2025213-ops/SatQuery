# app/evidence/schema.py

from pydantic import BaseModel
from typing import List, Optional


class EvidenceItem(BaseModel):
    claim: str
    confidence: float
    observation_ids: List[str]
    supporting_factors: dict = {}
