import json
from pathlib import Path
from contracts.models import SetRecord
from analytics.symmetry import SymmetryEngine
from analytics.report import ReportGenerator

def test_symmetry_calculation():
    sample_path = Path("data/samples/squat_front_sample.json")
    with open(sample_path, "r") as f:
        data = json.load(f)

    set_rec = SetRecord(**data)
    sym_report = SymmetryEngine.analyze_set_symmetry(set_rec)

    assert sym_report is not None
    assert sym_report.overall_mean_tilt_deg > 0.0
    assert len(sym_report.reps) == 2
    assert "bottom_zone_tilt_deg" in sym_report.reps[0].phase_asymmetry_heatmap

def test_report_generator_with_symmetry():
    sample_path = Path("data/samples/squat_front_sample.json")
    with open(sample_path, "r") as f:
        data = json.load(f)

    set_rec = SetRecord(**data)
    report = ReportGenerator.generate_set_report(set_rec)

    assert report.symmetry is not None
    assert report.symmetry.overall_mean_tilt_deg > 0.0
    assert len(report.micro_cues) > 0