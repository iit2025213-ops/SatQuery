import asyncio
import os
import time
from dotenv import load_dotenv

from app.models.changeformer.client import ChangeFormerClient
from app.config import get_settings

load_dotenv()

async def test_changeformer():
    settings = get_settings()
    client = ChangeFormerClient(
        endpoint=settings.changeformer_endpoint,
        api_key=settings.changeformer_api_key,
        timeout_seconds=1200  # Handle cold start
    )
    
    print(f"🚀 Triggering ChangeFormer at {client.endpoint}")
    print("⏳ This will wake up the deployment if it's asleep. Waiting up to 20 minutes...")
    
    t0 = time.time()
    
    payload = {
        # Using two arbitrary public images just to test the server inference pipeline
        "before_asset_uri": "https://raw.githubusercontent.com/pytorch/hub/master/images/dog.jpg",
        "after_asset_uri": "https://raw.githubusercontent.com/pytorch/hub/master/images/dog.jpg",
        "before_asset_id": "img1",
        "after_asset_id": "img2"
    }
    
    try:
        result = await client.infer(payload)
        print(f"\n✅ SUCCESS! (Total time: {(time.time()-t0)/60:.1f} minutes)")
        print(f"Result: {result}")
    except Exception as e:
        print(f"\n❌ Loop failed after {(time.time()-t0)/60:.1f} minutes: {e}")

if __name__ == "__main__":
    asyncio.run(test_changeformer())
