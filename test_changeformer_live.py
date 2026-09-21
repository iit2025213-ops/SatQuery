"""
Live test: send before.jpeg + after.jpeg to hosted ChangeFormer.
Saves the change mask PNG locally and prints accuracy statistics.
"""
import asyncio
import base64
import os
import time
from io import BytesIO
from PIL import Image
import json

from dotenv import load_dotenv
load_dotenv()

from app.config import get_settings
from app.models.changeformer.client import ChangeFormerClient

BEFORE = "before.jpeg"
AFTER  = "after.jpeg"

async def main():
    settings = get_settings()

    endpoint = settings.changeformer_endpoint
    api_key  = settings.changeformer_api_key

    print(f"ChangeFormer endpoint : {endpoint}")
    print(f"Before image          : {os.path.abspath(BEFORE)}")
    print(f"After  image          : {os.path.abspath(AFTER)}")
    print()

    if not os.path.exists(BEFORE) or not os.path.exists(AFTER):
        print("ERROR: before.jpeg or after.jpeg not found in current directory!")
        return

    client = ChangeFormerClient(
        endpoint=endpoint,
        api_key=api_key,
        timeout_seconds=300,   # generous timeout for cold starts
    )

    payload = {
        "before_asset_uri": BEFORE,
        "after_asset_uri":  AFTER,
        "before_asset_id":  "before",
        "after_asset_id":   "after",
    }

    print("Sending request to hosted ChangeFormer... (may take 30-60s on cold start)")
    t0 = time.time()
    try:
        result = await client.infer(payload)
    except Exception as exc:
        print(f"FAILED: {exc}")
        return

    elapsed = time.time() - t0
    print(f"Response received in {elapsed:.2f}s\n")

    # --- Print raw stats ---
    changed_px = result.get("changed_pixels", 0)
    total_px   = result.get("total_pixels", 0)
    mask_uri   = result.get("change_mask_uri", "")

    print("=" * 50)
    print("  CHANGEFORMER RESULTS")
    print("=" * 50)
    print(f"  Changed pixels : {changed_px:,}")
    print(f"  Total pixels   : {total_px:,}")

    if total_px > 0:
        pct = (changed_px / total_px) * 100
        print(f"  Change area    : {pct:.2f}%")

        # Qualitative accuracy judgement
        print()
        print("  ACCURACY JUDGEMENT:")
        if pct < 1.0:
            print("  Very low change detected (<1%) — model may be under-sensitive,")
            print("  OR images are nearly identical (good if that is expected).")
        elif 1.0 <= pct <= 30.0:
            print(f"  Reasonable change detected ({pct:.1f}%) — looks like real-world")
            print("  bitemporal change detection output. Result is plausible.")
        elif 30.0 < pct <= 70.0:
            print(f"  High change detected ({pct:.1f}%) — check if images are")
            print("  well-aligned. May indicate misregistration noise.")
        else:
            print(f"  Very high change detected ({pct:.1f}%) — likely misaligned images")
            print("  or the model is using a fallback/random head (not fine-tuned).")
    else:
        print("  Total pixels = 0 — server may have returned empty stats.")

    print("=" * 50)

    # --- Save and show the mask ---
    if mask_uri and os.path.exists(mask_uri):
        out_path = "scratch/changeformer_mask.png"
        os.makedirs("scratch", exist_ok=True)

        # Open, apply colormap, save
        mask_img = Image.open(mask_uri).convert("L")
        w, h = mask_img.size
        print(f"\n  Mask size      : {w} x {h} pixels")
        print(f"  Mask saved to  : {os.path.abspath(out_path)}")

        # Save raw mask
        mask_img.save(out_path)

        # Also generate a side-by-side comparison
        before_img = Image.open(BEFORE).convert("RGB").resize((256, 256))
        after_img  = Image.open(AFTER).convert("RGB").resize((256, 256))
        mask_resized = mask_img.resize((256, 256)).convert("RGB")

        comparison = Image.new("RGB", (768, 256))
        comparison.paste(before_img,  (0,   0))
        comparison.paste(after_img,   (256, 0))
        comparison.paste(mask_resized,(512, 0))
        comparison_path = "scratch/changeformer_comparison.png"
        comparison.save(comparison_path)
        print(f"  Comparison     : {os.path.abspath(comparison_path)}")
        print("  (Left=Before | Middle=After | Right=ChangeMask)")
    else:
        print("\n  No change mask returned by the server.")

    print()
    print("Full result dict:")
    # Avoid printing mask_uri path (it is a tempfile)
    display = {k: v for k, v in result.items() if k != "change_mask_uri"}
    display["change_mask_uri"] = mask_uri if mask_uri else "<none>"
    print(json.dumps(display, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
