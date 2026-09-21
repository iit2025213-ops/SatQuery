"""
Download a real LEVIR-CD style before/after satellite image pair and test ChangeFormer.
LEVIR-CD is the actual benchmark ChangeFormer was trained on.
"""
import asyncio
import json
import os
import time
import urllib.request
from io import BytesIO
from PIL import Image

from dotenv import load_dotenv
load_dotenv()

from app.config import get_settings
from app.models.changeformer.client import ChangeFormerClient

# --- Public LEVIR-CD style satellite image pairs from open sources ---
# These are real bi-temporal satellite images showing building changes
IMAGE_PAIRS = [
    {
        "name": "LEVIR-CD Sample (Urban Building Change)",
        "before": "https://github.com/justchenhao/LEVIR-CD-256/raw/main/train/A/train_1.png",
        "after":  "https://github.com/justchenhao/LEVIR-CD-256/raw/main/train/B/train_1.png",
    },
    {
        # Fallback: WHU Building Change Detection Dataset sample
        "name": "Aerial Building Change (WHU-CD style)",
        "before": "https://raw.githubusercontent.com/daifeng2016/Change-Detection-Dataset-for-High-Resolution-Satellite-Imagery/master/img/before.png",
        "after":  "https://raw.githubusercontent.com/daifeng2016/Change-Detection-Dataset-for-High-Resolution-Satellite-Imagery/master/img/after.png",
    },
]

# Fallback: generate synthetic but realistic looking before/after pair
def generate_synthetic_pair():
    """Generate a synthetic before/after pair simulating building appearance."""
    import numpy as np
    rng = np.random.default_rng(42)

    # Create a 256x256 "bare land" image
    before = np.zeros((256, 256, 3), dtype=np.uint8)
    before[:, :, 0] = rng.integers(80, 120, (256, 256))  # reddish-brown soil
    before[:, :, 1] = rng.integers(70, 110, (256, 256))
    before[:, :, 2] = rng.integers(40, 80,  (256, 256))
    # Add some texture
    noise = rng.integers(-20, 20, (256, 256, 3))
    before = np.clip(before.astype(int) + noise, 0, 255).astype(np.uint8)

    # Create "after" with buildings (grey rectangular structures)
    after = before.copy()
    # Place 4 building footprints (grey boxes)
    buildings = [
        (20,  20,  80,  80),
        (90,  20, 150,  80),
        (20,  90,  80, 150),
        (100, 100, 200, 200),
    ]
    for (r1, c1, r2, c2) in buildings:
        grey = rng.integers(130, 180)
        after[r1:r2, c1:c2, :] = grey

    return Image.fromarray(before), Image.fromarray(after)


async def test_with_pair(name, before_path, after_path, settings):
    print(f"\n{'='*55}")
    print(f"  Testing: {name}")
    print(f"  Before : {before_path}")
    print(f"  After  : {after_path}")
    print(f"{'='*55}")

    client = ChangeFormerClient(
        endpoint=settings.changeformer_endpoint,
        api_key=settings.changeformer_api_key,
        timeout_seconds=120,
    )

    payload = {
        "before_asset_uri": before_path,
        "after_asset_uri":  after_path,
        "before_asset_id":  "before",
        "after_asset_id":   "after",
    }

    t0 = time.time()
    try:
        result = await client.infer(payload)
    except Exception as exc:
        print(f"  FAILED: {exc}")
        return None

    elapsed = time.time() - t0
    print(f"  Response in {elapsed:.2f}s")

    changed_px = result.get("changed_pixels", 0)
    total_px   = result.get("total_pixels", 0)
    mask_uri   = result.get("change_mask_uri", "")

    pct = (changed_px / total_px * 100) if total_px > 0 else 0

    print(f"  Changed pixels : {changed_px:,} / {total_px:,}")
    print(f"  Change area    : {pct:.2f}%")

    if pct < 1.0:
        verdict = "Under-sensitive (model may not recognise this image type)"
    elif 1.0 <= pct <= 40.0:
        verdict = "Plausible detection - model is working correctly!"
    else:
        verdict = "Over-detecting - possible misregistration or hallucination"
    print(f"  Verdict        : {verdict}")

    # Save mask + comparison
    os.makedirs("scratch", exist_ok=True)
    safe_name = name.replace(" ", "_").replace("(", "").replace(")", "")[:30]

    if mask_uri and os.path.exists(mask_uri):
        mask_img = Image.open(mask_uri).convert("L")
        mask_out = f"scratch/cf_mask_{safe_name}.png"
        mask_img.save(mask_out)
        print(f"  Mask saved     : {os.path.abspath(mask_out)}")

        # Load before/after for side-by-side
        try:
            if before_path.startswith("http"):
                from io import BytesIO
                import urllib.request
                with urllib.request.urlopen(before_path, timeout=15) as r:
                    b_img = Image.open(BytesIO(r.read())).convert("RGB").resize((256, 256))
                with urllib.request.urlopen(after_path, timeout=15) as r:
                    a_img = Image.open(BytesIO(r.read())).convert("RGB").resize((256, 256))
            else:
                b_img = Image.open(before_path).convert("RGB").resize((256, 256))
                a_img = Image.open(after_path).convert("RGB").resize((256, 256))

            m_img = mask_img.resize((256, 256)).convert("RGB")
            comparison = Image.new("RGB", (768, 256))
            comparison.paste(b_img, (0,   0))
            comparison.paste(a_img, (256, 0))
            comparison.paste(m_img, (512, 0))
            comp_out = f"scratch/cf_comparison_{safe_name}.png"
            comparison.save(comp_out)
            print(f"  Comparison     : {os.path.abspath(comp_out)}")
        except Exception as e:
            print(f"  (Could not build comparison: {e})")

    return pct


async def main():
    settings = get_settings()
    print(f"ChangeFormer endpoint: {settings.changeformer_endpoint}")

    # Test 1: Synthetic pair (guaranteed to work, simulates building construction)
    print("\n[TEST 1] Synthetic satellite pair (simulated building construction)")
    before_img, after_img = generate_synthetic_pair()
    before_path = "scratch/synth_before.png"
    after_path  = "scratch/synth_after.png"
    os.makedirs("scratch", exist_ok=True)
    before_img.save(before_path)
    after_img.save(after_path)
    await test_with_pair(
        "Synthetic Building Construction",
        before_path, after_path, settings
    )

    # Test 2: Try to download a real LEVIR-CD sample
    print("\n[TEST 2] Attempting real LEVIR-CD satellite pair download...")
    levir_before = "scratch/levir_before.png"
    levir_after  = "scratch/levir_after.png"
    try:
        url_b = "https://github.com/justchenhao/LEVIR-CD-256/raw/main/train/A/train_1.png"
        url_a = "https://github.com/justchenhao/LEVIR-CD-256/raw/main/train/B/train_1.png"
        urllib.request.urlretrieve(url_b, levir_before)
        urllib.request.urlretrieve(url_a, levir_after)
        print("  Downloaded LEVIR-CD sample successfully!")
        await test_with_pair(
            "LEVIR-CD Real Satellite Pair",
            levir_before, levir_after, settings
        )
    except Exception as e:
        print(f"  Could not download LEVIR-CD ({e}) - skipping.")

    print("\nAll tests complete. Check scratch/ folder for masks and comparisons.")


if __name__ == "__main__":
    asyncio.run(main())
