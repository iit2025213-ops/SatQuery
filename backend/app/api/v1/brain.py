# app/api/v1/brain.py
#
# Routes ALL dashboard chat queries to the external SatQuery Brain service
# hosted on Render (friend's backend).
#
# API FLOW (asynchronous, non-blocking):
#   Frontend POSTs to /api/v1/brain
#   → we immediately submit to Brain, return { brain_job_id }
#   → frontend polls GET /api/v1/brain/status/{brain_job_id}
#   → when complete, frontend reads { reply, artifact_ids, confidence }
#
# This avoids the long-blocking pattern that starved uvicorn's event loop.
#
# Azure OpenAI is reserved ONLY for the AOI / MapPage (GeoAgent) feature.

import asyncio
import logging
import mimetypes
import httpx
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from app.config import settings
from app.auth.dependencies import get_current_user_id

logger = logging.getLogger("satquery")
router = APIRouter(prefix="/api/v1", tags=["brain"])

# ── In-memory job cache (brain_job_id → result/status) ────────────────────────
# Keyed by the Brain server's own job_id.
# Values: { "status": "polling"|"complete"|"failed", "reply": ..., ... }
_brain_jobs: Dict[str, Dict[str, Any]] = {}

# ── Request schemas ────────────────────────────────────────────────────────────

class BrainMessage(BaseModel):
    role: str
    content: str

class BrainRequest(BaseModel):
    query: str
    messages: Optional[List[BrainMessage]] = []
    asset_ids: Optional[List[str]] = []
    user_id: Optional[str] = None
    options: Optional[Dict] = None

# ── Helpers ───────────────────────────────────────────────────────────────────

def _base_url(url: str) -> str:
    url = url.strip().rstrip("/")
    if url.startswith("ws://"):
        url = "http://" + url[5:]
    elif url.startswith("wss://"):
        url = "https://" + url[6:]
    return url

def _mime_for_filename(filename: str) -> str:
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


# ── Background polling task ────────────────────────────────────────────────────

async def _poll_brain_job(brain_job_id: str, jobs_url: str):
    """
    Run in background. Polls the Brain server until the job completes,
    then stores the result in _brain_jobs[brain_job_id].
    """
    poll_timeout  = 600   # 10 minutes max
    poll_interval = 4     # seconds between polls
    elapsed       = 0

    _brain_jobs[brain_job_id] = {"status": "polling"}

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            while elapsed < poll_timeout:
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

                try:
                    resp = await client.get(jobs_url)
                except Exception as e:
                    logger.warning(f"Brain poll error at {elapsed}s: {e} — retrying")
                    continue

                if resp.status_code != 200:
                    logger.warning(f"Brain poll HTTP {resp.status_code} at {elapsed}s — retrying")
                    continue

                data       = resp.json()
                job_status = data.get("status", "")

                logger.info(f"   Brain job {brain_job_id}: status={job_status} ({elapsed}s)")

                if job_status == "complete":
                    # Debug dump
                    try:
                        import json
                        with open(r"c:\Users\avdes\OneDrive\SatQuery\backend\brain_debug_last_job.json", "w") as f:
                            json.dump(data, f, indent=2)
                    except:
                        pass
                    
                    result       = data.get("result") or {}
                    answer       = (
                        result.get("answer")
                        or result.get("reply")
                        or result.get("response")
                        or result.get("content")
                        or "The Brain returned an empty response."
                    )
                    # Aggressively search for artifact_ids recursively in case it's deeply nested
                    def find_artifacts(obj):
                        found = []
                        if isinstance(obj, dict):
                            for k, v in obj.items():
                                # Handle arrays of artifacts and trace output references
                                if k in ("artifact_ids", "artifacts", "visual_evidence", "images", "output_references") and isinstance(v, list):
                                    strings_only = [
                                        item for item in v 
                                        if isinstance(item, str) and (item.startswith("/tmp/") or item.startswith("http://") or item.startswith("https://"))
                                    ]
                                    found.extend(strings_only)
                                # Handle specific singleton string URIs from the new stateless guide
                                elif k in ("change_mask_uri", "change_overlay_uri", "grounded_image_uri") and isinstance(v, str):
                                    if v.startswith("/tmp/") or v.startswith("http://") or v.startswith("https://"):
                                        found.append(v)
                                elif isinstance(v, (dict, list)):
                                    found.extend(find_artifacts(v))
                        elif isinstance(obj, list):
                            for item in obj:
                                found.extend(find_artifacts(item))
                        return found

                    artifacts = find_artifacts(data)
                    # Deduplicate
                    artifacts = list(dict.fromkeys(artifacts))
                    
                    logger.info(f"✅ Brain job {brain_job_id} complete. Raw data keys: {list(data.keys())}")
                    if artifacts:
                        logger.info(f"Found artifacts recursively: {artifacts}")

                    _brain_jobs[brain_job_id] = {
                        "status":       "complete",
                        "reply":        answer,
                        "artifact_ids": artifacts,
                        "confidence":   result.get("confidence"),
                        "job_id":       brain_job_id,
                    }
                    try:
                        from app.main import supabase_client
                        supabase_client.get_admin_client().table("jobs").update({
                            "status": "completed",
                            "final_answer": answer
                        }).eq("job_id", brain_job_id).execute()
                    except Exception as e:
                        logger.error(f"Failed to update Brain job {brain_job_id} in DB: {e}")
                    
                    logger.info(f"✅ Brain job {brain_job_id} complete ({len(answer)} chars)")
                    return

                if job_status in ("failed", "error", "cancelled"):
                    _brain_jobs[brain_job_id] = {
                        "status": "failed",
                        "error":  f"Brain job ended with status: {job_status}",
                    }
                    logger.error(f"Brain job {brain_job_id} failed: {job_status}")
                    return

        # Timed out
        _brain_jobs[brain_job_id] = {
            "status": "failed",
            "error":  f"Brain job timed out after {poll_timeout}s",
        }
        logger.error(f"Brain job {brain_job_id} timed out")

    except Exception as e:
        _brain_jobs[brain_job_id] = {"status": "failed", "error": str(e)}
        logger.error(f"Brain poll task crashed: {e}", exc_info=True)


# ── POST /api/v1/brain — submit & immediately return job_id ──────────────────

@router.post("/brain")
async def query_brain(
    request: BrainRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id)
):
    """
    Submit a query to the Brain service. Returns immediately with a brain_job_id.
    The frontend should poll GET /api/v1/brain/status/{brain_job_id} for the result.
    """
    from app.main import supabase_client

    base        = _base_url(settings.ai_brain_url)
    analyze_url = f"{base}/api/v1/analyze"
    jobs_tpl    = f"{base}/api/v1/jobs/{{job_id}}"

    # Resolve asset_ids → Cloudinary URLs
    assets_payload = []
    if request.asset_ids:
        try:
            res = (
                supabase_client.get_user_client()
                .table("assets")
                .select("asset_id, file_url, modality, filename")
                .in_("asset_id", request.asset_ids)
                .execute()
            )
            for row in (res.data or []):
                if not row.get("file_url"):
                    continue
                filename = row.get("filename", "")
                assets_payload.append({
                    "asset_id": row["asset_id"],
                    "uri":      row["file_url"],
                    "modality": row.get("modality", "RGB").upper(),
                    "format":   _mime_for_filename(filename),
                    "metadata": {},
                })
        except Exception as e:
            logger.warning(f"Failed to resolve asset URLs for Brain: {e}")

    analyze_payload = {
        "query":    request.query,
        "assets":   assets_payload,
        "metadata": request.options or {},
        "options":  request.options or {},
    }

    logger.info(f"🧠 Submitting to Brain: {analyze_url}")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            submit_resp = await client.post(
                analyze_url,
                json=analyze_payload,
                headers={"Content-Type": "application/json"},
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Brain service did not respond in time (Render cold start). Please try again.")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Cannot connect to AI Brain. Check AI_BRAIN_URL in .env.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Brain submit error: {str(e)}")

    if submit_resp.status_code != 200:
        logger.error(f"Brain /analyze HTTP {submit_resp.status_code}: {submit_resp.text[:200]}")
        raise HTTPException(status_code=502, detail=f"Brain returned HTTP {submit_resp.status_code}.")

    data       = submit_resp.json()
    brain_job_id = data.get("job_id")
    if not brain_job_id:
        raise HTTPException(status_code=502, detail="Brain did not return a job_id.")

    logger.info(f"✅ Brain job accepted: {brain_job_id}")

    try:
        from app.main import supabase_client
        job_data = {
            "job_id": brain_job_id,
            "user_id": user_id,
            "query": request.query,
            "status": "queued",
        }
        supabase_client.get_admin_client().table("jobs").insert(job_data).execute()
    except Exception as e:
        logger.error(f"Failed to insert Brain job {brain_job_id} into DB: {e}")

    # Start background polling — does NOT block the server
    jobs_url = jobs_tpl.format(job_id=brain_job_id)
    background_tasks.add_task(_poll_brain_job, brain_job_id, jobs_url)

    return {
        "brain_job_id": brain_job_id,
        "status":       "accepted",
    }


# ── GET /api/v1/brain/status/{brain_job_id} — poll for result ────────────────

@router.get("/brain/status/{brain_job_id}")
async def get_brain_job_status(
    brain_job_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Poll for the result of a Brain job.
    Returns { status: 'polling'|'complete'|'failed', reply, artifact_ids, confidence }
    """
    job = _brain_jobs.get(brain_job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Brain job '{brain_job_id}' not found. It may have expired.")
    return job


# ── GET /api/v1/brain/artifacts/{artifact_path} — proxy artifact download ─────

@router.get("/brain/artifacts/{artifact_path:path}")
async def proxy_brain_artifact(
    artifact_path: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Proxy-download an artifact from the Brain server.
    artifact_path is the exact string from result.artifact_ids.
    """
    base       = _base_url(settings.ai_brain_url)
    # Do not strip leading slashes. The Brain expects the absolute path (e.g. /tmp/...) 
    # to be appended directly, resulting in .../api/v1/artifacts//tmp/...
    clean_path = artifact_path
    
    if clean_path.startswith("http://") or clean_path.startswith("https://"):
        remote_url = clean_path
    else:
        remote_url = f"{base}/api/v1/artifacts/{clean_path}"

    logger.info(f"Proxying Brain artifact: {remote_url}")

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(remote_url)

        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Brain returned HTTP {resp.status_code} for artifact.")

        filename, _ = artifact_path.split("/")[-1], None
        content_type, _ = mimetypes.guess_type(filename)
        content_type = content_type or "application/octet-stream"

        return StreamingResponse(
            content=iter([resp.content]),
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(resp.content)),
            },
        )
    except HTTPException:
        raise
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Cannot connect to Brain to download artifact.")
    except Exception as e:
        logger.error(f"Artifact proxy error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Artifact proxy error: {str(e)}")
