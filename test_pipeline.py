import asyncio
import os
import urllib.request
import json
from app.config import get_settings
from app.agent.controller import AgentController
from app.executor.executor import DefaultExecutor
from app.registry.registry import build_default_registry
from app.llm.openai import OpenAIProvider

async def test_prithvi():
    settings = get_settings()
    print(f"--- Testing Prithvi Integration ---")
    url = f"{settings.prithvi_endpoint}/v1/analyze"
    print(f"Pinging Prithvi at {url}")
    # We will just test if we get a 400 or 401 instead of a timeout, which means it's reachable.
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {settings.prithvi_api_key}'
    }
    req = urllib.request.Request(url, data=json.dumps({"asset_uri": "mock.tif", "task": "land_cover"}).encode(), headers=headers)
    try:
        urllib.request.urlopen(req, timeout=10)
        print("Prithvi: SUCCESS (or reachable)")
    except urllib.error.HTTPError as e:
        print(f"Prithvi reachable. HTTP Error: {e.code} (Expected since mock.tif doesn't exist)")
    except Exception as e:
        print(f"Prithvi error: {e}")

async def test_terramind_pipeline():
    print("\n--- Testing TerraMind Complete Pipeline ---")
    
    registry = build_default_registry()
    executor = DefaultExecutor(registry)
    llm = OpenAIProvider(api_key=get_settings().openai_api_key, model=get_settings().openai_model, base_url=get_settings().openai_base_url)
    
    ctrl = AgentController(
        llm=llm,
        executor=executor,
        registry=registry,
        settings=get_settings()
    )
    
    asset_uri = "../../examples/S2L2A/38D_378R_2_3.tif"
    prompt = "I have a Sentinel-2 image. Segment this image using the multimodal model into 3 classes and tell me if it succeeded."
    input_assets = [{"asset_id": "img1", "uri": asset_uri, "modality": "S2L2A", "format": "geotiff"}]
    
    # Mock the validation so it doesn't fail on local file not found
    from app.models.base import BaseModelAdapter
    from app.registry.capabilities import BUILTIN_CAPABILITIES
    class MockValidation(BaseModelAdapter):
        def validate_input(self, args): return True, ""
        async def predict(self, args): return {"valid": True, "modality": "S2L2A"}
        def normalize_output(self, raw, args):
            from app.evidence.schema import Observation, EvidenceSource, EvidenceType, ObservationStatus
            return Observation(source=EvidenceSource(capability="validate_remote_sensing_input", model="mock", backend="local"), type=EvidenceType.VALIDATION, status=ObservationStatus.SUCCESS, result=raw)
    
    registry.register(BUILTIN_CAPABILITIES["validate_remote_sensing_input"], lambda: MockValidation())

    print(f"Sending prompt to SatQuery: '{prompt}'")
    result = await ctrl.run(prompt, input_assets=input_assets)
    
    print("\n[PIPELINE RESULT]")
    print(f"Status: {result.get('status', 'unknown')}")
    print(f"Step count: {result.get('step_count', 0)}")
    print(f"Final Answer: {result.get('final_answer', 'None (Agent did not reach FINAL action)')}")
    
    print("\n[EVIDENCE GENERATED]")
    import pprint
    for e in result.get('evidence', []):
        print(f"- Capability: {e.get('capability', 'N/A')} | Status: {e.get('status', 'N/A')}")
        if e.get('status') == 'failure':
            pprint.pprint(e, indent=2)

async def main():
    await test_prithvi()
    await test_terramind_pipeline()

if __name__ == "__main__":
    asyncio.run(main())
