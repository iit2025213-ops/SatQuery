import urllib.request
import json
import time
from app.config import get_settings

settings = get_settings()
url = f"{settings.prithvi_endpoint}/v1/analyze"
print(f"Pinging LIVE Prithvi GPU Endpoint at: {url}")

payload = {
    "asset_uri": "test_image.tif", 
    "task": "land_cover"
}

headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {settings.prithvi_api_key}'
}

req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)

try:
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=120) as response:
        result = json.loads(response.read().decode())
        t1 = time.time()
        print(f"\nSUCCESS from SatQuery Backend! Inference took {t1 - t0:.2f} seconds.")
        
        # Check for mask and save it
        if "mask_base64" in result and result["mask_base64"]:
            import base64
            from io import BytesIO
            from PIL import Image
            
            img_data = base64.b64decode(result["mask_base64"])
            img = Image.open(BytesIO(img_data))
            out_path = "scratch/received_mask.png"
            img.save(out_path)
            print(f"Successfully received and decoded base64 mask! Saved to {out_path}")
            
            # Remove base64 string from result before printing so we don't flood the terminal
            result["mask_base64"] = "<base64_string_omitted>"
        
        print(json.dumps(result, indent=2))
        
except urllib.error.HTTPError as e:
    print(f"\nHTTP Error: {e.code}")
    print(f"Response: {e.read().decode()}")
except Exception as e:
    print(f"\nError: {e}")
