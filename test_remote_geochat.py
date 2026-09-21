import os
import sys
import time
import requests
from dotenv import load_dotenv

# Load credentials from your local .env file
load_dotenv()

endpoint = os.getenv("GEOCHAT_ENDPOINT")
api_key = os.getenv("GEOCHAT_API_KEY")

if not endpoint or "litng.ai" not in endpoint:
    print("❌ ERROR: GEOCHAT_ENDPOINT in .env does not look like a deployed Lightning URL.")
    print("Example: GEOCHAT_ENDPOINT=https://8000-dep-xyz.cloudspaces.litng.ai/predict")
    sys.exit(1)

# We use a highly reliable image URL hosted on GitHub so it won't be blocked by firewalls like Wikipedia was
img_url = "https://raw.githubusercontent.com/pytorch/hub/master/images/dog.jpg"

print(f"🔗 Connecting to deployed GeoChat endpoint at: {endpoint}")
print("⏳ Waiting for inference (this may take ~30 seconds)...")

t0 = time.time()
try:
    response = requests.post(
        endpoint,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "image_uri": img_url,
            "prompt": "What is visible in this image?"
        },
        timeout=60
    )
    
    if response.status_code == 200:
        print(f"\n✅ SUCCESS! ({time.time()-t0:.2f}s)")
        print("Remote GeoChat says:\n\n" + response.json().get("text", ""))
        print("\n🚀 Your deployment is 100% ready for SatQuery Brain!")
    else:
        print(f"\n❌ FAILED with status {response.status_code}")
        print(response.text)
        print("\nIf you got 401 Unauthorized, make sure your deployment is set to PUBLIC in Lightning Studio!")
        print("If you got 404, make sure the URL ends with /predict")
except Exception as e:
    print(f"\n❌ CONNECTION ERROR: {e}")
    print("Ensure your deployment is running and the URL is completely correct.")
