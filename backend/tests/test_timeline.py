# tests/test_timeline.py

"""
Unit tests for Phase 9: Temporal Timeline

Tests TimelineProcessor (alignment, normalisation, NDVI, GIF generation),
TimelineAdapter routing, and capability registry integration.
"""

import pytest
import numpy as np


# ---------------------------------------------------------------------------
# Test Data Helpers
# ---------------------------------------------------------------------------

def make_image(rows=32, cols=32, bands=3, seed=42):
    """Create a synthetic multi-band image."""
    rng = np.random.RandomState(seed)
    return rng.randint(0, 3000, (bands, rows, cols)).astype(np.float32)


def make_rgb_frame(rows=32, cols=32, colour=(100, 150, 80)):
    """Create a (H, W, 3) uint8 RGB frame."""
    frame = np.zeros((rows, cols, 3), dtype=np.uint8)
    frame[:, :, 0] = colour[0]
    frame[:, :, 1] = colour[1]
    frame[:, :, 2] = colour[2]
    return frame


# ---------------------------------------------------------------------------
# Spatial Alignment Tests
# ---------------------------------------------------------------------------

class TestSpatialAlignment:
    """Test cross-correlation alignment."""

    @pytest.mark.asyncio
    async def test_align_identical_images(self):
        """Aligning identical images should return near-zero RMSE."""
        from app.timeline.processor import TimelineProcessor

        img = make_image(32, 32, 3, seed=1)
        success, aligned, rmse = await TimelineProcessor.align_imagery(img, img.copy())

        assert success is True
        assert rmse < 0.01

    @pytest.mark.asyncio
    async def test_align_returns_same_shape(self):
        """Aligned image should have same shape as input."""
        from app.timeline.processor import TimelineProcessor

        ref = make_image(32, 32, 3, seed=1)
        tgt = make_image(32, 32, 3, seed=2)

        success, aligned, rmse = await TimelineProcessor.align_imagery(ref, tgt)

        assert aligned.shape == ref.shape

    @pytest.mark.asyncio
    async def test_align_2d_images(self):
        """Should handle 2D (single band) images."""
        from app.timeline.processor import TimelineProcessor

        ref = make_image(32, 32, 1, seed=1)[0]  # (H, W)
        tgt = make_image(32, 32, 1, seed=2)[0]

        success, aligned, rmse = await TimelineProcessor.align_imagery(ref, tgt)

        assert success is True
        assert aligned.shape == ref.shape


# ---------------------------------------------------------------------------
# Radiometric Normalisation Tests
# ---------------------------------------------------------------------------

class TestRadiometricNormalisation:
    """Test mean/std normalisation across years."""

    @pytest.mark.asyncio
    async def test_normalise_preserves_reference(self):
        """Reference image should be unchanged."""
        from app.timeline.processor import TimelineProcessor

        ref = make_image(16, 16, 3, seed=1)
        tgt = make_image(16, 16, 3, seed=2)

        normalised = await TimelineProcessor.normalize_radiometry([ref, tgt], reference_idx=0)

        assert len(normalised) == 2
        np.testing.assert_array_equal(normalised[0], ref)

    @pytest.mark.asyncio
    async def test_normalise_adjusts_target(self):
        """Target should be adjusted toward reference statistics."""
        from app.timeline.processor import TimelineProcessor

        ref = make_image(16, 16, 3, seed=1)
        # Make target with very different stats
        tgt = ref * 2 + 500

        normalised = await TimelineProcessor.normalize_radiometry([ref, tgt], reference_idx=0)

        # Normalised target mean should be closer to reference mean
        ref_mean = np.mean(ref)
        tgt_orig_mean = np.mean(tgt)
        tgt_norm_mean = np.mean(normalised[1])

        assert abs(tgt_norm_mean - ref_mean) < abs(tgt_orig_mean - ref_mean)

    @pytest.mark.asyncio
    async def test_normalise_multiple_images(self):
        """Should handle a stack of 5+ images."""
        from app.timeline.processor import TimelineProcessor

        stack = [make_image(16, 16, 3, seed=i) for i in range(6)]

        normalised = await TimelineProcessor.normalize_radiometry(stack, reference_idx=0)

        assert len(normalised) == 6


# ---------------------------------------------------------------------------
# NDVI Tests
# ---------------------------------------------------------------------------

class TestNDVI:
    """Test NDVI calculation."""

    @pytest.mark.asyncio
    async def test_ndvi_range(self):
        """NDVI should be in [-1, 1]."""
        from app.timeline.processor import TimelineProcessor

        nir = np.array([[800, 1200], [500, 1500]], dtype=np.float32)
        red = np.array([[300, 400], [600, 200]], dtype=np.float32)

        result = await TimelineProcessor.calculate_ndvi(nir, red)

        assert result["min"] >= -1.0
        assert result["max"] <= 1.0

    @pytest.mark.asyncio
    async def test_ndvi_vegetation(self):
        """High NIR / low Red should give positive NDVI."""
        from app.timeline.processor import TimelineProcessor

        nir = np.full((10, 10), 2000, dtype=np.float32)
        red = np.full((10, 10), 500, dtype=np.float32)

        result = await TimelineProcessor.calculate_ndvi(nir, red)

        assert result["mean"] > 0.3  # healthy vegetation

    @pytest.mark.asyncio
    async def test_ndvi_bare_soil(self):
        """Similar NIR/Red should give near-zero NDVI."""
        from app.timeline.processor import TimelineProcessor

        nir = np.full((10, 10), 1000, dtype=np.float32)
        red = np.full((10, 10), 900, dtype=np.float32)

        result = await TimelineProcessor.calculate_ndvi(nir, red)

        assert abs(result["mean"]) < 0.2

    @pytest.mark.asyncio
    async def test_ndvi_keys(self):
        """Result should contain min, max, mean."""
        from app.timeline.processor import TimelineProcessor

        nir = np.ones((5, 5), dtype=np.float32) * 1000
        red = np.ones((5, 5), dtype=np.float32) * 400

        result = await TimelineProcessor.calculate_ndvi(nir, red)

        assert "min" in result
        assert "max" in result
        assert "mean" in result


# ---------------------------------------------------------------------------
# Animation Tests
# ---------------------------------------------------------------------------

class TestGIFGeneration:
    """Test GIF animation generation."""

    @pytest.mark.asyncio
    async def test_gif_returns_bytes(self):
        """GIF should return non-empty bytes."""
        from app.timeline.processor import TimelineProcessor

        frames = [
            make_rgb_frame(32, 32, (100, 150, 80)),
            make_rgb_frame(32, 32, (120, 130, 90)),
            make_rgb_frame(32, 32, (80, 160, 70)),
        ]

        gif_bytes = await TimelineProcessor.generate_gif(frames)

        assert isinstance(gif_bytes, bytes)
        assert len(gif_bytes) > 0

    @pytest.mark.asyncio
    async def test_gif_magic_bytes(self):
        """GIF should start with GIF89a magic."""
        from app.timeline.processor import TimelineProcessor

        frames = [make_rgb_frame(16, 16), make_rgb_frame(16, 16)]

        gif_bytes = await TimelineProcessor.generate_gif(frames)

        assert gif_bytes[:6] in (b"GIF89a", b"GIF87a")

    @pytest.mark.asyncio
    async def test_gif_with_labels(self):
        """GIF with year labels should still generate."""
        from app.timeline.processor import TimelineProcessor

        frames = [make_rgb_frame(32, 32) for _ in range(3)]
        labels = ["2020", "2021", "2022"]

        gif_bytes = await TimelineProcessor.generate_gif(frames, labels)

        assert len(gif_bytes) > 0

    @pytest.mark.asyncio
    async def test_gif_empty_frames(self):
        """Empty frame list should return empty bytes."""
        from app.timeline.processor import TimelineProcessor

        gif_bytes = await TimelineProcessor.generate_gif([])

        assert gif_bytes == b""

    @pytest.mark.asyncio
    async def test_gif_greyscale_frames(self):
        """Should handle 2D greyscale frames."""
        from app.timeline.processor import TimelineProcessor

        frames = [
            np.ones((16, 16), dtype=np.uint8) * 100,
            np.ones((16, 16), dtype=np.uint8) * 200,
        ]

        gif_bytes = await TimelineProcessor.generate_gif(frames)

        assert len(gif_bytes) > 0


# ---------------------------------------------------------------------------
# Adapter + Registry Tests
# ---------------------------------------------------------------------------

class TestTimelineAdapter:
    """Test adapter initialisation."""

    def test_adapter_init(self):
        from app.models.timeline_adapter import TimelineAdapter

        adapter = TimelineAdapter()
        assert adapter is not None


class TestTimelineRegistry:
    """Test capability registry integration."""

    def test_retrieve_temporal_registered(self):
        from app.registry.registry import CapabilityRegistry

        registry = CapabilityRegistry()
        cap = registry.get_capability("retrieve_temporal_imagery")
        assert cap is not None
        assert cap["adapter"] == "TimelineAdapter"

    def test_animation_registered(self):
        from app.registry.registry import CapabilityRegistry

        registry = CapabilityRegistry()
        cap = registry.get_capability("generate_timeline_animation")
        assert cap is not None
        assert cap["adapter"] == "TimelineAdapter"

    def test_timeline_adapter_instance_exists(self):
        from app.registry.registry import CapabilityRegistry

        registry = CapabilityRegistry()
        adapter = registry.get_adapter("retrieve_temporal_imagery")
        assert adapter is not None
