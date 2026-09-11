# tests/test_terrain.py

"""
Unit tests for Phase 8: Terrain Experience

Tests TerrainProcessor (hillshade, contours, 3D mesh, GLB export),
TerrainAdapter routing, and capability registry integration.
"""

import pytest
import numpy as np


# ---------------------------------------------------------------------------
# Test Data Helpers
# ---------------------------------------------------------------------------

def make_dem(rows=64, cols=64):
    """Create a synthetic DEM with a hill in the centre."""
    x = np.linspace(-1, 1, cols)
    y = np.linspace(-1, 1, rows)
    xx, yy = np.meshgrid(x, y)
    # Gaussian hill centred at origin — peak ~500 m, base ~200 m
    dem = 200 + 300 * np.exp(-(xx ** 2 + yy ** 2) / 0.3)
    return dem.astype(np.float32)


def make_texture(rows=64, cols=64):
    """Create a simple RGB texture array."""
    texture = np.zeros((rows, cols, 3), dtype=np.uint8)
    texture[:, :, 0] = 80   # R
    texture[:, :, 1] = 140  # G
    texture[:, :, 2] = 60   # B
    return texture


# ---------------------------------------------------------------------------
# 2D Terrain Tests
# ---------------------------------------------------------------------------

class TestHillshade:
    """Test hillshade generation."""

    @pytest.mark.asyncio
    async def test_hillshade_shape(self):
        """Hillshade output should match DEM shape."""
        from app.terrain.processor import TerrainProcessor

        dem = make_dem(64, 64)
        hillshade, _, _ = await TerrainProcessor.generate_2d_terrain(dem)

        assert hillshade.shape == (64, 64)

    @pytest.mark.asyncio
    async def test_hillshade_dtype(self):
        """Hillshade should be uint8 (0-255)."""
        from app.terrain.processor import TerrainProcessor

        dem = make_dem(32, 32)
        hillshade, _, _ = await TerrainProcessor.generate_2d_terrain(dem)

        assert hillshade.dtype == np.uint8
        assert hillshade.max() <= 255
        assert hillshade.min() >= 0

    @pytest.mark.asyncio
    async def test_hillshade_not_uniform(self):
        """Hillshade should have variation (not a flat grey image)."""
        from app.terrain.processor import TerrainProcessor

        dem = make_dem(64, 64)
        hillshade, _, _ = await TerrainProcessor.generate_2d_terrain(dem)

        assert hillshade.std() > 0, "Hillshade should not be uniform"

    @pytest.mark.asyncio
    async def test_custom_azimuth(self):
        """Different azimuth should produce different hillshades."""
        from app.terrain.processor import TerrainProcessor

        dem = make_dem(32, 32)
        hs1, _, _ = await TerrainProcessor.generate_2d_terrain(
            dem, {"hillshade_azimuth": 0}
        )
        hs2, _, _ = await TerrainProcessor.generate_2d_terrain(
            dem, {"hillshade_azimuth": 180}
        )

        assert not np.array_equal(hs1, hs2)


class TestContours:
    """Test contour generation."""

    @pytest.mark.asyncio
    async def test_contour_shape(self):
        """Contour output should match DEM shape."""
        from app.terrain.processor import TerrainProcessor

        dem = make_dem(64, 64)
        _, contours, _ = await TerrainProcessor.generate_2d_terrain(dem)

        assert contours.shape == (64, 64)

    @pytest.mark.asyncio
    async def test_contour_binary(self):
        """Contours should be binary (0 or 255)."""
        from app.terrain.processor import TerrainProcessor

        dem = make_dem(64, 64)
        _, contours, _ = await TerrainProcessor.generate_2d_terrain(dem)

        unique = np.unique(contours)
        assert set(unique).issubset({0, 255})

    @pytest.mark.asyncio
    async def test_contour_interval(self):
        """Smaller interval should produce more contour pixels."""
        from app.terrain.processor import TerrainProcessor

        dem = make_dem(64, 64)
        _, c_wide, _ = await TerrainProcessor.generate_2d_terrain(
            dem, {"contour_interval": 50}
        )
        _, c_narrow, _ = await TerrainProcessor.generate_2d_terrain(
            dem, {"contour_interval": 10}
        )

        wide_count = np.sum(c_wide == 255)
        narrow_count = np.sum(c_narrow == 255)
        assert narrow_count >= wide_count


class TestElevationStats:
    """Test elevation statistics."""

    @pytest.mark.asyncio
    async def test_stats_keys(self):
        """Stats should contain expected keys."""
        from app.terrain.processor import TerrainProcessor

        dem = make_dem(32, 32)
        _, _, stats = await TerrainProcessor.generate_2d_terrain(dem)

        assert "min_elevation_m" in stats
        assert "max_elevation_m" in stats
        assert "mean_elevation_m" in stats
        assert "std_elevation_m" in stats
        assert "relief_m" in stats

    @pytest.mark.asyncio
    async def test_stats_values(self):
        """Stats should reflect the synthetic DEM."""
        from app.terrain.processor import TerrainProcessor

        dem = make_dem(64, 64)
        _, _, stats = await TerrainProcessor.generate_2d_terrain(dem)

        assert stats["min_elevation_m"] >= 200
        assert stats["max_elevation_m"] <= 510
        assert stats["relief_m"] > 0


# ---------------------------------------------------------------------------
# 3D Terrain Tests
# ---------------------------------------------------------------------------

class TestMeshGeneration:
    """Test 3D mesh generation."""

    @pytest.mark.asyncio
    async def test_mesh_returns_bytes(self):
        """3D terrain should return GLB bytes."""
        from app.terrain.processor import TerrainProcessor

        dem = make_dem(32, 32)
        glb_bytes, metadata = await TerrainProcessor.generate_3d_terrain(
            dem, [77.0, 28.5, 77.2, 28.7]
        )

        assert isinstance(glb_bytes, bytes)
        assert len(glb_bytes) > 0

    @pytest.mark.asyncio
    async def test_mesh_metadata(self):
        """Metadata should contain vertex/triangle counts."""
        from app.terrain.processor import TerrainProcessor

        dem = make_dem(32, 32)
        _, metadata = await TerrainProcessor.generate_3d_terrain(
            dem, [77.0, 28.5, 77.2, 28.7]
        )

        assert "vertex_count" in metadata
        assert "triangle_count" in metadata
        assert "file_size_bytes" in metadata
        assert metadata["vertex_count"] > 0
        assert metadata["triangle_count"] > 0

    @pytest.mark.asyncio
    async def test_mesh_vertex_count(self):
        """Vertex count should match grid dimensions."""
        from app.terrain.processor import TerrainProcessor

        dem = make_dem(16, 16)
        _, metadata = await TerrainProcessor.generate_3d_terrain(
            dem, [77.0, 28.5, 77.2, 28.7],
            options={"mesh_resolution": 256},  # no downsampling needed
        )

        assert metadata["vertex_count"] == 16 * 16

    @pytest.mark.asyncio
    async def test_mesh_triangle_count(self):
        """Triangle count should be 2*(rows-1)*(cols-1)."""
        from app.terrain.processor import TerrainProcessor

        dem = make_dem(16, 16)
        _, metadata = await TerrainProcessor.generate_3d_terrain(
            dem, [77.0, 28.5, 77.2, 28.7],
            options={"mesh_resolution": 256},
        )

        expected = 2 * (16 - 1) * (16 - 1)
        assert metadata["triangle_count"] == expected

    @pytest.mark.asyncio
    async def test_mesh_with_texture(self):
        """3D terrain with RGB texture should still export."""
        from app.terrain.processor import TerrainProcessor

        dem = make_dem(16, 16)
        tex = make_texture(16, 16)

        glb_bytes, metadata = await TerrainProcessor.generate_3d_terrain(
            dem, [77.0, 28.5, 77.2, 28.7], texture_rgb=tex
        )

        assert len(glb_bytes) > 0
        assert metadata["vertex_count"] > 0

    @pytest.mark.asyncio
    async def test_glb_magic_bytes(self):
        """GLB files should start with the glTF magic bytes."""
        from app.terrain.processor import TerrainProcessor

        dem = make_dem(16, 16)
        glb_bytes, _ = await TerrainProcessor.generate_3d_terrain(
            dem, [77.0, 28.5, 77.2, 28.7]
        )

        # glTF magic: 0x46546C67 = "glTF" in little-endian
        assert glb_bytes[:4] == b"glTF"

    @pytest.mark.asyncio
    async def test_exaggeration(self):
        """Higher exaggeration should produce a larger GLB (more z spread)."""
        from app.terrain.processor import TerrainProcessor

        dem = make_dem(16, 16)
        _, meta_low = await TerrainProcessor.generate_3d_terrain(
            dem, [77.0, 28.5, 77.2, 28.7],
            options={"elevation_exaggeration": 0.5},
        )
        _, meta_high = await TerrainProcessor.generate_3d_terrain(
            dem, [77.0, 28.5, 77.2, 28.7],
            options={"elevation_exaggeration": 5.0},
        )

        # Both should have same vertex count
        assert meta_low["vertex_count"] == meta_high["vertex_count"]


# ---------------------------------------------------------------------------
# Adapter + Registry Tests
# ---------------------------------------------------------------------------

class TestTerrainAdapter:
    """Test adapter initialisation."""

    def test_adapter_init(self):
        """Adapter should import and init."""
        from app.models.terrain_adapter import TerrainAdapter

        adapter = TerrainAdapter()
        assert adapter is not None


class TestTerrainRegistry:
    """Test capability registry integration."""

    def test_2d_capability_registered(self):
        from app.registry.registry import CapabilityRegistry

        registry = CapabilityRegistry()
        cap = registry.get_capability("generate_terrain_2d")
        assert cap is not None
        assert cap["adapter"] == "TerrainAdapter"

    def test_3d_capability_registered(self):
        from app.registry.registry import CapabilityRegistry

        registry = CapabilityRegistry()
        cap = registry.get_capability("generate_terrain_3d")
        assert cap is not None
        assert cap["adapter"] == "TerrainAdapter"

    def test_terrain_adapter_instance_exists(self):
        from app.registry.registry import CapabilityRegistry

        registry = CapabilityRegistry()
        adapter = registry.get_adapter("generate_terrain_2d")
        assert adapter is not None
