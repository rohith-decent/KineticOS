from contracts.models import IsometricSample, ChronometerState
from analytics.chronometer import TrueTimeChronometer
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_chronometer_hysteresis_and_pause():
    chrono = TrueTimeChronometer()
    
    # 0.0s to 1.0s: Clean plank (error = 3.0 deg)
    for i in range(11):
        t = i * 0.1
        state = chrono.process_sample(IsometricSample(t=t, angle_error_deg=3.0))
        assert state == ChronometerState.ACTIVE

    # 1.1s: Error spikes to 9 deg (< 150 ms, must enter AMBER, not PAUSED)
    state = chrono.process_sample(IsometricSample(t=1.1, angle_error_deg=9.0))
    assert state == ChronometerState.AMBER
    assert chrono.pause_count == 0

    # 1.3s: Sustained 9 deg for 200 ms (> 150 ms threshold -> must transition to PAUSED)
    state = chrono.process_sample(IsometricSample(t=1.3, angle_error_deg=9.0))
    assert state == ChronometerState.PAUSED
    assert chrono.pause_count == 1

def test_isometric_api_endpoint():
    samples = [
        {"t": 0.0, "angle_error_deg": 2.0, "valid": True},
        {"t": 1.0, "angle_error_deg": 2.5, "valid": True},
        {"t": 2.0, "angle_error_deg": 9.5, "valid": True},
        {"t": 2.2, "angle_error_deg": 9.5, "valid": True},
        {"t": 3.0, "angle_error_deg": 2.0, "valid": True},
        {"t": 3.4, "angle_error_deg": 2.0, "valid": True},
    ]
    response = client.post("/isometric/process", json=samples)
    assert response.status_code == 200
    data = response.json()
    assert "true_tut_s" in data
    assert "pause_count" in data
    assert data["pause_count"] >= 1