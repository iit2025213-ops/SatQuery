# app/timeline/processor.py

"""
Timeline Processor — Phase 9

Retrieves multi-year satellite imagery from GEE, aligns spatially,
normalises radiometrically, calculates spectral indices, and
generates animations (GIF/MP4).

Source of truth: 6-9.md Phase 9 architecture.
"""

import logging
import io
import uuid
from typing import List, Dict, Optional, Tuple

import numpy as np
from scipy import ndimage

logger = logging.getLogger("satquery")


class TimelineProcessor:
    """Process multi-year satellite imagery into timelines."""

    # ------------------------------------------------------------------
    # Multi-year retrieval
    # ------------------------------------------------------------------

    @staticmethod
    async def retrieve_timeline(
        gee_connector,
        aoi_geojson: dict,
        date_start: str,
        date_end: str,
        collection: str = "Sentinel-2",
        cloud_cover_max: int = 20,
    ) -> Tuple[Dict[int, Dict], Optional[int]]:
        """
        Retrieve the best (lowest cloud cover) scene for each year.

        Args:
            gee_connector: Authenticated GEEConnector instance.
            aoi_geojson: GeoJSON Polygon dict.
            date_start: "YYYY-MM-DD" — first year to query.
            date_end: "YYYY-MM-DD" — last year to query.
            collection: "Sentinel-2" or "Landsat-8".
            cloud_cover_max: Max cloud cover percentage.

        Returns:
            (scenes_by_year dict, reference_year int)
        """
        try:
            start_year = int(date_start.split("-")[0])
            end_year = int(date_end.split("-")[0])

            scenes_by_year: Dict[int, Dict] = {}

            for year in range(start_year, end_year + 1):
                year_start = f"{year}-01-01"
                year_end = f"{year}-12-31"

                if collection == "Sentinel-2":
                    scenes = await gee_connector.query_sentinel2(
                        aoi_geojson, year_start, year_end, cloud_cover_max
                    )
                else:
                    scenes = await gee_connector.query_landsat(
                        aoi_geojson, year_start, year_end, cloud_cover_max
                    )

                if scenes:
                    best = min(
                        scenes,
                        key=lambda s: s.get("cloud_cover_percent", 100),
                    )
                    scenes_by_year[year] = best
                    logger.info(
                        f"Year {year}: {best['id']} "
                        f"(cloud {best.get('cloud_cover_percent', '?')}%)"
                    )
                else:
                    logger.warning(f"Year {year}: no scenes found")

            reference_year = min(scenes_by_year.keys()) if scenes_by_year else start_year

            logger.info(
                f"✅ Timeline retrieved — {len(scenes_by_year)} years, "
                f"ref year {reference_year}"
            )
            return scenes_by_year, reference_year

        except Exception as e:
            logger.error(f"❌ Error retrieving timeline: {e}")
            return {}, None

    # ------------------------------------------------------------------
    # Spatial alignment
    # ------------------------------------------------------------------

    @staticmethod
    async def align_imagery(
        reference: np.ndarray,
        target: np.ndarray,
        max_shift: int = 20,
    ) -> Tuple[bool, np.ndarray, float]:
        """
        Align a target image to a reference image using
        cross-correlation shift estimation.

        Args:
            reference: (H, W) or (C, H, W) reference array.
            target: same shape as reference.
            max_shift: maximum pixel shift to search.

        Returns:
            (success, aligned_image, rmse)
        """
        try:
            # Work with 2D greyscale for shift estimation
            if reference.ndim == 3:
                ref_grey = np.mean(reference, axis=0).astype(np.float32)
                tgt_grey = np.mean(target, axis=0).astype(np.float32)
            else:
                ref_grey = reference.astype(np.float32)
                tgt_grey = target.astype(np.float32)

            # Normalise
            ref_grey = (ref_grey - ref_grey.min()) / (ref_grey.max() - ref_grey.min() + 1e-8)
            tgt_grey = (tgt_grey - tgt_grey.min()) / (tgt_grey.max() - tgt_grey.min() + 1e-8)

            # Estimate shift via cross-correlation
            shift = TimelineProcessor._estimate_shift(ref_grey, tgt_grey, max_shift)

            # Apply shift
            if target.ndim == 3:
                aligned = ndimage.shift(target, [0, shift[0], shift[1]], order=1, cval=0)
            else:
                aligned = ndimage.shift(target, [shift[0], shift[1]], order=1, cval=0)

            # RMSE
            if aligned.ndim == 3:
                aligned_grey = np.mean(aligned, axis=0).astype(np.float32)
            else:
                aligned_grey = aligned.astype(np.float32)

            aligned_grey = (aligned_grey - aligned_grey.min()) / (
                aligned_grey.max() - aligned_grey.min() + 1e-8
            )
            rmse = float(np.sqrt(np.mean((ref_grey - aligned_grey) ** 2)))

            logger.info(f"✅ Aligned image — shift {shift}, RMSE {rmse:.4f}")
            return True, aligned, rmse

        except Exception as e:
            logger.error(f"❌ Error aligning imagery: {e}")
            return False, target, 999.0

    @staticmethod
    def _estimate_shift(
        ref: np.ndarray, tgt: np.ndarray, max_shift: int = 20
    ) -> Tuple[int, int]:
        """Estimate pixel shift using cross-correlation (coarse → fine)."""
        best_shift = (0, 0)
        best_corr = -np.inf

        # Coarse search (step=5)
        for dy in range(-max_shift, max_shift + 1, 5):
            for dx in range(-max_shift, max_shift + 1, 5):
                shifted = ndimage.shift(tgt, [dy, dx], order=0, cval=0)
                corr = float(np.sum(ref * shifted))
                if corr > best_corr:
                    best_corr = corr
                    best_shift = (dy, dx)

        # Fine search around best coarse result (step=1)
        cy, cx = best_shift
        for dy in range(cy - 4, cy + 5):
            for dx in range(cx - 4, cx + 5):
                shifted = ndimage.shift(tgt, [dy, dx], order=0, cval=0)
                corr = float(np.sum(ref * shifted))
                if corr > best_corr:
                    best_corr = corr
                    best_shift = (dy, dx)

        return best_shift

    # ------------------------------------------------------------------
    # Radiometric normalisation
    # ------------------------------------------------------------------

    @staticmethod
    async def normalize_radiometry(
        imagery_stack: List[np.ndarray],
        reference_idx: int = 0,
    ) -> List[np.ndarray]:
        """
        Normalise reflectance across years using histogram matching
        to a reference image (linear mean/std correction per band).

        Args:
            imagery_stack: List of (C, H, W) arrays.
            reference_idx: Index of reference image.

        Returns:
            List of normalised arrays (same shapes).
        """
        try:
            reference = imagery_stack[reference_idx].astype(np.float32)
            normalised = []

            for i, image in enumerate(imagery_stack):
                if i == reference_idx:
                    normalised.append(reference)
                    continue

                img = image.astype(np.float32)
                norm_img = np.zeros_like(img)

                n_bands = img.shape[0] if img.ndim == 3 else 1

                for band in range(n_bands):
                    ref_band = reference[band] if reference.ndim == 3 else reference
                    img_band = img[band] if img.ndim == 3 else img

                    ref_mean = np.nanmean(ref_band)
                    ref_std = np.nanstd(ref_band) + 1e-8
                    img_mean = np.nanmean(img_band)
                    img_std = np.nanstd(img_band) + 1e-8

                    normalised_band = (img_band - img_mean) * (ref_std / img_std) + ref_mean

                    if img.ndim == 3:
                        norm_img[band] = normalised_band
                    else:
                        norm_img = normalised_band

                normalised.append(norm_img)

            logger.info(f"✅ Normalised {len(normalised)} images")
            return normalised

        except Exception as e:
            logger.error(f"❌ Error normalising radiometry: {e}")
            return imagery_stack

    # ------------------------------------------------------------------
    # Spectral indices
    # ------------------------------------------------------------------

    @staticmethod
    async def calculate_ndvi(
        nir: np.ndarray,
        red: np.ndarray,
    ) -> Dict[str, float]:
        """
        Calculate NDVI from NIR and Red bands.

        Returns: {"min", "max", "mean"}
        """
        try:
            nir_f = nir.astype(np.float32)
            red_f = red.astype(np.float32)

            ndvi = (nir_f - red_f) / (nir_f + red_f + 1e-8)
            valid = ndvi[np.isfinite(ndvi)]

            if len(valid) == 0:
                return {"min": 0.0, "max": 0.0, "mean": 0.0}

            return {
                "min": float(np.min(valid)),
                "max": float(np.max(valid)),
                "mean": float(np.mean(valid)),
            }

        except Exception as e:
            logger.error(f"❌ NDVI calculation error: {e}")
            return {"min": 0.0, "max": 0.0, "mean": 0.0}

    # ------------------------------------------------------------------
    # Animation generation
    # ------------------------------------------------------------------

    @staticmethod
    async def generate_gif(
        frames: List[np.ndarray],
        labels: List[str] = None,
        duration_ms: int = 800,
    ) -> bytes:
        """
        Generate an animated GIF from a list of uint8 frame arrays.

        Args:
            frames: List of (H, W, 3) uint8 RGB arrays.
            labels: Optional year labels (same length as frames).
            duration_ms: Milliseconds per frame.

        Returns:
            GIF bytes.
        """
        from PIL import Image, ImageDraw, ImageFont

        try:
            pil_frames = []
            for i, frame in enumerate(frames):
                if frame.ndim == 2:
                    img = Image.fromarray(frame, mode="L").convert("RGB")
                else:
                    img = Image.fromarray(frame, mode="RGB")

                # Draw year label if provided
                if labels and i < len(labels):
                    draw = ImageDraw.Draw(img)
                    try:
                        font = ImageFont.truetype("arial.ttf", 24)
                    except (OSError, IOError):
                        font = ImageFont.load_default()

                    draw.text(
                        (10, 10), str(labels[i]),
                        fill=(255, 255, 255), font=font,
                    )

                pil_frames.append(img)

            if not pil_frames:
                return b""

            buf = io.BytesIO()
            pil_frames[0].save(
                buf,
                format="GIF",
                save_all=True,
                append_images=pil_frames[1:],
                duration=duration_ms,
                loop=0,
            )
            gif_bytes = buf.getvalue()

            logger.info(
                f"✅ Generated GIF — {len(pil_frames)} frames, "
                f"{len(gif_bytes)} bytes"
            )
            return gif_bytes

        except Exception as e:
            logger.error(f"❌ GIF generation error: {e}")
            return b""

    @staticmethod
    async def generate_mp4(
        frames: List[np.ndarray],
        fps: int = 2,
    ) -> bytes:
        """
        Generate an MP4 video from a list of frame arrays.

        Returns: MP4 bytes (or empty bytes if imageio[ffmpeg] unavailable).
        """
        try:
            import imageio.v3 as iio

            buf = io.BytesIO()
            writer = iio.imopen(buf, "w", plugin="pillow")

            # imageio pillow plugin writes GIF, not MP4
            # For actual MP4 we need ffmpeg plugin:
            try:
                import imageio_ffmpeg  # noqa: F401

                buf2 = io.BytesIO()
                with iio.imopen(buf2, "w", extension=".mp4") as f:
                    for frame in frames:
                        if frame.ndim == 2:
                            frame = np.stack([frame] * 3, axis=-1)
                        f.write(frame)
                mp4_bytes = buf2.getvalue()
                logger.info(f"✅ Generated MP4 — {len(frames)} frames")
                return mp4_bytes

            except ImportError:
                # Fallback: return GIF bytes instead
                logger.warning("imageio-ffmpeg not installed, falling back to GIF")
                return await TimelineProcessor.generate_gif(frames)

        except Exception as e:
            logger.error(f"❌ MP4 generation error: {e}")
            return b""
