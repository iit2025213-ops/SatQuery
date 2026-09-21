"""Shared test fixtures."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.llm.mock import MockLLM
from app.registry.registry import build_default_registry, CapabilityRegistry
from app.executor.executor import DefaultExecutor
from app.agent.controller import AgentController
from app.agent.state import AgentState, AssetReference


@pytest.fixture
def settings() -> Settings:
    return Settings(
        openai_api_key="",
        max_steps=20,
        max_replans=3,
        max_retries_per_task=2,
    )


@pytest.fixture
def registry() -> CapabilityRegistry:
    return build_default_registry()


@pytest.fixture
def mock_llm() -> MockLLM:
    return MockLLM()


@pytest.fixture
def default_executor(registry: CapabilityRegistry) -> DefaultExecutor:
    return DefaultExecutor(registry)


@pytest.fixture
def controller(
    mock_llm: MockLLM,
    default_executor: DefaultExecutor,
    registry: CapabilityRegistry,
    settings: Settings,
) -> AgentController:
    return AgentController(
        llm=mock_llm,
        executor=default_executor,
        registry=registry,
        settings=settings,
    )


@pytest.fixture
def sample_optical_assets() -> list[dict]:
    return [
        {
            "asset_id": "asset_001",
            "uri": "mock://images/optical_001.tif",
            "modality": "optical",
            "format": "geotiff",
            "metadata": {"crs": "EPSG:4326", "resolution_m": 10.0},
        }
    ]


@pytest.fixture
def sample_sar_assets() -> list[dict]:
    return [
        {
            "asset_id": "asset_sar_001",
            "uri": "mock://images/sar_001.tif",
            "modality": "sar",
            "format": "geotiff",
            "metadata": {"crs": "EPSG:32643", "resolution_m": 5.0},
        }
    ]


@pytest.fixture
def sample_temporal_assets() -> list[dict]:
    return [
        {
            "asset_id": "asset_001",
            "uri": "mock://images/before.tif",
            "modality": "optical",
            "format": "geotiff",
            "metadata": {"date": "2018-05-10"},
        },
        {
            "asset_id": "asset_002",
            "uri": "mock://images/after.tif",
            "modality": "optical",
            "format": "geotiff",
            "metadata": {"date": "2024-05-12"},
        },
    ]


@pytest.fixture
def empty_state() -> AgentState:
    return AgentState(request="test", current_goal="test")


@pytest.fixture
def optical_state(sample_optical_assets) -> AgentState:
    return AgentState(
        request="Analyze this satellite image.",
        current_goal="Analyze this satellite image.",
        input_assets=[AssetReference(**a) for a in sample_optical_assets],
    )
