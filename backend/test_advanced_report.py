import asyncio
import logging
from unittest.mock import MagicMock
import json

from app.agents.geo_agent import GeoAgent
from app.services.report_planner import ReportPlanner
from app.utils.doc_generator import DocGenerator
from app.schemas.report import ReportPackage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DELHI_AOI = {
    "type": "Polygon",
    "coordinates": [
        [
            [77.1000, 28.6000],
            [77.2500, 28.6000],
            [77.2500, 28.7000],
            [77.1000, 28.7000],
            [77.1000, 28.6000]
        ]
    ]
}

class MockAdminClient:
    def __init__(self):
        self.evidence_db = []
        self.artifacts_db = []
        self.artifact_evidence_db = []
    
    def table(self, name):
        class Table:
            def __init__(self, admin, tname):
                self.admin = admin
                self.tname = tname
                self.filters = {}
            
            def insert(self, data):
                class InsertBuilder:
                    def __init__(self, t, d):
                        self.t = t
                        self.d = d
                    def execute(self):
                        if self.t.tname == "evidence":
                            self.t.admin.evidence_db.append(self.d)
                        elif self.t.tname == "artifacts":
                            import uuid
                            self.d["artifact_id"] = str(uuid.uuid4())
                            self.t.admin.artifacts_db.append(self.d)
                            class MockData:
                                data = [self.d]
                            return MockData()
                        elif self.t.tname == "artifact_evidence":
                            self.t.admin.artifact_evidence_db.extend(self.d)
                        return None
                return InsertBuilder(self, data)
                
            def select(self, cols):
                return self
                
            def in_(self, col, values):
                self.filters[col] = values
                return self
                
            def execute(self):
                class MockData:
                    def __init__(self, t):
                        if t.tname == "evidence":
                            res = t.admin.evidence_db
                            if "evidence_id" in t.filters:
                                res = [r for r in res if r["evidence_id"] in t.filters["evidence_id"]]
                            self.data = res
                        else:
                            self.data = []
                return MockData(self)
        return Table(self, name)

class MockSupabaseClient:
    def __init__(self):
        self.admin = MockAdminClient()
    def get_admin_client(self):
        return self.admin
    def get_user_client(self):
        return self.admin

class MockCloudinaryClient:
    async def upload_bytes(self, data, artifact_type, job_id, filename, resource_type="image"):
        return {"url": f"http://cloudinary.mock/{filename}"}

async def run_tests():
    mock_supabase = MockSupabaseClient()
    mock_cloudinary = MockCloudinaryClient()
    
    planner = ReportPlanner(supabase_client=mock_supabase)
    
    # ---------------------------------------------------------
    # TEST 1: Spatial Report
    # ---------------------------------------------------------
    print("\n" + "="*50)
    print("TEST 1: Spatial Report Generation")
    print("="*50)
    
    agent_spatial = GeoAgent(
        max_tool_calls=3,
        deterministic=True,
        supabase_client=mock_supabase,
        job_id="test-job-spatial",
        user_id="test-user",
        analysis_id="test-analysis-spatial"
    )
    
    res_spatial = await agent_spatial.run(
        user_question="Provide a single-date spatial snapshot of vegetation and urbanization indices for this specific AOI using zonal statistics.",
        aoi_geojson=DELHI_AOI,
        start_date="2024-01-01",
        end_date="2024-02-28"
    )
    
    pkg_spatial = await planner.generate_package(
        job_id="test-job-spatial",
        analysis_id="test-analysis-spatial",
        user_id="test-user",
        agent_response=res_spatial,
        evidence_records=mock_supabase.admin.evidence_db,
        aoi=DELHI_AOI,
        start_date="2024-01-01",
        end_date="2024-02-28",
        cloudinary_client=mock_cloudinary
    )
    
    assert pkg_spatial.report_type == "spatial", f"Expected spatial, got {pkg_spatial.report_type}"
    assert len(pkg_spatial.sections) >= 3, "Missing core sections in report package"
    
    docx_spatial = DocGenerator.generate_advanced_docx(pkg_spatial)
    assert len(docx_spatial) > 1000, "DOCX file is suspiciously small"
    print("✅ Spatial Report Package and DOCX generated successfully.")

    # ---------------------------------------------------------
    # TEST 2: Temporal Report
    # ---------------------------------------------------------
    print("\n" + "="*50)
    print("TEST 2: Temporal Report Generation")
    print("="*50)
    
    agent_temporal = GeoAgent(
        max_tool_calls=3,
        deterministic=True,
        supabase_client=mock_supabase,
        job_id="test-job-temporal",
        user_id="test-user",
        analysis_id="test-analysis-temporal"
    )
    
    res_temporal = await agent_temporal.run(
        user_question="Analyze NDVI changes over the selected period.",
        aoi_geojson=DELHI_AOI,
        start_date="2023-01-01",
        end_date="2024-01-01"
    )
    
    # We must filter evidence to just the temporal analysis
    temporal_evidence = [e for e in mock_supabase.admin.evidence_db if e["analysis_id"] == "test-analysis-temporal"]
    
    pkg_temporal = await planner.generate_package(
        job_id="test-job-temporal",
        analysis_id="test-analysis-temporal",
        user_id="test-user",
        agent_response=res_temporal,
        evidence_records=temporal_evidence,
        aoi=DELHI_AOI,
        start_date="2023-01-01",
        end_date="2024-01-01",
        cloudinary_client=mock_cloudinary
    )
    
    assert pkg_temporal.report_type in ["temporal", "integrated"], f"Expected temporal/integrated, got {pkg_temporal.report_type}"
    docx_temporal = DocGenerator.generate_advanced_docx(pkg_temporal)
    assert len(docx_temporal) > 1000
    print("✅ Temporal Report Package and DOCX generated successfully.")
    
    # ---------------------------------------------------------
    # TEST 5: Numerical Integrity
    # ---------------------------------------------------------
    print("\n" + "="*50)
    print("TEST 5: Numerical Integrity")
    print("="*50)
    
    factual_section = next((s for s in pkg_spatial.sections if s.type == "factual_metrics"), None)
    assert factual_section is not None, "Factual metrics section missing"
    
    metrics = factual_section.metrics
    assert len(metrics) > 0, "No metrics found in factual section"
    
    # Verify metric exists in evidence DB
    for m in metrics:
        ev = next((e for e in mock_supabase.admin.evidence_db if e["evidence_id"] == m["evidence_id"]), None)
        assert ev is not None, f"Evidence ID {m['evidence_id']} not found in DB"
        if ev["value"] is not None:
            assert ev["value"] == m["value"], f"Metric value mismatch! {ev['value']} != {m['value']}"
        else:
            # Check if it's in raw_data
            raw = ev.get("parameters", {}).get("raw_data", {})
            
            def find_value(d, target):
                if isinstance(d, dict):
                    for v in d.values():
                        if v == target or find_value(v, target):
                            return True
                elif isinstance(d, list):
                    for item in d:
                        if find_value(item, target):
                            return True
                return False
                
            assert find_value(raw, m["value"]), f"Nested metric value {m['value']} not found in raw_data"
            
    print("✅ Numerical integrity verified. No hallucinated values found.")
    print("\n🚀 All advanced report tests passed successfully!")

if __name__ == "__main__":
    asyncio.run(run_tests())
