import asyncio
import os
import time
from dotenv import load_dotenv

from app.api.routes import _build_controller
from app.config import get_settings

load_dotenv()

async def test_loop():
    settings = get_settings()
    controller = _build_controller(settings)
    
    request = "Please ground the dog in this image. Provide the bounding box coordinates for it."
    # We use a reliable remote image so the Lightning deployment can fetch it!
    input_assets = [{
        "asset_id": "test_image", 
        "uri": "https://raw.githubusercontent.com/pytorch/hub/master/images/dog.jpg", 
        "modality": "optical",
        "format": "jpeg"
    }]
    
    print("🚀 Triggering SatQuery Agent Controller (End-to-End Test)...")
    print("⏳ This will wake up your GeoChat deployment. Since the deployment is scaled down to 0, it will take ~12 to 15 minutes for Lightning AI to provision a GPU, boot up the model, and return the answer.")
    print(f"The connection will NOT drop because we increased the timeout to 20 minutes (1200s).")
    print("--------------------------------------------------")
    
    t0 = time.time()
    try:
        result = await controller.run(request=request, input_assets=input_assets, metadata={})
        print(f"\n✅ SUCCESS! (Total time: {(time.time()-t0)/60:.1f} minutes)")
        print(f"\n🤖 FINAL ANSWER FROM AGENT:")
        print(f"{result.get('answer')}")
        
        print(f"\nEvidence collected:")
        for ev in result.get('evidence', []):
            print(f"- {ev.get('capability')} via {ev.get('source', {}).get('model')} -> {ev.get('status')}")
            
    except Exception as e:
        print(f"\n❌ Loop failed after {(time.time()-t0)/60:.1f} minutes: {e}")

if __name__ == "__main__":
    asyncio.run(test_loop())
