import uuid
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timezone
import json

from app.schemas.report import ReportPackage, ReportSection

logger = logging.getLogger("satquery")

class ReportPlanner:
    """
    Assembles a deterministic ReportPackage based on the GeoAgent's outputs and evidence.
    """
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        
    def _determine_report_type(self, tools_used: List[str]) -> str:
        temporal_tools = {"gee_analyze_trend", "gee_analyze_change_persistence", "gee_get_temporal_series", "gee_detect_temporal_breaks"}
        spatial_tools = {"gee_calculate_change_area", "gee_detect_hotspots", "gee_calculate_overlap", "gee_get_zonal_statistics"}
        
        has_temporal = any(t in tools_used for t in temporal_tools)
        has_spatial = any(t in tools_used for t in spatial_tools)
        
        if has_temporal and has_spatial:
            return "integrated"
        elif has_temporal:
            return "temporal"
        else:
            return "spatial"

    async def generate_package(
        self, 
        job_id: str,
        user_id: str,
        agent_response,
        evidence_records: List[Dict[str, Any]],
        aoi: dict,
        start_date: str,
        end_date: str,
        cloudinary_client=None
    ) -> ReportPackage:
        """
        Builds the immutable report package deterministically.
        """
        tools_used = agent_response.tools_used
        report_type = self._determine_report_type(tools_used)
        
        title = f"SatQuery {report_type.capitalize()} Analysis Report"
        sections = []
        
        # 1. Executive Summary
        evidence_ids = [ev["evidence_id"] for ev in evidence_records]
        sections.append(ReportSection(
            type="executive_summary",
            title="Executive Summary",
            content=agent_response.answer,
            findings=[{"text": "Summary derived from GeoAgent analysis.", "evidence_ids": evidence_ids}]
        ))
        
        # 2. Factual Metrics
        metrics = []
        for ev in evidence_records:
            if ev.get("metric") and ev.get("value") is not None:
                metrics.append({
                    "name": ev["metric"],
                    "value": ev["value"],
                    "tool": ev.get("tool_name"),
                    "evidence_id": ev["evidence_id"]
                })
            
            # Also extract from raw_data if multiple metrics were returned
            params = ev.get("parameters", {})
            raw_data = params.get("raw_data", {}) if isinstance(params, dict) else {}
            
            def extract_numeric(d, prefix=""):
                for k, v in d.items():
                    key_name = f"{prefix}{k}" if prefix else k
                    if isinstance(v, (int, float)) and key_name != ev.get("metric"):
                        metrics.append({
                            "name": key_name,
                            "value": v,
                            "tool": ev.get("tool_name"),
                            "evidence_id": ev["evidence_id"]
                        })
                    elif isinstance(v, dict):
                        extract_numeric(v, prefix=f"{key_name}_")
            
            extract_numeric(raw_data)
                
        # 3. Chart Generation (using Matplotlib for temporal data)
        visuals = []
        timeline_data = agent_response.timeline_artifact
        if timeline_data and "frames" in timeline_data and cloudinary_client:
            frames = timeline_data["frames"]
            if frames:
                import matplotlib.pyplot as plt
                import io
                
                dates = [f["date"] for f in frames if "date" in f]
                ndvi = [f.get("ndvi_mean") for f in frames if "date" in f]
                
                plt.figure(figsize=(8, 4))
                plt.plot(dates, ndvi, marker='o', color='green', label='NDVI')
                plt.title("NDVI Temporal Trend")
                plt.xlabel("Date")
                plt.ylabel("NDVI Mean")
                plt.xticks(rotation=45)
                plt.tight_layout()
                
                buf = io.BytesIO()
                plt.savefig(buf, format='png')
                buf.seek(0)
                plt.close()
                
                # Upload chart to Cloudinary
                try:
                    upload_res = await cloudinary_client.upload_bytes(
                        buf.read(),
                        artifact_type="report_chart",
                        job_id=job_id,
                        filename="temporal_chart.png"
                    )
                    if upload_res and "url" in upload_res:
                        visuals.append({
                            "url": upload_res["url"],
                            "caption": "Temporal Chart of NDVI"
                        })
                except Exception as e:
                    logger.error(f"Failed to upload chart: {e}")
                    
        # Visual evidence from AgentResponse
        for vis in agent_response.visual_evidence:
            if vis.url:
                visuals.append({
                    "url": vis.url,
                    "caption": f"GEE Observation: {vis.observation}"
                })
                
        if metrics or visuals:
            sections.append(ReportSection(
                type="factual_metrics",
                title="Verified Scientific Metrics",
                metrics=metrics,
                visuals=visuals
            ))
            
        # 4. Limitations
        limitations = agent_response.limitations
        if limitations or agent_response.quality.get("status") == "insufficient":
            sections.append(ReportSection(
                type="limitations",
                title="Analysis Limitations",
                content="The following constraints were observed during the analysis:",
                metrics=[{"name": "Limitation", "value": l} for l in limitations]
            ))
            
        prov_dict = {
            "status": agent_response.provenance_status,
            "evidence_count": len(evidence_records),
            "tools_used": tools_used
        }

        package = ReportPackage(
            report_id=str(uuid.uuid4()),
            job_id=job_id,
            title=title,
            report_type=report_type,
            study_area=aoi,
            analysis_period={"start": start_date, "end": end_date},
            data_sources=["Sentinel-2 via Google Earth Engine"],
            sections=sections,
            provenance=prov_dict,
            quality=agent_response.quality,
            limitations=limitations
        )
        return package
