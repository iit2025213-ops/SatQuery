import asyncio
import json
import logging

from app.agents.geo_agent import GeoAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_temporal")

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
    print("TEST 1: Long-term NDVI Trend")
    print("==================================================")
    q1 = "What is the long-term trend of NDVI between 2022 and 2024?"
    res1 = await agent.run(q1, DELHI_AOI, "2022-01-01", "2024-12-31")
    print(f"\nFinal Answer:\n{res1.answer}\n")
    print(f"Tools Used: {res1.tools_used}")
    assert "gee_analyze_trend" in res1.tools_used, "Agent didn't use gee_analyze_trend"
    print("✅ Trend test passed.")

    print("\n==================================================")
    print("TEST 2: Seasonal vs Long-term Change")
    print("==================================================")
    q2 = "Is the vegetation change purely seasonal, or is there a structural trend? Look at 2022 to 2024."
    res2 = await agent.run(q2, DELHI_AOI, "2022-01-01", "2024-12-31")
    print(f"\nFinal Answer:\n{res2.answer}\n")
    print(f"Tools Used: {res2.tools_used}")
    assert any("season" in tool for tool in res2.tools_used) or "gee_analyze_trend" in res2.tools_used, "Agent didn't use temporal intelligence tools"
    print("✅ Seasonality vs Trend test passed.")

    print("\n==================================================")
    print("TEST 3: Temporal Break Detection")
    print("==================================================")
    q3 = "When did the most significant structural break in NDVI occur between 2022 and 2024?"
    res3 = await agent.run(q3, DELHI_AOI, "2022-01-01", "2024-12-31")
    print(f"\nFinal Answer:\n{res3.answer}\n")
    print(f"Tools Used: {res3.tools_used}")
    assert "gee_detect_temporal_breaks" in res3.tools_used, "Agent didn't use gee_detect_temporal_breaks"
    print("✅ Temporal Break Detection test passed.")

    print("\n==================================================")
    print("TEST 4: Change Persistence / Recovery")
    print("==================================================")
    q4 = "Did the vegetation recover after a hypothetical disturbance in March 2023? Use the year before as baseline and the year after as post-event."
    res4 = await agent.run(q4, DELHI_AOI, "2022-03-01", "2024-03-01")
    print(f"\nFinal Answer:\n{res4.answer}\n")
    print(f"Tools Used: {res4.tools_used}")
    assert "gee_analyze_change_persistence" in res4.tools_used or "gee_analyze_event_window" in res4.tools_used, "Agent didn't test persistence or window"
    print("✅ Change Persistence test passed.")

    print("\n==================================================")
    print("TEST 5: Pre/Post Event Window")
    print("==================================================")
    q5 = "Compare the 90 days before and 90 days after March 15, 2023 for NDVI."
    res5 = await agent.run(q5, DELHI_AOI, "2022-01-01", "2024-12-31")
    print(f"\nFinal Answer:\n{res5.answer}\n")
    print(f"Tools Used: {res5.tools_used}")
    assert "gee_analyze_event_window" in res5.tools_used, "Agent didn't use gee_analyze_event_window"
    print("✅ Event Window test passed.")
    
    print("\n==================================================")
    print("TEST 6: Adversarial Question (Temporary vs Permanent)")
    print("==================================================")
    q6 = "There was a massive drop in NDVI in May 2023. Does this prove permanent environmental collapse in the region?"
    res6 = await agent.run(q6, DELHI_AOI, "2022-01-01", "2024-12-31")
    print(f"\nFinal Answer:\n{res6.answer}\n")
    print(f"Tools Used: {res6.tools_used}")
    
    refusal_words = ["permanent", "temporary", "collapse", "persist", "recover", "season"]
    assert any(any(w in limit.lower() for w in refusal_words) for limit in res6.limitations) or \
           any(w in res6.answer.lower() for w in refusal_words), "Agent failed to critically address temporary vs permanent change"
    print("✅ Adversarial Temporary vs Permanent test passed.")

    print("\n==================================================")
    print("All Phase 6 Tests Completed Successfully.")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(run_tests())
