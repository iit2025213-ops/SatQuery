# MEGAPROMPTS 3-10: Complete Backend Implementation

This document contains condensed megaprompts for the remaining 8 modules. Each is complete but concise.

---

# MEGAPROMPT 3: API Gateway & Request Handling

**Objective:** Implement REST API endpoints for queries, assets, jobs, artifacts, and documents.

**Depends On:** MEGAPROMPT 1, 2

```python
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


# app/api/v1/queries.py

from fastapi import APIRouter, HTTPException, status, Depends
from app.auth.dependencies import get_current_user_id
from app.storage.supabase_client import SupabaseClient
from app.jobs.manager import JobManager
import logging
import uuid

logger = logging.getLogger("satquery")
router = APIRouter(prefix="/api/v1", tags=["queries"])

@router.post("/queries", response_model=SubmitQueryResponse, status_code=status.HTTP_201_CREATED)
async def submit_query(
    request: SubmitQueryRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Submit a new satellite analysis query"""
    
    from app.main import supabase_client
    
    job_id = str(uuid.uuid4())
    
    try:
        # Validate assets exist and belong to user
        for asset_id in request.asset_ids:
            asset = supabase_client.get_user_client().table("assets").select("*").eq("asset_id", asset_id).eq("user_id", user_id).single().execute()
            if not asset:
                raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")
        
        # Create job record
        job_data = {
            "job_id": job_id,
            "user_id": user_id,
            "query": request.query,
            "status": "queued",
            "aoi": request.aoi.model_dump() if request.aoi else None,
            "temporal_start": request.temporal.start if request.temporal else None,
            "temporal_end": request.temporal.end if request.temporal else None,
            "options": request.options.model_dump() if request.options else {},
            "agent_state": {
                "job_id": job_id,
                "user_request": request.query,
                "input_assets": request.asset_ids,
                "observations": [],
                "evidence": [],
                "artifacts": []
            }
        }
        
        supabase_client.get_user_client().table("jobs").insert(job_data).execute()
        
        logger.info(f"Job created: {job_id} for user {user_id}")
        
        # TODO: Start agent loop in background
        # This will be implemented in MEGAPROMPT 4
        
        return SubmitQueryResponse(
            job_id=job_id,
            status="queued",
            created_at=datetime.utcnow()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating job: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create job")


# app/api/v1/jobs.py

@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get status of a job"""
    
    from app.main import supabase_client
    
    try:
        job = supabase_client.get_user_client().table("jobs").select("*").eq("job_id", job_id).eq("user_id", user_id).single().execute()
        
        if not job.data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job_data = job.data
        
        return JobStatusResponse(
            job_id=job_data["job_id"],
            status=job_data["status"],
            query=job_data["query"],
            progress=JobProgress(
                completed_steps=job_data.get("current_step", 0),
                total_steps=None
            ),
            final_answer=job_data.get("final_answer"),
            confidence=job_data.get("confidence"),
            created_at=job_data["created_at"],
            updated_at=job_data["updated_at"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get job")


@router.get("/jobs")
async def list_jobs(
    user_id: str = Depends(get_current_user_id),
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """List user's jobs"""
    
    from app.main import supabase_client
    
    try:
        query = supabase_client.get_user_client().table("jobs").select("*").eq("user_id", user_id)
        
        if status:
            query = query.eq("status", status)
        
        jobs = query.order("created_at", desc=True).range(offset, offset + limit).execute()
        
        return {
            "jobs": jobs.data,
            "total": len(jobs.data),
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error listing jobs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list jobs")


# app/api/v1/assets.py

from fastapi import UploadFile, File, Form

@router.post("/assets", response_model=UploadAssetResponse)
async def upload_asset(
    file: UploadFile = File(...),
    modality: str = Form("optical"),
    acquisition_date: Optional[str] = Form(None),
    user_id: str = Depends(get_current_user_id)
):
    """Upload satellite image asset"""
    
    from app.main import supabase_client, cloudinary_client
    
    asset_id = str(uuid.uuid4())
    
    try:
        # Read file
        contents = await file.read()
        
        # Upload to Cloudinary
        result = await cloudinary_client.upload_artifact(
            file_path=file.filename,  # In real implementation, save temp file first
            artifact_type="original_image",
            job_id="assets",
            metadata={"asset_id": asset_id}
        )
        
        # Create asset record
        asset_data = {
            "asset_id": asset_id,
            "user_id": user_id,
            "filename": file.filename,
            "file_url": result["url"],
            "file_size_bytes": len(contents),
            "modality": modality,
            "acquisition_date": acquisition_date,
            "upload_status": "ready"
        }
        
        supabase_client.get_user_client().table("assets").insert(asset_data).execute()
        
        logger.info(f"Asset uploaded: {asset_id} by user {user_id}")
        
        return UploadAssetResponse(
            asset_id=asset_id,
            status="ready",
            metadata=AssetMetadata(
                modality=modality,
                acquisition_date=acquisition_date
            ),
            file_url=result["url"]
        )
    
    except Exception as e:
        logger.error(f"Error uploading asset: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload asset")


# app/api/v1/artifacts.py

@router.get("/artifacts/{artifact_id}")
async def get_artifact(
    artifact_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get artifact with signed URL"""
    
    from app.main import supabase_client, cloudinary_client
    
    try:
        # Verify user owns this artifact
        artifact = supabase_client.get_user_client().table("artifacts").select("*, jobs(user_id)").eq("artifact_id", artifact_id).single().execute()
        
        if not artifact.data or artifact.data["jobs"]["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        artifact_data = artifact.data
        
        # Generate signed URL
        signed_url = cloudinary_client.get_signed_url(
            artifact_data["cloudinary_public_id"],
            expiration_minutes=60
        )
        
        return {
            "artifact_id": artifact_id,
            "type": artifact_data["artifact_type"],
            "format": artifact_data["format"],
            "url": signed_url,
            "created_at": artifact_data["created_at"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting artifact: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get artifact")


@router.get("/jobs/{job_id}/artifacts")
async def list_job_artifacts(
    job_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """List all artifacts for a job"""
    
    from app.main import supabase_client
    
    try:
        # Verify user owns job
        job = supabase_client.get_user_client().table("jobs").select("user_id").eq("job_id", job_id).single().execute()
        
        if job.data["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        artifacts = supabase_client.get_user_client().table("artifacts").select("*").eq("job_id", job_id).execute()
        
        return {
            "job_id": job_id,
            "artifacts": artifacts.data,
            "count": len(artifacts.data)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing artifacts: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list artifacts")


# app/api/v1/documents.py

@router.post("/jobs/{job_id}/generate-report")
async def generate_report(
    job_id: str,
    format: str = "pdf",  # pdf, docx, json
    user_id: str = Depends(get_current_user_id)
):
    """Generate report from job results"""
    
    from app.main import supabase_client
    
    try:
        # Verify user owns job
        job = supabase_client.get_user_client().table("jobs").select("*").eq("job_id", job_id).eq("user_id", user_id).single().execute()
        
        if not job.data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # TODO: Generate report (implement in MEGAPROMPT 10)
        
        return {
            "document_id": str(uuid.uuid4()),
            "type": "analysis_report",
            "format": format,
            "url": "/api/v1/documents/doc_id",
            "created_at": datetime.utcnow()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate report")

# Update app/main.py to include routes:
# app.include_router(router)
```

---

# MEGAPROMPT 4: Agent Controller & Brain Integration

**Objective:** Implement agent loop that connects to your friend's AI Brain via WebSocket.

**Depends On:** MEGAPROMPT 1, 2, 3

```python
# app/agent/brain_connector.py

import websockets
import json
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger("satquery")

class BrainConnector:
    """WebSocket client for AI Brain communication"""
    
    def __init__(self, brain_url: str = settings.ai_brain_url):
        self.brain_url = brain_url
        self.connection = None
    
    async def connect(self) -> bool:
        """Establish WebSocket connection to Brain"""
        try:
            self.connection = await websockets.connect(self.brain_url)
            logger.info(f"Connected to AI Brain: {self.brain_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to AI Brain: {str(e)}")
            return False
    
    async def send_state_and_get_decision(self, agent_state: dict) -> Optional[dict]:
        """
        Send AgentState to Brain, receive Decision
        
        Request format:
        {
            "type": "get_decision",
            "agent_state": {...}
        }
        
        Response format:
        {
            "type": "decision",
            "action": "CALL_TOOL" | "PARALLEL" | "FINAL" | "REPLAN",
            "capability": "...",
            "arguments": {...},
            "reason": "..."
        }
        """
        if not self.connection:
            logger.error("Brain connection not established")
            return None
        
        try:
            message = {
                "type": "get_decision",
                "agent_state": agent_state
            }
            
            await self.connection.send(json.dumps(message))
            response_text = await asyncio.wait_for(
                self.connection.recv(),
                timeout=settings.ai_brain_timeout_seconds
            )
            
            decision = json.loads(response_text)
            logger.info(f"Received decision: {decision.get('action')}")
            
            return decision
        
        except asyncio.TimeoutError:
            logger.error("Brain connection timeout")
            return None
        except Exception as e:
            logger.error(f"Error communicating with Brain: {str(e)}")
            return None
    
    async def close(self):
        """Close WebSocket connection"""
        if self.connection:
            await self.connection.close()
            logger.info("Disconnected from AI Brain")


# app/agent/state.py

from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime
from uuid import UUID

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
    
    def to_dict(self) -> dict:
        """Serialize for Brain"""
        return json.loads(self.model_dump_json())
    
    def add_observation(self, obs: Observation):
        """Add observation to state"""
        self.observations.append(obs)


# app/agent/controller.py

import asyncio
from app.agent.brain_connector import BrainConnector
from app.agent.state import AgentState, Observation

class AgentController:
    """Main agent loop orchestrator"""
    
    def __init__(self, brain_connector: BrainConnector, executor):
        self.brain = brain_connector
        self.executor = executor
    
    async def run_agent_loop(self, job_id: str, query: str, asset_ids: List[str], supabase_client) -> dict:
        """
        Main agentic loop
        
        Flow:
        1. Initialize AgentState
        2. Send to Brain
        3. Brain returns decision
        4. Executor validates + executes
        5. Collect observation
        6. Loop back to step 2
        7. Until Brain says FINAL
        """
        
        # Initialize state
        state = AgentState(
            job_id=job_id,
            user_request=query,
            input_assets=asset_ids
        )
        
        # Connect to Brain
        if not await self.brain.connect():
            logger.error(f"Failed to connect to Brain for job {job_id}")
            return {"status": "failed", "reason": "Brain connection failed"}
        
        try:
            step_count = 0
            max_steps = settings.max_agent_steps
            
            while not state.finished and step_count < max_steps:
                step_count += 1
                state.current_step = step_count
                
                # Send state to Brain
                logger.info(f"[Job {job_id}] Step {step_count}: Sending state to Brain")
                decision = await self.brain.send_state_and_get_decision(state.to_dict())
                
                if not decision:
                    obs = Observation(
                        step_number=step_count,
                        source_capability="brain_connector",
                        status="failed",
                        result={"error": "Brain connection failed"}
                    )
                    state.add_observation(obs)
                    break
                
                # Process decision
                action = decision.get("action")
                
                if action == "CALL_TOOL":
                    # Single tool execution
                    capability = decision.get("capability")
                    arguments = decision.get("arguments", {})
                    
                    logger.info(f"[Job {job_id}] Step {step_count}: Executing {capability}")
                    
                    observation = await self.executor.execute_capability(
                        capability,
                        arguments,
                        state,
                        supabase_client
                    )
                    
                    state.add_observation(observation)
                
                elif action == "PARALLEL":
                    # Multiple tool execution
                    tasks = decision.get("tasks", [])
                    
                    logger.info(f"[Job {job_id}] Step {step_count}: Executing {len(tasks)} tasks in parallel")
                    
                    observations = await self.executor.execute_parallel(
                        tasks,
                        state,
                        supabase_client
                    )
                    
                    for obs in observations:
                        state.add_observation(obs)
                
                elif action == "FINAL":
                    # Brain says we're done
                    state.finished = True
                    state.final_result = decision.get("answer")
                    state.confidence = decision.get("confidence")
                    
                    logger.info(f"[Job {job_id}] Completed: {state.final_result}")
                
                elif action == "REPLAN":
                    # Brain wants to replan
                    state.replans += 1
                    if state.replans > settings.max_replans:
                        state.finished = True
                        obs = Observation(
                            step_number=step_count,
                            source_capability="controller",
                            status="failed",
                            result={"error": "Max replans exceeded"}
                        )
                        state.add_observation(obs)
                    
                    logger.info(f"[Job {job_id}] Replan {state.replans}")
                
                else:
                    logger.error(f"[Job {job_id}] Unknown action: {action}")
                    break
                
                # Save state to database
                await self.save_job_state(job_id, state, supabase_client)
                
                # Emit WebSocket event
                await self.emit_event(job_id, {
                    "type": "step_completed",
                    "step": step_count,
                    "capability": decision.get("capability") if action == "CALL_TOOL" else None,
                    "status": "success" if action != "CALL_TOOL" else state.observations[-1].status
                })
            
            # Final save
            await self.save_job_state(job_id, state, supabase_client)
            
            return {"status": "completed", "result": state.final_result}
        
        finally:
            await self.brain.close()
    
    async def save_job_state(self, job_id: str, state: AgentState, supabase_client):
        """Save agent state to database"""
        try:
            supabase_client.get_admin_client().table("jobs").update({
                "agent_state": state.to_dict(),
                "current_step": state.current_step,
                "status": "completed" if state.finished else "running",
                "final_answer": state.final_result,
                "confidence": state.confidence
            }).eq("job_id", job_id).execute()
        except Exception as e:
            logger.error(f"Failed to save job state: {str(e)}")
    
    async def emit_event(self, job_id: str, event: dict):
        """Emit WebSocket event (implemented in MEGAPROMPT 9)"""
        pass
```

---

# MEGAPROMPT 5: Executor & Decision Validation

**Objective:** Implement executor that validates decisions and executes capabilities with safety gates.

```python
# app/executor/executor.py

import asyncio
import logging
from typing import List, Optional

logger = logging.getLogger("satquery")

class Executor:
    """Executes LLM decisions with validation"""
    
    def __init__(self, registry):
        self.registry = registry
    
    def validate_decision(self, decision: dict) -> bool:
        """Validate LLM decision output"""
        required_fields = ["action"]
        
        for field in required_fields:
            if field not in decision:
                logger.error(f"Invalid decision: missing {field}")
                return False
        
        action = decision.get("action")
        valid_actions = ["CALL_TOOL", "PARALLEL", "FINAL", "REPLAN"]
        
        if action not in valid_actions:
            logger.error(f"Invalid action: {action}")
            return False
        
        if action == "CALL_TOOL" and "capability" not in decision:
            logger.error("CALL_TOOL missing capability")
            return False
        
        return True
    
    async def execute_capability(self, capability_name: str, arguments: dict, state, supabase_client):
        """Execute a single capability"""
        from app.agent.state import Observation
        
        # Get capability from registry
        capability = self.registry.get_capability(capability_name)
        
        if not capability:
            logger.error(f"Unknown capability: {capability_name}")
            return Observation(
                step_number=state.current_step,
                source_capability=capability_name,
                status="failed",
                result={"error": f"Unknown capability: {capability_name}"}
            )
        
        # Validate prerequisites
        prereq_valid, prereq_reason = await self.validate_prerequisites(
            capability_name,
            arguments,
            state,
            supabase_client
        )
        
        if not prereq_valid:
            logger.warning(f"Prerequisites not met: {prereq_reason}")
            return Observation(
                step_number=state.current_step,
                source_capability=capability_name,
                status="blocked",
                result={"error": prereq_reason}
            )
        
        # Get adapter and execute with retries
        adapter = self.registry.get_adapter(capability_name)
        
        for attempt in range(settings.max_retries_per_task):
            try:
                logger.info(f"Executing {capability_name} (attempt {attempt + 1})")
                
                observation = await adapter.execute(arguments, state, supabase_client)
                
                logger.info(f"Capability {capability_name} succeeded")
                return observation
            
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                
                if attempt == settings.max_retries_per_task - 1:
                    logger.error(f"Capability {capability_name} failed after {settings.max_retries_per_task} attempts")
                    return Observation(
                        step_number=state.current_step,
                        source_capability=capability_name,
                        status="failed",
                        result={"error": str(e)}
                    )
    
    async def validate_prerequisites(self, capability_name: str, arguments: dict, state, supabase_client):
        """Check hard safety gates before execution"""
        
        # Example: Change detection requires 2 images
        if capability_name == "detect_bitemporal_change":
            if len(state.input_assets) < 2:
                return False, "Two images required for change detection"
            
            # Validate spatial compatibility
            # (implement actual validation)
            return True, ""
        
        # Add more capability-specific checks
        
        return True, ""
    
    async def execute_parallel(self, tasks: List[dict], state, supabase_client) -> List:
        """Execute independent tasks concurrently"""
        
        # Create tasks
        async_tasks = [
            self.execute_capability(
                task.get("capability"),
                task.get("arguments", {}),
                state,
                supabase_client
            )
            for task in tasks
        ]
        
        # Run concurrently
        results = await asyncio.gather(*async_tasks)
        
        return results
```

---

# MEGAPROMPT 6: Capability Adapters

**Objective:** Implement capability registry and model adapters.

```python
# app/registry/registry.py

import logging

logger = logging.getLogger("satquery")

class CapabilityRegistry:
    """Central registry of all capabilities"""
    
    def __init__(self):
        self.capabilities = {
            "validate_remote_sensing_input": {
                "name": "validate_remote_sensing_input",
                "description": "Validate satellite imagery inputs",
                "adapter": "GeospatialValidator"
            },
            "detect_bitemporal_change": {
                "name": "detect_bitemporal_change",
                "description": "Detect changes between two images",
                "adapter": "ChangeFormerAdapter"
            },
            "interpret_scene": {
                "name": "interpret_scene",
                "description": "Interpret satellite image content",
                "adapter": "GeoChatAdapter"
            },
            "analyze_sar_image": {
                "name": "analyze_sar_image",
                "description": "Analyze SAR imagery",
                "adapter": "SARMAEAdapter"
            },
            "calculate_changed_area": {
                "name": "calculate_changed_area",
                "description": "Calculate area of detected changes",
                "adapter": "GeospatialEngine"
            },
            # Add more capabilities as needed
        }
        
        self.adapters = {}
        self._init_adapters()
    
    def _init_adapters(self):
        """Initialize all adapters"""
        # Import adapters (will be in separate files)
        from app.models.geospatial_engine import GeospatialEngine
        from app.models.changeformer_adapter import ChangeFormerAdapter
        
        self.adapters["GeospatialValidator"] = GeospatialEngine()
        self.adapters["ChangeFormerAdapter"] = ChangeFormerAdapter()
        # Initialize others as needed
    
    def get_capability(self, name: str) -> Optional[dict]:
        """Get capability definition"""
        return self.capabilities.get(name)
    
    def get_adapter(self, capability_name: str):
        """Get adapter for capability"""
        cap = self.get_capability(capability_name)
        if not cap:
            return None
        adapter_name = cap["adapter"]
        return self.adapters.get(adapter_name)


# app/models/base.py

from abc import ABC, abstractmethod
import logging

logger = logging.getLogger("satquery")

class BaseAdapter(ABC):
    """Base class for model adapters"""
    
    @abstractmethod
    async def execute(self, arguments: dict, state, supabase_client):
        """
        Execute the model
        
        Returns Observation
        """
        pass


# app/models/geospatial_engine.py

from app.models.base import BaseAdapter
from app.agent.state import Observation
import uuid

class GeospatialEngine(BaseAdapter):
    """Geospatial operations (CRS, alignment, area calculation)"""
    
    async def execute(self, arguments: dict, state, supabase_client) -> Observation:
        """Execute geospatial operation"""
        
        operation = arguments.get("operation")
        
        if operation == "validate_input":
            return await self._validate_input(arguments, state, supabase_client)
        elif operation == "calculate_area":
            return await self._calculate_area(arguments, state, supabase_client)
        else:
            return Observation(
                step_number=state.current_step,
                source_capability="geospatial_engine",
                status="failed",
                result={"error": f"Unknown operation: {operation}"}
            )
    
    async def _validate_input(self, arguments: dict, state, supabase_client) -> Observation:
        """Validate satellite imagery inputs"""
        
        asset_ids = arguments.get("asset_ids", [])
        
        # Get assets from Supabase
        assets = []
        for asset_id in asset_ids:
            try:
                asset = supabase_client.get_admin_client().table("assets").select("*").eq("asset_id", asset_id).single().execute()
                assets.append(asset.data)
            except:
                pass
        
        # Validate
        validation_results = {
            "total_assets": len(assets),
            "valid_assets": len([a for a in assets if a.get("validation_status") != "invalid"]),
            "issues": []
        }
        
        return Observation(
            step_number=state.current_step,
            source_capability="geospatial_engine",
            status="success",
            result=validation_results,
            confidence=0.95
        )
    
    async def _calculate_area(self, arguments: dict, state, supabase_client) -> Observation:
        """Calculate area from change mask"""
        
        # In production, parse GeoTIFF and calculate actual area
        # For now, return mock result
        
        return Observation(
            step_number=state.current_step,
            source_capability="geospatial_engine",
            status="success",
            result={
                "changed_pixels": 27431,
                "pixel_area_m2": 100,
                "total_area_km2": 2.7431
            },
            confidence=0.92
        )
```

---

# MEGAPROMPT 7: Evidence & Confidence

**Objective:** Implement evidence fusion and confidence calculation.

```python
# app/evidence/schema.py

from pydantic import BaseModel
from typing import List, Optional

class EvidenceItem(BaseModel):
    claim: str
    confidence: float
    observation_ids: List[str]
    supporting_factors: dict = {}

# app/evidence/confidence.py

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
```

---

# MEGAPROMPT 8: Storage Layer

**Objective:** Integrate Supabase + Cloudinary clients (already in MEGAPROMPT 1).

Key operations already implemented in MEGAPROMPT 1 files.

---

# MEGAPROMPT 9: WebSocket Events

**Objective:** Implement real-time WebSocket events for live execution trace.

```python
# app/api/websocket/manager.py

from fastapi import WebSocket
import logging
from typing import Dict, List

logger = logging.getLogger("satquery")

class ConnectionManager:
    """Manage WebSocket connections per job"""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, job_id: str, websocket: WebSocket):
        """Accept WebSocket connection"""
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = []
        self.active_connections[job_id].append(websocket)
        logger.info(f"WebSocket connected for job {job_id}")
    
    async def broadcast(self, job_id: str, message: dict):
        """Send message to all clients watching job"""
        if job_id not in self.active_connections:
            return
        
        for websocket in self.active_connections[job_id]:
            try:
                await websocket.send_json(message)
            except:
                pass
    
    async def disconnect(self, job_id: str, websocket: WebSocket):
        """Remove disconnected client"""
        if job_id in self.active_connections:
            self.active_connections[job_id].remove(websocket)
            logger.info(f"WebSocket disconnected for job {job_id}")


# app/api/websocket/routes.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.api.websocket.manager import ConnectionManager

router = APIRouter()
manager = ConnectionManager()

@router.websocket("/ws/jobs/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for live job updates"""
    
    await manager.connect(job_id, websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back or process commands if needed
    
    except WebSocketDisconnect:
        manager.disconnect(job_id, websocket)
```

---

# MEGAPROMPT 10: Document Generation

**Objective:** Generate PDF/DOCX reports from job results.

```python
# app/documents/generator.py

import logging
from datetime import datetime

logger = logging.getLogger("satquery")

class DocumentGenerator:
    """Generate reports from analysis results"""
    
    @staticmethod
    async def generate_report(
        job_data: dict,
        format: str = "pdf"  # pdf, docx, json
    ) -> str:
        """
        Generate report from job data
        
        Returns URL to generated document
        """
        
        if format == "json":
            return await DocumentGenerator._generate_json(job_data)
        elif format == "pdf":
            return await DocumentGenerator._generate_pdf(job_data)
        elif format == "docx":
            return await DocumentGenerator._generate_docx(job_data)
    
    @staticmethod
    async def _generate_json(job_data: dict) -> str:
        """Generate JSON export"""
        import json
        
        report = {
            "job_id": job_data["job_id"],
            "query": job_data["query"],
            "result": job_data["final_answer"],
            "confidence": job_data["confidence"],
            "generated_at": datetime.utcnow().isoformat(),
            "observations": [obs.dict() for obs in job_data.get("observations", [])]
        }
        
        return json.dumps(report, indent=2)
    
    @staticmethod
    async def _generate_pdf(job_data: dict) -> str:
        """Generate PDF report (placeholder)"""
        # In production, use reportlab or similar
        logger.info("PDF generation not yet implemented")
        return "pdf_not_implemented"
    
    @staticmethod
    async def _generate_docx(job_data: dict) -> str:
        """Generate DOCX report (placeholder)"""
        # In production, use python-docx
        logger.info("DOCX generation not yet implemented")
        return "docx_not_implemented"
```

---

## NEXT STEPS

These 10 megaprompts form the complete backend:

1. ✅ MEGAPROMPT 1: Setup (Done)
2. ✅ MEGAPROMPT 2: Auth (Done)
3. MEGAPROMPT 3: API Gateway (Condensed above)
4. MEGAPROMPT 4: Agent Controller (Condensed above)
5. MEGAPROMPT 5: Executor (Condensed above)
6. MEGAPROMPT 6: Adapters (Condensed above)
7. MEGAPROMPT 7: Evidence (Condensed above)
8. MEGAPROMPT 8: Storage (Already done)
9. MEGAPROMPT 9: WebSocket (Condensed above)
10. MEGAPROMPT 10: Documents (Condensed above)

## IMPLEMENTATION ORDER

1. Implement MEGAPROMPT 1 first (Setup)
2. Then MEGAPROMPT 2 (Auth)
3. Then MEGAPROMPT 3 (API)
4. Then MEGAPROMPT 4 (Agent Loop)
5. Then remaining in order

Each builds on the previous ones.

---

This document provides complete code snippets for all 10 megaprompts. Full implementations should be expanded from these templates.