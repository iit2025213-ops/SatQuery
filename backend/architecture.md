# SATQUERY AI - COMPLETE BACKEND ARCHITECTURE
## Design & Review Document

---

## EXECUTIVE SUMMARY

This backend is designed around:
- **Modular separation of concerns** (API, Agent, Executor, Models)
- **WebSocket integration** with your friend's AI Brain (not mocked)
- **Supabase** as primary database (PostgreSQL + Auth)
- **Cloudinary** for asset/artifact storage
- **JWT-based authentication** 
- **Render** deployment-ready
- **Zero hardcoded model routing**

---

## 1. TECHNOLOGY STACK

```
Backend Framework:     FastAPI (async/await)
Database:             Supabase (PostgreSQL)
Authentication:       Supabase Auth + JWT
Asset Storage:        Cloudinary
Real-time Events:     WebSockets + SSE hybrid
AI Brain:             WebSocket client (external)
Job Queue:            Redis (optional, via Render)
Deployment:           Render.com
Python Version:       3.11+
```

---

## 2. DIRECTORY STRUCTURE

```
satquery-backend/
│
├── app/
│   ├── __init__.py
│   ├── main.py                           # FastAPI app initialization
│   ├── config.py                         # Environment & configuration
│   │
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── schemas.py                    # Pydantic models
│   │   ├── jwt_handler.py                # JWT token logic
│   │   ├── dependencies.py               # Auth dependencies
│   │   └── routes.py                     # Auth endpoints
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py                     # Main API routes
│   │   ├── schemas.py                    # Request/response models
│   │   ├── dependencies.py               # Dependency injection
│   │   │
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── queries.py               # Query endpoints
│   │   │   ├── assets.py                # Asset upload endpoints
│   │   │   ├── jobs.py                  # Job status endpoints
│   │   │   ├── artifacts.py             # Artifact retrieval
│   │   │   └── documents.py             # Document generation
│   │   │
│   │   └── websocket/
│   │       ├── __init__.py
│   │       ├── manager.py               # WebSocket connection manager
│   │       ├── events.py                # Event schemas
│   │       └── handlers.py              # Event handlers
│   │
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── controller.py                # Agent main loop
│   │   ├── state.py                     # AgentState model
│   │   ├── decision.py                  # Decision schema
│   │   ├── context.py                   # Context management
│   │   └── brain_connector.py          # AI Brain WebSocket client
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py                      # Abstract LLM provider
│   │   ├── openai_provider.py           # OpenAI implementation
│   │   ├── config.py                    # LLM configuration
│   │   └── mock.py                      # Mock for testing (optional)
│   │
│   ├── registry/
│   │   ├── __init__.py
│   │   ├── capability_registry.py       # Capability definitions
│   │   ├── prerequisites.py             # Prerequisite validators
│   │   └── capabilities.json            # Capability definitions
│   │
│   ├── executor/
│   │   ├── __init__.py
│   │   ├── executor.py                  # Main executor
│   │   ├── parallel.py                  # Parallel task runner
│   │   ├── decision_validator.py        # Decision validation
│   │   └── retry_handler.py             # Retry logic
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py                      # Base adapter class
│   │   ├── geochat_adapter.py          # GeoChat wrapper
│   │   ├── changeformer_adapter.py     # ChangeFormer wrapper
│   │   ├── sarmae_adapter.py           # SARMAE wrapper
│   │   ├── prithvi_adapter.py          # Prithvi wrapper
│   │   ├── skysense_adapter.py         # SkySense wrapper
│   │   └── geospatial_engine.py        # Geospatial tools
│   │
│   ├── evidence/
│   │   ├── __init__.py
│   │   ├── schema.py                    # Observation/Evidence models
│   │   ├── fusion.py                    # Evidence fusion logic
│   │   └── confidence.py                # Confidence calculation
│   │
│   ├── critic/
│   │   ├── __init__.py
│   │   └── verifier.py                  # Verification logic
│   │
│   ├── documents/
│   │   ├── __init__.py
│   │   ├── generator.py                 # Document generation
│   │   ├── templates/                   # Report templates
│   │   │   ├── change_report.html
│   │   │   └── analysis_report.html
│   │   └── exporters.py                 # PDF/DOCX exporters
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── supabase_client.py          # Supabase wrapper
│   │   ├── cloudinary_client.py        # Cloudinary wrapper
│   │   ├── assets.py                   # Asset management
│   │   └── artifacts.py                # Artifact management
│   │
│   ├── jobs/
│   │   ├── __init__.py
│   │   ├── manager.py                  # Job state management
│   │   ├── models.py                   # Job data models
│   │   └── events.py                   # Job event emitter
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py                   # Logging setup
│   │   ├── error_handlers.py           # Global error handlers
│   │   ├── validators.py               # Data validators
│   │   └── geospatial.py               # Geo utilities
│   │
│   └── middleware/
│       ├── __init__.py
│       ├── cors.py
│       ├── error_handling.py
│       └── request_logging.py
│
├── migrations/
│   └── supabase_init.sql               # Database schema
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_queries.py
│   ├── test_agent.py
│   └── test_assets.py
│
├── .env.example
├── .env                                 # (gitignored)
├── requirements.txt
├── docker-compose.yml                   # For local development
├── Dockerfile
├── render.yaml                          # Render deployment config
└── README.md
```

---

## 3. CORE DATA MODELS (SUPABASE SCHEMA)

### 3.1 Users Table
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email VARCHAR(255) UNIQUE NOT NULL,
  display_name VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  CONSTRAINT fk_auth_users FOREIGN KEY (id) 
    REFERENCES auth.users(id) ON DELETE CASCADE
);

CREATE INDEX idx_users_email ON users(email);
```

### 3.2 Jobs Table
```sql
CREATE TABLE jobs (
  job_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  
  -- Request metadata
  query TEXT NOT NULL,
  status VARCHAR(50) DEFAULT 'queued', -- queued, running, waiting_for_input, completed, partial, failed, cancelled
  
  -- Spatial/Temporal info
  aoi JSONB,  -- GeoJSON polygon
  temporal_start DATE,
  temporal_end DATE,
  
  -- State
  agent_state JSONB,  -- Complete AgentState snapshot
  current_step INTEGER DEFAULT 0,
  
  -- Results
  final_answer TEXT,
  confidence FLOAT8,
  
  -- Config
  options JSONB,  -- generate_artifacts, generate_report, etc
  
  -- Tracking
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  CONSTRAINT status_check CHECK (status IN ('queued', 'running', 'waiting_for_input', 'waiting_for_resource', 'completed', 'partial', 'failed', 'cancelled'))
);

CREATE INDEX idx_jobs_user_id ON jobs(user_id);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_created_at ON jobs(created_at);
```

### 3.3 Assets Table
```sql
CREATE TABLE assets (
  asset_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  job_id UUID REFERENCES jobs(job_id),
  
  -- File info
  filename VARCHAR(255),
  file_url TEXT,  -- Cloudinary URL
  file_size_bytes BIGINT,
  
  -- Geospatial metadata
  modality VARCHAR(50),  -- optical, sar, thermal, etc
  asset_type VARCHAR(50) DEFAULT 'raster',  -- raster, vector
  acquisition_date DATE,
  
  -- CRS & spatial info
  crs VARCHAR(20),  -- EPSG:xxxxx
  width INTEGER,
  height INTEGER,
  resolution FLOAT8[],  -- [pixel_width, pixel_height]
  bbox JSONB,  -- [minx, miny, maxx, maxy]
  
  -- Bands
  bands JSONB,  -- ["B02", "B03", "B04", "B08"]
  
  -- Status
  upload_status VARCHAR(50) DEFAULT 'uploading',  -- uploading, ready, failed
  validation_status VARCHAR(50),  -- valid, invalid, pending
  
  -- Metadata (raw, unvalidated)
  raw_metadata JSONB,
  
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_assets_user_id ON assets(user_id);
CREATE INDEX idx_assets_job_id ON assets(job_id);
CREATE INDEX idx_assets_status ON assets(upload_status);
```

### 3.4 Observations Table
```sql
CREATE TABLE observations (
  observation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  job_id UUID NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
  
  -- Metadata
  step_number INTEGER,
  source_capability VARCHAR(100),
  source_backend VARCHAR(100),  -- geochat, changeformer, etc
  source_version VARCHAR(50),
  
  -- Observation data
  status VARCHAR(50),  -- success, failed, blocked, etc
  result JSONB,  -- Raw model output
  
  -- Spatial/Temporal
  bbox JSONB,
  crs VARCHAR(20),
  temporal_before DATE,
  temporal_after DATE,
  
  -- Confidence & validation
  confidence FLOAT8,
  validation_errors JSONB,
  
  -- References
  artifact_ids UUID[],  -- References to artifacts
  
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_observations_job_id ON observations(job_id);
CREATE INDEX idx_observations_capability ON observations(source_capability);
```

### 3.5 Artifacts Table
```sql
CREATE TABLE artifacts (
  artifact_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  job_id UUID NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
  
  -- Type & format
  artifact_type VARCHAR(50),  -- change_mask, change_map, geojson, etc
  format VARCHAR(20),  -- GeoTIFF, PNG, JSON, etc
  
  -- Storage
  cloudinary_url TEXT,
  cloudinary_public_id VARCHAR(255),
  file_size_bytes BIGINT,
  
  -- Metadata
  description TEXT,
  metadata JSONB,
  
  -- Provenance
  source_observation_id UUID REFERENCES observations(observation_id),
  created_by_capability VARCHAR(100),
  
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_artifacts_job_id ON artifacts(job_id);
CREATE INDEX idx_artifacts_type ON artifacts(artifact_type);
```

### 3.6 Evidence Table
```sql
CREATE TABLE evidence (
  evidence_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  job_id UUID NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
  
  -- Claim
  claim TEXT,
  claim_type VARCHAR(50),  -- quantitative, qualitative, etc
  
  -- Supporting evidence
  observation_ids UUID[],  -- References to observations
  artifact_ids UUID[],
  
  -- Strength
  confidence FLOAT8,
  supporting_factors JSONB,
  
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_evidence_job_id ON evidence(job_id);
```

### 3.7 Documents Table
```sql
CREATE TABLE documents (
  document_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  job_id UUID NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
  
  -- Type & format
  doc_type VARCHAR(50),  -- analysis_report, change_report, etc
  format VARCHAR(20),  -- PDF, DOCX, JSON, etc
  
  -- Storage
  cloudinary_url TEXT,
  cloudinary_public_id VARCHAR(255),
  
  -- Content reference
  source_observations JSONB,
  generated_from_result JSONB,
  
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_documents_job_id ON documents(job_id);
```

### 3.8 API Audit Log
```sql
CREATE TABLE audit_logs (
  log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id),
  job_id UUID REFERENCES jobs(job_id),
  
  action VARCHAR(100),
  endpoint VARCHAR(255),
  method VARCHAR(10),
  status_code INTEGER,
  
  request_body JSONB,
  response_body JSONB,
  
  ip_address INET,
  user_agent TEXT,
  
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
```

---

## 4. AUTHENTICATION FLOW (JWT + Supabase)

### 4.1 Auth Architecture

```
Frontend (Login)
    ↓
Supabase Auth API
    ↓
JWT Token (access + refresh)
    ↓
Backend API (Protected Routes)
    ↓
JWT Verification
    ↓
User Context
```

### 4.2 Auth Endpoints

```
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/logout
POST   /api/v1/auth/refresh
GET    /api/v1/auth/me
POST   /api/v1/auth/verify-email
POST   /api/v1/auth/reset-password
```

### 4.3 JWT Structure

**Access Token** (15 minutes):
```json
{
  "sub": "user_uuid",
  "email": "user@example.com",
  "iat": 1234567890,
  "exp": 1234568790,
  "type": "access"
}
```

**Refresh Token** (7 days):
```json
{
  "sub": "user_uuid",
  "type": "refresh",
  "iat": 1234567890,
  "exp": 1234567890 + 604800
}
```

---

## 5. API ENDPOINTS (COMPLETE)

### 5.1 Auth Endpoints

```python
# app/api/v1/auth/routes.py

POST   /api/v1/auth/register
       Body: { email, password, display_name }
       Response: { access_token, refresh_token, user }

POST   /api/v1/auth/login
       Body: { email, password }
       Response: { access_token, refresh_token, user }

POST   /api/v1/auth/refresh
       Body: { refresh_token }
       Response: { access_token, refresh_token }

GET    /api/v1/auth/me
       Headers: Authorization: Bearer {token}
       Response: { user }

POST   /api/v1/auth/logout
       Response: { message: "Logged out" }
```

### 5.2 Asset Endpoints

```python
# app/api/v1/assets.py

POST   /api/v1/assets
       Headers: Authorization, Content-Type: multipart/form-data
       Body: file, modality, acquisition_date (optional), metadata
       Response: { asset_id, status, metadata }

GET    /api/v1/assets/{asset_id}
       Response: { asset }

GET    /api/v1/assets
       Query: user_id, job_id, status
       Response: { assets[] }

DELETE /api/v1/assets/{asset_id}
       Response: { message: "Deleted" }
```

### 5.3 Query/Job Endpoints

```python
# app/api/v1/queries.py & jobs.py

POST   /api/v1/queries
       Body: {
         query, 
         asset_ids[], 
         aoi, 
         temporal: {start, end}, 
         options
       }
       Response: { job_id, status }

GET    /api/v1/jobs/{job_id}
       Response: { job, status, current_step, progress }

GET    /api/v1/jobs
       Query: status, user_id
       Response: { jobs[] }

GET    /api/v1/jobs/{job_id}/events
       Response: Server-Sent Events (or WebSocket)

POST   /api/v1/jobs/{job_id}/cancel
       Response: { status: "cancelled" }

GET    /api/v1/jobs/{job_id}/evidence
       Response: { evidence[], observations[] }
```

### 5.4 Artifact Endpoints

```python
# app/api/v1/artifacts.py

GET    /api/v1/artifacts/{artifact_id}
       Response: artifact metadata + signed Cloudinary URL

GET    /api/v1/jobs/{job_id}/artifacts
       Response: { artifacts[] }

DELETE /api/v1/artifacts/{artifact_id}
       Response: { message: "Deleted" }
```

### 5.5 Document Endpoints

```python
# app/api/v1/documents.py

POST   /api/v1/jobs/{job_id}/generate-report
       Body: { format: "pdf" | "docx" | "json" }
       Response: { document_id, url }

GET    /api/v1/jobs/{job_id}/documents
       Response: { documents[] }

GET    /api/v1/documents/{document_id}
       Response: signed Cloudinary URL
```

---

## 6. WEBSOCKET ARCHITECTURE

### 6.1 WebSocket Connection Flow

```
Frontend
   │
   └─ WebSocket: /ws/jobs/{job_id}
      │
      Backend Connection Manager
      │
      ├─ Stores connection
      ├─ Listens for job events
      └─ Broadcasts to frontend in real-time
```

### 6.2 WebSocket Events Schema

**Step Completed Event:**
```json
{
  "type": "step_completed",
  "job_id": "job_123",
  "step": 3,
  "capability": "detect_bitemporal_change",
  "backend": "changeformer",
  "status": "success",
  "latency_ms": 8420,
  "timestamp": "2024-01-15T10:30:45Z"
}
```

**Observation Created:**
```json
{
  "type": "observation_created",
  "job_id": "job_123",
  "observation_id": "obs_004",
  "step": 4,
  "capability": "detect_bitemporal_change",
  "result_summary": "Detected 27,431 changed pixels",
  "confidence": 0.87
}
```

**Waiting for Input:**
```json
{
  "type": "waiting_for_input",
  "job_id": "job_123",
  "question": "Please provide a second image or specify the comparison date."
}
```

**Job Completed:**
```json
{
  "type": "job_completed",
  "job_id": "job_123",
  "status": "completed",
  "answer": "approximately 2.74 km²",
  "confidence": 0.91
}
```

**Error Event:**
```json
{
  "type": "error",
  "job_id": "job_123",
  "step": 5,
  "error_message": "ChangeFormer inference timeout",
  "status": "failed"
}
```

### 6.3 WebSocket Manager (Connection Management)

```python
# app/api/websocket/manager.py

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        
    async def connect(self, job_id: str, websocket: WebSocket):
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = []
        self.active_connections[job_id].append(websocket)
    
    async def broadcast(self, job_id: str, message: dict):
        """Send event to all clients watching this job"""
        if job_id in self.active_connections:
            for connection in self.active_connections[job_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    # Handle disconnected client
                    pass
    
    async def disconnect(self, job_id: str, websocket: WebSocket):
        self.active_connections[job_id].remove(websocket)
```

---

## 7. AGENT CONTROLLER & AI BRAIN INTEGRATION

### 7.1 Brain Connector (WebSocket Client)

```python
# app/agent/brain_connector.py

class BrainConnector:
    """Client to communicate with your friend's AI Brain via WebSocket"""
    
    def __init__(self, brain_url: str):
        self.brain_url = brain_url  # e.g., ws://friend-server:8000/brain
        self.connection = None
    
    async def connect(self):
        """Establish WebSocket connection to AI Brain"""
        self.connection = await websockets.connect(self.brain_url)
    
    async def send_state_and_get_decision(self, agent_state: AgentState):
        """
        Send AgentState to Brain, get back decision.
        
        Brain receives:
        {
          "type": "get_decision",
          "agent_state": {...full AgentState...}
        }
        
        Brain responds:
        {
          "type": "decision",
          "action": "CALL_TOOL" | "PARALLEL" | "FINAL" | "REPLAN",
          "capability": "validate_remote_sensing_input",
          "arguments": {...},
          "reason": "..."
        }
        """
        message = {
            "type": "get_decision",
            "agent_state": agent_state.to_dict()
        }
        
        await self.connection.send(json.dumps(message))
        response = await self.connection.recv()
        decision = Decision(**json.loads(response))
        
        return decision
    
    async def close(self):
        if self.connection:
            await self.connection.close()
```

### 7.2 Agent Controller Main Loop

```python
# app/agent/controller.py

class AgentController:
    def __init__(self, brain_connector: BrainConnector, executor: Executor):
        self.brain = brain_connector
        self.executor = executor
    
    async def run_agent_loop(self, job_id: str, initial_request: str, assets: List[Asset]):
        """
        Main agentic loop: Brain → Decision → Execution → Observation → Brain
        """
        
        # Initialize state
        state = AgentState(
            job_id=job_id,
            user_request=initial_request,
            input_assets=assets,
            current_goal=initial_request
        )
        
        step_count = 0
        max_steps = 20
        
        while not state.finished and step_count < max_steps:
            step_count += 1
            state.current_step = step_count
            
            # Send state to brain, get decision
            decision = await self.brain.send_state_and_get_decision(state)
            
            # Validate decision
            try:
                self.executor.validate_decision(decision, state)
            except ValidationError as e:
                state.add_observation(Observation(
                    status="validation_failed",
                    reason=str(e)
                ))
                continue
            
            # Execute decision
            if decision.action == "CALL_TOOL":
                observation = await self.executor.execute_capability(
                    decision.capability,
                    decision.arguments,
                    state
                )
                state.add_observation(observation)
                
            elif decision.action == "PARALLEL":
                observations = await self.executor.execute_parallel(
                    decision.tasks,
                    state
                )
                state.add_observations(observations)
            
            elif decision.action == "FINAL":
                state.finished = True
                state.final_result = decision.get("final_answer")
            
            # Broadcast progress via WebSocket
            await self.emit_progress_event(job_id, step_count, decision)
        
        # Save final state to database
        await self.save_job_result(job_id, state)
        return state

    async def emit_progress_event(self, job_id: str, step: int, decision: Decision):
        """Send real-time update via WebSocket to frontend"""
        event = {
            "type": "step_completed",
            "job_id": job_id,
            "step": step,
            "capability": decision.capability,
            "status": "running"
        }
        await self.ws_manager.broadcast(job_id, event)
```

### 7.3 Agent State Model

```python
# app/agent/state.py

from typing import List, Optional
from datetime import datetime

class AgentState(BaseModel):
    """Complete state maintained throughout agent execution"""
    
    job_id: UUID
    user_request: str
    input_assets: List[Asset]
    
    current_goal: str
    current_step: int = 0
    
    observations: List[Observation] = []
    evidence: List[Evidence] = []
    executed_tasks: List[dict] = []
    failed_tasks: List[dict] = []
    
    artifacts: List[Artifact] = []
    
    confidence: Optional[float] = None
    final_result: Optional[str] = None
    
    finished: bool = False
    replans: int = 0
    retries: int = 0
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        """Serialize for sending to AI Brain"""
        return self.model_dump(mode='json')
    
    def add_observation(self, obs: Observation):
        self.observations.append(obs)
        # Automatically emit event
```

---

## 8. EXECUTOR ARCHITECTURE

### 8.1 Executor Core

```python
# app/executor/executor.py

class Executor:
    """Validates and executes LLM decisions"""
    
    def __init__(self, registry: CapabilityRegistry):
        self.registry = registry
    
    def validate_decision(self, decision: Decision, state: AgentState):
        """Validate LLM output before execution"""
        # Check action is valid
        assert decision.action in ["CALL_TOOL", "PARALLEL", "FINAL", "REPLAN"]
        
        # Check capability exists
        if decision.action == "CALL_TOOL":
            capability = self.registry.get_capability(decision.capability)
            if not capability:
                raise ValueError(f"Unknown capability: {decision.capability}")
    
    async def execute_capability(self, capability_name: str, args: dict, state: AgentState):
        """Execute a single capability"""
        
        capability = self.registry.get_capability(capability_name)
        
        # Check prerequisites
        prereq_check = await self.validate_prerequisites(capability, args, state)
        if not prereq_check.valid:
            return Observation(
                status="blocked",
                reason=prereq_check.reason
            )
        
        # Get adapter
        adapter = self.registry.get_adapter(capability_name)
        
        # Execute with retry logic
        observation = None
        for attempt in range(3):  # 3 retries
            try:
                observation = await adapter.execute(args, state)
                break
            except Exception as e:
                if attempt == 2:
                    return Observation(
                        status="failed",
                        reason=str(e)
                    )
        
        return observation
    
    async def validate_prerequisites(self, capability, args, state) -> PrerequisiteCheckResult:
        """Hard safety gates before model execution"""
        
        # Example for change detection
        if capability.name == "detect_bitemporal_change":
            # Check two compatible assets exist
            if len(state.input_assets) < 2:
                return PrerequisiteCheckResult(
                    valid=False,
                    reason="Two images required for change detection"
                )
            
            # Check spatial alignment
            align_check = await self.check_spatial_alignment(
                state.input_assets[0],
                state.input_assets[1]
            )
            if not align_check:
                return PrerequisiteCheckResult(
                    valid=False,
                    reason="Images not spatially aligned"
                )
        
        return PrerequisiteCheckResult(valid=True)
    
    async def execute_parallel(self, tasks: List[dict], state: AgentState):
        """Execute independent tasks concurrently"""
        
        results = await asyncio.gather(*[
            self.execute_capability(
                task["capability"],
                task["arguments"],
                state
            )
            for task in tasks
        ])
        
        return results
```

### 8.2 Capability Registry

```python
# app/registry/capability_registry.py

class CapabilityRegistry:
    """Central registry mapping capabilities to adapters"""
    
    def __init__(self):
        self.capabilities = {
            "validate_remote_sensing_input": CapabilityDef(
                name="validate_remote_sensing_input",
                adapter_class=GeospatialValidator,
                required_args=["asset_ids"]
            ),
            "detect_bitemporal_change": CapabilityDef(
                name="detect_bitemporal_change",
                adapter_class=ChangeFormerAdapter,
                required_args=["asset_id_t1", "asset_id_t2"]
            ),
            "interpret_scene": CapabilityDef(
                name="interpret_scene",
                adapter_class=GeoChatAdapter,
                required_args=["asset_id"]
            ),
            "analyze_sar_image": CapabilityDef(
                name="analyze_sar_image",
                adapter_class=SARMAEAdapter,
                required_args=["asset_id"]
            ),
            "calculate_changed_area": CapabilityDef(
                name="calculate_changed_area",
                adapter_class=GeospatialEngine,
                required_args=["change_mask"]
            ),
            # Add more capabilities...
        }
        
        # Initialize adapters
        self.adapters = {}
        for name, capability in self.capabilities.items():
            self.adapters[name] = capability.adapter_class()
    
    def get_capability(self, name: str) -> Optional[CapabilityDef]:
        return self.capabilities.get(name)
    
    def get_adapter(self, name: str):
        return self.adapters.get(name)
```

---

## 9. CONFIGURATION & ENVIRONMENT

### 9.1 Environment Variables (.env)

```bash
# Backend
BACKEND_URL=http://localhost:8000
BACKEND_PORT=8000
DEBUG=True

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Cloudinary
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret

# JWT
JWT_SECRET_KEY=your-super-secret-key-min-32-chars
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# AI Brain (Your Friend's Service)
AI_BRAIN_URL=ws://your-friend-server:8000/brain
AI_BRAIN_TIMEOUT_SECONDS=30

# OpenAI (For LLM decisions)
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL=gpt-4.1-mini

# Render
RENDER_EXTERNAL_URL=https://satquery-backend.onrender.com

# Optional: Redis for job queue
REDIS_URL=redis://localhost:6379

# Logging
LOG_LEVEL=INFO
```

### 9.2 Config.py

```python
# app/config.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App
    backend_url: str
    backend_port: int = 8000
    debug: bool = False
    
    # Supabase
    supabase_url: str
    supabase_key: str
    supabase_service_role_key: str
    
    # Cloudinary
    cloudinary_cloud_name: str
    cloudinary_api_key: str
    cloudinary_api_secret: str
    
    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    
    # AI Brain
    ai_brain_url: str
    ai_brain_timeout_seconds: int = 30
    
    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4.1-mini"
    
    # Limits
    max_agent_steps: int = 20
    max_replans: int = 3
    max_retries_per_task: int = 2
    max_execution_time_seconds: int = 3600
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

---

## 10. DEPLOYMENT ON RENDER

### 10.1 render.yaml

```yaml
services:
  - type: web
    name: satquery-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    
    envVars:
      - key: PYTHON_VERSION
        value: 3.11
      
      - key: SUPABASE_URL
        sync: false
      - key: SUPABASE_KEY
        sync: false
      
      - key: CLOUDINARY_CLOUD_NAME
        sync: false
      - key: CLOUDINARY_API_KEY
        sync: false
      
      - key: JWT_SECRET_KEY
        sync: false
      
      - key: OPENAI_API_KEY
        sync: false
      
      - key: AI_BRAIN_URL
        sync: false
    
    disk:
      name: satquery-data
      mountPath: /var/data
      sizeGB: 10
```

### 10.2 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Expose port
EXPOSE 8000

# Run app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 11. REQUIREMENTS.TXT

```
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-dotenv==1.0.0
pydantic==2.5.0
pydantic-settings==2.1.0

# Database
supabase==2.3.1
postgresql[psycopg]==2.9.9

# Storage
cloudinary==1.35.0

# Authentication
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6

# WebSocket
websockets==12.0
python-socketio==5.10.0

# AI/ML
openai==1.3.8
langchain==0.1.1

# Utilities
pydantic-core==2.14.1
httpx==0.25.0
requests==2.31.0
Pillow==10.1.0
rasterio==1.3.8
geopandas==0.14.0
shapely==2.0.1

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.0

# Monitoring/Logging
python-json-logger==2.0.7
```

---

## 12. KEY SECURITY FEATURES

### 12.1 Built-in Security

```python
# app/middleware/security.py

class SecurityMiddleware:
    # ✓ JWT validation on all protected routes
    # ✓ Rate limiting per user (via Render)
    # ✓ CORS configured for frontend only
    # ✓ Request/response logging (no sensitive data)
    # ✓ SQL injection prevention (Supabase + SQLAlchemy ORM)
    # ✓ No credentials in logs
    # ✓ Cloudinary URLs are signed/expiring
    # ✓ Job isolation (users can't access other users' jobs)
    # ✓ Asset validation before processing
```

### 12.2 Data Privacy

```python
# Users can only access their own:
# - Jobs
# - Assets  
# - Artifacts
# - Documents
# - Evidence

# Enforced via:
# - JWT user_id extraction
# - Database query filters
# - Frontend-backend contracts
```

---

## 13. INTEGRATION FLOW (END-TO-END)

```
1. USER SUBMITS QUERY (Frontend)
   ├─ auth/login → JWT token
   ├─ POST /assets (upload images) → asset_ids
   └─ POST /queries → job_id

2. BACKEND RECEIVES QUERY
   ├─ Validate JWT
   ├─ Load assets from Supabase
   ├─ Validate geospatial metadata
   └─ Create job record

3. AGENT LOOP STARTS
   ├─ Initialize AgentState
   ├─ Connect to AI Brain via WebSocket
   ├─ Send: AgentState
   └─ Receive: Decision

4. BRAIN RESPONDS WITH DECISION
   ├─ "CALL_TOOL: validate_remote_sensing_input"
   ├─ "CALL_TOOL: detect_bitemporal_change"
   ├─ "CALL_TOOL: calculate_changed_area"
   └─ "FINAL: answer"

5. FOR EACH DECISION
   ├─ Validate prerequisites
   ├─ Execute capability (call adapter/model)
   ├─ Collect observation
   ├─ Save to database
   ├─ Emit WebSocket event → frontend updates UI
   └─ Loop back to Brain

6. WHEN BRAIN SAYS FINAL
   ├─ Synthesize final answer
   ├─ Calculate confidence
   ├─ Collect all evidence
   ├─ Store artifacts in Cloudinary
   ├─ Save final state to database
   └─ Emit completion event

7. FRONTEND RENDERS RESULT
   ├─ Display answer + confidence
   ├─ Render dynamic artifacts
   ├─ Show evidence trail
   └─ Offer report generation
```

---

## 14. ERROR HANDLING STRATEGY

### 14.1 Error Types & Responses

```python
# app/utils/error_handlers.py

class SatQueryError(Exception):
    """Base error"""

class ValidationError(SatQueryError):
    """Input validation failed"""

class PrerequisiteError(SatQueryError):
    """Prerequisite check failed (recoverable)"""

class ModelExecutionError(SatQueryError):
    """Model inference failed"""

class BrainConnectionError(SatQueryError):
    """AI Brain WebSocket connection failed"""

class StorageError(SatQueryError):
    """Cloudinary/Supabase operations failed"""

# All errors → structured JSON response
# No stack traces to frontend
# Logged securely on backend
```

---

## 15. TESTING STRATEGY

```python
# tests/test_agent.py

@pytest.mark.asyncio
async def test_agent_loop_with_mock_brain():
    """Test agent loop without actual AI Brain"""
    # Mock brain decisions
    # Test state transitions
    # Verify observations are created

@pytest.mark.asyncio
async def test_prerequisite_validation():
    """Test hard safety gates"""
    # Missing image → blocked
    # Misaligned images → blocked

@pytest.mark.asyncio
async def test_websocket_events():
    """Test real-time updates"""
    # Connect WebSocket
    # Trigger job
    # Verify events received

@pytest.mark.asyncio
async def test_artifact_storage():
    """Test Cloudinary integration"""
    # Create artifact
    # Upload to Cloudinary
    # Verify signed URL
```

---

## 16. MONITORING & LOGGING

### 16.1 Logging Setup

```python
# app/utils/logger.py

logger = setup_logger(
    name="satquery",
    level=LOG_LEVEL,  # From env
    format="json"  # Structured logging for Render
)

# Log examples:
logger.info("Job started", extra={
    "job_id": job_id,
    "user_id": user_id,
    "query": query
})

logger.error("Brain connection failed", extra={
    "job_id": job_id,
    "error": str(e)
})
```

### 16.2 Metrics to Track

```
- Job completion rate
- Average execution time
- Model confidence distribution
- Error rate per capability
- WebSocket connection duration
- Cloudinary upload latency
- AI Brain response latency
```

---

## 17. SCALABILITY CONSIDERATIONS

### 17.1 Current Architecture (Single Instance)

```
Render Web Service (single instance)
├─ FastAPI app
├─ WebSocket connections
├─ Job execution
└─ Can handle ~100 concurrent jobs
```

### 17.2 Future Scaling (When Needed)

```
Render Web Service (multiple instances)
├─ Load balancer
├─ Shared Redis queue
├─ Supabase (auto-scales)
└─ Separate model inference services
```

---

## 18. NEXT STEPS

### Phase 1: Setup (Week 1)
- [ ] Supabase project creation & schema migration
- [ ] Cloudinary setup
- [ ] Render project creation
- [ ] Environment configuration

### Phase 2: Core API (Week 2)
- [ ] FastAPI app skeleton
- [ ] Auth system (JWT + Supabase)
- [ ] Asset upload endpoints
- [ ] Job creation endpoint

### Phase 3: Agent Integration (Week 3)
- [ ] Brain WebSocket connector
- [ ] Agent controller main loop
- [ ] Executor & capability registry
- [ ] Observation schema & storage

### Phase 4: Advanced Features (Week 4)
- [ ] WebSocket events to frontend
- [ ] Document generation
- [ ] Evidence fusion
- [ ] Confidence calculation

### Phase 5: Testing & Deployment (Week 5)
- [ ] Unit tests
- [ ] Integration tests
- [ ] Deployment to Render
- [ ] Monitoring setup

---

## 19. QUICK REFERENCE - KEY FILES TO CREATE

```
✓ app/main.py                    - FastAPI initialization
✓ app/config.py                  - Environment configuration
✓ app/auth/jwt_handler.py        - JWT token creation/validation
✓ app/auth/routes.py             - Auth endpoints
✓ app/api/v1/queries.py          - Query submission endpoint
✓ app/api/v1/assets.py           - Asset upload endpoint
✓ app/api/v1/jobs.py             - Job status endpoints
✓ app/agent/brain_connector.py   - WebSocket to AI Brain
✓ app/agent/controller.py        - Main agent loop
✓ app/agent/state.py             - AgentState model
✓ app/executor/executor.py       - Decision executor
✓ app/registry/registry.py       - Capability registry
✓ app/evidence/schema.py         - Observation/Evidence models
✓ app/storage/supabase_client.py - Supabase wrapper
✓ app/storage/cloudinary_client.py - Cloudinary wrapper
✓ app/api/websocket/manager.py   - WebSocket connection manager
✓ migrations/supabase_init.sql   - Database schema
```

---

## 20. ARCHITECTURE REVIEW CHECKLIST

Before you approve, verify:

- [ ] AI Brain integration via WebSocket is clear
- [ ] No hardcoded model routing (all capability-based)
- [ ] Agent loop architecture matches specification
- [ ] Supabase schema covers all requirements
- [ ] API endpoints are complete and versioned
- [ ] JWT auth flow is secure
- [ ] Job isolation guarantees are clear
- [ ] WebSocket event schema is comprehensive
- [ ] Error handling strategy is robust
- [ ] Render deployment is feasible
- [ ] Logging doesn't expose secrets
- [ ] Database connection pooling is configured
- [ ] CORS is restricted to frontend domain
- [ ] Rate limiting is in place
- [ ] Artifact storage via Cloudinary is integrated

---

## CONCLUSION

This architecture is:

✅ **Modular**: Each component has clear responsibilities
✅ **Extensible**: New models/capabilities via adapters only
✅ **Secure**: JWT auth, data isolation, no exposed credentials
✅ **Real-time**: WebSocket integration for live progress
✅ **Scalable**: Ready for horizontal scaling if needed
✅ **Brain-Ready**: Designed specifically for your friend's AI orchestration
✅ **Production-Grade**: Error handling, logging, monitoring
✅ **Frontend-Agnostic**: Stable API contracts, no model-specific logic

---

**READY FOR APPROVAL?**

Please review and confirm:
1. Does this align with your AI Brain's interface?
2. Are the database schemas sufficient?
3. Is the WebSocket strategy acceptable?
4. Any changes needed before implementation?

Once approved, I'll generate detailed implementation megaprompts for each module.