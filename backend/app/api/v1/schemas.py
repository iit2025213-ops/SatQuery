# app/api/v1/schemas.py

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
import json

# Query Request/Response
class AOI(BaseModel):
    """Area of Interest - GeoJSON Polygon"""
    type: str = "Polygon"
    coordinates: List[List[List[float]]]

class TemporalRange(BaseModel):
    start: str  # ISO date
    end: str

class AnalysisOptions(BaseModel):
    generate_artifacts: bool = True
    generate_report: bool = True
    include_visualizations: bool = True
    include_trace: bool = True

class SubmitQueryRequest(BaseModel):
    query: str
    asset_ids: List[str]
    aoi: Optional[AOI] = None
    temporal: Optional[TemporalRange] = None
    options: Optional[AnalysisOptions] = None

class SubmitQueryResponse(BaseModel):
    job_id: str
    status: str
    created_at: datetime

# Asset Upload/Response
class AssetMetadata(BaseModel):
    crs: Optional[str] = None
    acquisition_date: Optional[str] = None
    modality: Optional[str] = None  # optical, sar, etc
    bands: Optional[List[str]] = None

class UploadAssetResponse(BaseModel):
    asset_id: str
    status: str
    metadata: AssetMetadata
    file_url: str

# Job Status Response
class JobProgress(BaseModel):
    completed_steps: int
    total_steps: Optional[int] = None
    current_step: Optional[int] = None

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    query: str
    progress: JobProgress
    final_answer: Optional[str] = None
    confidence: Optional[float] = None
    created_at: datetime
    updated_at: datetime

# Evidence Response
class EvidenceItem(BaseModel):
    claim: str
    confidence: float
    observation_ids: List[str]

class JobEvidenceResponse(BaseModel):
    job_id: str
    evidence: List[EvidenceItem]
    observations_count: int

# Artifact Response
class ArtifactMetadata(BaseModel):
    artifact_id: str
    type: str  # change_mask, change_map, geojson, etc
    format: str
    url: str
    created_at: datetime

# Document Response
class DocumentMetadata(BaseModel):
    document_id: str
    type: str
    format: str
    url: str
    created_at: datetime
