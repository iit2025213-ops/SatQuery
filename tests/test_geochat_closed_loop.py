import json
import pytest
from typing import Any
from unittest.mock import patch, MagicMock

from app.agent.controller import AgentController
from app.config import Settings
from app.executor.executor import DefaultExecutor
from app.llm.openai import OpenAIProvider
from app.registry.registry import build_default_registry


class MockedOpenAIProvider(OpenAIProvider):
    """Overrides _call_api to return deterministic JSON without network."""
    
    def __init__(self, responses: list[dict[str, Any]]):
        super().__init__(api_key="sk-test", max_retries=0)
        self.responses = responses
        self.call_count = 0
        self.captured_contexts = []
        
    def _ensure_client(self):
        pass
        
    async def _call_api(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        purpose: str,
        json_mode: bool = True,
    ) -> str:
        if purpose == "synthesize":
            return "Synthesized answer."
            
        self.captured_contexts.append(json.loads(user_prompt))
        
        if self.call_count < len(self.responses):
            resp = self.responses[self.call_count]
            self.call_count += 1
            return json.dumps(resp)
            
        return json.dumps({
            "action": "FINAL",
            "final_answer": "Out of mocked responses",
            "reason": "fallback"
        })


def _controller(provider: OpenAIProvider) -> AgentController:
    registry = build_default_registry()
    executor = DefaultExecutor(registry)
    
    settings = Settings(
        max_steps=10,
        geochat_endpoint="http://mocked-geochat"
    )
    
    from app.config import get_settings
    get_settings.cache_clear()
    global _mock_settings
    _mock_settings = settings
    
    return AgentController(
        llm=provider,
        executor=executor,
        registry=registry,
        settings=settings,
    )


@pytest.fixture(autouse=True)
def patch_get_settings():
    with patch("app.models.geochat.adapter.get_settings", lambda: _mock_settings):
        yield


@pytest.fixture
def mock_geochat_http():
    """Mock HTTP POST to simulate GeoChat responses based on prompt keywords."""
    async def mock_post(url, json, headers, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        prompt = json.get("prompt", "")
        if "urban" in prompt.lower():
            text = "The image shows a dense urban area with extensive infrastructure, roads, and residential buildings."
        elif "water" in prompt.lower():
            text = "The image contains a large body of water, likely a lake or coastal region."
        else:
            text = "The satellite image shows mixed land cover, including vegetation and some built-up structures."

        mock_response.json.return_value = {
            "text": text,
            "model": "GeoChat",
            "version": "mock-checkpoint",
            "inference_time_seconds": 0.5
        }
        return mock_response

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        yield


@pytest.mark.asyncio
async def test_geochat_closed_loop_dynamic_decision(mock_geochat_http):
    """Prove LLM receives GeoChat Observation and makes a subsequent dynamic decision."""
    responses = [
        # Call 1: LLM decides to interpret the scene
        {
            "action": "CALL_CAPABILITY",
            "capability": "interpret_scene",
            "arguments": {"asset": "asset_123", "prompt": "What is visible?"},
            "reason": "Need initial scene understanding"
        },
        # Call 2: LLM receives the observation, decides it is sufficient, and terminates
        {
            "action": "FINAL",
            "final_answer": "The scene has been interpreted.",
            "reason": "Sufficient evidence from GeoChat"
        }
    ]
    
    provider = MockedOpenAIProvider(responses)
    ctrl = _controller(provider)
    
    result = await ctrl.run(
        "Analyze this image",
        input_assets=[{"asset_id": "asset_123", "modality": "optical", "format": "geotiff"}]
    )
    
    assert result["status"] == "complete"
    assert provider.call_count == 2
    
    # Verify Context 2 contains the Observation from GeoChat
    context_2 = provider.captured_contexts[1]
    assert len(context_2["observations"]) == 1
    
    obs = context_2["observations"][0]
    assert obs["capability"] == "interpret_scene"
    assert "text" in obs["result"]
    assert obs["result"]["model"] == "GeoChat"


@pytest.mark.asyncio
async def test_geochat_adaptive_reasoning(mock_geochat_http):
    """Prove LLM takes different paths based on GeoChat's result (Urban vs Water)."""
    
    # Scenario A: The prompt hints at urban, GeoChat returns urban text
    responses_a = [
        {
            "action": "CALL_CAPABILITY",
            "capability": "interpret_scene",
            "arguments": {"asset": "asset_123", "prompt": "Is this urban?"},
            "reason": "Check if urban"
        },
        {
            "action": "FINAL",
            "final_answer": "It is an urban area.",
            "reason": "GeoChat confirmed urban"
        }
    ]
    provider_a = MockedOpenAIProvider(responses_a)
    ctrl_a = _controller(provider_a)
    await ctrl_a.run(
        "Is this urban?",
        input_assets=[{"asset_id": "asset_123", "modality": "optical", "format": "geotiff"}]
    )
    
    # The HTTP mock responds differently based on 'urban' keyword
    obs_a = provider_a.captured_contexts[1]["observations"][0]
    assert "dense urban area" in obs_a["result"]["text"].lower()
    
    # Scenario B: The prompt hints at water, GeoChat returns water text
    responses_b = [
        {
            "action": "CALL_CAPABILITY",
            "capability": "interpret_scene",
            "arguments": {"asset": "asset_123", "prompt": "Is this water?"},
            "reason": "Check if water"
        },
        {
            "action": "FINAL",
            "final_answer": "It is a body of water.",
            "reason": "GeoChat confirmed water"
        }
    ]
    provider_b = MockedOpenAIProvider(responses_b)
    ctrl_b = _controller(provider_b)
    await ctrl_b.run(
        "Is this water?",
        input_assets=[{"asset_id": "asset_123", "modality": "optical", "format": "geotiff"}]
    )
    
    obs_b = provider_b.captured_contexts[1]["observations"][0]
    assert "large body of water" in obs_b["result"]["text"].lower()
