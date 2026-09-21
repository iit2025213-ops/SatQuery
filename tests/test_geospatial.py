"""Tests for the Phase 3 Deterministic Geospatial Foundation."""

import os
import tempfile
import numpy as np
import pytest
from datetime import datetime
try:
    import rasterio
    from rasterio.transform import from_origin
except ImportError:
    rasterio = None

from app.geospatial.raster import inspect_raster, determine_modality
from app.geospatial.spatial import calculate_spatial_compatibility
from app.geospatial.temporal import validate_temporal_ordering
from app.tools.area import calculate_area_deterministic


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


def create_synthetic_raster(path: str, width: int=100, height: int=100, count: int=1, 
                            crs: str="EPSG:32643", resolution: float=10.0, tags: dict=None, mask_pixels: int=0):
    """Helper to create a valid GeoTIFF for testing."""
    if rasterio is None:
        pytest.skip("rasterio not installed")
        
    transform = from_origin(500000.0, 4600000.0, resolution, resolution)
    
    with rasterio.open(
        path, 'w',
        driver='GTiff',
        height=height, width=width,
        count=count, dtype=rasterio.uint8,
        crs=crs, transform=transform
    ) as dst:
        if tags:
            dst.update_tags(**tags)
            
        if mask_pixels > 0:
            data = np.zeros((height, width), dtype=np.uint8)
            # Fill first `mask_pixels`
            data.flat[:mask_pixels] = 1
            dst.write(data, 1)


# ------------------------------------------------------------------
# Raster tests
# ------------------------------------------------------------------

def test_inspect_valid_raster(temp_dir):
    if rasterio is None: pytest.skip()
    path = os.path.join(temp_dir, "valid.tif")
    create_synthetic_raster(path, width=50, height=50, count=3, tags={"modality": "optical"})
    
    meta = inspect_raster(path)
    assert meta["valid"] is True
    assert meta["width"] == 50
    assert meta["count"] == 3
    assert meta["crs"] == "EPSG:32643"
    assert meta["resolution_m"] == 10.0
    assert "optical" == determine_modality(meta["tags"], meta["count"])


def test_inspect_missing_file():
    meta = inspect_raster("does_not_exist.tif")
    assert meta["valid"] is False
    assert "error" in meta


def test_determine_modality_heuristics():
    assert determine_modality({}, 3) == "optical"
    assert determine_modality({}, 13) == "multispectral"
    assert determine_modality({}, 2) == "sar"
    assert determine_modality({}, 5) == "unknown"


# ------------------------------------------------------------------
# Spatial tests
# ------------------------------------------------------------------

def test_spatial_compatibility_overlapping():
    # Two identical bounds
    bounds1 = [0.0, 0.0, 100.0, 100.0]
    bounds2 = [0.0, 0.0, 100.0, 100.0]
    res = calculate_spatial_compatibility(bounds1, "EPSG:32643", bounds2, "EPSG:32643")
    assert res["compatible"] is True
    assert res["overlap_percentage"] == 100.0


def test_spatial_compatibility_disjoint():
    bounds1 = [0.0, 0.0, 100.0, 100.0]
    bounds2 = [200.0, 200.0, 300.0, 300.0]
    res = calculate_spatial_compatibility(bounds1, "EPSG:32643", bounds2, "EPSG:32643")
    assert res["compatible"] is False
    assert res["overlap_percentage"] == 0.0


def test_spatial_compatibility_reprojection():
    # Bounds in EPSG:4326 (lon/lat) roughly around Paris
    bounds_4326 = [2.2, 48.8, 2.4, 48.9]
    # Synthetic bounds in a projected CRS that overlapping with Paris
    bounds_32631 = [441000, 5405000, 456000, 5417000] 
    
    res = calculate_spatial_compatibility(bounds_4326, "EPSG:4326", bounds_32631, "EPSG:32631")
    # As long as there's no error and it attempted reprojection, it's a pass for the unit test.
    assert "error" not in res
    assert isinstance(res["overlap_percentage"], float)


# ------------------------------------------------------------------
# Temporal tests
# ------------------------------------------------------------------

def test_temporal_ordering_valid():
    res = validate_temporal_ordering("2024-01-01T10:00:00Z", "2024-02-01T10:00:00Z")
    assert res["valid"] is True
    assert res["interval_days"] == 31


def test_temporal_ordering_invalid_reversed():
    res = validate_temporal_ordering("2024-02-01T10:00:00Z", "2024-01-01T10:00:00Z")
    assert res["valid"] is False
    assert "Reversed" in res["reason"]


def test_temporal_ordering_invalid_equal():
    res = validate_temporal_ordering("2024-01-01T10:00:00Z", "2024-01-01T10:00:00Z")
    assert res["valid"] is False
    assert "identical" in res["reason"]


def test_temporal_ordering_missing():
    res = validate_temporal_ordering(None, "2024-01-01T10:00:00Z")
    assert res["valid"] is False
    assert res["status"] == "UNKNOWN_TIMESTAMP"


# ------------------------------------------------------------------
# Area tests
# ------------------------------------------------------------------

def test_area_calculation_deterministic(temp_dir):
    if rasterio is None: pytest.skip()
    path = os.path.join(temp_dir, "mask.tif")
    # 100 pixels * 10x10 resolution = 10,000 m2
    create_synthetic_raster(path, width=10, height=10, count=1, crs="EPSG:32643", resolution=10.0, mask_pixels=100)
    
    res = calculate_area_deterministic(mask_uri=path)
    assert "error" not in res
    assert res["changed_pixel_count"] == 100
    assert res["pixel_area_m2"] == 100.0
    assert res["area_m2"] == 10000.0
    assert res["total_pixel_count"] == 100
    assert res["valid_pixel_count"] == 100
    assert res["pixel_width"] == 10.0
    assert res["pixel_height"] == 10.0


def test_area_calculation_geographic():
    # If mask is geographic, it should attempt to use Geod or fallback
    # Pass arbitrary bounds
    res = calculate_area_deterministic(
        mask_uri="mock://mask.tif",
        mock_changed_pixels=10, 
        resolution_m=10.0, 
        crs_str="EPSG:4326", 
        bounds=[0.0, 0.0, 1.0, 1.0]
    )
    assert "error" not in res
    assert "EPSG:6933" in res["crs"]
    assert res["area_m2"] > 0

def test_area_calculation_missing_crs(temp_dir):
    if rasterio is None: pytest.skip()
    path = os.path.join(temp_dir, "no_crs.tif")
    # Missing CRS
    create_synthetic_raster(path, width=10, height=10, count=1, crs=None, resolution=10.0, mask_pixels=100)
    
    res = calculate_area_deterministic(mask_uri=path)
    assert "error" in res
    assert "missing CRS" in res["error"]

def test_area_calculation_zero_changed_pixels(temp_dir):
    if rasterio is None: pytest.skip()
    path = os.path.join(temp_dir, "no_change.tif")
    # 0 mask pixels
    create_synthetic_raster(path, width=10, height=10, count=1, crs="EPSG:32643", resolution=10.0, mask_pixels=0)
    
    res = calculate_area_deterministic(mask_uri=path)
    assert "error" not in res
    assert res["changed_pixel_count"] == 0
    assert res["area_m2"] == 0.0

def test_area_calculation_nodata_exclusion(temp_dir):
    if rasterio is None: pytest.skip()
    path = os.path.join(temp_dir, "nodata.tif")
    
    from rasterio.transform import from_origin
    transform = from_origin(500000.0, 4600000.0, 10.0, 10.0)
    with rasterio.open(
        path, 'w', driver='GTiff', height=10, width=10, count=1, 
        dtype=rasterio.uint8, crs="EPSG:32643", transform=transform, nodata=255
    ) as dst:
        data = np.zeros((10, 10), dtype=np.uint8)
        data.flat[:10] = 1   # 10 changed pixels
        data.flat[10:30] = 255 # 20 nodata pixels
        dst.write(data, 1)

    res = calculate_area_deterministic(mask_uri=path)
    assert "error" not in res
    assert res["changed_pixel_count"] == 10
    assert res["valid_pixel_count"] == 80 # 100 - 20 nodata
    assert res["total_pixel_count"] == 100

# ------------------------------------------------------------------
# Processing tests
# ------------------------------------------------------------------

from app.geospatial.processing import create_visual_preview

def test_create_visual_preview(temp_dir):
    if rasterio is None: pytest.skip()
    
    path = os.path.join(temp_dir, "to_normalize.tif")
    # Use uint16 type for testing normalization
    transform = from_origin(500000.0, 4600000.0, 10.0, 10.0)
    with rasterio.open(
        path, 'w',
        driver='GTiff',
        height=50, width=50,
        count=1, dtype=rasterio.uint16,
        crs="EPSG:32643", transform=transform
    ) as dst:
        # Create a gradient from 0 to 10000
        data = np.linspace(0, 10000, 50*50, dtype=np.uint16).reshape(50, 50)
        dst.write(data, 1)
        
    res = create_visual_preview(path)
    
    assert "error" not in res
    assert "preview_uri" in res
    assert res["new_dtype"] == "uint8"
    assert res["original_dtype"] == "uint16"
    assert len(res["percentiles"]) == 1
    
    # Read back and check it's 0-255
    with rasterio.open(res["preview_uri"]) as norm_src:
        norm_data = norm_src.read(1)
        assert norm_src.dtypes[0] == rasterio.uint8
        assert np.max(norm_data) <= 255
        assert np.min(norm_data) >= 0

    # Ensure source was not modified
    with rasterio.open(path) as src:
        assert src.dtypes[0] == rasterio.uint16

# ------------------------------------------------------------------
# Reprojection tests
# ------------------------------------------------------------------

from app.geospatial.reprojection import reproject_raster

def test_reproject_raster(temp_dir):
    if rasterio is None: pytest.skip()
    path = os.path.join(temp_dir, "to_reproject.tif")
    create_synthetic_raster(path, width=20, height=20, crs="EPSG:32643")
    
    res = reproject_raster(path, "EPSG:4326")
    
    assert "error" not in res
    assert res["reprojected"] is True
    assert res["source_crs"] == "EPSG:32643"
    assert res["target_crs"] == "EPSG:4326"
    
    # Check the new file actually exists and has the right CRS
    with rasterio.open(res["output_uri"]) as src:
        assert src.crs.to_epsg() == 4326

# ------------------------------------------------------------------
# Statistics tests
# ------------------------------------------------------------------

from app.geospatial.statistics import compute_raster_stats

def test_compute_raster_stats(temp_dir):
    if rasterio is None: pytest.skip()
    path = os.path.join(temp_dir, "stats.tif")
    
    from rasterio.transform import from_origin
    transform = from_origin(500000.0, 4600000.0, 10.0, 10.0)
    with rasterio.open(
        path, 'w', driver='GTiff', height=10, width=10, count=2, 
        dtype=rasterio.uint8, crs="EPSG:32643", transform=transform, nodata=255
    ) as dst:
        data1 = np.full((10, 10), 10, dtype=np.uint8)
        data2 = np.full((10, 10), 20, dtype=np.uint8)
        data2[0, 0] = 255 # one nodata pixel
        dst.write(data1, 1)
        dst.write(data2, 2)

    res = compute_raster_stats(path)
    assert "error" not in res
    assert res["valid"] is True
    assert res["band_count"] == 2
    
    band1 = res["bands"][0]
    assert band1["min"] == 10.0
    assert band1["mean"] == 10.0
    assert band1["nodata_count"] == 0
    
    band2 = res["bands"][1]
    assert band2["min"] == 20.0
    assert band2["nodata_count"] == 1
    assert band2["valid_count"] == 99
