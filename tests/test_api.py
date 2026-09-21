"""API integration tests."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_analyze_returns_job_id(client):
    r = client.post(
        "/api/v1/analyze",
        json={
            "query": "Analyze this satellite image.",
            "assets": [
                {
                    "asset_id": "asset_001",
                    "uri": "mock://images/001.tif",
                    "modality": "optical",
                    "format": "geotiff",
                }
            ],
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert "job_id" in data
    assert data["status"] == "accepted"


def test_job_not_found(client):
    r = client.get("/api/v1/jobs/nonexistent")
    assert r.status_code == 404


def test_analyze_and_poll(client):
    """Submit a job, wait briefly, then poll for completion."""
    import time

    r = client.post(
        "/api/v1/analyze",
        json={
            "query": "Describe this image.",
            "assets": [
                {
                    "asset_id": "asset_001",
                    "modality": "optical",
                    "format": "geotiff",
                }
            ],
        },
    )
    job_id = r.json()["job_id"]

    # Poll until complete (max 5 seconds)
    for _ in range(50):
        time.sleep(0.1)
        r = client.get(f"/api/v1/jobs/{job_id}")
        if r.json()["status"] in ("complete", "failed"):
            break

    data = r.json()
    assert data["status"] == "complete"
    assert data["result"] is not None
    assert data["result"]["answer"] != ""
    assert data["result"]["step_count"] > 0
    assert len(data["result"]["trace"]) > 0

    # Test the new endpoints on the completed job
    r = client.get(f"/api/v1/jobs/{job_id}/events")
    assert r.status_code == 200
    events = r.json()
    assert isinstance(events, list)
    assert len(events) > 0

    r = client.get(f"/api/v1/jobs/{job_id}/evidence")
    assert r.status_code == 200
    evidence = r.json()
    assert isinstance(evidence, list)

    r = client.get(f"/api/v1/jobs/{job_id}/report")
    assert r.status_code == 200
    report = r.json()
    assert "report_markdown" in report
    assert report["job_id"] == job_id

def test_get_artifact_not_found(client):
    r = client.get("/api/v1/artifacts/nonexistent_path.tif")
    assert r.status_code == 404
