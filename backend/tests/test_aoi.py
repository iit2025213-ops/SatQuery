# tests/test_aoi.py

"""
Unit tests for Phase 6: AOI System

Tests AOIValidator, AOICalculator, and AOIIntersection with
real Shapely + pyproj operations — no mocks.
"""

import pytest
from app.geospatial.aoi import AOIValidator, AOICalculator, AOIIntersection


# ---------------------------------------------------------------------------
# AOIValidator tests
# ---------------------------------------------------------------------------

class TestAOIValidation:

    def test_valid_polygon(self):
        """Test valid polygon passes validation"""
        geojson = {
            "type": "Polygon",
            "coordinates": [[
                [0, 0], [1, 0], [1, 1], [0, 1], [0, 0]
            ]]
        }
        is_valid, errors = AOIValidator.validate_geojson(geojson)
        assert is_valid is True
        assert errors is None

    def test_invalid_not_polygon_type(self):
        """Test non-Polygon type is rejected"""
        geojson = {
            "type": "LineString",
            "coordinates": [[0, 0], [1, 1]]
        }
        is_valid, errors = AOIValidator.validate_geojson(geojson)
        assert is_valid is False
        assert any("Polygon" in e for e in errors)

    def test_invalid_polygon_not_closed(self):
        """Test polygon that isn't closed is rejected"""
        geojson = {
            "type": "Polygon",
            "coordinates": [[
                [0, 0], [1, 0], [1, 1], [0, 1]  # Missing closing point
            ]]
        }
        is_valid, errors = AOIValidator.validate_geojson(geojson)
        assert is_valid is False
        assert any("closed" in e.lower() for e in errors)

    def test_invalid_too_few_points(self):
        """Test polygon with fewer than 4 points is rejected"""
        geojson = {
            "type": "Polygon",
            "coordinates": [[
                [0, 0], [1, 0], [0, 0]
            ]]
        }
        is_valid, errors = AOIValidator.validate_geojson(geojson)
        assert is_valid is False
        assert any("4 points" in e for e in errors)

    def test_invalid_empty_coordinates(self):
        """Test empty coordinates rejected"""
        geojson = {
            "type": "Polygon",
            "coordinates": []
        }
        is_valid, errors = AOIValidator.validate_geojson(geojson)
        assert is_valid is False

    def test_invalid_longitude_out_of_bounds(self):
        """Test longitude > 180 is rejected"""
        geojson = {
            "type": "Polygon",
            "coordinates": [[
                [200, 0], [201, 0], [201, 1], [200, 1], [200, 0]
            ]]
        }
        is_valid, errors = AOIValidator.validate_geojson(geojson)
        assert is_valid is False
        assert any("Longitude" in e for e in errors)

    def test_invalid_latitude_out_of_bounds(self):
        """Test latitude > 90 is rejected"""
        geojson = {
            "type": "Polygon",
            "coordinates": [[
                [0, 95], [1, 95], [1, 96], [0, 96], [0, 95]
            ]]
        }
        is_valid, errors = AOIValidator.validate_geojson(geojson)
        assert is_valid is False
        assert any("Latitude" in e for e in errors)

    def test_self_intersecting_polygon(self):
        """Test self-intersecting polygon (bowtie) is rejected"""
        geojson = {
            "type": "Polygon",
            "coordinates": [[
                [0, 0], [2, 2], [2, 0], [0, 2], [0, 0]  # Bowtie shape
            ]]
        }
        is_valid, errors = AOIValidator.validate_geojson(geojson)
        assert is_valid is False
        assert any("self-intersecting" in e.lower() or "invalid" in e.lower() for e in errors)

    def test_size_limit_within(self):
        """Test area within limit passes"""
        is_valid, error = AOIValidator.check_size_limit(500, max_km2=1000)
        assert is_valid is True
        assert error is None

    def test_size_limit_exceeded(self):
        """Test area exceeding limit fails"""
        is_valid, error = AOIValidator.check_size_limit(1500, max_km2=1000)
        assert is_valid is False
        assert "exceeds" in error.lower()

    def test_valid_bounds_check(self):
        """Test bbox within valid bounds passes"""
        ok, err = AOIValidator.check_valid_bounds([10, 20, 30, 40])
        assert ok is True
        assert err is None

    def test_invalid_bounds_check(self):
        """Test bbox outside valid bounds fails"""
        ok, err = AOIValidator.check_valid_bounds([200, 20, 210, 40])
        assert ok is False
        assert "outside" in err.lower()


# ---------------------------------------------------------------------------
# AOICalculator tests
# ---------------------------------------------------------------------------

class TestAOICalculator:

    def test_bounds_extraction(self):
        """Test bounding box extraction"""
        geojson = {
            "type": "Polygon",
            "coordinates": [[
                [0, 0], [2, 0], [2, 1], [0, 1], [0, 0]
            ]]
        }
        bbox = AOIValidator.extract_bounds(geojson)
        assert bbox == [0.0, 0.0, 2.0, 1.0]

    def test_area_calculation_at_equator(self):
        """Test area calculation: 1° × 1° square at equator ≈ 12,300 km²"""
        geojson = {
            "type": "Polygon",
            "coordinates": [[
                [0, 0], [1, 0], [1, 1], [0, 1], [0, 0]
            ]]
        }
        area_m2, area_km2 = AOICalculator.calculate_area(geojson)

        assert area_m2 > 0
        assert area_km2 > 0
        # Web Mercator at equator: ~12,300 km² for 1°×1°
        assert 10000 < area_km2 < 15000

    def test_area_calculation_nonzero(self):
        """Test that a small polygon has non-zero area"""
        geojson = {
            "type": "Polygon",
            "coordinates": [[
                [77.0, 28.0], [77.1, 28.0], [77.1, 28.1], [77.0, 28.1], [77.0, 28.0]
            ]]
        }
        area_m2, area_km2 = AOICalculator.calculate_area(geojson)
        assert area_km2 > 0

    def test_centroid_calculation(self):
        """Test centroid of a symmetric square"""
        geojson = {
            "type": "Polygon",
            "coordinates": [[
                [0, 0], [2, 0], [2, 2], [0, 2], [0, 0]
            ]]
        }
        centroid = AOICalculator.calculate_centroid(geojson)
        assert centroid is not None
        assert centroid == (1.0, 1.0)

    def test_centroid_delhi(self):
        """Test centroid of a bbox around Delhi"""
        geojson = {
            "type": "Polygon",
            "coordinates": [[
                [77.0, 28.0], [77.4, 28.0], [77.4, 28.4], [77.0, 28.4], [77.0, 28.0]
            ]]
        }
        centroid = AOICalculator.calculate_centroid(geojson)
        assert centroid is not None
        lon, lat = centroid
        assert 77.1 < lon < 77.3
        assert 28.1 < lat < 28.3

    def test_create_bbox_polygon(self):
        """Test creating polygon from bbox"""
        polygon = AOICalculator.create_bbox_polygon([10, 20, 30, 40])
        assert polygon["type"] == "Polygon"
        coords = polygon["coordinates"][0]
        assert len(coords) == 5  # 4 corners + closing point
        assert coords[0] == coords[-1]  # closed ring


# ---------------------------------------------------------------------------
# AOIIntersection tests
# ---------------------------------------------------------------------------

class TestAOIIntersection:

    def test_overlapping_polygons(self):
        """Test intersection of two overlapping squares"""
        geo1 = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]]
        }
        geo2 = {
            "type": "Polygon",
            "coordinates": [[[1, 1], [3, 1], [3, 3], [1, 3], [1, 1]]]
        }
        result = AOIIntersection.intersection(geo1, geo2)
        assert result is not None
        assert result["type"] in ("Polygon", "MultiPolygon")

    def test_non_overlapping_polygons(self):
        """Test intersection of two non-overlapping squares returns None"""
        geo1 = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
        }
        geo2 = {
            "type": "Polygon",
            "coordinates": [[[5, 5], [6, 5], [6, 6], [5, 6], [5, 5]]]
        }
        result = AOIIntersection.intersection(geo1, geo2)
        assert result is None

    def test_overlap_percentage(self):
        """Test overlap percentage of two overlapping squares"""
        geo1 = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]]
        }
        geo2 = {
            "type": "Polygon",
            "coordinates": [[[1, 1], [3, 1], [3, 3], [1, 3], [1, 1]]]
        }
        pct = AOIIntersection.overlap_percentage(geo1, geo2)
        assert pct is not None
        # Overlap is 1×1 square out of 2×2 square = 25%
        assert abs(pct - 25.0) < 0.01

    def test_overlap_percentage_no_overlap(self):
        """Test overlap percentage of non-overlapping polygons"""
        geo1 = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
        }
        geo2 = {
            "type": "Polygon",
            "coordinates": [[[5, 5], [6, 5], [6, 6], [5, 6], [5, 5]]]
        }
        pct = AOIIntersection.overlap_percentage(geo1, geo2)
        assert pct == 0.0

    def test_full_containment(self):
        """Test 100% overlap when one polygon fully contains the other"""
        geo1 = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [4, 0], [4, 4], [0, 4], [0, 0]]]
        }
        geo2 = {
            "type": "Polygon",
            "coordinates": [[[1, 1], [3, 1], [3, 3], [1, 3], [1, 1]]]
        }
        # geo2 is inside geo1, so overlap of geo1 w.r.t. geo2
        pct = AOIIntersection.overlap_percentage(geo2, geo1)
        assert pct is not None
        assert abs(pct - 100.0) < 0.01
