# app/models/changeformer_adapter.py

from app.models.base import BaseAdapter
from app.agent.state import Observation
import logging

logger = logging.getLogger("satquery")


class ChangeFormerAdapter(BaseAdapter):
    """Adapter for ChangeFormer bitemporal change detection model"""

    async def execute(self, arguments: dict, state, supabase_client) -> Observation:
        """Execute ChangeFormer inference"""

        asset_id_t1 = arguments.get("asset_id_t1")
        asset_id_t2 = arguments.get("asset_id_t2")

        logger.info(f"ChangeFormer: comparing {asset_id_t1} vs {asset_id_t2}")

        # In production, this would:
        # 1. Download images from Cloudinary
        # 2. Preprocess & align
        # 3. Run ChangeFormer model
        # 4. Generate change mask
        # 5. Upload artifact to Cloudinary

        return Observation(
            step_number=state.current_step,
            source_capability="detect_bitemporal_change",
            status="success",
            result={
                "change_detected": True,
                "changed_pixels": 27431,
                "change_mask_artifact_id": None  # Will be set when artifact is uploaded
            },
            confidence=0.87
        )
