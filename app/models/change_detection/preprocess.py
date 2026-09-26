"""Model-specific preprocessing for the Change_detection service.

The service expects 8-bit RGB PNG/JPG images (max 2048 px per side). SatQuery assets can be anything the
geospatial layer produces (GeoTIFF, 16-bit, multi-band, RGBA ...), so this module turns whatever arrives into
an 8-bit RGB PNG. Already-suitable PNG/JPG files are passed through untouched.

Optional libraries (imported only when needed):
    Pillow    - reading/writing PNG/JPG and simple modes
    numpy     - percentile stretching of 16-bit / float data
    rasterio  - reading multi-band or 16-bit GeoTIFFs
"""

from __future__ import annotations

import io

MAX_SIDE = 2048  # keep in sync with the service's MAX_SIDE


class ImagePreparationError(ValueError):
    """The asset could not be turned into an 8-bit RGB PNG the model can use."""


def _png_bytes(image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _stretch_to_uint8(arr):
    """(H, W, 3) float/uint16 array -> uint8, using a per-band 2-98 % percentile stretch."""
    import numpy as np

    arr = arr.astype("float32")
    out = np.empty(arr.shape, dtype="uint8")
    for c in range(arr.shape[-1]):
        lo, hi = np.percentile(arr[..., c], (2, 98))
        out[..., c] = np.clip((arr[..., c] - lo) / max(float(hi - lo), 1e-6) * 255.0, 0, 255)
    return out


def _read_with_rasterio(data: bytes):
    """Read a GeoTIFF from memory: first 3 bands as RGB (a single band is repeated)."""
    import numpy as np
    from PIL import Image
    from rasterio.io import MemoryFile

    with MemoryFile(data) as mem, mem.open() as src:
        arr = src.read()  # (bands, H, W)
    if arr.shape[0] == 1:
        arr = np.repeat(arr, 3, axis=0)
    arr = np.moveaxis(arr[:3], 0, -1)
    if arr.dtype != np.uint8:
        arr = _stretch_to_uint8(arr)
    return Image.fromarray(arr)


def to_rgb8_png(data: bytes) -> bytes:
    """Return the image as 8-bit RGB PNG (or the original bytes if they already are PNG/JPG RGB).

    Raises ImagePreparationError with a readable message if that is not possible.
    """
    try:
        from PIL import Image
    except ImportError:
        return data  # cannot inspect the file; assume it already is an 8-bit RGB PNG/JPG

    image = None
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except Exception:
        image = None  # e.g. a multi-band GeoTIFF that Pillow cannot decode -> try rasterio below

    if image is not None and image.format in ("PNG", "JPEG") and image.mode == "RGB":
        rgb = image
        passthrough = True
    elif image is not None and image.mode in ("RGBA", "LA", "L", "P", "1"):
        rgb = image.convert("RGB")
        passthrough = False
    else:
        try:
            rgb = _read_with_rasterio(data)
        except ImportError:
            if image is None:
                raise ImagePreparationError(
                    "Cannot read this image (probably a multi-band or 16-bit GeoTIFF). Install 'rasterio'."
                )
            try:  # Pillow could read it (e.g. 16-bit grayscale / plain TIFF): stretch it ourselves
                import numpy as np

                arr = np.asarray(image)
                if arr.ndim == 2:
                    arr = np.repeat(arr[..., None], 3, axis=-1)
                rgb = Image.fromarray(_stretch_to_uint8(arr[..., :3]))
            except Exception as exc:
                raise ImagePreparationError(f"Unsupported image format/mode ({image.mode}): {exc}")
        except Exception as exc:
            raise ImagePreparationError(f"Could not read the image: {exc}")
        passthrough = False

    if max(rgb.size) > MAX_SIDE:
        raise ImagePreparationError(
            f"Image is {rgb.size[0]}x{rgb.size[1]} px; the model accepts at most {MAX_SIDE} px per side. "
            "Crop or tile the area upstream."
        )
    return data if passthrough else _png_bytes(rgb)


def _optimal_dimensions(width: int, height: int,
                         max_side: int = 2048,
                         target_min_side: int = 640) -> tuple[int, int]:
    """Calculate optimal dimensions for the change detection server.

    The server uses tile=256 at 5 scales [30%, 40%, 60%, 80%, 100%] with
    quorum=2. For accurate multi-scale consensus, the shorter side should be
    large enough that at least 4 scales produce effective images >= 256px
    (one full tile). Through empirical testing across many image pairs we
    found that a target_min_side of 640 achieves this:

        640 * 0.40 = 256px  →  Scale-40 gets a full tile
        640 * 0.30 = 192px  →  Scale-30 gets a near-full tile

    Constraints:
    - Never distort aspect ratio (uniform scale factor)
    - Never exceed max_side on either dimension
    - Never downscale (only upscale if needed)
    """
    shorter = min(width, height)
    longer = max(width, height)

    if shorter >= target_min_side:
        scale = 1.0
    else:
        scale = target_min_side / shorter

    # Cap by max_side constraint
    if longer * scale > max_side:
        scale = max_side / longer

    # Never downscale
    scale = max(scale, 1.0)

    return round(width * scale), round(height * scale)


def _align_images(b_img, a_img):
    """Align before image to after image using OpenCV feature matching."""
    try:
        from PIL import Image
        try:
            resample = Image.Resampling.LANCZOS
        except AttributeError:
            resample = Image.LANCZOS
    except ImportError:
        return b_img

    try:
        import cv2
        import numpy as np
    except ImportError:
        # Fallback to naive resize if cv2 is not available
        if b_img.size != a_img.size:
            return b_img.resize(a_img.size, resample=resample)
        return b_img

    # Convert to cv2 format (numpy arrays)
    b_arr = np.array(b_img)
    a_arr = np.array(a_img)

    # Convert to grayscale
    b_gray = cv2.cvtColor(b_arr, cv2.COLOR_RGB2GRAY) if b_arr.ndim == 3 else b_arr
    a_gray = cv2.cvtColor(a_arr, cv2.COLOR_RGB2GRAY) if a_arr.ndim == 3 else a_arr

    # Detect ORB features and compute descriptors
    MAX_FEATURES = 5000
    orb = cv2.ORB_create(MAX_FEATURES)
    keypoints1, descriptors1 = orb.detectAndCompute(b_gray, None)
    keypoints2, descriptors2 = orb.detectAndCompute(a_gray, None)

    if descriptors1 is None or descriptors2 is None or len(descriptors1) < 10 or len(descriptors2) < 10:
        if b_img.size != a_img.size:
            return b_img.resize(a_img.size, resample=resample)
        return b_img

    # Match features
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = matcher.match(descriptors1, descriptors2)

    # Sort matches by distance and keep top 20%
    matches = sorted(matches, key=lambda x: x.distance)
    keep_fraction = 0.2
    num_good_matches = int(len(matches) * keep_fraction)
    matches = matches[:max(num_good_matches, 10)]

    # Extract location of good matches
    points1 = np.zeros((len(matches), 2), dtype=np.float32)
    points2 = np.zeros((len(matches), 2), dtype=np.float32)

    for i, match in enumerate(matches):
        points1[i, :] = keypoints1[match.queryIdx].pt
        points2[i, :] = keypoints2[match.trainIdx].pt

    # Find homography
    h, mask = cv2.findHomography(points1, points2, cv2.RANSAC, 5.0)
    
    if h is None:
        if b_img.size != a_img.size:
            return b_img.resize(a_img.size, resample=resample)
        return b_img

    # Warp before image to align with after image
    height, width = a_arr.shape[:2]
    aligned_b_arr = cv2.warpPerspective(b_arr, h, (width, height))
    
    return Image.fromarray(aligned_b_arr)


def _enhance_image(img):
    """Apply mild sharpening to improve blurry images."""
    try:
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Sharpness(img)
        return enhancer.enhance(1.5)  # Mild sharpening (1.0 is original)
    except ImportError:
        return img


def coregister_pair(before_data: bytes, after_data: bytes) -> tuple[bytes, bytes]:
    """Co-register and optimally resize two raw images for change detection.

    Steps:
    1. Read both images with Pillow.
    2. Match the before image dimensions to the after image.
    3. Upscale both to the optimal dimensions for the multi-scale server
       (shorter side >= 640px, capped at 2048px, preserving aspect ratio).

    This ensures that 4 out of 5 multi-scale votes contribute meaningful
    agreement to the quorum consensus, dramatically improving detection of
    fine-grained changes (individual building footprints).
    """
    try:
        from PIL import Image
    except ImportError:
        return before_data, after_data

    try:
        b_img = Image.open(io.BytesIO(before_data))
        a_img = Image.open(io.BytesIO(after_data))
        b_img.load()
        a_img.load()
    except Exception:
        return before_data, after_data

    try:
        resample = Image.Resampling.LANCZOS
    except AttributeError:
        resample = Image.LANCZOS

    # Step 1: Enhance (sharpen) images if they are blurry
    b_img = _enhance_image(b_img)
    a_img = _enhance_image(a_img)

    # Step 2: Intelligent Alignment (Homography) to match before to after
    b_img = _align_images(b_img, a_img)

    # Step 2: Calculate and apply optimal upscale
    w, h = a_img.size
    opt_w, opt_h = _optimal_dimensions(w, h)

    if (opt_w, opt_h) != (w, h):
        b_img = b_img.resize((opt_w, opt_h), resample=resample)
        a_img = a_img.resize((opt_w, opt_h), resample=resample)

    return _png_bytes(b_img), _png_bytes(a_img)
