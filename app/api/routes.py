"""FastAPI routes for the SatQuery public API.

Frontend communicates ONLY with these endpoints — never with
specialist model APIs directly.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.agent.controller import AgentController
from app.api.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    EvidenceSummary,
    JobResult,
    JobStatusResponse,
    JobReportResponse,
)
from app.config import Settings, get_settings
from app.executor.executor import DefaultExecutor
from app.llm.mock import MockLLM
from app.registry.registry import build_default_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["SatQuery"])

# In-memory job store (Phase 1).
_jobs: dict[str, dict[str, Any]] = {}


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _build_controller(settings: Settings) -> AgentController:
    registry = build_default_registry()
    executor = DefaultExecutor(registry)

    # LLM selection
    if settings.openai_api_key:
        from app.llm.openai import OpenAIProvider

        llm = OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            base_url=settings.openai_base_url,
            temperature=settings.openai_temperature,
            max_retries=settings.openai_max_retries,
        )
    else:
        llm = MockLLM()

    return AgentController(
        llm=llm, executor=executor, registry=registry, settings=settings
    )


async def _run_job(job_id: str, request: AnalyzeRequest) -> None:
    """Background coroutine that runs the agent loop for a job."""
    settings = get_settings()
    controller = _build_controller(settings)
    _jobs[job_id]["status"] = "running"

    try:
        result = await controller.run(
            request=request.query,
            input_assets=[a.model_dump() for a in request.assets],
            metadata=request.metadata,
        )
        _jobs[job_id]["status"] = "complete"
        _jobs[job_id]["result"] = result
    except Exception as exc:
        logger.exception("Job %s failed", job_id)
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["result"] = {
            "answer": f"Job failed: {exc}",
            "confidence": 0.0,
            "status": "failed",
            "evidence": [],
            "artifact_ids": [],
            "trace": [],
            "step_count": 0,
            "replans": 0,
        }


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """Submit a remote-sensing analysis request."""
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    _jobs[job_id] = {"status": "accepted", "result": None}
    background_tasks.add_task(_run_job, job_id, request)
    return AnalyzeResponse(job_id=job_id, status="accepted")


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str):
    """Poll job status and results."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = _jobs[job_id]
    result = None
    if job["result"]:
        raw = job["result"]
        result = JobResult(
            answer=raw.get("answer", ""),
            confidence=raw.get("confidence", 0.0),
            status=raw.get("status", "unknown"),
            evidence=[
                EvidenceSummary(**e) for e in raw.get("evidence", [])
            ],
            artifact_ids=raw.get("artifact_ids", []),
            verification=raw.get("verification"),
            trace=raw.get("trace", []),
            step_count=raw.get("step_count", 0),
            replans=raw.get("replans", 0),
        )
    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        result=result,
    )


@router.get("/jobs/{job_id}/events", response_model=list[dict[str, Any]])
async def get_job_events(job_id: str):
    """Get the trace events for a job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = _jobs[job_id]
    if not job["result"]:
        return []
    return job["result"].get("trace", [])


@router.get("/jobs/{job_id}/evidence", response_model=list[EvidenceSummary])
async def get_job_evidence(job_id: str):
    """Get the evidence (observations) collected by the agent."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = _jobs[job_id]
    if not job["result"]:
        return []
    return [EvidenceSummary(**e) for e in job["result"].get("evidence", [])]


@router.get("/jobs/{job_id}/report", response_model=JobReportResponse)
async def get_job_report(job_id: str):
    """Generate a markdown report for the job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = _jobs[job_id]
    if not job["result"]:
        raise HTTPException(status_code=400, detail="Job not completed")
    
    result = job["result"]
    answer = result.get("answer", "")
    evidence = result.get("evidence", [])
    
    lines = [
        f"# SatQuery AI Report (Job: {job_id})",
        "",
        "## Final Answer",
        answer,
        "",
        "## Evidence Collected",
    ]
    for e in evidence:
        lines.append(f"- **{e.get('capability', 'Unknown')}** ({e.get('status', 'unknown')}): {e.get('type', 'unknown')}")
        
    return JobReportResponse(job_id=job_id, report_markdown="\n".join(lines))


from fastapi.responses import FileResponse
import os

@router.get("/artifacts/{artifact_id:path}")
async def get_artifact(artifact_id: str):
    """Retrieve a generated artifact file."""
    # Note: artifact_id might be an absolute path depending on the executor.
    # In production with cloud storage, this would return a pre-signed URL or stream.
    if not os.path.exists(artifact_id):
        raise HTTPException(status_code=404, detail="Artifact not found or not accessible locally")
    return FileResponse(artifact_id)
