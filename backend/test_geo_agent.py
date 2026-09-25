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
    agent = GeoAgent(max_tool_calls=5, deterministic=True)
    
    print("\n" + "="*50)
    print("TEST 1: Vegetation Condition")
    print("="*50)
    res_1 = await agent.run(
        user_question="What is the vegetation condition of this area?",
        aoi_geojson=DELHI_AOI,
        start_date="2024-01-01",
        end_date="2024-03-31"
    )
    print("\n[FINAL RESPONSE]")
    print(json.dumps(res_1.model_dump(), indent=2))
    
    
    print("\n" + "="*50)
    print("TEST 2: Urbanization vs Vegetation")
    print("="*50)
    res_2 = await agent.run(
        user_question="Has urbanization increased while vegetation decreased?",
        aoi_geojson=DELHI_AOI,
        start_date="2023-01-01",
        end_date="2024-03-31"
    )
    print("\n[FINAL RESPONSE]")
    print(json.dumps(res_2.model_dump(), indent=2))


if __name__ == "__main__":
    asyncio.run(run_tests())
