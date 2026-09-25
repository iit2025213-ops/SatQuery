import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
import traceback

from app.config import settings
from app.gee.tools import GEEToolLayer, GEEToolResponse

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------------
# Pydantic Schemas for Agent Response
# --------------------------------------------------------------------------------

class EvidenceItem(BaseModel):
    finding: Optional[str] = Field(None, description="The scientific finding")
    metric: Optional[str] = Field(None, description="The index or metric used (e.g. NDVI)")
    value: Optional[Any] = Field(None, description="The quantitative value if applicable")
    source: str = Field(default="GEE", description="Source of the evidence")
    
    class Config:
        extra = "allow"

class VisualEvidenceItem(BaseModel):
    type: str = Field(default="gee_raster", description="Type of visual evidence")
    index: Optional[str] = Field(None, description="The index visualized")
    date: Optional[str] = Field(None, description="Date of the imagery")
    period: Optional[dict] = Field(None, description="Time period if applicable")
    url: Optional[str] = Field(None, description="URL of the validated raster")
    source: str = Field(default="GEE", description="Source of the raster")
    observation: str = Field(..., description="The model's visual observation")
    
    class Config:
        extra = "allow"

class AgentResponse(BaseModel):
    answer: str = Field(..., description="The final, evidence-backed answer to the user's question.")
    findings: List[str] = Field(default_factory=list, description="Key bullet points summarizing the findings.")
    evidence: List[EvidenceItem] = Field(default_factory=list, description="Specific scientific evidence supporting the findings.")
    visual_evidence: List[VisualEvidenceItem] = Field(default_factory=list, description="Visual observations from GEE rasters.")
    limitations: List[str] = Field(default_factory=list, description="Limitations of the analysis (e.g. cloud cover, resolution).")
    tools_used: List[str] = Field(default_factory=list, description="Names of the GEE tools executed.")
    source: str = Field(default="GEE", description="Source of the scientific data.")
    timeline_artifact: Optional[Dict[str, Any]] = Field(default=None, description="The complete timeline artifact dictionary returned by gee_generate_timeline_artifact, if requested.")
    provenance_status: Optional[str] = Field(default="degraded", description="Status of backend provenance persistence (complete or degraded).")
    provenance: Optional[Dict[str, Any]] = Field(default=None, description="Backend-attached provenance metadata linking to evidence IDs.")
    quality: Dict[str, Any] = Field(default_factory=lambda: {"status": "sufficient", "issues": []}, description="Backend-assessed quality status")
    replanning: Dict[str, Any] = Field(default_factory=lambda: {"performed": False, "count": 0, "reason": ""}, description="Replanning state")

# --------------------------------------------------------------------------------
# OpenAI Tool Schemas
# --------------------------------------------------------------------------------

GEE_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "gee_search_imagery",
            "description": "Search for the best available imagery over an AOI within a date range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format"},
                    "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format"},
                    "max_cloud_cover": {"type": "integer", "description": "Maximum acceptable cloud cover percentage (default 20)"}
                },
                "required": ["start_date", "end_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gee_calculate_indices",
            "description": "Calculate specified remote sensing indices (NDVI, NDWI, NDBI, NBR) for a given scene and AOI.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scene_id": {"type": "string", "description": "The specific GEE scene ID to analyze"},
                    "indices": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["NDVI", "NDWI", "NDBI", "NBR"]},
                        "description": "List of indices to calculate"
                    }
                },
                "required": ["scene_id", "indices"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gee_get_zonal_statistics",
            "description": "Get extended zonal statistics (mean, min, max, stdDev) for the AOI on a specific scene.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scene_id": {"type": "string", "description": "The specific GEE scene ID to analyze"}
                },
                "required": ["scene_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gee_get_temporal_series",
            "description": "Retrieve a time series of index statistics across a date range to observe trends.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format"},
                    "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format"},
                    "indices": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["NDVI", "NDWI", "NDBI", "NBR"]},
                        "description": "List of indices to track"
                    }
                },
                "required": ["start_date", "end_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gee_compare_periods",
            "description": "Compare statistics between two distinct periods for change detection.",
            "parameters": {
                "type": "object",
                "properties": {
                    "period_1_start": {"type": "string", "description": "Start date of first period (YYYY-MM-DD)"},
                    "period_1_end": {"type": "string", "description": "End date of first period (YYYY-MM-DD)"},
                    "period_2_start": {"type": "string", "description": "Start date of second period (YYYY-MM-DD)"},
                    "period_2_end": {"type": "string", "description": "End date of second period (YYYY-MM-DD)"},
                    "indices": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["NDVI", "NDWI", "NDBI", "NBR"]},
                        "description": "List of indices to compare"
                    }
                },
                "required": ["period_1_start", "period_1_end", "period_2_start", "period_2_end"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gee_get_raster",
            "description": "Generate a visual raster URL for a specific index or RGB.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scene_id": {"type": "string", "description": "The specific GEE scene ID to visualize"},
                    "index_name": {"type": "string", "description": "The index to visualize, e.g. NDVI, or RGB"}
                },
                "required": ["scene_id", "index_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gee_calculate_change_area",
            "description": "Calculate the exact geographic area (km2) of change between two scenes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scene_id_1": {"type": "string", "description": "Baseline scene ID"},
                    "scene_id_2": {"type": "string", "description": "Comparison scene ID"},
                    "index_name": {"type": "string", "description": "Index to use for change detection (e.g. NDVI, NDBI)"},
                    "threshold": {"type": "number", "description": "The difference threshold to consider as change"},
                    "direction": {"type": "string", "enum": ["increase", "decrease"], "description": "Whether to look for an increase or decrease"}
                },
                "required": ["scene_id_1", "scene_id_2", "index_name", "threshold", "direction"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gee_detect_anomalies",
            "description": "Detect temporal anomalies based on historical z-score.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_scene_id": {"type": "string", "description": "Scene ID to check for anomalies"},
                    "index_name": {"type": "string", "description": "Index to use (e.g. NDVI, NDBI)"},
                    "threshold": {"type": "number", "description": "Z-score threshold for anomaly (e.g. 2.0)"},
                    "hist_start": {"type": "string", "description": "Start date for historical baseline (YYYY-MM-DD)"},
                    "hist_end": {"type": "string", "description": "End date for historical baseline (YYYY-MM-DD)"}
                },
                "required": ["target_scene_id", "index_name", "threshold", "hist_start", "hist_end"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gee_get_subregion_statistics",
            "description": "Calculate index statistics across a regular rectangular grid covering the AOI.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scene_id": {"type": "string", "description": "The specific GEE scene ID to analyze"},
                    "index_name": {"type": "string", "description": "Index to use (e.g. NDVI, NDBI)"},
                    "grid_size_deg": {"type": "number", "description": "Size of the grid cells in degrees (e.g. 0.05)"}
                },
                "required": ["scene_id", "index_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gee_calculate_overlap",
            "description": "Calculate spatial overlap between two separate change analyses (e.g. vegetation loss AND urban expansion).",
            "parameters": {
                "type": "object",
                "properties": {
                    "scene_id_1": {"type": "string", "description": "Baseline scene ID"},
                    "scene_id_2": {"type": "string", "description": "Comparison scene ID"},
                    "index_1": {"type": "string", "description": "First index (e.g. NDVI)"},
                    "threshold_1": {"type": "number", "description": "Difference threshold for first index"},
                    "dir_1": {"type": "string", "enum": ["increase", "decrease"], "description": "Direction for first index"},
                    "index_2": {"type": "string", "description": "Second index (e.g. NDBI)"},
                    "threshold_2": {"type": "number", "description": "Difference threshold for second index"},
                    "dir_2": {"type": "string", "enum": ["increase", "decrease"], "description": "Direction for second index"}
                },
                "required": ["scene_id_1", "scene_id_2", "index_1", "threshold_1", "dir_1", "index_2", "threshold_2", "dir_2"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gee_compare_indices",
            "description": "Compare two indices spatially within a single scene.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scene_id": {"type": "string", "description": "The specific GEE scene ID to analyze"},
                    "index_1": {"type": "string", "description": "First index (e.g. NDVI)"},
                    "index_2": {"type": "string", "description": "Second index (e.g. NDWI)"},
                    "operation": {"type": "string", "enum": ["spatial correlation", "difference", "ratio"], "description": "The comparison operation to perform"}
                },
                "required": ["scene_id", "index_1", "index_2", "operation"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gee_detect_hotspots",
            "description": "Detect significant clusters (hotspots) of change using spatial convolution.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scene_id_1": {"type": "string", "description": "Baseline scene ID"},
                    "scene_id_2": {"type": "string", "description": "Comparison scene ID"},
                    "index_name": {"type": "string", "description": "Index to use (e.g. NDVI, NDBI)"},
                    "threshold": {"type": "number", "description": "The difference threshold to consider as change"},
                    "direction": {"type": "string", "enum": ["increase", "decrease"], "description": "Whether to look for an increase or decrease"}
                },
                "required": ["scene_id_1", "scene_id_2", "index_name", "threshold", "direction"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gee_analyze_trend",
            "description": "Analyze long-term temporal trend of an index using linear fit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "index_name": {"type": "string", "description": "Index to use (e.g. NDVI, NDBI)"},
                    "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"}
                },
                "required": ["index_name", "start_date", "end_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gee_analyze_seasonality",
            "description": "Analyze seasonal amplitude and recurring patterns over a multi-year period.",
            "parameters": {
                "type": "object",
                "properties": {
                    "index_name": {"type": "string", "description": "Index to use (e.g. NDVI)"},
                    "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"}
                },
                "required": ["index_name", "start_date", "end_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gee_detect_temporal_breaks",
            "description": "Detect candidate structural change-points/deviations in a time series.",
            "parameters": {
                "type": "object",
                "properties": {
                    "index_name": {"type": "string", "description": "Index to use (e.g. NDVI)"},
                    "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                    "threshold": {"type": "number", "description": "Z-score threshold (e.g. 2.0)"}
                },
                "required": ["index_name", "start_date", "end_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gee_analyze_change_persistence",
            "description": "Calculate if a detected change persists over time or recovers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "index_name": {"type": "string"},
                    "pre_start": {"type": "string"},
                    "pre_end": {"type": "string"},
                    "post_start": {"type": "string"},
                    "post_end": {"type": "string"},
                    "threshold": {"type": "number"},
                    "direction": {"type": "string", "enum": ["increase", "decrease"]}
                },
                "required": ["index_name", "pre_start", "pre_end", "post_start", "post_end", "threshold", "direction"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gee_analyze_event_window",
            "description": "Compare exact windows before and after a specific event date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "index_name": {"type": "string"},
                    "event_date": {"type": "string"},
                    "pre_days": {"type": "number", "description": "Days before event to average"},
                    "post_days": {"type": "number", "description": "Days after event to average"}
                },
                "required": ["index_name", "event_date", "pre_days", "post_days"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gee_generate_timeline_artifact",
            "description": "Generate a complete interactive UI timeline and timelapse visualization artifact. Call this when the user asks for a visual timeline, timelapse, or to show how an area changed over time visually.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                    "interval_months": {"type": "number", "description": "Interval in months between frames (e.g. 3)"},
                    "include_analytics": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["trend", "seasonality", "temporal_breaks"]},
                        "description": "Optional Phase 6 analytics to run and embed in the timeline if specifically relevant to the query."
                    }
                },
                "required": ["start_date", "end_date"]
            }
        }
    }
]

# --------------------------------------------------------------------------------
# System Prompts
# --------------------------------------------------------------------------------

SYSTEM_PROMPT = """You are SatQuery, an intelligent geospatial analyst powered by Google Earth Engine. You talk to users naturally, like a knowledgeable expert colleague — not like a system generating a report.

═══════════════════════════════════════════════════════════════
CORE IDENTITY
═══════════════════════════════════════════════════════════════
You are conversational, clear, and helpful. You use real GEE measurements to ground every statement. You adapt your depth to what the user actually asked — a simple question gets a concise answer; a complex analysis gets a detailed one.

You NEVER produce:
  • Raw JSON or structured data dumps
  • Unasked-for report sections ("KEY FINDINGS", "LIMITATIONS", "EVIDENCE")
  • Internal tool names, IDs, or execution metadata
  • Uncertain claims stated as facts

You ALWAYS:
  • Write your `answer` as natural prose a human would say
  • Ground numbers in real GEE measurements (mention them naturally, not as bullet labels)
  • Adapt length and depth to the question
  • Acknowledge limitations naturally ("I only have one clear scene, so this might reflect a seasonal dip rather than a permanent change.")
  • Offer useful follow-ups when appropriate — as a single conversational sentence, not a list of buttons

═══════════════════════════════════════════════════════════════
SCIENTIFIC RULES (INVIOLABLE)
═══════════════════════════════════════════════════════════════
1. GEE = scientific computation. You = interpretation and communication.
2. NEVER invent measurements, dates, scene IDs, or index values.
3. NEVER claim causation without specific GEE persistence/trend evidence.
4. NEVER confuse seasonal variation with permanent change without seasonality analysis.
5. If evidence is missing, call the appropriate tool. If it is still missing after tools, acknowledge it gracefully.
6. When provided a satellite image, describe spatial patterns; do NOT invent NDVI/NDBI/etc. numbers from it.
7. The `evidence` field MUST be a JSON array, not a dictionary.

═══════════════════════════════════════════════════════════════
RESPONSE DEPTH — ADAPT TO THE QUESTION
═══════════════════════════════════════════════════════════════
Simple / conversational:
  → 1-3 natural paragraphs in `answer`. Populate `findings` only if there are ≥3 distinct key observations.

Standard analysis ("analyse vegetation"):
  → Natural answer with measurements woven in. Populate `findings` with key observations. Set `visual_evidence` if relevant rasters were seen.

Complex / temporal / multi-year:
  → Richer answer + `findings` + `visual_evidence` + suggest follow-up.

Report request ("make me a report"):
  → Mention that the report is being generated. Populate all fields fully.

═══════════════════════════════════════════════════════════════
WRITING STYLE
═══════════════════════════════════════════════════════════════
BAD:  "NDVI Mean = 0.42. Trend slope = 0.04935."
GOOD: "The vegetation index (NDVI) averaged around 0.42 across the area, and the fitted trend over the period is gently positive — about 0.049 per unit time — which suggests the area has been gradually greening."

BAD:  "Evidence Quality: insufficient. Replanning count: 1."
GOOD: "I ran a second pass of the temporal analysis to be more certain, since a single observation doesn't tell us about permanence."

BAD:  "Tools used: gee_analyze_trend, gee_search_imagery"
GOOD: (do not mention tool names in the answer at all)

═══════════════════════════════════════════════════════════════
CONTEXT AWARENESS
═══════════════════════════════════════════════════════════════
- The full conversation history is provided. Use it. If the user says "Has that changed?", refer back to what you just discussed.
- If the user says "Show me", return the most relevant visual evidence you already have.
- If the user asks about a different topic, pivot gracefully.

═══════════════════════════════════════════════════════════════
NO-IMAGERY HANDLING
═══════════════════════════════════════════════════════════════
- If tool result contains `"status": "NO_IMAGERY_AVAILABLE"`, the backend already tried a fallback. Do not retry.
- Tell the user naturally: "I couldn't find a clear Sentinel-2 scene for that date range and area. You could try widening the date window or relaxing the cloud threshold."
- If `"status": "FALLBACK_USED"`, tell the user what changed: "I didn't find a scene under 20% cloud cover, but I found one at 45% — so the image quality is slightly lower than usual."

═══════════════════════════════════════════════════════════════
TEMPORAL INTELLIGENCE
═══════════════════════════════════════════════════════════════
- Use gee_analyze_trend for trend; gee_analyze_seasonality for seasonality; gee_analyze_change_persistence for permanence.
- A slope is directional, not causal. A single anomaly is not a trend.
- Mention temporal caveats naturally, not as a "LIMITATIONS" heading.

═══════════════════════════════════════════════════════════════
RESPONSE FORMAT RULES
═══════════════════════════════════════════════════════════════
14. Your final answer MUST be the AgentResponse JSON schema. Fill:
    - `answer`: Natural prose (required always)
    - `findings`: Array of short factual bullets — ONLY for substantive analyses with ≥2 distinct findings
    - `evidence`: Scientific evidence items (required when GEE tools returned data)
    - `visual_evidence`: When you observed a satellite image
    - `limitations`: ONLY actionable, specific limitations (e.g. "Cloud cover obscured the eastern region"). NEVER include generic statistical disclaimers (e.g. "seasonality analysis was not feasible", "interpret with caution", "timestamp limitations").
    - `quality`: Set `status` appropriately; do NOT leak this to the user verbatim
    - `replanning`: Record internally; do NOT mention count or "replanning" in the answer

When you have gathered enough evidence, return the AgentResponse JSON. Never include raw tool output or internal metadata in the `answer` field.
"""


class GeoAgent:
    def __init__(self, tool_layer: GEEToolLayer = None, max_tool_calls: int = 5, deterministic: bool = False,
                 supabase_client=None, job_id: str = None, user_id: str = None,
                 max_replans: int = 2):
        self.tool_layer = tool_layer or GEEToolLayer()
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key is required to use the Geo-Agent.")
            
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url
        )
        self.model = settings.openai_model
        self.max_tool_calls = max_tool_calls
        self.temperature = 0.0 if deterministic else 0.7
        self.supabase_client = supabase_client
        self.job_id = job_id
        self.user_id = user_id
        self.generated_evidence_ids = []
        self.provenance_status = "complete"
        self.max_replans = max_replans
        self.replan_count = 0
        
    def _validate_evidence(self, question: str, tools_used: list) -> tuple[bool, str]:
        """
        Deterministically validate objective conditions of the evidence gathered 
        so far against the user's question.
        Returns (is_sufficient, reason_if_insufficient)
        """
        q_lower = question.lower()
        issues = []
        
        # Rule 1: Temporal / Trend requirements
        trend_keywords = ["trend", "permanently", "permanent", "decline", "persistence", "long-term", "collapsed"]
        if any(kw in q_lower for kw in trend_keywords):
            if "gee_analyze_trend" not in tools_used and "gee_analyze_change_persistence" not in tools_used:
                issues.append("Question requires temporal trend or persistence analysis, but only simple tools were used. Please call gee_analyze_trend or gee_analyze_change_persistence.")
                
        # Rule 2: Spatial / Change Extent requirements
        spatial_keywords = ["where", "extent", "location", "map", "area of change"]
        if any(kw in q_lower for kw in spatial_keywords):
            if "gee_calculate_change_area" not in tools_used and "gee_detect_hotspots" not in tools_used:
                issues.append("Question asks for spatial extent or location of change. Mean numerical statistics are insufficient. Please call gee_calculate_change_area or gee_detect_hotspots.")
                
        # Rule 3: Overlap requirements
        overlap_keywords = ["overlap", "coincide", "together"]
        if any(kw in q_lower for kw in overlap_keywords):
            if "gee_calculate_overlap" not in tools_used:
                issues.append("Question asks if phenomena overlap. Please call gee_calculate_overlap.")
                
        if issues:
            return False, " ".join(issues)
        return True, ""
        
    async def run(self, user_question: str, aoi_geojson: dict, start_date: str = None, end_date: str = None) -> AgentResponse:
        """
        Orchestrate the OpenAI tool-calling loop until a final answer is reached or max calls hit.
        """
        self.replan_count = 0  # Reset replan count for each run
        
        # Ensure GEE is authenticated
        await self.tool_layer.connector.authenticate()
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Area of Interest (AOI) provided: {json.dumps(aoi_geojson)}\n\nQuestion: {user_question}\nContext Dates: {start_date} to {end_date}"}
        ]
        
        tools_used = []
        call_count = 0
        vision_images_sent = 0
        max_vision_images = 3
        
        while call_count < self.max_tool_calls:
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=GEE_TOOLS_SCHEMA,
                    tool_choice="auto",
                    temperature=self.temperature
                )
                
                response_message = response.choices[0].message
                
                # If no tool calls, the agent thinks it's done!
                if not response_message.tool_calls:
                    # Let's ask it to format its final response into our strict Pydantic schema
                    schema_json = json.dumps(AgentResponse.model_json_schema(), indent=2)
                    
                    messages.append({"role": "assistant", "content": response_message.content or "I have finished my analysis."})
                    messages.append({
                        "role": "user", 
                        "content": f"You have enough evidence. Please format your final answer strictly according to this JSON schema:\n\n{schema_json}"
                    })
                    
                    final_response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=self.temperature,
                        response_format={"type": "json_object"}
                    )
                    
                    try:
                        raw_content = final_response.choices[0].message.content.strip()
                        import re
                        raw_content = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_content).strip()
                        final_json = json.loads(raw_content)
                        # Ensure tools_used is included
                        final_json["tools_used"] = list(set(tools_used))
                        
                        # Phase 12 Backend Evidence Validation
                        is_sufficient, reason = self._validate_evidence(user_question, tools_used)
                        if not is_sufficient and self.replan_count < self.max_replans:
                            logger.info(f"🔄 Backend Validation Failed: {reason}. Forcing replan {self.replan_count + 1}/{self.max_replans}")
                            self.replan_count += 1
                            
                            messages.append({
                                "role": "assistant",
                                "content": final_response.choices[0].message.content
                            })
                            
                            messages.append({
                                "role": "user",
                                "content": f"Your evidence is insufficient. {reason} Do not guess. You must call the appropriate GEE tools to gather missing evidence."
                            })
                            continue  # Continue the outer while loop (replan)
                            
                        # If we get here, it's either sufficient or max replans reached.
                        final_json["quality"] = {
                            "status": "sufficient" if is_sufficient else "insufficient",
                            "issues": [] if is_sufficient else [reason]
                        }
                        
                        final_json["replanning"] = {
                            "performed": self.replan_count > 0,
                            "count": self.replan_count,
                            "reason": reason if self.replan_count > 0 else ""
                        }
                        
                        # Deterministically attach provenance backend data
                        if self.supabase_client and self.job_id:
                            final_json["provenance_status"] = self.provenance_status
                            final_json["provenance"] = {
                                "job_id": self.job_id,
                                "evidence_ids": self.generated_evidence_ids
                            }

                        return AgentResponse(**final_json)
                    except Exception as e:
                        logger.error(f"Failed to parse AgentResponse schema: {e}")
                        # Fallback
                        return AgentResponse(
                            answer=response_message.content or final_response.choices[0].message.content or "Error parsing answer.",
                            tools_used=list(set(tools_used)),
                            provenance_status=self.provenance_status if self.supabase_client else "unavailable",
                            provenance={"job_id": self.job_id, "evidence_ids": self.generated_evidence_ids} if self.supabase_client and self.job_id else None,
                            quality={"status": "insufficient", "issues": ["Error parsing response"]},
                            replanning={"performed": self.replan_count > 0, "count": self.replan_count, "reason": "Error parsing response"}
                        )

                # Process Tool Calls
                messages.append(response_message)
                
                for tool_call in response_message.tool_calls:
                    call_count += 1
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    
                    logger.info(f"🤖 Agent executing tool: {function_name} with args: {arguments}")
                    tools_used.append(function_name)
                    
                    tool_result = await self._execute_tool(function_name, arguments, aoi_geojson)

                    # ── Short-circuit: no imagery found ───────────────────────────────
                    if isinstance(tool_result, dict) and tool_result.get("status") == "NO_IMAGERY_AVAILABLE":
                        logger.info("NO_IMAGERY_AVAILABLE sentinel received — short-circuiting agent loop.")
                        fallback_tried = tool_result.get("fallback_attempted", False)
                        cloud_max = tool_result.get("original_cloud_max", 20)
                        suggestion = tool_result.get("suggestion", "Try a wider date range or increase the cloud-cover threshold.")
                        limitations = [f"No Sentinel-2 scene satisfied the requested criteria (cloud ≤ {cloud_max}%)."]
                        if fallback_tried:
                            limitations.append(f"A fallback search up to {self._FALLBACK_CLOUD_MAX}% also found nothing.")
                        return AgentResponse(
                            answer=(
                                f"⚠️ No suitable Sentinel-2 imagery was found for the selected area and date range.\n\n"
                                f"{tool_result.get('message', '')}\n\n"
                                f"{suggestion}"
                            ),
                            findings=[],
                            evidence=[],
                            visual_evidence=[],
                            limitations=limitations,
                            tools_used=list(set(tools_used)),
                            quality={"status": "insufficient", "issues": ["No suitable imagery was available."]},
                            provenance_status="unavailable",
                            provenance={"job_id": self.job_id, "evidence_ids": []} if self.job_id else None,
                            replanning={"performed": False, "count": 0, "reason": "No imagery available"}
                        )
                    # ─────────────────────────────────────────────────────────────────

                    # Base message content is the text result
                    tool_content = [{"type": "text", "text": json.dumps(tool_result, default=str)}]
                    
                    # If the tool returned visuals and we haven't hit the limit, try to fetch them
                    if "visuals" in tool_result and vision_images_sent < max_vision_images:
                        for url in tool_result.get("visuals", []):
                            if vision_images_sent >= max_vision_images:
                                break
                            
                            valid, b64_img = await self._validate_and_fetch_raster(url)
                            if valid and b64_img:
                                logger.info(f"👁️ Appending validated GEE raster to LLM context (Image {vision_images_sent + 1}/{max_vision_images})")
                                tool_content.append({
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/png;base64,{b64_img}"}
                                })
                                vision_images_sent += 1
                            else:
                                logger.warning(f"⚠️ Failed to validate GEE raster URL: {url}")
                                tool_result["visual_validation_error"] = "Image could not be fetched or validated."
                    
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": tool_content if len(tool_content) > 1 else tool_content[0]["text"]
                    })
                    
            except Exception as e:
                logger.error(f"Agent loop error: {traceback.format_exc()}")
                return AgentResponse(
                    answer=f"The agent encountered an error: {str(e)}",
                    tools_used=list(set(tools_used))
                )
                
        # If we hit max calls, force it to answer with what it has
        schema_json = json.dumps(AgentResponse.model_json_schema(), indent=2)
        messages.append({
            "role": "user", 
            "content": f"You have reached the maximum allowed tool calls. Please format your final answer based ONLY on the evidence gathered so far, strictly according to this JSON schema:\n\n{schema_json}"
        })
        
        try:
            final_response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            final_json = json.loads(final_response.choices[0].message.content)
            final_json["tools_used"] = list(set(tools_used))
            
            # Since max calls reached, we might not satisfy the condition, but we return what we have
            is_sufficient, reason = self._validate_evidence(user_question, tools_used)
            final_json["quality"] = {
                "status": "sufficient" if is_sufficient else "insufficient",
                "issues": [] if is_sufficient else [reason, "Maximum tool calls reached."]
            }
            final_json["replanning"] = {
                "performed": self.replan_count > 0,
                "count": self.replan_count,
                "reason": reason if self.replan_count > 0 else ""
            }
            
            if self.supabase_client and self.job_id:
                final_json["provenance_status"] = self.provenance_status
                final_json["provenance"] = {
                    "job_id": self.job_id,
                    "evidence_ids": self.generated_evidence_ids
                }
                
            return AgentResponse(**final_json)
        except Exception as e:
            return AgentResponse(
                answer="Analysis incomplete due to maximum tool call limit reached.",
                limitations=["Maximum tool calls reached."],
                tools_used=list(set(tools_used)),
                provenance_status=self.provenance_status if self.supabase_client else "unavailable",
                provenance={"job_id": self.job_id, "evidence_ids": self.generated_evidence_ids} if self.supabase_client and self.job_id else None,
                quality={"status": "insufficient", "issues": ["Maximum tool calls reached."]},
                replanning={"performed": self.replan_count > 0, "count": self.replan_count, "reason": "Max tool calls reached"}
            )

    # Maximum cloud cover to use in fallback — bounded by backend policy
    _FALLBACK_CLOUD_MAX = 50

    async def _execute_tool(self, function_name: str, arguments: dict, aoi_geojson: dict) -> dict:
        """Route tool calls to the GEEToolLayer."""
        try:
            if function_name == "gee_search_imagery":
                requested_cloud = arguments.get("max_cloud_cover", 20)
                res = await self.tool_layer.gee_search_imagery(
                    aoi=aoi_geojson,
                    start_date=arguments.get("start_date"),
                    end_date=arguments.get("end_date"),
                    max_cloud_cover=requested_cloud
                )

                # ── Controlled fallback (backend-only, at most once) ──────────────
                if not res.success:
                    fallback_cloud = self._FALLBACK_CLOUD_MAX
                    if requested_cloud < fallback_cloud:
                        logger.info(
                            f"No imagery at cloud<={requested_cloud}%. "
                            f"Attempting fallback at cloud<={fallback_cloud}%."
                        )
                        fallback_res = await self.tool_layer.gee_search_imagery(
                            aoi=aoi_geojson,
                            start_date=arguments.get("start_date"),
                            end_date=arguments.get("end_date"),
                            max_cloud_cover=fallback_cloud
                        )
                        if fallback_res.success:
                            # Return success but flag that a fallback was used
                            fb_dict = fallback_res.model_dump()
                            fb_dict["status"] = "FALLBACK_USED"
                            fb_dict["fallback_cloud_max"] = fallback_cloud
                            fb_dict["original_cloud_max"] = requested_cloud
                            fb_dict["message"] = (
                                f"No scene met the requested {requested_cloud}% cloud limit. "
                                f"A fallback search up to {fallback_cloud}% found "
                                f"{len(fb_dict.get('data', {}).get('scenes', []))} scene(s)."
                            )
                            logger.info(fb_dict["message"])
                            # Save evidence for the fallback scene
                            if self.supabase_client and self.job_id:
                                try:
                                    ev_id = await self._save_evidence(function_name, arguments, fb_dict)
                                    fb_dict["evidence_id"] = ev_id
                                    self.generated_evidence_ids.append(ev_id)
                                except Exception as ev_err:
                                    logger.error(f"Evidence save failed (fallback): {ev_err}")
                                    self.provenance_status = "partial"
                            return fb_dict

                    # Both primary and fallback (or fallback not applicable) failed
                    return {
                        "status": "NO_IMAGERY_AVAILABLE",
                        "success": False,
                        "original_cloud_max": requested_cloud,
                        "fallback_attempted": requested_cloud < self._FALLBACK_CLOUD_MAX,
                        "message": (
                            f"No suitable Sentinel-2 imagery was found for the selected AOI "
                            f"and date range. Primary search used cloud<={requested_cloud}%. "
                            + (f"A fallback up to {self._FALLBACK_CLOUD_MAX}% also found nothing."
                               if requested_cloud < self._FALLBACK_CLOUD_MAX else "")
                        ),
                        "suggestion": "Try a wider date range or increase the cloud-cover threshold."
                    }
            elif function_name == "gee_calculate_indices":
                res = await self.tool_layer.gee_calculate_indices(
                    aoi=aoi_geojson,
                    scene_id=arguments.get("scene_id"),
                    indices=arguments.get("indices", [])
                )
            elif function_name == "gee_get_zonal_statistics":
                res = await self.tool_layer.gee_get_zonal_statistics(
                    aoi=aoi_geojson,
                    scene_id=arguments.get("scene_id")
                )
            elif function_name == "gee_get_temporal_series":
                res = await self.tool_layer.gee_get_temporal_series(
                    aoi=aoi_geojson,
                    start_date=arguments.get("start_date"),
                    end_date=arguments.get("end_date"),
                    indices=arguments.get("indices")
                )
            elif function_name == "gee_compare_periods":
                period_1 = {
                    "start_date": arguments.get("period_1_start"),
                    "end_date": arguments.get("period_1_end")
                }
                period_2 = {
                    "start_date": arguments.get("period_2_start"),
                    "end_date": arguments.get("period_2_end")
                }
                res = await self.tool_layer.gee_compare_periods(
                    aoi=aoi_geojson,
                    period_1=period_1,
                    period_2=period_2,
                    indices=arguments.get("indices", ["NDVI", "NDBI"])
                )
            elif function_name == "gee_get_raster":
                res = await self.tool_layer.gee_get_raster(
                    aoi=aoi_geojson,
                    scene_id=arguments.get("scene_id"),
                    index_name=arguments.get("index_name")
                )
            elif function_name == "gee_calculate_change_area":
                res = await self.tool_layer.gee_calculate_change_area(
                    aoi=aoi_geojson,
                    scene_id_1=arguments.get("scene_id_1"),
                    scene_id_2=arguments.get("scene_id_2"),
                    index_name=arguments.get("index_name"),
                    threshold=arguments.get("threshold"),
                    direction=arguments.get("direction")
                )
            elif function_name == "gee_detect_anomalies":
                res = await self.tool_layer.gee_detect_anomalies(
                    aoi=aoi_geojson,
                    target_scene_id=arguments.get("target_scene_id"),
                    index_name=arguments.get("index_name"),
                    threshold=arguments.get("threshold"),
                    hist_start=arguments.get("hist_start"),
                    hist_end=arguments.get("hist_end")
                )
            elif function_name == "gee_get_subregion_statistics":
                res = await self.tool_layer.gee_get_subregion_statistics(
                    aoi=aoi_geojson,
                    scene_id=arguments.get("scene_id"),
                    index_name=arguments.get("index_name"),
                    grid_size_deg=arguments.get("grid_size_deg", 0.05)
                )
            elif function_name == "gee_calculate_overlap":
                res = await self.tool_layer.gee_calculate_overlap(
                    aoi=aoi_geojson,
                    scene_id_1=arguments.get("scene_id_1"),
                    scene_id_2=arguments.get("scene_id_2"),
                    index_1=arguments.get("index_1"),
                    threshold_1=arguments.get("threshold_1"),
                    dir_1=arguments.get("dir_1"),
                    index_2=arguments.get("index_2"),
                    threshold_2=arguments.get("threshold_2"),
                    dir_2=arguments.get("dir_2")
                )
            elif function_name == "gee_compare_indices":
                res = await self.tool_layer.gee_compare_indices(
                    aoi=aoi_geojson,
                    scene_id=arguments.get("scene_id"),
                    index_1=arguments.get("index_1"),
                    index_2=arguments.get("index_2"),
                    operation=arguments.get("operation")
                )
            elif function_name == "gee_detect_hotspots":
                res = await self.tool_layer.gee_detect_hotspots(
                    aoi=aoi_geojson,
                    scene_id_1=arguments.get("scene_id_1"),
                    scene_id_2=arguments.get("scene_id_2"),
                    index_name=arguments.get("index_name"),
                    threshold=arguments.get("threshold"),
                    direction=arguments.get("direction")
                )
            elif function_name == "gee_analyze_trend":
                res = await self.tool_layer.gee_analyze_trend(
                    aoi=aoi_geojson,
                    index_name=arguments.get("index_name"),
                    start_date=arguments.get("start_date"),
                    end_date=arguments.get("end_date")
                )
            elif function_name == "gee_analyze_seasonality":
                res = await self.tool_layer.gee_analyze_seasonality(
                    aoi=aoi_geojson,
                    index_name=arguments.get("index_name"),
                    start_date=arguments.get("start_date"),
                    end_date=arguments.get("end_date")
                )
            elif function_name == "gee_detect_temporal_breaks":
                res = await self.tool_layer.gee_detect_temporal_breaks(
                    aoi=aoi_geojson,
                    index_name=arguments.get("index_name"),
                    start_date=arguments.get("start_date"),
                    end_date=arguments.get("end_date"),
                    threshold=arguments.get("threshold", 2.0)
                )
            elif function_name == "gee_analyze_change_persistence":
                res = await self.tool_layer.gee_analyze_change_persistence(
                    aoi=aoi_geojson,
                    index_name=arguments.get("index_name"),
                    pre_start=arguments.get("pre_start"),
                    pre_end=arguments.get("pre_end"),
                    post_start=arguments.get("post_start"),
                    post_end=arguments.get("post_end"),
                    threshold=arguments.get("threshold"),
                    direction=arguments.get("direction")
                )
            elif function_name == "gee_analyze_event_window":
                res = await self.tool_layer.gee_analyze_event_window(
                    aoi=aoi_geojson,
                    index_name=arguments.get("index_name"),
                    event_date=arguments.get("event_date"),
                    pre_days=arguments.get("pre_days", 90),
                    post_days=arguments.get("post_days", 90)
                )
            elif function_name == "gee_generate_timeline_artifact":
                res_dict = await self.tool_layer.gee_generate_timeline_artifact(
                    aoi=aoi_geojson,
                    start_date=arguments.get("start_date"),
                    end_date=arguments.get("end_date"),
                    interval_months=arguments.get("interval_months", 3),
                    include_analytics=arguments.get("include_analytics", [])
                )
                return res_dict
            
            res_dict = res.model_dump()
            
            # Save to Evidence Graph if supabase is available and it's a success
            if res.success and self.supabase_client and self.job_id:
                try:
                    evidence_id = await self._save_evidence(function_name, arguments, res_dict)
                    res_dict["evidence_id"] = evidence_id
                    self.generated_evidence_ids.append(evidence_id)
                except Exception as e:
                    logger.error(f"Failed to save evidence for {function_name}: {e}")
                    self.provenance_status = "partial"
                    
            return res_dict
            
        except Exception as e:
            return {"error": str(e)}

    async def _save_evidence(self, tool_name: str, arguments: dict, res_dict: dict) -> str:
        import hashlib
        import uuid
        import json
        
        # Create a deterministic fingerprint from core scientific data
        core_data = res_dict.get("data", {})
        fingerprint_input = json.dumps({
            "tool": tool_name,
            "args": arguments,
            "data": core_data
        }, sort_keys=True).encode("utf-8")
        
        fingerprint_hash = hashlib.sha256(fingerprint_input).hexdigest()
        
        # Get scalar metric/value if simple dict
        metric = None
        value = None
        unit = None
        if len(core_data) == 1:
            for k, v in core_data.items():
                if isinstance(v, (int, float)):
                    metric = k
                    value = float(v)
        elif "slope" in core_data:
            metric = "trend_slope"
            value = float(core_data["slope"])
        elif "break_count" in core_data:
            metric = "break_count"
            value = float(core_data["break_count"])
            
        scene_ids = res_dict.get("metadata", {}).get("scene_ids", [])
        if not scene_ids and "scene_id" in arguments:
            scene_ids = [arguments["scene_id"]]
            
        evidence_id = str(uuid.uuid4())
        
        # Embed core_data into parameters so ReportPlanner can access multiple metrics
        enhanced_parameters = dict(arguments)
        if isinstance(core_data, dict):
            enhanced_parameters["raw_data"] = core_data
        
        # Embed metric/value/unit into parameters
        if metric:
            enhanced_parameters["metric"] = metric
        if value is not None:
            enhanced_parameters["value"] = value
        if unit:
            enhanced_parameters["unit"] = unit
            
        record = {
            "evidence_id": evidence_id,
            "job_id": self.job_id,
            "user_id": self.user_id,
            "source": res_dict.get("source", "GEE"),
            "tool_name": tool_name,
            "parameters": enhanced_parameters,
            "scene_ids": scene_ids,
            "quality_metadata": res_dict.get("quality", {}),
        }

        
        # Use sync client or admin client
        admin_client = self.supabase_client.get_admin_client()
        admin_client.table("evidence").insert(record).execute()
        return evidence_id

    async def _validate_and_fetch_raster(self, url: str) -> tuple[bool, str]:
        """
        Validates that a GEE raster URL is alive, returns an image, and fetches it as base64.
        """
        import httpx
        import base64
        
        if not url or not url.startswith("http"):
            return False, ""
            
        try:
            async with httpx.AsyncClient() as http_client:
                resp = await http_client.get(url, timeout=30.0)
                
                if resp.status_code == 200:
                    content_type = resp.headers.get("content-type", "")
                    if "image" in content_type:
                        b64 = base64.b64encode(resp.content).decode("utf-8")
                        return True, b64
                        
                return False, ""
        except Exception as e:
            logger.error(f"Raster validation failed for {url}: {e}")
            return False, ""
