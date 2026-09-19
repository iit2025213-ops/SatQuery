# app/workers/gee_worker.py
"""
Background worker that processes a queued SatQuery job:
  1. Authenticates to GEE
  2. Queries Sentinel-2 for the best cloud-free scene over the AOI
  3. Downloads an RGB true-color thumbnail + NDVI thumbnail via getThumbURL
  4. Uploads both PNGs to Cloudinary
  5. Saves gee_assets rows to Supabase
  6. Marks the job as completed with a human-readable final_answer
"""

import logging
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import httpx

logger = logging.getLogger("satquery")


def _vegetation_label(mean_ndvi: float) -> str:
    if mean_ndvi >= 0.6:
        return "Dense/Healthy Vegetation 🌿"
    elif mean_ndvi >= 0.4:
        return "Moderate Vegetation 🌱"
    elif mean_ndvi >= 0.2:
        return "Sparse Vegetation / Grassland 🟡"
    elif mean_ndvi >= 0.0:
        return "Bare Soil / Urban 🟤"
    else:
        return "Water / Clouds / Snow 💧"


async def _download_bytes(url: str) -> Optional[bytes]:
    """Download image bytes from a URL (e.g. GEE getThumbURL signed link)."""
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content
    except Exception as e:
        logger.error(f"Failed to download from {url}: {e}")
        return None


async def run_gee_analysis(
    job_id: str,
    aoi_geojson: dict,
    user_id: str,
    query_text: str,
    supabase_client,
    cloudinary_client,
):
    """
    Main background coroutine. Called by FastAPI BackgroundTasks after
    a job is saved to Supabase.
    """
    from app.main import gee_connector  # imported here to avoid circular deps

    logger.info(f"🛰 GEE Worker starting for job: {job_id}")

    def update_job(status: str, **kwargs):
        try:
            update = {"status": status, "updated_at": datetime.utcnow().isoformat(), **kwargs}
            supabase_client.get_admin_client().table("jobs").update(update).eq("job_id", job_id).execute()
        except Exception as e:
            logger.error(f"Failed to update job {job_id}: {e}")

    try:
        # ── Step 1: Mark job as running ──────────────────────────────────
        update_job("running")

        # ── Step 2: Authenticate to GEE ──────────────────────────────────
        if not gee_connector:
            raise RuntimeError("GEE connector not initialised in main.py")

        auth_ok = await gee_connector.authenticate()
        if not auth_ok:
            raise RuntimeError("GEE authentication failed — check service account key")

        # ── Step 3: Query Sentinel-2 (last 6 months) ─────────────────────
        date_end = datetime.utcnow().strftime("%Y-%m-%d")
        date_start = (datetime.utcnow() - timedelta(days=180)).strftime("%Y-%m-%d")

        logger.info(f"GEE: Querying Sentinel-2 {date_start} → {date_end}")
        scenes = await gee_connector.query_sentinel2(
            aoi_geojson=aoi_geojson,
            date_start=date_start,
            date_end=date_end,
            cloud_cover_max=25,
            max_results=5,
        )

        if not scenes:
            # Fallback: try Landsat
            logger.warning("No Sentinel-2 scenes found — trying Landsat")
            scenes = await gee_connector.query_landsat(
                aoi_geojson=aoi_geojson,
                date_start=date_start,
                date_end=date_end,
                cloud_cover_max=25,
                max_results=5,
            )

        if not scenes:
            update_job(
                "completed",
                final_answer=(
                    f"No cloud-free satellite imagery found over your selected area "
                    f"in the last 6 months (before {date_end}). "
                    f"Try a different date range or a larger area."
                ),
            )
            return

        # Pick the least-cloudy scene
        best_scene = scenes[0]
        scene_id = best_scene["id"]
        source = best_scene["source"]
        acq_date = best_scene["acquisition_date"]
        cloud_pct = best_scene.get("cloud_cover_percent", 0)

        logger.info(f"Best scene: {scene_id} | {acq_date} | ☁ {cloud_pct:.1f}%")

        # ── Step 4: Generate RGB thumbnail URL from GEE ───────────────────
        rgb_url = await gee_connector.get_thumbnail_url(
            scene_id=scene_id,
            aoi_geojson=aoi_geojson,
        )

        # ── Step 5: Generate NDVI thumbnail URL from GEE ──────────────────
        ndvi_url = await gee_connector.compute_ndvi_thumbnail_url(
            scene_id=scene_id,
            aoi_geojson=aoi_geojson,
        )

        # ── Step 6: Get NDVI statistics ────────────────────────────────────
        ndvi_stats = await gee_connector.get_ndvi_stats(
            scene_id=scene_id,
            aoi_geojson=aoi_geojson,
        )
        ndvi_mean = ndvi_stats["mean"] if ndvi_stats else None

        # ── Step 7: Download & Upload to Cloudinary ───────────────────────
        cloudinary_rgb_url = None
        cloudinary_ndvi_url = None

        if rgb_url:
            logger.info("Downloading RGB thumbnail from GEE...")
            rgb_bytes = await _download_bytes(rgb_url)
            if rgb_bytes:
                try:
                    result = await cloudinary_client.upload_bytes(
                        image_bytes=rgb_bytes,
                        artifact_type="rgb-thumbnail",
                        job_id=job_id,
                        filename="rgb.png",
                        metadata={"scene_id": scene_id},
                    )
                    cloudinary_rgb_url = result["url"]
                    logger.info(f"✅ RGB uploaded to Cloudinary: {cloudinary_rgb_url}")
                except Exception as e:
                    logger.error(f"RGB Cloudinary upload failed: {e}")

        if ndvi_url:
            logger.info("Downloading NDVI thumbnail from GEE...")
            ndvi_bytes = await _download_bytes(ndvi_url)
            if ndvi_bytes:
                try:
                    result = await cloudinary_client.upload_bytes(
                        image_bytes=ndvi_bytes,
                        artifact_type="ndvi-thumbnail",
                        job_id=job_id,
                        filename="ndvi.png",
                        metadata={"scene_id": scene_id},
                    )
                    cloudinary_ndvi_url = result["url"]
                    logger.info(f"✅ NDVI uploaded to Cloudinary: {cloudinary_ndvi_url}")
                except Exception as e:
                    logger.error(f"NDVI Cloudinary upload failed: {e}")

        # ── Step 8: Save gee_assets rows to Supabase ──────────────────────
        collection_id = str(uuid.uuid4())   # synthetic collection for this job
        try:
            # Create gee_collections record first to satisfy foreign key constraint
            supabase_client.get_admin_client().table("gee_collections").insert({
                "collection_id": collection_id,
                "job_id": job_id,
                "user_id": user_id,
                "collection_name": "Thumbnails",
                "status": "completed",
                "progress_percent": 100,
            }).execute()

            gee_asset_id = str(uuid.uuid4())
            supabase_client.get_admin_client().table("gee_assets").insert({
                "gee_asset_id": gee_asset_id,
                "collection_id": collection_id,
                "job_id": job_id,
                "scene_id": scene_id,
                "source": source,
                "acquisition_date": acq_date,
                "cloud_cover_percent": cloud_pct,
                "cloudinary_url": cloudinary_rgb_url,
                "status": "uploaded" if cloudinary_rgb_url else "metadata_stored",
            }).execute()

            if cloudinary_ndvi_url:
                ndvi_asset_id = str(uuid.uuid4())
                supabase_client.get_admin_client().table("gee_assets").insert({
                    "gee_asset_id": ndvi_asset_id,
                    "collection_id": collection_id,
                    "job_id": job_id,
                    "scene_id": scene_id,
                    "source": f"{source}-NDVI",
                    "acquisition_date": acq_date,
                    "cloud_cover_percent": cloud_pct,
                    "cloudinary_url": cloudinary_ndvi_url,
                    "status": "uploaded",
                }).execute()
        except Exception as e:
            logger.error(f"Failed to save gee_assets: {e}")

        # ── Step 9: Build final_answer and complete the job ───────────────
        veg_label = _vegetation_label(ndvi_mean) if ndvi_mean is not None else "Unknown"
        ndvi_str = f"{ndvi_mean:.3f}" if ndvi_mean is not None else "N/A"

        lines = [
            f"Analysis complete for your query: **{query_text}**\n",
            f"📡 **Satellite Source:** {source}",
            f"📅 **Best Scene Date:** {acq_date} (☁ {cloud_pct:.1f}% cloud cover)",
            f"🌿 **Vegetation Health:** {veg_label} (NDVI mean: {ndvi_str})",
        ]

        if cloudinary_rgb_url:
            lines.append(f"\n🛰 **True-Color Image:** {cloudinary_rgb_url}")
        if cloudinary_ndvi_url:
            lines.append(f"🌱 **NDVI Visualization:** {cloudinary_ndvi_url}")

        final_answer = "\n".join(lines)

        update_job(
            "completed",
            final_answer=final_answer,
            confidence=0.85,
        )
        logger.info(f"✅ Job {job_id} completed successfully")

    except Exception as e:
        logger.error(f"❌ GEE Worker failed for job {job_id}: {e}", exc_info=True)
        update_job(
            "failed",
            final_answer=f"Analysis failed: {str(e)}. Please try again.",
        )
