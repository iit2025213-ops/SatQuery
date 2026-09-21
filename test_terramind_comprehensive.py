import asyncio
import os
import json
import time
from app.config import get_settings
from app.models.terramind.client import TerraMindClient
from app.models.terramind.adapter import TerraMindAdapter

async def run_test(name: str, file_path: str):
    print(f"\n{'='*50}\nTesting Image: {name} ({file_path})\n{'='*50}")
    
    # We will use the adapter directly to test all preprocessing/postprocessing logic
    adapter = TerraMindAdapter()
    
    # Test 1: 3-Class Segmentation
    print("\n--- Test 1: Segmentation (3 classes) ---")
    payload_3c = {
        "asset_uri": file_path,
        "task": "segmentation",
        "num_classes": 3,
        "clustering_method": "pca_kmeans",
        "_capability": "perform_multimodal_analysis"
    }
    
    t0 = time.time()
    res_3c = await adapter.predict(payload_3c)
    t1 = time.time()
    
    if "_error" in res_3c:
        print(f"FAILED: {res_3c['_error']}")
    else:
        print(f"SUCCESS in {t1-t0:.2f}s")
        # Save the returned base64 mask (which is already colorized by the adapter)
        if "mask_base64" in res_3c.get("result", {}):
            import base64
            with open(f"scratch/test_imagery/{name}_mask_3c.png", "wb") as f:
                f.write(base64.b64decode(res_3c["result"]["mask_base64"]))
            print(f"Saved mask to scratch/test_imagery/{name}_mask_3c.png")
            
    # Test 2: Segmentation (6 classes)
    print("\n--- Test 2: Segmentation (6 classes) ---")
    payload_6c = {
        "asset_uri": file_path,
        "task": "segmentation",
        "num_classes": 6,
        "clustering_method": "pca_kmeans",
        "_capability": "perform_multimodal_analysis"
    }
    
    t0 = time.time()
    res_6c = await adapter.predict(payload_6c)
    t1 = time.time()
    
    if "_error" in res_6c:
        print(f"FAILED: {res_6c['_error']}")
    else:
        print(f"SUCCESS in {t1-t0:.2f}s")
        if "mask_base64" in res_6c.get("result", {}):
            import base64
            with open(f"scratch/test_imagery/{name}_mask_6c.png", "wb") as f:
                f.write(base64.b64decode(res_6c["result"]["mask_base64"]))
            print(f"Saved mask to scratch/test_imagery/{name}_mask_6c.png")

    # Test 3: Feature Extraction (Zero-shot tokens)
    print("\n--- Test 3: Feature Extraction (Raw Embeddings) ---")
    payload_feat = {
        "asset_uri": file_path,
        "task": "features",
        "_capability": "perform_multimodal_analysis"
    }
    
    t0 = time.time()
    res_feat = await adapter.predict(payload_feat)
    t1 = time.time()
    
    if "_error" in res_feat:
        print(f"FAILED: {res_feat['_error']}")
    else:
        print(f"SUCCESS in {t1-t0:.2f}s")
        # Features should be returned as an array or dict shape
        feat_data = res_feat.get("result", {}).get("features", [])
        if feat_data:
            print(f"Successfully extracted embeddings! Shape/Length: {len(feat_data)}")
        else:
            print(f"No features array found. Result keys: {res_feat.get('result', {}).keys()}")

async def main():
    images = [
        ("test_image", "test_image.tif"),
    ]
    
    for name, path in images:
        await run_test(name, path)

if __name__ == "__main__":
    asyncio.run(main())
