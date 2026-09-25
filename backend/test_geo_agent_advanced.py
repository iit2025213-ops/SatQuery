import asyncio
import json
import logging

from app.agents.geo_agent import GeoAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_advanced")

DELHI_AOI = {
    "type": "Polygon",
    "coordinates": [[
        [77.1000, 28.5000],
        [77.3000, 28.5000],
        [77.3000, 28.7000],
        [77.1000, 28.7000],
        [77.1000, 28.5000]
    ]]
}

async def run_tests():
    agent = GeoAgent(deterministic=True, max_tool_calls=8)
    
    print("\n==================================================")
    print("TEST 1: Regression Test (Phase 1-4 Core)")
    print("==================================================")
    q1 = "What is the average NDVI in March 2024?"
    res1 = await agent.run(q1, DELHI_AOI, "2024-03-01", "2024-03-31")
    print(f"\nFinal Answer:\n{res1.answer}\n")
    print(f"Tools Used: {res1.tools_used}")
    assert "gee_search_imagery" in res1.tools_used, "Regression failed: gee_search_imagery not used"
    assert "gee_calculate_indices" in res1.tools_used or "gee_get_zonal_statistics" in res1.tools_used, "Regression failed: No index extraction tool used"
    print("✅ Regression test passed.")

    print("\n==================================================")
    print("TEST 2: Advanced Spatial Correlation")
    print("==================================================")
    q2 = "What is the spatial correlation between NDVI and NDBI in March 2024?"
    res2 = await agent.run(q2, DELHI_AOI, "2024-03-01", "2024-03-31")
    print(f"\nFinal Answer:\n{res2.answer}\n")
    print(f"Tools Used: {res2.tools_used}")
    assert "gee_compare_indices" in res2.tools_used, "Advanced test failed: gee_compare_indices not used"
    assert len(res2.evidence) > 0, "No scientific evidence returned."
    print("✅ Spatial correlation test passed.")

    print("\n==================================================")
    print("TEST 3: Advanced Change Area")
    print("==================================================")
    q3 = "Calculate the exact geographic area in km2 of significant vegetation decrease (NDVI threshold -0.1) between Jan 2024 and March 2024."
    res3 = await agent.run(q3, DELHI_AOI, "2024-01-01", "2024-03-31")
    print(f"\nFinal Answer:\n{res3.answer}\n")
    print(f"Tools Used: {res3.tools_used}")
    assert "gee_calculate_change_area" in res3.tools_used, "Advanced test failed: gee_calculate_change_area not used"
    print("✅ Change Area test passed.")

    print("\n==================================================")
    print("TEST 4: Adversarial Causality Question")
    print("==================================================")
    q4 = "Can you prove that urban expansion is causing the vegetation loss based on this data?"
    res4 = await agent.run(q4, DELHI_AOI, "2024-01-01", "2024-03-31")
    print(f"\nFinal Answer:\n{res4.answer}\n")
    assert "gee_calculate_overlap" in res4.tools_used or "gee_compare_indices" in res4.tools_used, "Agent didn't use a relational tool to test causality"
    
    causality_words = ["caus", "correlation", "explain", "contribut", "prove"]
    assert any(any(w in limit.lower() for w in causality_words) for limit in res4.limitations) or \
           any(w in res4.answer.lower() for w in causality_words), "Agent failed to address causality critically"
    print("✅ Adversarial causality test passed.")
    
    print("\n==================================================")
    print("TEST 5: Advanced Anomaly Detection")
    print("==================================================")
    q5 = "Are there any anomalies in vegetation in March 2024 compared to the historical baseline of 2022 to 2023? Use a z-score threshold of 2.0."
    res5 = await agent.run(q5, DELHI_AOI, "2024-03-01", "2024-03-31")
    print(f"\nFinal Answer:\n{res5.answer}\n")
    print(f"Tools Used: {res5.tools_used}")
    assert "gee_detect_anomalies" in res5.tools_used, "Advanced test failed: gee_detect_anomalies not used"
    print("✅ Anomaly Detection test passed.")

    print("\n==================================================")
    print("All Phase 5 Tests Completed Successfully.")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(run_tests())
