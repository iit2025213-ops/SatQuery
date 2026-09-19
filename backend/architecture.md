# SATQUERY AI - FINAL BACKEND ARCHITECTURE
## Complete System Documentation (Phases 1-9)

---

## 1. EXECUTIVE SUMMARY

The SatQuery AI Backend is a production-grade, highly scalable geospatial intelligence orchestrator built with FastAPI. It serves as the intelligent bridge between a user's natural language queries, an external "AI Brain" (via WebSockets), and heavy remote-sensing execution engines (Google Earth Engine, Cloudinary, and local numpy/rasterio processors).

**Key Architectural Pillars:**
- **Modular AI Capabilities:** The AI Brain does not write code or execute functions; it selects predefined "Capabilities" (tools) via the `CapabilityRegistry`.
- **Geospatial Processing Engine:** The backend handles all heavy lifting—fetching gigabytes of raster data, aligning pixels, building 3D meshes, and calculating spectral indices—locally, passing only statistical summaries and Cloudinary URLs back to the AI.
- **Persistent State:** Everything (users, jobs, drawn polygons, timelines, meshes) is tracked securely in a Supabase PostgreSQL database using Row-Level Security.

---

## 2. TECHNOLOGY STACK

- **Backend Framework:** FastAPI (Python 3.11+)
- **Database / Auth:** Supabase (PostgreSQL, Row-Level Security, JWT Auth)
- **Asset Storage:** Cloudinary (For caching meshes, thumbnails, GIFs)
- **Geospatial Core:** `numpy`, `rasterio`, `shapely`, `pyproj`, `scipy`, `imageio`
- **Earth Data Provider:** Google Earth Engine (GEE) Python API (`earthengine-api`)
- **3D Modeling:** `trimesh`, `pygltflib`
- **Real-time Comms:** WebSockets (FastAPI natively)
- **Testing:** `pytest` (with fully mocked AI Brain & real GEE integrations)

---

## 3. FEATURE PHASES IMPLEMENTED

### Phases 1-5: Core Infrastructure & Agent Engine
- **JWT Authentication:** Complete user registration, login, and token refreshing via Supabase.
- **WebSocket AI Brain Connector:** A two-way socket where the backend sends `AgentState` (JSON) and receives `Decision` payloads (`CALL_TOOL`, `FINAL`) from the external AI.
- **Direct Image Queries (Multimodal):** Users can upload their own images to Cloudinary, and the URLs are injected into the AI's `input_assets` to answer direct questions without map interfaces.
- **Document Generation:** Automated generation of PDF/HTML reports based on AI summaries, stored in Cloudinary.

### Phase 6: AOI (Area of Interest) System
- **GeoJSON Validation:** Strict validation of user-drawn polygons (Must be closed, non-intersecting, within valid lat/lng bounds).
- **Area Calculation:** Uses `pyproj` to calculate exact area in square kilometers.
- **Database Storage:** `aois` table in Supabase links the spatial context directly to user jobs.

### Phase 7: GEE / STAC Data Layer
- **Live Google Earth Engine Integration:** Service account authentication for live querying.
- **Optical Imagery:** Queries `COPERNICUS/S2_SR_HARMONIZED` (Sentinel-2) and Landsat for the lowest cloud-cover scenes across custom date ranges.
- **Elevation Data:** Queries `USGS/3DEP/10m` for high-resolution Digital Elevation Models (DEMs).

### Phase 8: Terrain Experience
- **2D Mapping:** Generates shaded relief (hillshades) and topographic contour masks dynamically from DEM arrays using `scipy.ndimage`.
- **3D Mesh Generation:** Converts 2D DEM rasters into high-fidelity 3D meshes. Calculates vertex normals, UV mapping, and exports to optimized `.glb` formats using `trimesh` and `pygltflib`.

### Phase 9: Temporal Timelines & Interactive Data
- **Multi-Year Retrieval:** Automatically finds the clearest image for every year in a sequence (e.g., 2019 to 2025).
- **Algorithmic Alignment:** Uses pixel cross-correlation (coarse-to-fine search) to perfectly align satellite images across years.
- **Radiometric Normalization:** Histogram matching (mean/std) so images look consistent across years.
- **NDVI Calculations:** Calculates exact vegetation density changes.
- **Interactive Data Charts:** Passes numerical time-series arrays (e.g., NDVI changes over 5 years) to the frontend for rendering interactive line graphs (e.g., via Recharts).
- **Timelapse Animations:** Stitches aligned images into year-stamped GIF or MP4 animations using `imageio`.

---

## 4. THE CAPABILITY REGISTRY (TOOLS FOR AI)

The AI Brain has access to the following deterministic capabilities, executed safely by the Python backend:

| Capability | Backend Adapter | Description |
|---|---|---|
| `validate_remote_sensing_input` | GeospatialEngine | Validates drawn AOI geometry and bounds. |
| `calculate_changed_area` | GeospatialEngine | Core area calculation logic. |
| `retrieve_satellite_imagery` | GEEAdapter | Queries single scenes from Sentinel/Landsat. |
| `retrieve_dem` | GEEAdapter | Gets min/max elevation stats for an AOI. |
| `generate_terrain_2d` | TerrainAdapter | Creates hillshade/contour maps (Cloudinary URL). |
| `generate_terrain_3d` | TerrainAdapter | Creates .glb 3D mesh (Cloudinary URL). |
| `retrieve_temporal_imagery` | TimelineAdapter | Multi-year alignment and NDVI calculation. |
| `generate_timeline_animation` | TimelineAdapter | Creates GIF/MP4 timelapses (Cloudinary URL). |

---

## 5. SUPABASE DATABASE SCHEMA (HIGHLIGHTS)

The database relies on Row-Level Security (RLS) to ensure users can only access their own data.

*   `users`: Mirrors Supabase Auth users.
*   `jobs`: The primary tracking table for an AI execution loop.
*   `aois`: Stores validated GeoJSON polygons and area statistics.
*   `gee_collections` & `gee_assets`: Tracks single scenes pulled from Earth Engine.
*   `dem_assets`: Tracks elevation arrays.
*   `terrain_assets`: Stores references to generated 2D maps and 3D GLB meshes.
*   `timeline_collections`: Tracks a multi-year chronological job.
*   `timeline_imagery`: Stores individual year metadata (NDVI, cloud cover, alignment RMSE).
*   `timeline_animations`: Stores the resulting GIF/MP4 Cloudinary URLs.
*   `documents`: Stores generated PDF/HTML reports.

---

## 6. AI BRAIN INTERACTION FLOW (WEBSOCKETS)

1.  **Frontend** sends prompt + Polygon GeoJSON.
2.  **FastAPI Backend** creates a Job and an `AgentState`.
3.  **FastAPI** sends `AgentState` via WebSocket to AI Brain.
    *   *Note: Does NOT send raw pixels. Sends AOI, user prompt, and statistical observations.*
4.  **AI Brain** responds with `CALL_TOOL: generate_terrain_3d`.
5.  **FastAPI** connects to GEE, downloads DEM, builds 3D mesh, uploads to Cloudinary.
6.  **FastAPI** updates `AgentState.observations` with the new Cloudinary URL.
7.  **FastAPI** loops back to step 3.
8.  **AI Brain** responds with `FINAL` + summary string.
9.  **FastAPI** sends final data & URLs back to the Frontend.

---

## 7. TEST INFRASTRUCTURE

- Uses `pytest` with `pytest-asyncio`.
- Tests run against **Real Services** (`.env` credentials for GEE, Cloudinary, and Supabase test DB).
- **Mocked AI Brain:** The only mocked component is the AI Brain itself. It uses a deterministic `MockAIBrain` class to simulate tool-calling behavior, ensuring CI/CD tests are reliable and fast without paying LLM token costs.