"""Tests for spatial alignment and co-registration."""

import os
import tempfile
import pytest
import numpy as np

try:
    import rasterio
    from rasterio.transform import from_origin
except ImportError:
    rasterio = None

from app.geospatial.alignment import align_rasters
from tests.test_geospatial import create_synthetic_raster


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


def test_align_perfect_match(temp_dir):
    if rasterio is None: pytest.skip()
    ref_path = os.path.join(temp_dir, "ref.tif")
    tgt_path = os.path.join(temp_dir, "tgt.tif")
    
    create_synthetic_raster(ref_path, width=50, height=50, crs="EPSG:32643")
    create_synthetic_raster(tgt_path, width=50, height=50, crs="EPSG:32643")
    
    res = align_rasters(ref_path, tgt_path)
    
    assert res.get("aligned") is True
    assert res["provenance"] == "perfect_match"
    assert res["aligned_uri"] == tgt_path


def test_align_resampling_required(temp_dir):
    if rasterio is None: pytest.skip()
    ref_path = os.path.join(temp_dir, "ref.tif")
    tgt_path = os.path.join(temp_dir, "tgt.tif")
    
    # Reference is 50x50, EPSG:32643, resolution 10m
    create_synthetic_raster(ref_path, width=50, height=50, crs="EPSG:32643", resolution=10.0)
    
    # Target is 100x100, EPSG:32643, resolution 5m
    create_synthetic_raster(tgt_path, width=100, height=100, crs="EPSG:32643", resolution=5.0)
    
    res = align_rasters(ref_path, tgt_path)
    
    assert res.get("aligned") is True
    assert "bilinear" in res["provenance"]
    
    aligned_uri = res["aligned_uri"]
    assert os.path.exists(aligned_uri)
    assert aligned_uri != tgt_path
    
    # Verify the aligned raster exactly matches the reference
    with rasterio.open(ref_path) as ref_src, rasterio.open(aligned_uri) as aln_src:
        assert ref_src.crs == aln_src.crs
        assert ref_src.transform == aln_src.transform
        assert ref_src.width == aln_src.width
        assert ref_src.height == aln_src.height

def test_align_resampling_mask(temp_dir):
    if rasterio is None: pytest.skip()
    ref_path = os.path.join(temp_dir, "ref_mask.tif")
    tgt_path = os.path.join(temp_dir, "tgt_mask.tif")
    
    create_synthetic_raster(ref_path, width=50, height=50, crs="EPSG:32643", resolution=10.0)
    create_synthetic_raster(tgt_path, width=100, height=100, crs="EPSG:32643", resolution=5.0)
    
    res = align_rasters(ref_path, tgt_path, is_mask=True)
    
    assert res.get("aligned") is True
    assert "nearest" in res["provenance"]


def test_align_missing_file(temp_dir):
    res = align_rasters(os.path.join(temp_dir, "nope.tif"), os.path.join(temp_dir, "nope2.tif"))
    assert "error" in res


def test_align_mock_fallback():
    res = align_rasters("mock://ref.tif", "mock://tgt.tif")
    assert res["aligned"] is True
    assert res["provenance"] == "mock_alignment"
def test_align_missing_crs(temp_dir):
    if rasterio is None: pytest.skip()
    ref_path = os.path.join(temp_dir, "ref_nocrs.tif")
    tgt_path = os.path.join(temp_dir, "tgt_nocrs.tif")
    
    create_synthetic_raster(ref_path, width=50, height=50, crs=None)
    create_synthetic_raster(tgt_path, width=50, height=50, crs="EPSG:32643")
    
    res = align_rasters(ref_path, tgt_path)
    assert "error" in res
    assert "CRS" in res["error"]

def test_align_different_crs(temp_dir):
    if rasterio is None: pytest.skip()
    ref_path = os.path.join(temp_dir, "ref_32643.tif")
    tgt_path = os.path.join(temp_dir, "tgt_32644.tif")
    
    create_synthetic_raster(ref_path, width=50, height=50, crs="EPSG:32643")
    create_synthetic_raster(tgt_path, width=50, height=50, crs="EPSG:32644")
    
    res = align_rasters(ref_path, tgt_path)
    assert res.get("aligned") is True
    assert "bilinear" in res["provenance"]
    
    with rasterio.open(res["aligned_uri"]) as aln_src:
        assert aln_src.crs.to_epsg() == 32643
