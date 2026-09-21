"""Critical closed-loop test for Phase 3 boundary enforcement.

Proves that:
1. Geospatial deterministic checks emit Observations.
2. The AgentController routes to the LLM.
3. The LLM decision explicitly depends on that Observation.
4. Phase 3 does not impose hidden ML preprocessing sequences.
"""

import os
import tempfile
import pytest

from app.agent.controller import AgentController
from app.agent.decision import ActionType, Decision
from app.config import Settings
from app.executor.executor import DefaultExecutor
from app.llm.mock import MockLLM
from app.registry.registry import build_default_registry

from tests.test_geospatial import create_synthetic_raster


class BoundaryTestMockLLM(MockLLM):
    """Overrides MockLLM to explicitly test spatial alignment decisions."""
    
    async def decide(self, context: dict) -> Decision:
        observations = context.get("observations", [])
        
        # 1. No observations -> validate temporal pair
        if not observations:
            return Decision(
                action=ActionType.CALL_CAPABILITY,
                capability="validate_temporal_pair",
                arguments=self._temporal_pair_args(context),
                reason="Initial step: validate the temporal pair."
            )
            
        last_obs = observations[-1]
        
        # 2. If temporal validation failed due to alignment, call alignment check
        if last_obs.get("capability") == "validate_temporal_pair":
            if last_obs.get("status") == "invalid_input":
                err = last_obs.get("error", "")
                if "align" in err.lower() or "CRS" in err:
                    return Decision(
                        action=ActionType.CALL_CAPABILITY,
                        capability="validate_spatial_alignment",
                        arguments=self._temporal_pair_args(context),
                        reason="Temporal pair validation failed due to alignment. Checking spatial alignment."
                    )
            elif last_obs.get("status") == "success":
                return Decision(
                    action=ActionType.FINAL,
                    final_answer="Temporal pair is fully valid and aligned.",
                    reason="Validation passed."
                )
                
        # 3. If alignment check succeeded, return final
        if last_obs.get("capability") == "validate_spatial_alignment":
            if last_obs.get("status") == "success":
                return Decision(
                    action=ActionType.FINAL,
                    final_answer="Alignment check complete and resolved.",
                    reason="Alignment passed."
                )
                
        return Decision(
            action=ActionType.FINAL,
            final_answer="Test complete.",
            reason="Fallback final."
        )


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


def _controller() -> AgentController:
    registry = build_default_registry()
    executor = DefaultExecutor(registry)
    return AgentController(
        llm=BoundaryTestMockLLM(),
        executor=executor,
        registry=registry,
        settings=Settings(
            max_steps=10,
        ),
    )


@pytest.mark.asyncio
async def test_phase3_boundary_enforcement(temp_dir):
    """Test that a misaligned pair triggers alignment logic via LLM decision, not hidden preprocessing."""
    try:
        import rasterio
    except ImportError:
        pytest.skip("rasterio not installed")
        
    ref_path = os.path.join(temp_dir, "ref_boundary.tif")
    tgt_path = os.path.join(temp_dir, "tgt_boundary.tif")
    
    # Intentionally misaligned
    create_synthetic_raster(ref_path, width=50, height=50, crs="EPSG:32643", resolution=10.0, tags={"timestamp": "2024-01-01T00:00:00Z"})
    create_synthetic_raster(tgt_path, width=100, height=100, crs="EPSG:32643", resolution=5.0, tags={"timestamp": "2024-02-01T00:00:00Z"})
    
    ctrl = _controller()
    
    result = await ctrl.run(
        "Analyze these images.",
        input_assets=[
            {"asset_id": "asset_1", "uri": ref_path, "format": "geotiff", "modality": "optical"},
            {"asset_id": "asset_2", "uri": tgt_path, "format": "geotiff", "modality": "optical"}
        ],
    )
    
    capabilities = [e["capability"] for e in result["evidence"]]
    
    # 1. It must have attempted temporal validation
    assert "validate_temporal_pair" in capabilities
    
    # 2. It must have failed temporal validation because `align_rasters` is strictly enforced
    # (The LLM logic in this test then issues validate_spatial_alignment)
    assert "validate_spatial_alignment" in capabilities
    
    # 3. We prove the LLM handled it, not a silent preprocessing pipeline
    assert result["step_count"] >= 2
    assert "Alignment check complete" in result["answer"]
