import json
from pathlib import Path
from contracts.models import SetRecord
from analytics.report import ReportGenerator
from analytics.evaluation import AccuracyStudyHarness, RepGroundTruth
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_accuracy_study_benchmark():
    sample_path = Path("data/samples/squat_sample.json")
    with open(sample_path, "r") as f:
        data = json.load(f)

    set_rec = SetRecord(**data)
    report = ReportGenerator.generate_set_report(set_rec)

    # Reference values: Rep 1 calculated is ~0.562 m/s, Rep 2 is ~0.477 m/s
    ground_truth = [
        RepGroundTruth(rep_idx=1, true_mcv_mps=0.550, true_depth_achieved=True),
        RepGroundTruth(rep_idx=2, true_mcv_mps=0.480, true_depth_achieved=True),
    ]

    benchmark = AccuracyStudyHarness.evaluate_set(report, ground_truth)

    assert benchmark.total_reps_evaluated == 2
    assert benchmark.depth_agreement_pct == 100.0
    assert benchmark.mcv_mape_pct < 5.0  # High fidelity agreement
    assert benchmark.passed_validation is True

def test_upload_json_file_endpoint():
    sample_path = Path("data/samples/squat_sample.json")
    with open(sample_path, "rb") as f:
        response = client.post(
            "/sets/upload",
            files={"file": ("squat_sample.json", f, "application/json")}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["set_id"] == "mock-squat-001"
    assert data["total_reps"] == 2