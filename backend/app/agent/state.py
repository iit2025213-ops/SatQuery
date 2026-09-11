# app/agent/state.py

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid
import json


class Observation(BaseModel):
    observation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    step_number: int
    source_capability: str
    status: str  # success, failed, blocked
    result: dict = {}
    confidence: Optional[float] = None
    artifact_ids: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AgentState(BaseModel):
    job_id: str
    user_request: str
    input_assets: List[str]
    current_step: int = 0
    observations: List[Observation] = []
    evidence: List[dict] = []
    artifacts: List[str] = []
    confidence: Optional[float] = None
    final_result: Optional[str] = None
    finished: bool = False
    replans: int = 0

    # AOI (Phase 6) — injected when user provides geographic context
    aoi: Optional[dict] = None  # GeoJSON Polygon
    aoi_area_km2: Optional[float] = None
    aoi_bbox: Optional[List[float]] = None  # [minx, miny, maxx, maxy]

    def to_dict(self) -> dict:
        """Serialize for Brain"""
        return json.loads(self.model_dump_json())

    def add_observation(self, obs: Observation):
        """Add observation to state"""
        self.observations.append(obs)

    def inject_aoi(self, aoi_geojson: dict, aoi_area_km2: float, aoi_bbox: List[float]):
        """Inject AOI data into state for AI Brain geographic context"""
        self.aoi = aoi_geojson
        self.aoi_area_km2 = aoi_area_km2
        self.aoi_bbox = aoi_bbox

