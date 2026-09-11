# app/gee/processor.py

"""
GEE Processor — Phase 7

Handles persisting GEE query results to Supabase and
coordinating Cloudinary uploads for imagery/DEM assets.
"""

import uuid
import logging
from typing import List, Optional, Dict
from datetime import datetime

logger = logging.getLogger("satquery")


class GEEProcessor:
    """Process and store GEE imagery metadata and assets."""

    def __init__(self, cloudinary_client=None):
        self.cloudinary = cloudinary_client

    # ------------------------------------------------------------------
    # Collection management
    # ------------------------------------------------------------------

    async def create_collection(
        self,
        job_id: str,
        user_id: str,
        query_params: dict,
        collection_name: str,
        supabase_client,
    ) -> str:
        """
        Create a gee_collections record to track the query.

        Returns: collection_id
        """
        collection_id = str(uuid.uuid4())

        record = {
            "collection_id": collection_id,
            "job_id": job_id,
            "user_id": user_id,
            "query_params": query_params,
            "collection_name": collection_name,
            "status": "queued",
            "progress_percent": 0,
        }

        supabase_client.get_admin_client().table("gee_collections").insert(record).execute()

        logger.info(f"GEE collection created: {collection_id} for job {job_id}")
        return collection_id

    async def update_collection_status(
        self,
        collection_id: str,
        status: str,
        supabase_client,
        progress_percent: int = 0,
        results_count: int = 0,
        scenes_retrieved: int = 0,
        error_message: Optional[str] = None,
    ):
        """Update the status of a gee_collections record."""
        update = {
            "status": status,
            "progress_percent": progress_percent,
            "results_count": results_count,
            "scenes_retrieved": scenes_retrieved,
        }
        if error_message:
            update["error_message"] = error_message

        supabase_client.get_admin_client().table("gee_collections").update(
            update
        ).eq("collection_id", collection_id).execute()

    # ------------------------------------------------------------------
    # Scene asset storage
    # ------------------------------------------------------------------

    async def store_scenes(
        self,
        scenes: List[Dict],
        collection_id: str,
        job_id: str,
        supabase_client,
    ) -> List[str]:
        """
        Persist scene metadata to the gee_assets table.

        Returns: list of gee_asset_ids
        """
        asset_ids: List[str] = []

        for scene in scenes:
            try:
                gee_asset_id = str(uuid.uuid4())
                acq_date = scene.get("acquisition_date", "")

                record = {
                    "gee_asset_id": gee_asset_id,
                    "collection_id": collection_id,
                    "job_id": job_id,
                    "scene_id": scene["id"],
                    "source": scene["source"],
                    "acquisition_date": acq_date,
                    "year_month": acq_date[:7] if len(acq_date) >= 7 else None,
                    "cloud_cover_percent": scene.get("cloud_cover_percent"),
                    "crs": scene.get("crs"),
                    "resolution_m": scene.get("resolution_m"),
                    "bands": scene.get("bands"),
                    "band_wavelengths": scene.get("band_wavelengths"),
                    "status": "metadata_stored",
                }

                supabase_client.get_admin_client().table("gee_assets").insert(record).execute()
                asset_ids.append(gee_asset_id)

            except Exception as e:
                logger.error(f"Error storing scene {scene.get('id')}: {e}")

        logger.info(f"Stored {len(asset_ids)} scene assets for collection {collection_id}")
        return asset_ids

    # ------------------------------------------------------------------
    # DEM storage
    # ------------------------------------------------------------------

    async def store_dem(
        self,
        dem_info: Dict,
        collection_id: str,
        job_id: str,
        supabase_client,
        bbox: Optional[List[float]] = None,
    ) -> Optional[str]:
        """
        Persist DEM metadata to the dem_assets table.

        Returns: dem_id
        """
        try:
            dem_id = str(uuid.uuid4())

            record = {
                "dem_id": dem_id,
                "collection_id": collection_id,
                "job_id": job_id,
                "source": dem_info.get("source"),
                "resolution_m": dem_info.get("resolution_m"),
                "elevation_stats": dem_info.get("elevation_stats"),
                "crs": dem_info.get("crs", "EPSG:4326"),
                "bbox": bbox,
                "status": "metadata_stored",
            }

            supabase_client.get_admin_client().table("dem_assets").insert(record).execute()

            logger.info(f"DEM stored: {dem_id} ({dem_info.get('source')})")
            return dem_id

        except Exception as e:
            logger.error(f"Error storing DEM: {e}")
            return None

    # ------------------------------------------------------------------
    # Cloudinary upload (stub — will use actual download in production)
    # ------------------------------------------------------------------

    async def upload_scene_to_cloudinary(
        self,
        file_path: str,
        job_id: str,
        scene_id: str,
        gee_asset_id: str,
        supabase_client,
    ) -> Optional[str]:
        """
        Upload a downloaded scene to Cloudinary and update the
        gee_assets record with the URL.

        Returns: cloudinary_url
        """
        if not self.cloudinary:
            logger.warning("Cloudinary client not configured — skipping upload")
            return None

        try:
            result = await self.cloudinary.upload_artifact(
                file_path=file_path,
                artifact_type="gee-imagery",
                job_id=job_id,
                metadata={"scene_id": scene_id},
            )

            cloudinary_url = result.get("url")
            cloudinary_public_id = result.get("cloudinary_public_id")

            # Update database record
            supabase_client.get_admin_client().table("gee_assets").update({
                "cloudinary_url": cloudinary_url,
                "cloudinary_public_id": cloudinary_public_id,
                "status": "uploaded",
            }).eq("gee_asset_id", gee_asset_id).execute()

            logger.info(f"Scene uploaded to Cloudinary: {cloudinary_url}")
            return cloudinary_url

        except Exception as e:
            logger.error(f"Error uploading scene to Cloudinary: {e}")
            return None
