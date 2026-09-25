import asyncio
import json
import logging

from app.agents.geo_agent import GeoAgent
from app.gee.tools import GEEToolLayer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_timeline")

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
    tool_layer = GEEToolLayer()
    await tool_layer.connector.authenticate()
    
    print("\n==================================================")
    print("TEST 1: Terminal-First Tool Validation (No Agent)")
    print("==================================================")
    
    res = await tool_layer.gee_generate_timeline_artifact(
        aoi=DELHI_AOI,
        start_date="2024-01-01",
        end_date="2024-12-31",
        interval_months=3,
        include_analytics=["trend"]
    )
    
    assert res.get("status") == "success", "Timeline generation failed"
    data = res.get("timeline_data", {})
    frames = data.get("frames", [])
    
    assert len(frames) > 0, "No frames generated"
    assert "date" in frames[0], "Frames missing actual dates"
    assert "cloud_cover" in frames[0], "Frames missing cloud cover"
    assert "quality" in frames[0], "Frames missing quality metadata"
    
    # Check chronological ordering
    dates = [f["date"] for f in frames]
    assert dates == sorted(dates), "Frames are not chronologically ordered"
    
    assert data.get("video_url"), "Timelapse GIF not generated"
    assert "analytics" in data, "Analytics not included when requested"
    assert "trend" in data["analytics"], "Trend analysis missing"
    
    print("✅ Terminal Tool Validation passed.")

    print("\n==================================================")
    print("TEST 2: Geo-Agent Timeline Request")
    print("==================================================")
    q2 = "Show me a timeline of how vegetation changed over 2024. Also include the long-term trend."
    res2 = await agent.run(q2, DELHI_AOI, "2024-01-01", "2024-12-31")
    print(f"\nFinal Answer:\n{res2.answer}\n")
    print(f"Tools Used: {res2.tools_used}")
    
    assert "gee_generate_timeline_artifact" in res2.tools_used, "Agent didn't use timeline tool"
    
    print("✅ Geo-Agent Timeline tool usage passed.")
    print("\nAll Terminal Tests Passed Successfully.")

if __name__ == "__main__":
    asyncio.run(run_tests())
