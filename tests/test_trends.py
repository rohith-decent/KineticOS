import json
from pathlib import Path
from fastapi.testclient import TestClient
from api.main import app
from contracts.models import SetRecord
from analytics.report import ReportGenerator

client = TestClient(app)
def test_trends_and_history_endpoints():
    sample_side = Path("data/samples/squat_sample.json")
    with open(sample_side, "r") as f:
        data_100kg = json.load(f)

    # Ingest first set at 100 kg
    resp1 = client.post("/sets/process", json=data_100kg)
    assert resp1.status_code == 200

    # Ingest second set at 120 kg with lower velocity to form a load-velocity profile
    data_120kg = json.loads(json.dumps(data_100kg))
    data_120kg["set_id"] = "mock-squat-002"
    data_120kg["load_kg"] = 120.0
    for frame in data_120kg["frames"]:
        # Increase duration slightly to simulate lower speed
        frame["t"] = frame["t"] * 1.3
    for rep in data_120kg["reps"]:
        rep["start_t"] *= 1.3
        rep["bottom_t"] *= 1.3
        rep["end_t"] *= 1.3

    resp2 = client.post("/sets/process", json=data_120kg)
    assert resp2.status_code == 200

    # Verify set list endpoint
    list_resp = client.get("/sets?exercise=back_squat")
    assert list_resp.status_code == 200
    sets = list_resp.json()
    assert len(sets) >= 2

    # Verify trends endpoint
    trends_resp = client.get("/analytics/trends/back_squat")
    assert trends_resp.status_code == 200
    trends = trends_resp.json()
    assert trends["exercise"] == "back_squat"
    assert trends["total_sets_analyzed"] >= 2
    assert trends["total_tonnage_kg"] > 0
    assert trends["estimated_1rm_kg"] is not None
    assert trends["estimated_1rm_kg"] > 100.0