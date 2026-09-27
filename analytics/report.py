from contracts.models import SetRecord, SetReport
from analytics.kinematics import KinematicsEngine
from analytics.cues import CueEngine
from analytics.symmetry import SymmetryEngine

class ReportGenerator:
    @staticmethod
    def estimate_rpe(velocity_loss_pct: float, last_rep_mcv: float) -> float:
        if velocity_loss_pct >= 35.0 or last_rep_mcv <= 0.25:
            return 10.0
        elif velocity_loss_pct >= 28.0 or last_rep_mcv <= 0.32:
            return 9.5
        elif velocity_loss_pct >= 22.0:
            return 9.0
        elif velocity_loss_pct >= 16.0:
            return 8.5
        elif velocity_loss_pct >= 10.0:
            return 8.0
        elif velocity_loss_pct >= 5.0:
            return 7.5
        else:
            return 7.0

    @classmethod
    def generate_set_report(cls, set_record: SetRecord) -> SetReport:
        report = KinematicsEngine.analyze_set(set_record)

        # Evaluate symmetry if front/rear view or dual collars are tracked
        if set_record.camera_view in ("front", "rear"):
            report.symmetry = SymmetryEngine.analyze_set_symmetry(set_record)

        last_mcv = report.reps[-1].mcv_mps if report.reps else 0.0
        report.estimated_rpe = cls.estimate_rpe(report.overall_velocity_loss_pct, last_mcv)
        report.micro_cues = CueEngine.generate_cues(report)

        return report