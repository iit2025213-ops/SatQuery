# app/api/v1/chat.py

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Optional
import logging
from openai import AsyncOpenAI

from app.config import settings
from app.auth.dependencies import get_current_user_id

logger = logging.getLogger("satquery")
router = APIRouter(prefix="/api/v1", tags=["chat"])

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    aoi: Optional[dict] = None
    mapbox_image: Optional[str] = None
    job_id: Optional[str] = None
    use_agent: bool = False

@router.post("/chat")
async def chat_interactive(
    request: ChatRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Simple interactive chat endpoint using the configured OpenAI key"""
    if not settings.openai_api_key:
        raise HTTPException(status_code=400, detail="OpenAI API key is not configured in the backend.")

    try:
        from app.main import gee_connector
        from datetime import datetime, timezone, timedelta
        import httpx
        
        system_content = """You are SatQuery AI, an intelligent geospatial analyst assistant. You are conversational, helpful, and grounded. When an area has been analysed you may reference those measurements. When no analysis has been done yet, suggest what the user can explore. Be concise and natural — like an expert colleague."""
        
        # ── Intent classifier: is this a GEE analysis request? ────────────────
        latest_user_msg = request.messages[-1].content if request.messages else ""
        CONVERSATIONAL_PHRASES = [
            "hi", "hello", "hey", "thanks", "thank you", "ok", "okay",
            "what can you", "what can you do", "help", "who are you",
            "what are you", "good morning", "good evening", "bye",
        ]
        ANALYSIS_KEYWORDS = [
            "analyse", "analyze", "vegetation", "ndvi", "ndbi", "ndwi", "nbr",
            "urban", "built-up", "water", "burn", "fire", "deforestation",
            "change", "trend", "timeline", "timelapse", "temporal",
            "flood", "drought", "cropland", "land use", "land cover",
            "hotspot", "anomaly", "seasonal", "compare", "report",
            "satellite", "sentinel", "gee", "imagery", "area",
            "show me", "what's happening", "what is happening", "how is",
            "has it changed", "has that changed", "is it",
        ]
        msg_lower = latest_user_msg.lower().strip()
        is_casual = (
            any(msg_lower == p or msg_lower.startswith(p + " ") or msg_lower.startswith(p + "!") for p in CONVERSATIONAL_PHRASES)
            and not any(kw in msg_lower for kw in ANALYSIS_KEYWORDS)
        )
        # Also skip agent if no AOI is drawn and message has no analytical intent
        has_analytical_intent = any(kw in msg_lower for kw in ANALYSIS_KEYWORDS)
        skip_agent = is_casual or (not request.aoi and not has_analytical_intent)
        
        # Quick GEE context for non-agent path — skipped for casual messages
        # (GEE context not needed for "Hi", "thanks", etc.)
        if request.aoi and not request.use_agent and not is_casual:
            try:
                await gee_connector.authenticate()
                now = datetime.now(timezone.utc)
                thirty_days_ago = now - timedelta(days=30)
                
                scenes = await gee_connector.query_sentinel2(
                    aoi_geojson=request.aoi,
                    date_start=thirty_days_ago.strftime("%Y-%m-%d"),
                    date_end=now.strftime("%Y-%m-%d"),
                    max_results=1
                )
                
                if scenes:
                    stats = await gee_connector.get_spatial_stats(scenes[0]["id"], request.aoi)
                    if stats:
                        system_content += "\n\nContext for the current drawn area (computed from Google Earth Engine):\n"
                        system_content += f"NDVI (Vegetation Health: -1 to 1): {stats.get('ndvi_mean', 'N/A')}\n"
                        system_content += f"NDWI (Water Bodies: -1 to 1): {stats.get('ndwi_mean', 'N/A')}\n"
                        system_content += f"NDBI (Built-up/Urban: -1 to 1): {stats.get('ndbi_mean', 'N/A')}\n"
                        system_content += f"NBR (Burn Scars: -1 to 1): {stats.get('nbr_mean', 'N/A')}\n"
                        system_content += "Use these exact scientific measurements to inform your visual analysis."
            except Exception as gee_ctx_err:
                logger.warning(f"GEE context fetch skipped: {gee_ctx_err}")

        
        client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url
        )
        
        messages = [{"role": "system", "content": system_content}]
        
        # Add all historical messages
        for m in request.messages[:-1]:
            messages.append({"role": m.role, "content": m.content})
            
        # Add the latest message
        if request.messages:
            latest_msg = request.messages[-1]
            user_content = [{"type": "text", "text": latest_msg.content}]
            
            # Mapbox imagery is for UI context only, NEVER for Phase 3/4 scientific reasoning
            if request.mapbox_image and not request.use_agent:
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": request.mapbox_image}
                })
                
            messages.append({"role": latest_msg.role, "content": user_content})
            
        # -------------------------------------------------------------
        # Feature Flag: Use Geo-Agent (Phase 3) vs Legacy GPT (Phase 1)
        # -------------------------------------------------------------
        timeline_data = None
        provenance_status = None
        provenance = None
        findings = []
        visual_evidence = []
        quality = {"status": "sufficient", "issues": []}
        limitations = []
        replanning = {"performed": False, "count": 0}
        tools_used = []
        if request.use_agent and request.aoi and request.messages and not skip_agent:
            from app.agents.geo_agent import GeoAgent
            from app.main import supabase_client
            import uuid
            
            logger.info("🧠 Routing query to Phase 3 Geo-Agent...")

            # Build full conversation history for multi-turn context
            conversation_history = []
            for m in request.messages[:-1]:
                conversation_history.append({"role": m.role, "content": m.content})
                
            agent = GeoAgent(
                supabase_client=supabase_client,
                job_id=request.job_id,
                user_id=user_id
            )

            # Pass the full prior conversation into the agent's system context
            if conversation_history:
                history_summary = "\n".join(
                    f"{m['role'].upper()}: {m['content'][:300]}"
                    for m in conversation_history[-6:]  # last 3 turns
                )
                agent_question = (
                    f"[Prior conversation context]\n{history_summary}\n\n"
                    f"[Current question]\n{latest_user_msg}"
                )
            else:
                agent_question = latest_user_msg
            
            now = datetime.now(timezone.utc)
            thirty_days_ago = now - timedelta(days=30)
            
            agent_response = await agent.run(
                user_question=agent_question,
                aoi_geojson=request.aoi,
                start_date=thirty_days_ago.strftime("%Y-%m-%d"),
                end_date=now.strftime("%Y-%m-%d")
            )
            
            # Override AI answer with Agent's structured answer
            ai_answer = agent_response.answer
            
            # Extract all structured fields for the frontend
            timeline_data = agent_response.timeline_artifact
            provenance_status = getattr(agent_response, "provenance_status", None)
            provenance = getattr(agent_response, "provenance", None)
            findings = [str(f) for f in agent_response.findings] if agent_response.findings else []
            visual_evidence = [v.model_dump() if hasattr(v, 'model_dump') else (v.dict() if hasattr(v, 'dict') else v) for v in agent_response.visual_evidence] if agent_response.visual_evidence else []
            quality = agent_response.quality if agent_response.quality else {"status": "sufficient", "issues": []}
            limitations = list(agent_response.limitations) if agent_response.limitations else []
            replanning = agent_response.replanning if agent_response.replanning else {"performed": False, "count": 0}
            tools_used = list(agent_response.tools_used) if agent_response.tools_used else []
        else:
            # Legacy GPT execution
            response = await client.chat.completions.create(
                model=settings.openai_model,
                messages=messages,
                max_tokens=500
            )
            ai_answer = response.choices[0].message.content
            
        # -------------------------------------------------------------
        # Selective Media Generation
        # -------------------------------------------------------------
        media = {"images": [], "videos": []}
        if request.use_agent and request.job_id:
            try:
                from app.main import cloudinary_client, supabase_client, gee_connector
                from datetime import datetime, timezone, timedelta
                import httpx

                # ── Authenticate GEE (deferred) ──────────────────────────────────
                await gee_connector.authenticate()

                # Force schema cache reload to fix PGRST204
                try:
                    supabase_client.get_admin_client().rpc("reload_schema_cache", {}).execute()
                except Exception:
                    # In case the RPC doesn't exist, try falling back or ignoring
                    pass

                evidence_res = supabase_client.get_admin_client().table("evidence").select("*").eq("job_id", request.job_id).execute()
                evidence_records = evidence_res.data or []

                # Collect index names and scene_ids from evidence
                required_indices = set()
                scene_ids_ordered = []       # preserves insertion order (chronological from GEE calls)
                start_date_str = None
                end_date_str = None

                for rec in evidence_records:
                    tool = rec.get("tool_name", "")
                    params = rec.get("parameters", {})
                    if tool in ["gee_analyze_trend", "gee_search_imagery", "gee_get_spatial_stats",
                                "gee_analyze_change_persistence", "gee_analyze_seasonality",
                                "gee_detect_temporal_breaks", "gee_calculate_indices", "gee_get_temporal_series"]:
                        idx = params.get("index_name")
                        if idx:
                            required_indices.add(idx.upper())
                        if not start_date_str:
                            start_date_str = params.get("start_date")
                        if not end_date_str:
                            end_date_str = params.get("end_date")
                    for sid in (rec.get("scene_ids") or []):
                        if sid not in scene_ids_ordered:
                            scene_ids_ordered.append(sid)

                # ── Query-aware index inference ──────────────────────────────────
                # Always scan the user query to ensure requested indices are rendered
                # even if the agent didn't explicitly create an evidence record for them.
                q_lower = latest_user_msg.lower()
                if any(kw in q_lower for kw in [
                    "urban", "built-up", "built up", "city", "cities",
                    "construction", "impervious", "concrete", "urbanis", "urbaniz",
                ]):
                    required_indices.add("NDBI")
                
                if any(kw in q_lower for kw in [
                    "water", "flood", "river", "lake", "wetland",
                    "inundation", "moisture", "rainfall",
                ]):
                    required_indices.add("NDWI")
                
                if any(kw in q_lower for kw in [
                    "fire", "burn", "wildfire", "scorched", "nbr",
                    "forest fire", "burned",
                ]):
                    required_indices.add("NBR")
                
                if any(kw in q_lower for kw in [
                    "deforest", "forest", "tree", "canopy", "cropland",
                    "agriculture", "farm", "plantation", "vegetation",
                ]):
                    required_indices.add("NDVI")
                
                if not required_indices:
                    # Temporal / change / general → default to NDVI
                    required_indices.add("NDVI")                # Pull RGB from gee_assets (already uploaded by the GEE worker)
                assets_res = supabase_client.get_admin_client().table("gee_assets").select(
                    "cloudinary_url,scene_id,source,acquisition_date"
                ).eq("job_id", request.job_id).execute()

                for asset in (assets_res.data or []):
                    asset_url = asset.get("cloudinary_url")
                    src = asset.get("source", "")
                    if asset_url and ("rgb" in src.lower()):
                        media["images"].append({
                            "type": "gee_raster",
                            "index": "RGB",
                            "url": asset_url,
                            "source": "GEE",
                            "caption": "True-colour (RGB) — latest scene"
                        })
                    if asset.get("scene_id") and asset["scene_id"] not in scene_ids_ordered:
                        scene_ids_ordered.append(asset["scene_id"])

                # ── Before / After NDVI comparison ──────────────────────────────
                # Try to find two scenes: earliest in period (before) and latest (after)
                # If we already have ordered scene IDs from evidence, use first/last.
                # Otherwise query Sentinel-2 for the full period.
                if request.aoi:
                    now = datetime.now(timezone.utc)
                    one_year_ago = now - timedelta(days=365)
                    period_start = start_date_str or one_year_ago.strftime("%Y-%m-%d")
                    period_end   = end_date_str   or now.strftime("%Y-%m-%d")

                    # If we don't have ≥2 scene IDs, query GEE for the period
                    if len(scene_ids_ordered) < 2:
                        try:
                            all_scenes = await gee_connector.query_sentinel2(
                                aoi_geojson=request.aoi,
                                date_start=period_start,
                                date_end=period_end,
                                max_results=50
                            )
                            # Sort by acquisition date
                            all_scenes_sorted = sorted(
                                all_scenes,
                                key=lambda s: s.get("date", s.get("acquisition_date", ""))
                            )
                            new_ids = [s["id"] for s in all_scenes_sorted if s.get("id")]
                            # Prepend/append without duplication
                            for sid in new_ids:
                                if sid not in scene_ids_ordered:
                                    scene_ids_ordered.append(sid)
                        except Exception as q_err:
                            logger.warning(f"Could not query scenes for before/after: {q_err}")

                    before_scene = scene_ids_ordered[0]  if scene_ids_ordered else None
                    after_scene  = scene_ids_ordered[-1] if scene_ids_ordered else None

                    async with httpx.AsyncClient() as http_client:
                        for idx in list(required_indices):
                            pairs = []
                            if period_start and period_end and period_start != period_end:
                                d1_end = (datetime.strptime(period_start, "%Y-%m-%d") + timedelta(days=90)).strftime("%Y-%m-%d")
                                d2_start = (datetime.strptime(period_end, "%Y-%m-%d") - timedelta(days=90)).strftime("%Y-%m-%d")
                                pairs = [
                                    (None, f"{idx} — Start of period (before)", period_start, d1_end),
                                    (None, f"{idx} — End of period (after)", d2_start, period_end),
                                ]
                            elif before_scene and after_scene and before_scene != after_scene:
                                pairs = [
                                    (before_scene, f"{idx} — Start of period (before)", None, None),
                                    (after_scene,  f"{idx} — End of period (after)", None, None),
                                ]
                            elif after_scene:
                                pairs = [(after_scene, f"{idx} — Current snapshot", None, None)]

                            for scene_id, caption, d_start, d_end in pairs:
                                try:
                                    thumb_url = await gee_connector.compute_index_thumbnail_url(
                                        scene_id=scene_id, 
                                        aoi_geojson=request.aoi, 
                                        index_name=idx,
                                        date_start=d_start,
                                        date_end=d_end
                                    )
                                    if thumb_url:
                                        resp = await http_client.get(thumb_url, timeout=30.0)
                                        if resp.status_code == 200:
                                            safe_name = caption.lower().replace(" ", "_").replace("/", "_").replace("—", "").replace("(", "").replace(")", "")[:40]
                                            upload_res = await cloudinary_client.upload_bytes(
                                                image_bytes=resp.content,
                                                artifact_type=f"{idx.lower()}_thumbnail",
                                                job_id=request.job_id,
                                                filename=f"{safe_name}.png"
                                            )
                                            media["images"].append({
                                                "type": "gee_raster",
                                                "index": idx.upper(),
                                                "url": upload_res["url"],
                                                "source": "GEE",
                                                "caption": caption
                                            })
                                except Exception as idx_err:
                                    logger.warning(f"Could not generate {idx} thumbnail for {scene_id}: {idx_err}")

                # ── Timelapse ────────────────────────────────────────────────────
                t_url = None

                # 1. Try to find in saved evidence raw_data
                for rec in evidence_records:
                    if rec.get("tool_name") == "gee_get_temporal_series":
                        raw = (rec.get("parameters") or {}).get("raw_data") or {}
                        if raw.get("video_url"):
                            t_url = raw["video_url"]
                            logger.info(f"Found timelapse URL in evidence: {t_url}")
                            break

                # 2. Fall back: generate fresh from scene_ids_ordered via connector
                if not t_url and len(scene_ids_ordered) >= 2 and request.aoi:
                    try:
                        logger.info(f"Generating timelapse from {len(scene_ids_ordered)} scenes...")
                        t_url = await gee_connector.generate_timelapse_url(
                            scene_ids=scene_ids_ordered,
                            aoi_geojson=request.aoi
                        )
                        if t_url:
                            logger.info(f"Generated fresh timelapse URL: {t_url}")
                    except Exception as tl_err:
                        logger.warning(f"Timelapse generation failed: {tl_err}")

                if t_url:
                    try:
                        async with httpx.AsyncClient() as http_client:
                            resp = await http_client.get(t_url, timeout=60.0)
                            if resp.status_code == 200 and len(resp.content) > 1000:
                                upload_res = await cloudinary_client.upload_bytes(
                                    image_bytes=resp.content,
                                    artifact_type="timelapse",
                                    job_id=request.job_id,
                                    filename="timelapse.gif"
                                )
                                caption = (
                                    f"Satellite timelapse — {period_start} to {period_end}"
                                    if "period_start" in dir() else "Satellite timelapse"
                                )
                                media["videos"].append({
                                    "type": "timelapse",
                                    "url": upload_res["url"],
                                    "source": "GEE",
                                    "caption": caption
                                })
                                logger.info(f"Timelapse uploaded to Cloudinary: {upload_res['url']}")
                            else:
                                media["videos"].append({
                                    "type": "timelapse",
                                    "url": t_url,
                                    "source": "GEE",
                                    "caption": "Satellite timelapse (direct GEE link)"
                                })
                    except Exception as vid_err:
                        logger.warning(f"Timelapse upload failed: {vid_err}")
                        media["videos"].append({
                            "type": "timelapse",
                            "url": t_url,
                            "source": "GEE",
                            "caption": "Satellite timelapse (direct GEE link)"
                        })

            except Exception as e:
                logger.error(f"Failed to generate selective media: {e}", exc_info=True)

        # -------------------------------------------------------------
        # Vision Analysis: Feed satellite images to OpenAI for commentary
        # -------------------------------------------------------------
        if request.use_agent and media.get("images") and request.aoi:
            try:
                vision_imgs = [img for img in media["images"] if img.get("url")]
                if vision_imgs:
                    # Build the vision message content
                    vision_content = [
                        {
                            "type": "text",
                            "text": (
                                "You are a remote sensing expert. The following satellite index images have just been generated "
                                "for the user's area of interest. Analyse the visual patterns you see in each image and write "
                                "a concise, natural 2-3 sentence interpretation per image. Focus on what the colors mean for "
                                "each specific index (NDVI = vegetation, NDBI = built-up, NDWI = water, NBR = burn severity, "
                                "RGB = true colour). Describe what changed between before/after pairs if present. "
                                "Do NOT output any JSON. Write only plain natural prose.\n\n"
                                f"Images:\n" + 
                                "\n".join(f"- [{img.get('index','?')}] {img.get('caption','')}" for img in vision_imgs)
                            )
                        }
                    ]
                    for img in vision_imgs[:6]:  # max 6 images (e.g. 3 index before/after pairs)
                        vision_content.append({
                            "type": "image_url",
                            "image_url": {"url": img["url"], "detail": "low"}
                        })

                    vision_resp = await client.chat.completions.create(
                        model=settings.openai_model,
                        messages=[{"role": "user", "content": vision_content}],
                        max_tokens=600,
                        temperature=0.4
                    )
                    vision_text = vision_resp.choices[0].message.content.strip()
                    if vision_text:
                        ai_answer = ai_answer + "\n\n---\n**🛰 Visual Analysis**\n\n" + vision_text
                        logger.info("✅ Vision analysis appended to answer")
            except Exception as vis_err:
                logger.warning(f"Vision analysis failed: {vis_err}")

        
        # -------------------------------------------------------------
        # Advanced Evidence-Driven DOCX Generation (Phase 13)
        # -------------------------------------------------------------
        document_url = None
        if request.use_agent and request.aoi and request.job_id:
            try:
                from app.main import cloudinary_client, supabase_client
                from app.services.report_planner import ReportPlanner
                from app.utils.doc_generator import DocGenerator
                
                logger.info("Generating Advanced Evidence-Driven DOCX Document...")
                
                # Fetch evidence records for this job
                evidence_res = supabase_client.get_admin_client().table("evidence").select("*").eq("job_id", request.job_id).execute()
                evidence_records = evidence_res.data if evidence_res and evidence_res.data else []
                
                planner = ReportPlanner(supabase_client=supabase_client)
                package = await planner.generate_package(
                    job_id=request.job_id,
                    user_id=user_id,
                    agent_response=agent_response,
                    evidence_records=evidence_records,
                    aoi=request.aoi,
                    start_date=thirty_days_ago.strftime("%Y-%m-%d"),
                    end_date=now.strftime("%Y-%m-%d"),
                    cloudinary_client=cloudinary_client
                )
                
                docx_bytes = DocGenerator.generate_advanced_docx(package)
                
                # Upload to Cloudinary
                filename = f"{package.report_type}_analysis.docx"
                upload_res = await cloudinary_client.upload_bytes(
                    docx_bytes, 
                    artifact_type="report_docx", 
                    job_id=request.job_id,
                    filename=filename,
                    resource_type="raw"
                )
                
                document_url = upload_res["url"]
                
                # Save to DB (Documents tab)
                new_doc = {
                    "job_id": request.job_id,
                    "doc_type": f"{package.report_type}_report",
                    "format": "docx",
                    "cloudinary_public_id": upload_res["cloudinary_public_id"],
                    "cloudinary_url": document_url
                }
                supabase_client.get_admin_client().table("documents").insert(new_doc).execute()
                
                # Link Artifact to Evidence Graph
                if provenance and "evidence_ids" in provenance:
                    try:
                        new_artifact = {
                            "job_id": request.job_id,
                            "artifact_type": "docx",
                            "cloudinary_url": document_url,
                            "cloudinary_public_id": upload_res.get("cloudinary_public_id", ""),
                            "format": "docx",
                        }
                        artifact_res = supabase_client.get_admin_client().table("artifacts").insert(new_artifact).execute()
                        if artifact_res.data:
                            art_id = artifact_res.data[0]["artifact_id"]
                            for ev_id in provenance.get("evidence_ids", []):
                                supabase_client.get_admin_client().table("artifact_evidence").insert({
                                    "artifact_id": art_id,
                                    "evidence_id": ev_id
                                }).execute()
                    except Exception as e:
                        logger.error(f"Failed to save artifact provenance link: {e}")

                        
                # Force job to completed so frontend Documents tab picks it up
                supabase_client.get_admin_client().table("jobs").update({"status": "completed"}).eq("job_id", request.job_id).execute()
                logger.info(f"✅ Saved Advanced {package.report_type.capitalize()} Document to database for job {request.job_id}")
                
            except Exception as doc_err:
                logger.error(f"Failed to generate/save advanced DOCX: {doc_err}")
                
        return {
            "reply": ai_answer, 
            "document_url": document_url, 
            "timeline_data": timeline_data,
            "provenance_status": provenance_status,
            "provenance": provenance,
            "findings": findings,
            "visual_evidence": visual_evidence,
            "media": media,
            "quality": quality,
            "limitations": limitations,
            "replanning": replanning,
            "tools_used": tools_used
        }
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        err_str = str(e)
        if "PGRST" in err_str:
            msg = "A database operation failed while processing your request."
        elif "JSONDecodeError" in err_str or "KeyError" in err_str or "schema cache" in err_str:
            msg = "An internal processing error occurred while interpreting the satellite data."
        else:
            msg = "An unexpected error occurred while orchestrating the analysis."
        raise HTTPException(status_code=500, detail=msg)
