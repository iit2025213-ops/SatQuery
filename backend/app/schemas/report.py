from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ReportSection(BaseModel):
    """A generic section in the report."""
    type: str = Field(..., description="The type of section, e.g., 'executive_summary', 'spatial_findings'")
    title: str = Field(..., description="The title of the section")
    content: Optional[str] = Field(None, description="Narrative text content")
    metrics: Optional[List[Dict[str, Any]]] = Field(None, description="Factual metrics for this section")
    visuals: Optional[List[Dict[str, str]]] = Field(None, description="List of visual dicts, e.g., {'url': '...', 'caption': '...'}")
    findings: Optional[List[Dict[str, Any]]] = Field(None, description="List of finding dicts with evidence_ids")
    
    class Config:
        frozen = True

class ReportPackage(BaseModel):
    """
    The normalized, immutable single source of truth for generating a DOCX report.
    This package is completely assembled by the backend (ReportPlanner) before DOCX generation.
    """
    report_id: str = Field(..., description="Unique ID for this report package")
    job_id: str = Field(..., description="The parent job ID")
    title: str = Field(..., description="The generated title of the report")
    report_type: str = Field(..., description="Type of report: 'spatial', 'temporal', or 'integrated'")
    
    study_area: Dict[str, Any] = Field(..., description="AOI geometry or metadata")
    analysis_period: Dict[str, str] = Field(..., description="Start and end dates")
    data_sources: List[str] = Field(..., description="Sources, e.g., 'Sentinel-2 via Google Earth Engine'")
    
    sections: List[ReportSection] = Field(default_factory=list, description="Ordered list of report sections")
    
    provenance: Dict[str, Any] = Field(..., description="Provenance information, methodologies")
    quality: Dict[str, Any] = Field(..., description="Quality metadata, cloud cover, observation counts")
    limitations: List[str] = Field(..., description="Explicit limitations of the analysis")
    
    class Config:
        frozen = True
