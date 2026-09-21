import asyncio
import time
from dotenv import load_dotenv

from app.api.routes import _build_controller
from app.config import get_settings

load_dotenv()

async def run_exhaustive():
    settings = get_settings()
    controller = _build_controller(settings)
    
    # We ask the agent to do BOTH change detection and scene interpretation
    request = (
        "I have provided two images of the same area taken at different times. "
        "Please detect the bi-temporal changes between them. Also, provide a high-level "
        "scene interpretation of the before image."
    )
    
    # Using public images that can be downloaded by the client
    input_assets = [
        {
            "asset_id": "image_before", 
            "uri": "https://raw.githubusercontent.com/pytorch/hub/master/images/dog.jpg", 
            "modality": "optical",
            "format": "jpeg"
        },
        {
            "asset_id": "image_after", 
            "uri": "https://raw.githubusercontent.com/pytorch/hub/master/images/dog.jpg", 
            "modality": "optical",
            "format": "jpeg"
        }
    ]
    
    print("🚀 Triggering Exhaustive Closed-Loop Test...")
    print("This will test the Agent's ability to chain multiple specialist models (GeoChat and ChangeFormer).")
    print("Waiting for any cold starts...\n")
    
    t0 = time.time()
    try:
        result = await controller.run(request=request, input_assets=input_assets, metadata={})
        print(f"✅ EXHAUSTIVE TEST SUCCESS! (Total time: {(time.time()-t0)/60:.1f} minutes)\n")
        print("🤖 FINAL ANSWER:")
        print(result.get('answer', ''))
        
        print("\n🔍 EVIDENCE CHAIN:")
        for i, ev in enumerate(result.get('evidence', [])):
            capability = ev.get('capability', 'Unknown')
            model = ev.get('source', {}).get('model', 'Local')
            status = ev.get('status', 'Unknown')
            print(f"  {i+1}. {capability} [{model}] -> {status}")
            
    except Exception as e:
        print(f"\n❌ Loop failed after {(time.time()-t0)/60:.1f} minutes: {e}")

if __name__ == "__main__":
    asyncio.run(run_exhaustive())
