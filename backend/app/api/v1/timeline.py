# app/api/v1/timeline.py

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
import logging

from app.auth.dependencies import get_current_user_id

logger = logging.getLogger("satquery")
router = APIRouter(prefix="/api/v1", tags=["timeline"])

@router.post("/timeline")
async def generate_timeline(
    payload: dict,
    user_id: str = Depends(get_current_user_id)
):
    """
    Generate a 36-month time-series (sampled every 3 months) for a given AOI.
    Expected payload:
    {
        "aoi": { "type": "Polygon", "coordinates": [...] }
    }
    """
    from app.main import gee_connector
    from openai import AsyncOpenAI
    from app.config import settings
    
    aoi = payload.get("aoi")
    if not aoi:
        raise HTTPException(status_code=400, detail="AOI is required")
        
    try:
        # Generate timeline data
        timeline_data = await gee_connector.get_timeline_data(aoi_geojson=aoi, months=36, interval_months=3)
        
        if not timeline_data or not timeline_data.get("frames"):
            raise HTTPException(status_code=404, detail="No satellite imagery found for this AOI over the last 36 months.")
            
        # Ask OpenAI Vision to summarize the timeline!
        ai_summary = "AI analysis unavailable."
        if settings.openai_api_key:
            try:
                from openai import AsyncOpenAI
                
                client = AsyncOpenAI(
                    api_key=settings.openai_api_key,
                    base_url=settings.openai_base_url
                )
                
                content = [
                    {"type": "text", "text": "You are a geospatial AI analyst. I am providing you with satellite imagery snapshots of the exact same area over a 3-year period (1 image every 3 months), along with 4 scientific index scores: NDVI (Vegetation), NDWI (Water), NDBI (Urban/Infrastructure), and NBR (Burn scars/Wildfires).\n\nGenerate a COMPREHENSIVE Markdown report. Do NOT just give a 2 paragraph summary. Use the following structure:\n# Executive Summary\n## Vegetation & Agriculture (NDVI)\n## Water Bodies (NDWI)\n## Urbanization (NDBI)\n## Natural Disasters & Anomalies (NBR)\n# Actionable Insights\n\nUse bold text, bullet points, and highlight seasonal patterns, urbanization, floods, droughts, or deforestation based heavily on the index numbers provided."}
                ]
                
                import httpx
                import base64
                import asyncio
                
                async def fetch_as_base64(url: str):
                    try:
                        async with httpx.AsyncClient() as http_client:
                            resp = await http_client.get(url, timeout=15.0)
                            if resp.status_code == 200:
                                b64 = base64.b64encode(resp.content).decode("utf-8")
                                return f"data:image/png;base64,{b64}"
                    except Exception as e:
                        logger.warning(f"Failed to download frame image: {e}")
                    return None

                # Download all images concurrently
                tasks = [fetch_as_base64(frame["thumbnail_url"]) if frame.get("thumbnail_url") else asyncio.sleep(0) for frame in timeline_data["frames"]]
                base64_images = await asyncio.gather(*tasks)

                for idx, frame in enumerate(timeline_data["frames"]):
                    stats_text = (
                        f"Date: {frame['date']} | "
                        f"NDVI: {frame.get('ndvi_mean', 'N/A')} | "
                        f"NDWI: {frame.get('ndwi_mean', 'N/A')} | "
                        f"NDBI: {frame.get('ndbi_mean', 'N/A')} | "
                        f"NBR: {frame.get('nbr_mean', 'N/A')}"
                    )
                    content.append({"type": "text", "text": stats_text})
                    
                    b64_url = base64_images[idx]
                    if b64_url:
                        content.append({
                            "type": "image_url",
                            "image_url": {"url": b64_url}
                        })
                        
                response = await client.chat.completions.create(
                    model=settings.openai_model,
                    messages=[{"role": "user", "content": content}],
                    max_tokens=2000
                )
                ai_summary = response.choices[0].message.content.strip()
            except Exception as openai_err:
                logger.error(f"OpenAI Vision analysis failed: {openai_err}")
                
        # Append the video to the AI summary so the frontend renders it
        video_url = timeline_data.get("video_url")
        cloudinary_vid_url = None
        if video_url:
            try:
                import httpx
                async with httpx.AsyncClient() as http_client:
                    vid_resp = await http_client.get(video_url, timeout=45.0)
                    if vid_resp.status_code == 200:
                        from app.main import cloudinary_client
                        job_id = payload.get("job_id") if payload else "test_job"
                        vid_upload_res = await cloudinary_client.upload_bytes(
                            vid_resp.content, 
                            "timeline_animation", 
                            job_id, 
                            "timelapse.gif"
                        )
                        cloudinary_vid_url = vid_upload_res["url"]
            except Exception as vid_err:
                logger.error(f"Failed to save video to Cloudinary: {vid_err}")
                
        timeline_data["ai_summary"] = ai_summary
        
        # Save DOCX to documents table if job_id is provided
        job_id = payload.get("job_id")
        if job_id and settings.openai_api_key:
            try:
                from app.main import cloudinary_client, supabase_client
                import asyncio
                import httpx
                from app.utils.doc_generator import DocGenerator
                
                # Fetch index images for the latest frame
                latest_frame = timeline_data["frames"][-1] if timeline_data.get("frames") else None
                index_images = {}
                if latest_frame and latest_frame.get("scene_id") and payload.get("aoi"):
                    logger.info("Fetching GEE Index Image overlays for DOCX...")
                    indices = ["NDVI", "NDWI", "NDBI", "NBR"]
                    
                    async def fetch_idx(idx_name):
                        try:
                            url = await gee_connector.compute_index_thumbnail_url(latest_frame["scene_id"], payload["aoi"], idx_name, dimensions=512)
                            if url:
                                async with httpx.AsyncClient() as http_client:
                                    resp = await http_client.get(url, timeout=30.0)
                                    if resp.status_code == 200:
                                        return idx_name, resp.content
                        except Exception as e:
                            logger.error(f"Failed to fetch {idx_name}: {e}")
                        return idx_name, None
                        
                    results = await asyncio.gather(*(fetch_idx(idx) for idx in indices))
                    for idx_name, img_bytes in results:
                        if img_bytes:
                            index_images[idx_name] = img_bytes
                
                # Generate DOCX
                logger.info("Generating DOCX Document in memory...")
                docx_bytes = DocGenerator.generate_timeline_docx(
                    ai_summary=ai_summary,
                    timeline_data={"frames": timeline_data.get("frames", [])},
                    video_url=cloudinary_vid_url or video_url,
                    index_images=index_images
                )
                
                # Upload DOCX to Cloudinary
                upload_res = await cloudinary_client.upload_bytes(
                    docx_bytes, 
                    artifact_type="timeline_report_docx", 
                    job_id=job_id,
                    filename="temporal_analysis.docx",
                    resource_type="raw"
                )
                
                # Insert into documents table
                new_doc = {
                    "job_id": job_id,
                    "doc_type": "timeline_report",
                    "format": "docx",
                    "cloudinary_public_id": upload_res["cloudinary_public_id"],
                    "cloudinary_url": upload_res["url"]
                }
                supabase_client.get_admin_client().table("documents").insert(new_doc).execute()
                
                # Also force update the job to completed so it immediately shows up in the Documents page
                supabase_client.get_admin_client().table("jobs").update({"status": "completed"}).eq("job_id", job_id).execute()
                
                logger.info(f"✅ Saved Timeline Document to database for job {job_id}")
                
                # Attach document URL to response so frontend can show download button
                timeline_data["document_url"] = upload_res["url"]
                
            except Exception as doc_err:
                logger.error(f"Failed to save timeline document to DB: {doc_err}")
            
        return {
            "status": "success",
            "data": timeline_data
        }
        
    except Exception as e:
        logger.error(f"Timeline generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate timeline data")
