# SATQUERY AI - Project Context & Implementation Guide

**Smart India Hackathon (SIH) 2024**  
**Team:** Frontend + Backend Dev | Legal Brain AI (Friend)  
**Duration:** 8 weeks to production (or 36 hours for hackathon)  
**Status:** Design complete, implementation starting

---

## 1. PROJECT OVERVIEW

### Mission
**SATQUERY AI** is an agentic, multimodal satellite imagery analysis platform that answers complex geospatial questions by combining real-time satellite data (Sentinel-1/2, Landsat) with AI models to detect, analyze, and report on land-use changes, urban expansion, environmental disasters, and climate impacts.

**Example Use Cases:**
- "Analyze urban expansion in Delhi from 2019-2025 and quantify built-up area growth"
- "Detect flood-affected regions in Maharashtra and map severity"
- "Monitor deforestation in Amazon and track vegetation loss annually"
- "Analyze agricultural patterns and identify crop rotation cycles"

### Problem Being Solved
**Current gap:** Geospatial analysts manually collect satellite imagery, run separate analysis tools (QGIS, Python scripts, proprietary software), cross-reference results, and spend days generating reports. This is slow, error-prone, and requires specialized expertise.

**Our solution:** One unified platform where users describe their question in natural language → the system automatically fetches the right data, validates it, runs multiple AI models in parallel, synthesizes findings, and exports publication-ready reports with full evidence traceability.

### Target Users
1. **Government agencies** (ISRO, MoEFCC, revenue departments) - environmental monitoring, land use planning
2. **NGOs & research** (environmental impact assessments, climate studies)
3. **Urban planners** (city expansion tracking, infrastructure planning)
4. **Insurance companies** (disaster damage assessment)
5. **Journalists** (investigative geospatial reporting)

---

## 2. ARCHITECTURE OVERVIEW

### How It Works (End-to-End Flow)

```
User Query
    ↓
┌─────────────────────────────────────┐
│ LEGAL BRAIN (Friend's responsibility)│
├─────────────────────────────────────┤
│ P1: Parse intent, decompose query    │
│ P2: Fetch satellite imagery (GEE)    │
│ P3: Validate & repair data           │
│ P4: Re-verify sufficiency            │
│ P5: Run specialist models in parallel│
│     - GeoChat (RGB VQA)              │
│     - ChangeFormer (temporal)        │
│     - Prithvi (EO features)          │
│     - SARMAE (SAR analysis)          │
│     - SkySense (multimodal fusion)   │
└─────────────────────────────────────┘
    ↓ Structured results
┌─────────────────────────────────────┐
│ FRONTEND + VISUALIZATION             │
├─────────────────────────────────────┤
│ Your responsibility:                 │
│ - Display results interactively      │
│ - Allow user exploration             │
│ - Generate reports                   │
│ - Export in multiple formats         │
└─────────────────────────────────────┘
    ↓
Reports (PDF, DOCX, GeoPackage)
```

### Your Responsibility: Frontend + Backend Infrastructure

You handle:
1. **User-facing UI** (11 pages)
2. **Backend infrastructure** (API layer, auth, database, file storage)
3. **Integration glue** (connect legal brain APIs, handle real-time streaming)
4. **Document generation** (reports in multiple formats)

Friend handles:
1. **Query understanding** (P1: intent parsing, requirement graphs)
2. **Data intelligence** (P2: Google Earth Engine queries)
3. **Validation & repair** (P3: geospatial checks, auto-normalization)
4. **Model orchestration** (P5: running GeoChat, ChangeFormer, etc.)

---

## 3. FRONTEND ARCHITECTURE

### 11 Core Pages

**User Journey Flow:**

```
Landing Page
    ↓
Login / Signup
    ↓
Dashboard (Home)
    ├→ New Analysis (Query Console)
    │   ├→ Query Console (write query, upload images, draw AOI, pick dates)
    │   └→ Data Explorer (preview satellite scenes, metadata)
    │
    ├→ Analysis Workspace (view results)
    │   ├→ Analysis Hub (RGB, change map, multimodal)
    │   ├→ Time Machine (animated T1→T2 slider)
    │   ├→ Evidence Explorer (trace findings)
    │   └→ Findings Summary (AI insights)
    │
    ├→ Report Studio (create documents)
    │   ├→ Report Generator (drag-drop sections)
    │   ├→ Traceability View (evidence audit)
    │   └→ Export (PDF/DOCX/GeoPackage)
    │
    ├→ Projects Hub (manage all analyses)
    │
    └→ Settings (profile, API keys, preferences)

Global: Copilot (chat, available everywhere)
```

### Page Breakdown

#### **1. Landing Page** (`/`)
- Hero section with value prop
- Feature cards
- CTA buttons (Sign up / Login)
- Tech highlights (satellite imagery, AI-powered, real-time)

#### **2. Login / Signup** (`/auth/login`, `/auth/signup`)
- Email/password form
- Google OAuth (optional)
- Supabase authentication

#### **3. Dashboard** (`/dashboard`)
- Welcome card (user name, stats)
- Recent projects carousel
- Quick stats: total analyses, saved docs, starred projects
- Search bar with filters
- "New Analysis" CTA button

#### **4. Query Console** (`/analyze/new`)
**Purpose:** Unified interface for submitting analysis queries

**Components:**
- **Text Query Input** (large textarea)
  - Natural language: "Analyze urban expansion in Delhi 2019-2025"
  - Autocomplete suggestions
  - Parsing feedback (shows detected: intent, AOI, timeframe, modality)

- **Image Upload Section** (Cloudinary)
  - Drag-drop or file picker
  - Support: RGB, multispectral, SAR, T1-T2 pairs
  - Auto-metadata extraction (bands, resolution, date)
  - Progress bars

- **Map Section** (Leaflet)
  - Draw polygon for AOI
  - Or paste GeoJSON
  - Or search location by name
  - Shows bounds + area

- **Temporal Selector**
  - Dual-date picker (T1 ← → T2)
  - Visual timeline bar
  - Suggests years with available imagery

- **Modality Selector** (checkboxes)
  - ☑ RGB (optical)
  - ☑ Multispectral (vegetation indices)
  - ☑ SAR (radar, cloud-proof)
  - ☑ Temporal (change detection)

- **Advanced Options** (collapsible)
  - Cloud cover threshold (0-50%)
  - Sensor preference (Sentinel-1/2, Landsat, etc.)
  - Resolution range (10-30m)

- **Preview Panel** (right sidebar)
  - Shows exactly what will be sent to backend
  - Parsed query structure
  - Data requirements
  - Estimated processing time

- **Submit Button**
  - "Run Analysis" (disabled until valid)
  - Shows spinner + progress message while submitting

#### **5. Data Explorer** (`/analyze/data`)
**Purpose:** Preview available satellite scenes for the query

**Components:**
- AOI map with footprints of available scenes
- Scene list (grid view)
  - Date, sensor, resolution, cloud cover
  - Status badges (✓ Valid, ⚠ Repairable, ✗ Bad)
- Click to view scene metadata (CRS, bands, etc.)
- Real-time updates as legal brain finds more imagery

#### **6. Analysis Workspace** (`/analysis/{analysisId}`)
**Purpose:** Explore and interact with analysis results

**Layout:** Split screen (map + sidebars)

**Left Sidebar - Layers Panel:**
```
☑ AOI boundary
☑ RGB imagery
☑ Change mask
☑ Buildings
☑ Roads
☑ Vegetation
🎚️ Opacity slider
```

**Center - Interactive Map** (Leaflet):
- RGB satellite image
- Change heatmap overlay (opacity-controlled)
- Click locations to open VQA panel
- Zoom + pan
- North arrow + scale bar

**Right Sidebar - Tabs:**

1. **RGB View**
   - Full-res satellite image
   - VQA panel: click region → ask question → get AI answer
   - Example Q: "What is this building?" → A: "Residential complex, 5-story"
   - Region grounding (highlights what the model is looking at)

2. **Change Map**
   - Heatmap showing change probability (0-100%)
   - Color scale: blue (no change) → red (high change)
   - Shows affected area statistics

3. **Temporal Slider**
   - Animated transition between T1 and T2
   - Year labels on each keyframe
   - Statistics updating in real-time
   - Play/pause button

4. **Multimodal Panel**
   - RGB + NDVI + EVI + NDBI side-by-side
   - Toggle each layer on/off
   - Legend for each index

5. **SAR Overlay**
   - Amplitude and coherence maps
   - Overlay on RGB with opacity control
   - Useful for cloud-covered regions

6. **Statistics Card**
   - Total change area (km²)
   - % of AOI changed
   - Confidence level (89%)
   - Evidence quality score (94%)

#### **7. Time Machine** (`/analysis/{analysisId}/timeline`)
**Purpose:** Animate changes over time

**Components:**
- Timeline of satellite scenes (2019, 2020, 2021, ..., 2025)
- Animated transition between consecutive years
- Change mask overlay with confidence heatmap
- Real-time statistics: "2023: vegetation loss 12%, confidence 91%"
- Anomaly detection: ⚠️ "Flood detected in Q3 2023"
- Playback controls (play, pause, speed)

#### **8. Evidence Explorer** (`/analysis/{analysisId}/evidence`)
**Purpose:** Trace findings back to source data

**Flow:**
```
User clicks "Evidence for urban expansion claim"
    ↓
Shows: Claim → AI Finding (confidence %) → Model output → Satellite scene → Exact pixels
    ↓
User can click any step:
  - Click "Claim" → shows full report section mentioning it
  - Click "Model output" → shows raw change mask
  - Click "Scene" → loads full satellite image + date
  - Click "Pixels" → highlights region on map
```

**Components:**
- Evidence list (cards, each with a claim)
- Expandable detail panels
- Links back to maps/visualizations
- Confidence bars per piece of evidence

#### **9. Findings Summary** (`/analysis/{analysisId}/findings`)
**Purpose:** AI-generated insights and conclusions

**Components:**
- Executive summary (auto-generated by Claude API)
  - "Between 2019-2024, the AOI experienced 34% vegetation loss..."
- Key findings (bullets)
- Anomalies detected (with severity badges)
  - 🔴 High: Unauthorized construction in protected area
  - 🟡 Medium: Unusual crop rotation pattern
  - 🟢 Low: Seasonal water level variation
- Change attribution (pie chart)
  - 72% agricultural
  - 18% urban
  - 10% natural disaster
- Metadata summary
  - Models used, confidence levels, data sources

#### **10. Report Studio** (`/analysis/{analysisId}/report`)
**Purpose:** Build and export reports

**Components:**
- Template selector (Executive Brief, Technical Report, Change Report)
- Drag-drop section builder
  ```
  ⊕ Sections (drag to reorder):
    1. Cover page
    2. Executive summary
    3. Methodology
    4. Maps
    5. Temporal analysis
    6. Statistics
    7. Findings
    8. Technical appendix
  ```
- Live preview (PDF rendering)
- Export buttons: PDF, DOCX, GeoPackage
- Share with link generation
- Email delivery option

#### **11. Projects Hub** (`/projects`)
**Purpose:** Manage all analyses

**Components:**
- Grid of project cards
  - Thumbnail (latest analysis RGB)
  - Title, created date
  - Recent analyses count
  - "View" button
- Filter by: date, location, analysis type
- Bulk operations: delete, export, share
- Search bar

#### **12. Settings** (`/settings`)
**Purpose:** User configuration

**Sections:**
- Profile (name, email, avatar)
- API keys (for team/org use)
- Notifications (email on analysis complete, etc.)
- Theme (light/dark)
- Privacy & sharing settings

#### **13. Copilot** (Global, persistent)
**Purpose:** AI chat assistant available everywhere

**Features:**
- Ask about current analysis: "What does this change mean?"
- Ask to generate report: "Create an executive summary"
- Ask to explain findings: "Why did vegetation drop 40%?"
- Context-aware (knows what analysis user is viewing)
- Powered by Claude API

---

## 4. TECHNOLOGY STACK

### Frontend
```
React 18 + TypeScript        → UI framework
Vite                         → Build tool
Redux Toolkit                → State management
Tailwind CSS + shadcn/ui     → Styling
React Router v6              → Routing
Leaflet.js                   → Map visualization
ECharts / Recharts           → Charts & stats
Framer Motion                → Animations
Axios / TanStack Query       → Data fetching
Zustand (optional)           → Local state (doc builder)
```

### Backend / Infrastructure
```
Supabase                     → PostgreSQL + Auth + Real-time
Cloudinary                   → Image storage & optimization
Node.js / Express (optional) → API gateway (if needed)
```

### Document Generation
```
PDFKit                       → PDF export
docx                         → Word document export
sqlite3 / GeoPackage tools   → GeoPackage export (spatial data)
```

### Integrations
```
Claude API                   → AI insights & report generation
Legal Brain APIs (friend)    → Query understanding, model orchestration
Google Earth Engine API      → Satellite imagery (via friend's code)
```

### Killer Features (Phase 4)
```
Cesium.js                    → 3D terrain visualization
Three.js                     → AR/XR visualization
```

---

## 5. DATABASE SCHEMA (Supabase PostgreSQL)

### Core Tables

```sql
-- User Management
CREATE TABLE users (
  id UUID PRIMARY KEY (auth.uid),
  email TEXT,
  username TEXT,
  avatar_url TEXT,  -- Cloudinary URL
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Projects (collection of analyses)
CREATE TABLE projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  thumbnail_url TEXT,  -- Cloudinary
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Queries (user's analysis request)
CREATE TABLE queries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id),
  query_text TEXT NOT NULL,
  aoi_geojson JSON NOT NULL,  -- GeoJSON polygon
  time_start DATE,
  time_end DATE,
  modality TEXT[] DEFAULT '{RGB,MS,SAR}',  -- Which types needed
  status TEXT DEFAULT 'pending',  -- pending|processing|completed|failed
  error_message TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Image uploads (user-provided)
CREATE TABLE images (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  query_id UUID REFERENCES queries(id),
  cloudinary_public_id TEXT,
  cloudinary_url TEXT,
  original_filename TEXT,
  file_type TEXT,  -- rgb|ms|sar|t1|t2
  metadata JSON,  -- bands, resolution, date, CRS
  uploaded_at TIMESTAMP DEFAULT NOW()
);

-- Analysis results (output from legal brain)
CREATE TABLE analysis (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  query_id UUID NOT NULL REFERENCES queries(id),
  status TEXT DEFAULT 'processing',
  progress INT DEFAULT 0,  -- 0-100%
  legal_brain_request_id TEXT,  -- for tracking
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Results visualization data
CREATE TABLE results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  analysis_id UUID NOT NULL REFERENCES analysis(id),
  rgb_url TEXT,  -- Cloudinary
  change_mask_url TEXT,  -- PNG heatmap
  confidence_map JSON,  -- GeoJSON with confidence polygons
  findings TEXT[],  -- Array of detected changes
  metadata JSON,  -- CRS, resolution, bands used
  model_versions JSON,  -- { geochat: "1.0", changeformer: "2.1" }
  created_at TIMESTAMP DEFAULT NOW()
);

-- Evidence chain (for traceability)
CREATE TABLE evidence (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  result_id UUID NOT NULL REFERENCES results(id),
  claim_text TEXT,  -- "Urban expansion detected in eastern corridor"
  finding_type TEXT,  -- urban|agricultural|disaster|vegetation|water
  model_used TEXT,  -- GeoChat, ChangeFormer, etc.
  confidence FLOAT,  -- 0-1
  model_output JSON,  -- Raw model response
  satellite_scene JSON,  -- { date, sensor, bands, url }
  pixel_region JSON,  -- GeoJSON of highlighted pixels
  created_at TIMESTAMP DEFAULT NOW()
);

-- Exported documents
CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id),
  name TEXT,
  document_type TEXT,  -- report|export
  export_format TEXT,  -- pdf|docx|gpkg
  cloudinary_url TEXT,
  file_size_kb INT,
  created_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP  -- For sharing links
);

-- Row-level security (RLS)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE queries ENABLE ROW LEVEL SECURITY;
ALTER TABLE images ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE results ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- RLS Policies (examples)
CREATE POLICY "Users see own data"
  ON users FOR SELECT
  USING (auth.uid() = id);

CREATE POLICY "Users see own projects"
  ON projects FOR SELECT
  USING (auth.uid() = user_id);
```

---

## 6. API ENDPOINTS

### Authentication
```
POST /auth/signup
  Input: { email, password }
  Output: { user, session }

POST /auth/login
  Input: { email, password }
  Output: { user, session }

POST /auth/logout
  Output: {}
```

### Projects
```
POST /projects
  Input: { name, description }
  Output: { id, ... }

GET /projects
  Output: { projects[] }

GET /projects/{projectId}
  Output: { project, analyses[] }

DELETE /projects/{projectId}
  Output: {}
```

### Query Submission & Streaming
```
POST /query/submit
  Input: {
    projectId,
    queryText: "Analyze urban expansion in Delhi 2019-25",
    aoi: { type: "Polygon", coordinates: [...] },
    timeStart: "2019-01-01",
    timeEnd: "2025-12-31",
    modality: ["RGB", "MS", "SAR"],
    imageIds: [...]  // Optional: user-provided images
  }
  Output: {
    queryId,
    estimatedTime: "5 minutes",
    message: "Query submitted to legal brain"
  }

WS /analysis/{queryId}/stream
  (WebSocket for real-time progress)
  Output (streamed):
    { progress: 25, step: "Fetching satellite imagery..." }
    { progress: 50, step: "Validating data..." }
    { progress: 75, step: "Running AI models..." }
    { progress: 100, step: "Generating results..." }

GET /query/{queryId}
  Output: {
    id,
    status,
    query_text,
    parsed_intent: { entities, aoi, time, modality },
    requirements: { evidence_needed },
    error: null
  }
```

### Images (Cloudinary)
```
POST /image/upload
  Input: multipart/form-data { file, query_id }
  Output: {
    imageId,
    cloudinaryUrl,
    metadata: { width, height, format, bands, date }
  }

DELETE /image/{imageId}
  Output: {}
```

### Results & Visualization
```
GET /results/{analysisId}
  Output: {
    rgb_url,
    change_mask_url,
    confidence_map: { ... },
    findings: ["Urban expansion", "Vegetation loss"],
    metadata: { CRS, resolution, bands }
  }

GET /results/{analysisId}/compare?t1={sceneId}&t2={sceneId}
  Output: {
    diff_map,
    change_area_km2,
    confidence: 0.89,
    change_type: "urban"
  }

GET /evidence/{resultId}
  Output: {
    evidence: [
      {
        claim: "Urban expansion in eastern corridor",
        confidence: 0.92,
        model: "ChangeFormer",
        satellite_scene: { date, sensor },
        pixels: { type: "Polygon", ... }
      }
    ]
  }
```

### Document Generation
```
POST /document/generate
  Input: {
    analysisId,
    format: "pdf" | "docx" | "gpkg",
    sections: ["cover", "summary", "maps", "findings", "technical"],
    includeEvidence: true
  }
  Output: {
    documentId,
    downloadUrl,
    format,
    createdAt
  }

POST /document/{documentId}/share
  Input: {
    expiryDays: 7
  }
  Output: {
    shareUrl: "https://satquery.com/share/xyz123",
    expiresAt: "2025-01-17"
  }

GET /projects/{projectId}/documents
  Output: {
    documents: [...]
  }
```

### AI Integration
```
POST /ai/generate-insights
  Input: {
    analysisId,
    resultsData,
    geographicContext
  }
  Output: {
    executiveSummary: "Between 2019-2024...",
    keyFindings: [...],
    anomalies: [...]
  }

POST /ai/chat
  Input: {
    message: "What does this change mean?",
    analysisId,  -- For context
    conversationHistory: [...]
  }
  Output: {
    response: "Based on the satellite data..."
  }
```

---

## 7. STATE MANAGEMENT (Redux)

### Store Structure

```javascript
{
  // Auth state
  auth: {
    user: { id, email, username, avatar },
    isAuthenticated: boolean,
    loading: boolean,
    error: string | null
  },

  // Projects
  projects: {
    byId: { 'proj-1': {...}, 'proj-2': {...} },
    allIds: ['proj-1', 'proj-2'],
    currentProjectId: 'proj-1',
    loading: boolean
  },

  // Queries
  queries: {
    byId: { 'q-1': {...} },
    allIds: ['q-1'],
    currentQueryId: 'q-1'
  },

  // Real-time analysis progress
  analysis: {
    byId: { 'a-1': { status, progress, step } },
    currentAnalysisId: 'a-1',
    streaming: boolean
  },

  // Results visualization
  results: {
    byId: { 'r-1': { rgb, changeMask, confidence, findings } },
    currentResultId: 'r-1',
    loading: boolean
  },

  // Document builder
  documents: {
    draft: {
      sections: [],
      selectedFormat: 'pdf',
      templateId: null
    }
  },

  // UI state
  ui: {
    sidebarOpen: boolean,
    theme: 'light' | 'dark',
    notificationQueue: [],
    selectedLayersMap: {}
  }
}
```

### Redux Slices

```
slices/
├── authSlice.ts         (login, signup, logout)
├── projectsSlice.ts     (CRUD projects)
├── queriesSlice.ts      (submit, fetch query status)
├── analysisSlice.ts     (streaming progress)
├── resultsSlice.ts      (fetch & cache results)
├── documentsSlice.ts    (draft builder state)
└── uiSlice.ts           (theme, notifications, etc.)
```

---

## 8. FRONTEND FOLDER STRUCTURE

```
satquery-frontend/
├── src/
│   ├── pages/                          # 11 page components
│   │   ├── Landing.tsx
│   │   ├── Auth/
│   │   │   ├── Login.tsx
│   │   │   └── Signup.tsx
│   │   ├── Dashboard.tsx
│   │   ├── QueryConsole.tsx
│   │   ├── DataExplorer.tsx
│   │   ├── AnalysisWorkspace.tsx
│   │   ├── TimeMachine.tsx
│   │   ├── EvidenceExplorer.tsx
│   │   ├── FindingsSummary.tsx
│   │   ├── ReportStudio.tsx
│   │   ├── ProjectsHub.tsx
│   │   ├── Settings.tsx
│   │   └── NotFound.tsx
│   │
│   ├── components/                     # Reusable components
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── Footer.tsx
│   │   ├── map/
│   │   │   ├── InteractiveMap.tsx      (Leaflet)
│   │   │   ├── ChangeMapOverlay.tsx
│   │   │   ├── TimelineSlider.tsx
│   │   │   └── AOIDrawer.tsx
│   │   ├── forms/
│   │   │   ├── QueryInputForm.tsx
│   │   │   ├── ImageUploader.tsx
│   │   │   ├── TemporalSelector.tsx
│   │   │   └── ModalitySelector.tsx
│   │   ├── visualization/
│   │   │   ├── ChangeHeatmap.tsx
│   │   │   ├── StatisticsCard.tsx
│   │   │   ├── EChartsWrapper.tsx
│   │   │   ├── VQAPanel.tsx
│   │   │   └── AnomalyBadge.tsx
│   │   ├── report/
│   │   │   ├── ReportBuilder.tsx
│   │   │   ├── SectionDragDrop.tsx
│   │   │   ├── ReportPreview.tsx
│   │   │   └── ExportButtons.tsx
│   │   ├── copilot/
│   │   │   ├── CopilotChat.tsx
│   │   │   └── ContextAware.tsx
│   │   └── common/
│   │       ├── LoadingSpinner.tsx
│   │       ├── ErrorBoundary.tsx
│   │       ├── Card.tsx
│   │       └── Modal.tsx
│   │
│   ├── hooks/                          # Custom React hooks
│   │   ├── useAuth.ts
│   │   ├── useQuery.ts
│   │   ├── useAnalysis.ts
│   │   ├── useWebSocket.ts
│   │   └── useCopilot.ts
│   │
│   ├── api/                            # API client functions
│   │   ├── auth.ts
│   │   ├── projects.ts
│   │   ├── queries.ts
│   │   ├── images.ts
│   │   ├── results.ts
│   │   ├── documents.ts
│   │   └── copilot.ts
│   │
│   ├── redux/                          # State management
│   │   ├── store.ts
│   │   ├── slices/
│   │   │   ├── authSlice.ts
│   │   │   ├── projectsSlice.ts
│   │   │   ├── queriesSlice.ts
│   │   │   ├── analysisSlice.ts
│   │   │   ├── resultsSlice.ts
│   │   │   ├── documentsSlice.ts
│   │   │   └── uiSlice.ts
│   │   └── selectors.ts
│   │
│   ├── services/                       # Business logic
│   │   ├── cloudinary.ts
│   │   ├── supabase.ts
│   │   ├── documentGenerator.ts
│   │   └── spatialUtils.ts
│   │
│   ├── styles/                         # Global styles
│   │   ├── globals.css
│   │   └── variables.css
│   │
│   ├── types/                          # TypeScript types
│   │   ├── api.ts
│   │   ├── domain.ts
│   │   └── ui.ts
│   │
│   ├── utils/                          # Utility functions
│   │   ├── validators.ts
│   │   ├── formatters.ts
│   │   ├── mappers.ts
│   │   └── constants.ts
│   │
│   ├── App.tsx                         # Root component
│   ├── main.tsx                        # Entry point
│   └── index.css
│
├── public/                             # Static assets
├── .env.example                        # Environment variables template
├── vite.config.ts                      # Vite configuration
├── tsconfig.json                       # TypeScript config
├── tailwind.config.js                  # Tailwind config
├── package.json
└── README.md
```

---

## 9. KEY COMPONENTS DEEP DIVE

### InteractiveMap Component

```typescript
// components/map/InteractiveMap.tsx

interface Props {
  aoi?: GeoJSON;
  imagery?: { url: string, bounds: LatLngBounds };
  changeMask?: { url: string, opacity: number };
  onAOIChange?: (geojson: GeoJSON) => void;
  onLocationClick?: (lat: number, lng: number) => void;
  mode: 'draw' | 'view'; // draw for query console, view for results
}

export const InteractiveMap: React.FC<Props> = ({ ... }) => {
  const mapRef = useRef<L.Map | null>(null);
  const [aoiLayer, setAoiLayer] = useState<L.GeoJSON | null>(null);
  const [imageryLayer, setImageryLayer] = useState<L.TileLayer | null>(null);
  const [changeMaskLayer, setChangeMaskLayer] = useState<L.ImageOverlay | null>(null);

  // Initialize Leaflet map
  useEffect(() => {
    mapRef.current = L.map('map').setView([20, 78], 5); // India center
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(mapRef.current);
  }, []);

  // Handle AOI drawing
  const handleDraw = (geojson: GeoJSON) => {
    if (aoiLayer) mapRef.current?.removeLayer(aoiLayer);
    const layer = L.geoJSON(geojson, { color: 'blue' }).addTo(mapRef.current!);
    setAoiLayer(layer);
    onAOIChange?.(geojson);
  };

  // Overlay satellite imagery
  useEffect(() => {
    if (!imagery) return;
    const layer = L.imageOverlay(imagery.url, imagery.bounds).addTo(mapRef.current!);
    setImageryLayer(layer);
    return () => mapRef.current?.removeLayer(layer);
  }, [imagery]);

  // Overlay change mask with opacity control
  useEffect(() => {
    if (!changeMask) return;
    const layer = L.imageOverlay(changeMask.url, aoiLayer?.getBounds()!)
      .setOpacity(changeMask.opacity)
      .addTo(mapRef.current!);
    setChangeMaskLayer(layer);
    return () => mapRef.current?.removeLayer(layer);
  }, [changeMask]);

  return (
    <div className="w-full h-full">
      <div id="map" className="w-full h-full" ref={mapRef} />
      {mode === 'draw' && <AOIDrawer onDraw={handleDraw} />}
      {mode === 'view' && <MapToolbar />}
    </div>
  );
};
```

### VQA Panel Component

```typescript
// components/visualization/VQAPanel.tsx

interface Props {
  imageUrl: string;
  onQuestion: (question: string) => void;
  answers?: Array<{ q: string, a: string, confidence: number }>;
  loading?: boolean;
}

export const VQAPanel: React.FC<Props> = ({ imageUrl, ...props }) => {
  const [question, setQuestion] = useState('');
  const [selectedRegion, setSelectedRegion] = useState<{ x: number, y: number, w: number, h: number } | null>(null);

  const handleSubmit = () => {
    if (!selectedRegion) {
      alert('Please select a region first');
      return;
    }
    props.onQuestion(question);
  };

  return (
    <div className="w-80 bg-white rounded-lg shadow-lg p-4">
      <h3 className="font-semibold mb-4">Visual Question Answering</h3>
      
      {/* Image with region selector */}
      <img 
        src={imageUrl} 
        className="w-full rounded cursor-crosshair mb-4"
        onClick={(e) => {
          // Handle region selection (simplified)
          setSelectedRegion({ x: 0, y: 0, w: 50, h: 50 });
        }}
      />
      {selectedRegion && (
        <p className="text-sm text-gray-600 mb-4">Region selected: {selectedRegion.w}x{selectedRegion.h}px</p>
      )}

      {/* Question input */}
      <textarea
        placeholder="Ask a question about this region..."
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        className="w-full p-2 border rounded mb-3 text-sm"
        rows={3}
      />

      {/* Submit button */}
      <button
        onClick={handleSubmit}
        disabled={!selectedRegion || !question || props.loading}
        className="w-full bg-blue-600 text-white py-2 rounded disabled:opacity-50"
      >
        {props.loading ? 'Analyzing...' : 'Get Answer'}
      </button>

      {/* Previous answers */}
      {props.answers && (
        <div className="mt-4 border-t pt-4 space-y-3">
          {props.answers.map((item, i) => (
            <div key={i} className="text-sm">
              <p className="font-medium">Q: {item.q}</p>
              <p className="text-gray-700">A: {item.a}</p>
              <p className="text-xs text-gray-500">Confidence: {(item.confidence * 100).toFixed(0)}%</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
```

### QueryConsole Component

```typescript
// pages/QueryConsole.tsx

export const QueryConsole: React.FC = () => {
  const dispatch = useAppDispatch();
  const { projects } = useAppSelector(state => state.projects);
  const currentProject = projects.currentProjectId ? projects.byId[projects.currentProjectId] : null;

  const [formData, setFormData] = useState({
    queryText: '',
    aoi: null as GeoJSON | null,
    timeStart: '',
    timeEnd: '',
    modality: { RGB: true, MS: true, SAR: false },
    imageIds: [] as string[]
  });

  const [parsedIntent, setParsedIntent] = useState(null);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  // Real-time parsing as user types
  useEffect(() => {
    const timer = setTimeout(async () => {
      if (formData.queryText.length > 10) {
        try {
          const response = await fetch('/api/query/understand', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: formData.queryText })
          });
          const data = await response.json();
          setParsedIntent(data);
        } catch (err) {
          console.error('Parsing error:', err);
        }
      }
    }, 1000);
    return () => clearTimeout(timer);
  }, [formData.queryText]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validation
    const errors: string[] = [];
    if (!formData.queryText) errors.push('Query text required');
    if (!formData.aoi) errors.push('AOI required');
    if (!formData.timeStart) errors.push('Start date required');
    if (!formData.timeEnd) errors.push('End date required');
    
    if (errors.length > 0) {
      setValidationErrors(errors);
      return;
    }

    try {
      // Submit to backend
      const response = await fetch('/api/query/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          projectId: currentProject?.id,
          ...formData
        })
      });
      const result = await response.json();
      
      // Redirect to analysis
      window.location.href = `/analysis/${result.queryId}`;
    } catch (err) {
      console.error('Submit error:', err);
    }
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">New Analysis</h1>

      <form onSubmit={handleSubmit} className="grid grid-cols-3 gap-6">
        {/* Left: Query & Options */}
        <div className="col-span-2 space-y-6">
          {/* Query Input */}
          <div>
            <label className="block font-semibold mb-2">Your Question</label>
            <textarea
              placeholder="e.g., Analyze urban expansion in Delhi from 2019 to 2025"
              value={formData.queryText}
              onChange={(e) => setFormData({ ...formData, queryText: e.target.value })}
              className="w-full h-24 p-3 border rounded-lg text-lg"
            />
          </div>

          {/* Parsed Intent Feedback */}
          {parsedIntent && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h3 className="font-semibold text-blue-900 mb-2">Detected Intent</h3>
              <ul className="text-sm text-blue-800 space-y-1">
                <li>📍 <strong>Location:</strong> {parsedIntent.aoi || 'Not detected'}</li>
                <li>📅 <strong>Time:</strong> {parsedIntent.timeStart} to {parsedIntent.timeEnd || 'Latest'}</li>
                <li>🛰️ <strong>Data Needed:</strong> {parsedIntent.modality?.join(', ') || 'RGB'}</li>
              </ul>
            </div>
          )}

          {/* Temporal Selector */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block font-semibold mb-2">Start Date</label>
              <input
                type="date"
                value={formData.timeStart}
                onChange={(e) => setFormData({ ...formData, timeStart: e.target.value })}
                className="w-full p-2 border rounded"
              />
            </div>
            <div>
              <label className="block font-semibold mb-2">End Date</label>
              <input
                type="date"
                value={formData.timeEnd}
                onChange={(e) => setFormData({ ...formData, timeEnd: e.target.value })}
                className="w-full p-2 border rounded"
              />
            </div>
          </div>

          {/* Modality Selector */}
          <div>
            <label className="block font-semibold mb-2">Data Types</label>
            <div className="space-y-2">
              {(['RGB', 'MS', 'SAR'] as const).map(mod => (
                <label key={mod} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.modality[mod]}
                    onChange={(e) => setFormData({
                      ...formData,
                      modality: { ...formData.modality, [mod]: e.target.checked }
                    })}
                    className="mr-2"
                  />
                  <span>{mod === 'RGB' ? 'Optical (Sentinel-2)' : mod === 'MS' ? 'Multispectral' : 'Radar (Sentinel-1)'}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Image Upload */}
          <div>
            <label className="block font-semibold mb-2">Upload Images (Optional)</label>
            <ImageUploader
              onUpload={(imageIds) => setFormData({ ...formData, imageIds })}
            />
          </div>

          {/* Validation Errors */}
          {validationErrors.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded p-4">
              <h3 className="font-semibold text-red-900 mb-2">Fix these errors:</h3>
              <ul className="text-sm text-red-800 space-y-1">
                {validationErrors.map((err, i) => <li key={i}>• {err}</li>)}
              </ul>
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            className="w-full bg-blue-600 text-white font-semibold py-3 rounded-lg hover:bg-blue-700"
          >
            Run Analysis
          </button>
        </div>

        {/* Right: Map & AOI */}
        <div>
          <label className="block font-semibold mb-2">Area of Interest (AOI)</label>
          <InteractiveMap
            aoi={formData.aoi}
            mode="draw"
            onAOIChange={(aoi) => setFormData({ ...formData, aoi })}
          />
          {formData.aoi && (
            <p className="text-sm text-gray-600 mt-2">✓ AOI selected</p>
          )}
        </div>
      </form>
    </div>
  );
};
```

---

## 10. IMPLEMENTATION PRIORITY & TIMELINE

### Phase 1: Foundation (Weeks 1-2)
**Focus:** Auth, DB, landing page, dashboard
- [ ] Supabase project setup + DB schema
- [ ] Authentication (login, signup, JWT)
- [ ] Landing page UI
- [ ] Dashboard with project list
- [ ] RLS policies
- [ ] React + Redux boilerplate

### Phase 2: Query Pipeline (Weeks 3-4) **CRITICAL**
**Focus:** Integration with legal brain
- [ ] Query Console page (text + map + dates)
- [ ] Real-time query parsing feedback
- [ ] Image upload to Cloudinary
- [ ] `/api/query/submit` endpoint
- [ ] WebSocket connection for streaming progress
- [ ] Data Explorer page (preview scenes)
- [ ] **Coordinate with friend on:** Legal brain API spec, request/response formats

### Phase 3: Results Visualization (Weeks 5-6)
**Focus:** Analysis Workspace + interactive maps
- [ ] Analysis Workspace (RGB viewer, change map, stats)
- [ ] Time Machine (animated slider)
- [ ] Evidence Explorer (trace findings)
- [ ] Findings Summary (with LLM insights)
- [ ] VQA Panel component
- [ ] Charts & statistics cards

### Phase 4: Reports & Polish (Weeks 7-8)
**Focus:** Document generation, killer features
- [ ] Report Studio (section builder, preview)
- [ ] PDF export (PDFKit)
- [ ] DOCX export (docx library)
- [ ] GeoPackage export
- [ ] Cesium 3D viewer (killer feature)
- [ ] AI insights panel (Claude API)
- [ ] Projects Hub
- [ ] Settings page
- [ ] Copilot chatbot
- [ ] Error handling, testing, documentation

---

## 11. INTEGRATION POINTS WITH LEGAL BRAIN

### Critical Handoff: Query Understanding

**Your request:**
```json
POST /api/query/submit
{
  "projectId": "proj-123",
  "queryText": "Analyze urban expansion in Delhi 2019-2025",
  "aoi": {"type": "Polygon", "coordinates": [...]},
  "timeStart": "2019-01-01",
  "timeEnd": "2025-12-31",
  "modality": ["RGB", "MS", "SAR"]
}
```

**Friend's response (from legal brain):**
```json
{
  "queryId": "q-456",
  "parsedIntent": {
    "task": "change_detection",
    "entity": "urban_infrastructure",
    "aoi": {...},
    "timeRange": ["2019", "2025"],
    "requiredEvidence": ["RGB", "changeFormer", "multimodal"]
  },
  "estimatedTime": "5 minutes",
  "status": "processing"
}
```

### Real-time Streaming

```
WebSocket /analysis/{queryId}/stream

Friend sends updates like:
{ progress: 10, step: "Parsing query..." }
{ progress: 25, step: "Fetching Sentinel-2 imagery..." }
{ progress: 50, step: "Running ChangeFormer..." }
{ progress: 75, step: "Fusing multimodal results..." }
{ progress: 100, step: "Done", results: {...} }
```

### Results Callback

**Friend's final output:**
```json
{
  "resultId": "r-789",
  "analysisId": "a-123",
  "rgb_url": "https://cloudinary.com/.../rgb.jpg",
  "change_mask_url": "https://cloudinary.com/.../mask.png",
  "confidence_map": {
    "type": "FeatureCollection",
    "features": [
      {
        "geometry": {"type": "Polygon", "coordinates": [...]},
        "properties": {"confidence": 0.92, "changeType": "urban"}
      }
    ]
  },
  "findings": [
    "Urban expansion detected in eastern corridor (34% area growth)",
    "New infrastructure: roads, buildings covering 8.5 km²"
  ],
  "evidence": [
    {
      "claim": "Urban expansion",
      "model": "ChangeFormer",
      "confidence": 0.92,
      "satellite_scene": {
        "date": "2025-01-15",
        "sensor": "Sentinel-2",
        "resolution": "10m"
      }
    }
  ]
}
```

---

## 12. DEPLOYMENT & DevOps

### Frontend
- **Hosting:** Vercel or Netlify
- **CI/CD:** GitHub Actions
- **Env:** `.env.local` for development, `.env.production` for prod
- **Build:** `npm run build` → optimized React bundle

### Backend / Database
- **Supabase:** Managed PostgreSQL + Auth + Real-time
- **Cloudinary:** Image storage + CDN
- **API Gateway:** (Optional) Express middleware for custom logic

### Environment Variables

```
# .env.example
VITE_SUPABASE_URL=https://xxxxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyxxx...

VITE_CLOUDINARY_CLOUD_NAME=satquery
VITE_CLOUDINARY_UPLOAD_PRESET=unsigned_preset

VITE_LEGAL_BRAIN_API=http://localhost:5000/api  # Friend's backend
VITE_CLAUDE_API_KEY=sk-ant-xxx...

VITE_APP_NAME=SATQUERY
VITE_APP_VERSION=1.0.0
```

---

## 13. KEY CONTACTS & RESPONSIBILITIES

**Your role:**
- Frontend UI/UX implementation (11 pages)
- Backend API infrastructure (REST + WebSocket)
- Database schema + RLS policies
- Cloudinary integration
- Document generation
- Integration glue (connecting to legal brain)
- Deployment & DevOps

**Friend's role (Legal Brain):**
- P1: Query understanding (NLP parsing)
- P2: Data fetching (Google Earth Engine)
- P3: Validation & repair (geospatial checks)
- P4: Re-verification (evidence sufficiency)
- P5: Model orchestration (GeoChat, ChangeFormer, Prithvi, SARMAE, SkySense)

**Dependencies:**
- ✅ **Week 1:** Friend provides API endpoint specs + request/response schemas
- ✅ **Week 2:** Legal brain API accessible at agreed endpoint
- ✅ **Week 3:** Your `/query/submit` works with friend's backend
- ✅ **Week 4:** WebSocket streaming verified
- ✅ **Week 5+:** Results flowing correctly to visualization components

---

## 14. TESTING STRATEGY

### Unit Tests (Jest)
```typescript
// __tests__/components/InteractiveMap.test.tsx
describe('InteractiveMap', () => {
  it('should render Leaflet map', () => {
    render(<InteractiveMap />);
    expect(screen.getByRole('region')).toBeInTheDocument();
  });

  it('should call onAOIChange when polygon drawn', () => {
    const mock = jest.fn();
    render(<InteractiveMap onAOIChange={mock} />);
    // Simulate drawing
    fireEvent.click(screen.getByText('Draw'));
    expect(mock).toHaveBeenCalled();
  });
});
```

### Integration Tests (Cypress)
```typescript
// cypress/e2e/query.cy.ts
describe('Query Submission Flow', () => {
  it('should submit query and show results', () => {
    cy.visit('/analyze/new');
    cy.get('textarea[placeholder*="Question"]').type('Analyze urban expansion');
    cy.get('input[type="date"]').eq(0).type('2019-01-01');
    cy.get('input[type="date"]').eq(1).type('2025-12-31');
    cy.get('button:contains("Run Analysis")').click();
    cy.url().should('include', '/analysis/');
    cy.get('[data-testid="analysis-workspace"]').should('be.visible');
  });
});
```

---

## 15. SUCCESS CRITERIA (SIH)

### MVP (Minimum Viable Product)
- ✅ User can submit query with text + AOI + dates
- ✅ Integration with legal brain working
- ✅ Results displayed on interactive map
- ✅ PDF report generation
- ✅ Evidence traceability for key findings

### Nice-to-Have (if time permits)
- ✅ 3D Cesium viewer
- ✅ AI insights panel (Claude API)
- ✅ Multi-AOI batch analysis
- ✅ Copilot chatbot

### Demo Talking Points
1. **Problem:** Manual geospatial analysis takes days
2. **Solution:** Natural language query → AI analysis → instant reports
3. **Live demo:**
   - Submit query: "Analyze flooding in city X from 2023-2024"
   - Show real-time progress (legal brain working)
   - Display results: maps, statistics, evidence
   - Generate PDF report with one click
4. **Differentiator:** Full evidence traceability (claim → model → satellite → pixels)

---

## 16. RESOURCES & LINKS

### Documentation
- [React Docs](https://react.dev)
- [TypeScript](https://www.typescriptlang.org)
- [Redux Toolkit](https://redux-toolkit.js.org)
- [Tailwind CSS](https://tailwindcss.com)
- [Leaflet.js](https://leafletjs.com)
- [Supabase](https://supabase.com/docs)
- [Cloudinary](https://cloudinary.com/documentation)

### Tools
- **Design:** Figma (shared design file)
- **Code:** GitHub (repository)
- **Planning:** Notion/Trello (task tracking)
- **Communication:** Slack/Discord (team sync)

---

## SUMMARY

**SATQUERY AI** is a **geospatial intelligence platform** that combines:
1. **Legal Brain** (friend's AI): Understands queries, fetches data, runs models
2. **Your Frontend**: Provides UI for query submission, result exploration, report generation
3. **Database**: Stores projects, queries, results, documents
4. **Storage**: Cloudinary for satellite imagery, PDFs, exports

**Your 8-week roadmap:**
- **Week 1-2:** Foundation (auth, DB, landing page)
- **Week 3-4:** Query pipeline (console, integration with legal brain)
- **Week 5-6:** Results visualization (maps, temporal views, evidence)
- **Week 7-8:** Reports & killer features (PDF/DOCX/GeoPackage, 3D, AI insights)

**For hackathon (36 hours):**
- **0-6h:** Setup + auth
- **6-16h:** Query console + legal brain integration
- **16-24h:** Analysis workspace + maps
- **24-32h:** Report generation
- **32-36h:** Polish + demo

Good luck with implementation! 🚀