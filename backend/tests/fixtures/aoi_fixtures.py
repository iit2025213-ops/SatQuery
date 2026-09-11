# tests/fixtures/aoi_fixtures.py
"""
Real AOI test fixtures with actual geospatial validation
"""

# Real test cases with valid AOI geometries
TEST_CASES_VALID = {
    "small_square_sf": {
        "coordinates": [[
            [-122.415, 37.774],
            [-122.414, 37.774],
            [-122.414, 37.775],
            [-122.415, 37.775],
            [-122.415, 37.774]
        ]],
        "location": "San Francisco",
        "expected_area_km2": (0.01, 0.1)
    },
    "large_rectangle_bayarea": {
        "coordinates": [[
            [-122.5, 37.7],
            [-122.4, 37.7],
            [-122.4, 37.8],
            [-122.5, 37.8],
            [-122.5, 37.7]
        ]],
        "location": "Bay Area",
        "expected_area_km2": (100, 150)
    },
    "complex_polygon_agriculture": {
        "coordinates": [[
            [-120.5, 36.7],
            [-120.4, 36.7],
            [-120.4, 36.75],
            [-120.45, 36.8],
            [-120.5, 36.75],
            [-120.5, 36.7]
        ]],
        "location": "California Agriculture",
        "expected_area_km2": (20, 80)
    }
}

# Real invalid test cases
TEST_CASES_INVALID = {
    "not_closed": {
        "coordinates": [[
            [-122.415, 37.774],
            [-122.414, 37.774],
            [-122.414, 37.775]
        ]],
        "error": "Polygon ring not closed"
    },
    "self_intersecting": {
        "coordinates": [[
            [0, 0], [2, 2], [2, 0], [0, 2], [0, 0]
        ]],
        "error": "Self-intersecting polygon"
    },
    "longitude_out_of_bounds": {
        "coordinates": [[
            [200, 37.774],
            [201, 37.774],
            [201, 37.775],
            [200, 37.775],
            [200, 37.774]
        ]],
        "error": "Longitude out of valid range [-180, 180]"
    },
    "latitude_out_of_bounds": {
        "coordinates": [[
            [-122.415, 91],
            [-122.414, 91],
            [-122.414, 92],
            [-122.415, 92],
            [-122.415, 91]
        ]],
        "error": "Latitude out of valid range [-90, 90]"
    }
}
