import json
from pathlib import Path
from contracts.models import SetRecord, SetReport
from analytics.kinematics import KinematicsEngine

def test_analyze_set_kinematics():
    sample_path = Path("data/samples/squat_sample.json")
    with open(sample_path, "r") as f:
        data = json.load(f)

    set_rec = SetRecord(**data)
    report = KinematicsEngine.analyze_set(set_rec)

    assert isinstance(report, SetReport)
    assert report.set_id == "mock-squat-001"
    assert report.total_reps == 2
    assert len(report.reps) == 2
    assert report.reps[0].mcv_mps > 0.0
    assert report.reps[0].concentric_tut_s > 0.0
    assert report.reps[1].velocity_loss_pct >= 0.0