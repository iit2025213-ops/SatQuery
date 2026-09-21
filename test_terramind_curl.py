import urllib.request
import json
from app.config import get_settings

settings = get_settings()
url = f"{settings.terramind_endpoint}/v1/analyze"
print(f"Pinging TerraMind at {url}")

headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {settings.terramind_api_key}'
}

payload = {
    "assets": [
        {
            "uri": "https://raw.githubusercontent.com/rasterio/rasterio/master/tests/data/byte.tif",
            "modality": "optical"
        }
    ],
    "task": "segmentation"
}

req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
try:
    with urllib.request.urlopen(req, timeout=30) as response:
        print("Success:", response.read().decode())
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code}")
    print(f"Response: {e.read().decode()}")
except Exception as e:
    print(f"Error: {e}")
