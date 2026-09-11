# tests/test_agent_mock_brain.py
import pytest

@pytest.mark.asyncio
@pytest.mark.requires_gee
async def test_agent_decision_flow(
    mock_brain,
    gee_connector,
    test_aoi_medium
):
    """
    Test agent loop using MOCK brain (deterministic)
    with REAL GEE for data retrieval
    """
    
    agent_state = {
        "aoi": test_aoi_medium,
        "observations": []
    }
    
    # Step 1: Mock brain decides to retrieve satellite imagery
    decision = await mock_brain.send_state_and_get_decision(agent_state)
    assert decision["capability"] == "retrieve_satellite_imagery"
    
    # Step 2: Call REAL GEE with decision parameters
    sentinel2_scenes = await gee_connector.query_sentinel2(
        aoi_geojson=agent_state["aoi"],
        date_start=decision["arguments"]["date_start"],
        date_end=decision["arguments"]["date_end"],
        cloud_cover_max=decision["arguments"]["cloud_cover_max"]
    )
    
    assert len(sentinel2_scenes) > 0
    assert sentinel2_scenes[0]["source"] == "Sentinel-2"
    
    # Add observation
    agent_state["observations"].append({"type": "satellite_imagery", "data": sentinel2_scenes})
    
    # Step 3: Mock brain decides next action
    decision = await mock_brain.send_state_and_get_decision(agent_state)
    assert decision["capability"] == "generate_terrain_2d"
