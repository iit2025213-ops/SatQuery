import asyncio
import json
import logging
from app.gee.tools import GEEToolLayer
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
    tools = GEEToolLayer()
    await tools.connector.authenticate()
    
    print("\n" + "="*50)
    print("TEST 1: gee_search_imagery")
    print("="*50)
    res_search = await tools.gee_search_imagery(
        aoi=DELHI_AOI,
        start_date="2024-01-01",
        end_date="2024-03-31",
        max_cloud_cover=20
    )
    print(json.dumps(res_search.model_dump(), indent=2))
    
    if not res_search.success:
        print("Failed early.")
        return
        
    scene_id = res_search.data["selected_scene"]["id"]
    print(f"\nUsing Scene: {scene_id}")
    
    print("\n" + "="*50)
    print("TEST 2: gee_calculate_indices")
    print("="*50)
    res_indices = await tools.gee_calculate_indices(
        aoi=DELHI_AOI,
        scene_id=scene_id,
        indices=["NDVI", "NDWI"]
    )
    print(json.dumps(res_indices.model_dump(), indent=2))
    
    print("\n" + "="*50)
    print("TEST 3: gee_get_zonal_statistics")
    print("="*50)
    res_stats = await tools.gee_get_zonal_statistics(
        aoi=DELHI_AOI,
        scene_id=scene_id
    )
    print(json.dumps(res_stats.model_dump(), indent=2))
    
    print("\n" + "="*50)
    print("TEST 4: gee_get_temporal_series")
    print("="*50)
    res_temp = await tools.gee_get_temporal_series(
        aoi=DELHI_AOI,
        start_date="2023-01-01",
        end_date="2024-01-01"
    )
    print(json.dumps(res_temp.model_dump(), indent=2))
    
    print("\n" + "="*50)
    print("TEST 5: gee_compare_periods")
    print("="*50)
    res_compare = await tools.gee_compare_periods(
        aoi=DELHI_AOI,
        period_1={"start_date": "2023-01-01", "end_date": "2023-03-31"},
        period_2={"start_date": "2024-01-01", "end_date": "2024-03-31"}
    )
    print(json.dumps(res_compare.model_dump(), indent=2))
    
    print("\n" + "="*50)
    print("TEST 6: gee_get_raster")
    print("="*50)
    res_raster = await tools.gee_get_raster(
        aoi=DELHI_AOI,
        scene_id=scene_id,
        index_name="NDVI"
    )
    print(json.dumps(res_raster.model_dump(), indent=2))


if __name__ == "__main__":
    asyncio.run(run_tests())
