# tests/fixtures/gee_fixtures.py
"""
Real GEE test fixtures
All fixtures make ACTUAL Google Earth Engine API calls
"""

# Real GEE collections used in tests
GEE_COLLECTIONS = {
    "SENTINEL2": "COPERNICUS/S2_SR_HARMONIZED",
    "LANDSAT9": "LANDSAT/LC09/C02/T1_L2",
    "USGS_DEM": "USGS/3DEP/10m",
    "NAIP": "USDA/NAIP/DOQQ"
}

# Real date ranges for historical analysis
DATE_RANGES = {
    "single_year": {
        "start": "2024-01-01",
        "end": "2024-12-31",
        "label": "2024 Analysis"
    },
    "multi_year": {
        "start": "2019-01-01",
        "end": "2025-12-31",
        "label": "6-year Historical Analysis"
    },
    "recent": {
        "start": "2024-09-01",
        "end": "2024-09-11",
        "label": "Recent (current month)"
    }
}

# Real query parameters
QUERY_PARAMETERS = {
    "cloud_cover_low": 5,
    "cloud_cover_medium": 20,
    "cloud_cover_high": 50,
    "dem_resolution_coarse": 90,
    "dem_resolution_medium": 30,
    "dem_resolution_fine": 10
}
