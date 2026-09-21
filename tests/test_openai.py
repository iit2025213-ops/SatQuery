"""Tests for the Phase 2 OpenAI LLM provider."""

import json
import pytest

from app.agent.decision import ActionType
from app.llm.base import LLMProvider
from app.llm.openai import OpenAIProvider, OpenAIConfigError, OpenAIResponseError


def test_provider_interfaces():
    from app.llm.mock import MockLLM
    assert issubclass(MockLLM, LLMProvider)
    assert issubclass(OpenAIProvider, LLMProvider)


def test_missing_api_key_fails_gracefully():
    # Construction with empty key succeeds to not break imports
    provider = OpenAIProvider(api_key="", model="gpt-4.1-mini")
    
    # But invocation raises the config error, not a crash
    with pytest.raises(OpenAIConfigError, match="OpenAI API key is not configured"):
        provider._ensure_client()


def test_missing_model_fails_gracefully():
    # Construction with empty model succeeds
    provider = OpenAIProvider(api_key="sk-test", model="")
    
    # But invocation raises the config error
    with pytest.raises(OpenAIConfigError, match="OpenAI model is not configured"):
        provider._ensure_client()


def test_configuration_overrides():
    provider = OpenAIProvider(
        api_key="sk-test",
        model="gpt-3.5-turbo",
        base_url="http://localhost:8080",
        temperature=0.5,
        max_retries=5,
    )
    assert provider._api_key == "sk-test"
    assert provider._model == "gpt-3.5-turbo"
    assert provider._base_url == "http://localhost:8080"
    assert provider._temperature == 0.5
    assert provider._max_retries == 5


def test_normalize_response_action_casing():
    provider = OpenAIProvider(api_key="sk-test")
    data = {"action": "call_capability", "capability": "interpret_scene"}
    normalized = provider._normalize_response(data)
    assert normalized["action"] == "CALL_CAPABILITY"


def test_normalize_response_tool_alias():
    provider = OpenAIProvider(api_key="sk-test")
    data = {"action": "CALL_CAPABILITY", "tool_name": "interpret_scene"}
    normalized = provider._normalize_response(data)
    assert normalized["capability"] == "interpret_scene"


def test_normalize_response_reason_alias():
    provider = OpenAIProvider(api_key="sk-test")
    data = {"action": "FINAL", "answer": "Done", "rationale": "Finished"}
    normalized = provider._normalize_response(data)
    assert normalized["reason"] == "Finished"
    assert normalized["final_answer"] == "Done"


def test_parse_valid_decision():
    provider = OpenAIProvider(api_key="sk-test")
    raw = json.dumps({
        "action": "CALL_CAPABILITY",
        "capability": "interpret_scene",
        "arguments": {"asset": "asset_001"},
        "reason": "Need interpretation"
    })
    decision = provider._parse_decision(raw)
    assert decision.action == ActionType.CALL_CAPABILITY
    assert decision.capability == "interpret_scene"
    assert decision.arguments == {"asset": "asset_001"}
    assert decision.reason == "Need interpretation"


def test_parse_invalid_json():
    provider = OpenAIProvider(api_key="sk-test")
    with pytest.raises(OpenAIResponseError, match="Invalid JSON"):
        provider._parse_decision("This is not JSON")


def test_parse_invalid_schema():
    provider = OpenAIProvider(api_key="sk-test")
    raw = json.dumps({"action": "CALL_CAPABILITY"})  # missing capability
    with pytest.raises(OpenAIResponseError, match="validation failed"):
        provider._parse_decision(raw)
