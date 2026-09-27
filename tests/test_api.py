import json
from pathlib import Path
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_process_set_endpoint():
    sample_path = Path("data/samples/squat_sample.json")
    with open(sample_path, "r") as f:
        payload = json.load(f)

    response = client.post("/sets/process", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["set_id"] == "mock-squat-001"
    assert data["total_reps"] == 2
    assert "estimated_rpe" in data
    assert isinstance(data["estimated_rpe"], float)
    assert len(data["micro_cues"]) > 0
    assert "disclaimer" in data