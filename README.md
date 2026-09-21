# SatQuery AI Brain

SatQuery uses a **continuous closed-loop agent** architecture to orchestrate deterministic geospatial tools and remote deep-learning models. It grounds vague natural-language queries into concrete, mathematically aligned spatial tasks before executing remote HTTP model inference.

## Final Pre-Production Architecture (Phase 5)

As of Phase 5, the SatQuery Brain is fully decoupled from the Lightning AI GPU inference endpoints. All specialist models (GeoChat, ChangeFormer, Prithvi, SARMAE, TerraMind) are accessed securely over HTTP. 

```text
Frontend/Backend Client
         ↓ (HTTPS)
SatQuery Brain API (FastAPI)
         ↓
AgentController (Closed-loop reasoning)
         ↓
GPT-4.1-mini (Decision engine)
         ↓
Geospatial Pre-Flight (The Boundary)
         ↓ (HTTPS)
Lightning AI Hosted Specialist Models
```

## Developer API Integration

Frontend and backend developers should interact **ONLY** with the SatQuery Brain API. You do not need to manage the LLM, the capability registry, or the remote Lightning endpoints.

### Base URL

Check the `.env` file for your deployment's base URL (e.g., `BRAIN_BASE_URL=https://brain.satquery.ai`). By default, the API is available at `http://localhost:8000`.

### 1. Submit an Analysis Job

Start a new analysis job by submitting your query and asset references.

**`POST /api/v1/analyze`**

**Request Body:**
```json
{
  "query": "Identify the number of ships in this SAR image.",
  "assets": [
    {
      "asset_id": "sar_img_01",
      "uri": "/path/to/sar.tif",
      "modality": "sar",
      "format": "geotiff"
    }
  ],
  "metadata": {}
}
```

**Response (200 OK):**
```json
{
  "job_id": "job_a1b2c3d4e5f6",
  "status": "accepted"
}
```

### 2. Poll Job Status

The brain processes the job asynchronously. Poll this endpoint to check the status.

**`GET /api/v1/jobs/{job_id}`**

**Response (Pending/Running):**
```json
{
  "job_id": "job_a1b2c3d4e5f6",
  "status": "running",
  "result": null
}
```

**Response (Complete):**
```json
{
  "job_id": "job_a1b2c3d4e5f6",
  "status": "complete",
  "result": {
    "answer": "I found 14 ships in the provided SAR image.",
    "confidence": 0.95,
    "status": "complete",
    "step_count": 3,
    "replans": 0,
    "evidence": [...],
    "trace": [...]
  }
}
```

### 3. Get Job Events (Trace)

Retrieve the real-time agent execution trace to build a "thought process" UI for the user.

**`GET /api/v1/jobs/{job_id}/events`**

### 4. Get Job Evidence (Observations)

Retrieve the raw, immutable observations collected by the agent from the specialist models.

**`GET /api/v1/jobs/{job_id}/evidence`**

### 5. Get Job Report

Download a formatted Markdown summary report of the complete job.

**`GET /api/v1/jobs/{job_id}/report`**

### 6. Retrieve Artifacts

If the agent generates an artifact (e.g., a change detection mask GeoTIFF), you can retrieve it via this endpoint. 

**`GET /api/v1/artifacts/{artifact_id}`**

## Configuration

To run the Brain locally:

1. Copy `.env.example` to `.env`.
2. Configure `OPENAI_API_KEY`.
3. Set the remote specialist endpoints if they are hosted (e.g., `GEOCHAT_ENDPOINT=https://your-lightning-geochat.ai`). 
4. Leave unhosted endpoints empty! The agent will safely handle missing endpoints and inform the LLM.

```bash
# Install dependencies
pip install -r requirements.txt

# Run all 137 validation tests
pytest tests/ -v

# Start the API server
uvicorn app.main:app --reload
```

## Security & CORS
- The API is currently configured to allow CORS requests based on the `CORS_ORIGINS` environment variable (defaults to `*`). Update this to your frontend domains in production.
- Do not commit your `.env` secrets. 

## License

Private — All rights reserved.
