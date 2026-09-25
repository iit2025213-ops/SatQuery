import asyncio
import json
import logging
from app.agents.geo_agent import GeoAgent
import datetime

logging.basicConfig(level=logging.INFO)

# A real Delhi AOI
DELHI_AOI = {
    "type": "Polygon",
    "coordinates": [
        [
            [77.1000, 28.5500],
            [77.3000, 28.5500],
            [77.3000, 28.7000],
            [77.1000, 28.7000],
            [77.1000, 28.5500]
        ]
    ]
}

async def run_tests():
    agent = GeoAgent(max_tool_calls=6, deterministic=True)
    
    print("\n" + "="*50)
    print("TEST 1: Vegetation Condition (NDVI Vision)")
    print("="*50)
    res_1 = await agent.run(
        user_question="What is the vegetation condition of this area? Analyze the imagery visually as well as numerically.",
        aoi_geojson=DELHI_AOI,
        start_date="2024-01-01",
        end_date="2024-03-31"
    )
    print("\n[FINAL RESPONSE]")
    print(json.dumps(res_1.model_dump(), indent=2))
    assert len(res_1.visual_evidence) > 0, "No visual evidence found!"
    assert res_1.visual_evidence[0].source == "GEE", "Visual evidence provenance missing or invalid!"
    
    
    print("\n" + "="*50)
    print("TEST 2: Urbanization vs Vegetation (Multi-Raster Vision)")
    print("="*50)
    res_2 = await agent.run(
        user_question="Compare vegetation and urbanization changes in this area visually and numerically.",
        aoi_geojson=DELHI_AOI,
        start_date="2023-01-01",
        end_date="2024-03-31"
    )
    print("\n[FINAL RESPONSE]")
    print(json.dumps(res_2.model_dump(), indent=2))
    assert len(res_2.visual_evidence) > 0, "No visual evidence found for comparison!"

if __name__ == "__main__":
    asyncio.run(run_tests())
