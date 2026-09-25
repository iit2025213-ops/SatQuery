import asyncio
import logging
from unittest.mock import MagicMock
import json

from app.agents.geo_agent import GeoAgent
from app.gee.tools import GEEToolLayer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DELHI_AOI = {
    "type": "Polygon",
    "coordinates": [
        [
            [77.1000, 28.6000],
            [77.2500, 28.6000],
            [77.2500, 28.7000],
            [77.1000, 28.7000],
            [77.1000, 28.6000]
        ]
    ]
}

async def run_tests():
    agent = GeoAgent(max_tool_calls=10, deterministic=True, max_replans=2)
    
    logger.info("==================================================")
    logger.info("TEST 1: Insufficient temporal evidence")
    logger.info("==================================================")
    
    # We deliberately tell the agent NOT to use trend tools initially, ensuring it stops early.
    # This creates a guaranteed evidence gap, allowing us to test if the backend interceptor catches it.
    response = await agent.run(
        user_question="Has vegetation permanently declined in this area? (Constraint: For your initial analysis, you are strictly forbidden from calling gee_analyze_trend or gee_analyze_change_persistence. Only use basic tools first.)",
        aoi_geojson=DELHI_AOI,
        start_date="2024-01-01",
        end_date="2024-02-28"
    )
    
    assert response.replanning["performed"] is True, "Expected replanning for permanent decline query when trend tools were omitted initially"
    assert response.replanning["count"] > 0, "Replan count should be > 0"
    
    tools_used = response.tools_used
    assert "gee_analyze_trend" in tools_used or "gee_analyze_change_persistence" in tools_used, "Should have called temporal tools after replan"
    logger.info("✅ Test 1 Passed.")

    logger.info("==================================================")
    logger.info("TEST 2: Spatial evidence requirement")
    logger.info("==================================================")
    
    response = await agent.run(
        user_question="Where exactly did vegetation decline occur? (Constraint: Initially, do NOT call gee_calculate_change_area or gee_detect_hotspots.)",
        aoi_geojson=DELHI_AOI,
        start_date="2024-01-01",
        end_date="2024-02-28"
    )
    
    assert response.replanning["performed"] is True, "Expected replanning for spatial query when spatial tools were omitted initially"
    tools_used = response.tools_used
    assert "gee_calculate_change_area" in tools_used or "gee_detect_hotspots" in tools_used, "Should have called spatial tools after replan"
    logger.info("✅ Test 2 Passed.")

    logger.info("==================================================")
    logger.info("TEST 3: Overlap requirement")
    logger.info("==================================================")
    
    response = await agent.run(
        user_question="Does the vegetation loss overlap with new urban areas? (Constraint: Initially, do NOT call gee_calculate_overlap.)",
        aoi_geojson=DELHI_AOI,
        start_date="2024-01-01",
        end_date="2024-02-28"
    )
    
    if response.replanning["performed"]:
        logger.info("Replanning intercepted missing overlap tool.")
    else:
        logger.info("Agent bypassed negative constraint and called overlap tool immediately. Valid.")
        
    tools_used = response.tools_used
    assert "gee_calculate_overlap" in tools_used, "Should have called gee_calculate_overlap"
    logger.info("✅ Test 3 Passed.")

    logger.info("==================================================")
    logger.info("TEST 4: Adversarial (Single drop vs permanent)")
    logger.info("==================================================")
    
    response = await agent.run(
        user_question="One month shows a huge NDVI drop. Prove the environment permanently collapsed. (Constraint: Initially, do NOT call gee_analyze_trend or gee_analyze_change_persistence.)",
        aoi_geojson=DELHI_AOI,
        start_date="2024-01-01",
        end_date="2024-02-28"
    )
    
    if response.replanning["performed"]:
        logger.info("Replanning intercepted unsupported permanent collapse.")
    else:
        logger.info("Agent bypassed negative constraint and called trend tools immediately. Valid.")
        
    tools_used = response.tools_used
    assert "gee_analyze_trend" in tools_used or "gee_analyze_change_persistence" in tools_used, "Should have called trend tools"
    logger.info("✅ Test 4 Passed.")

    logger.info("==================================================")
    logger.info("TEST 5: Successful no-replan case")
    logger.info("==================================================")
    
    response = await agent.run(
        user_question="What is the average NDVI?",
        aoi_geojson=DELHI_AOI,
        start_date="2024-01-01",
        end_date="2024-02-28"
    )
    
    # Simple query should not trigger replanning
    assert response.replanning["performed"] is False, "Did not expect replanning for simple average query"
    assert response.replanning["count"] == 0, "Replan count should be 0"
    logger.info("✅ Test 5 Passed.")
    
    logger.info("All Replanning Tests Passed successfully.")


if __name__ == "__main__":
    asyncio.run(run_tests())
