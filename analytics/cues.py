from typing import List
from contracts.models import SetReport

class CueEngine:
    @staticmethod
    def generate_cues(report: SetReport) -> List[str]:
        cues: List[str] = []

        # 1. Depth check
        missed_depth = [r.rep_idx for r in report.reps if r.depth_achieved is False]
        if missed_depth:
            cues.append(f"Depth high on rep(s) {', '.join(map(str, missed_depth))}. Reach hip crease below knee.")

        # 2. Bar drift check
        high_drift = [r.rep_idx for r in report.reps if r.bar_drift_mm > 60.0]
        if high_drift:
            cues.append(f"Excessive bar drift on rep(s) {', '.join(map(str, high_drift))}. Keep bar balanced over midfoot.")

        # 3. Trunk lean
        chest_collapse = [r.rep_idx for r in report.reps if (r.max_trunk_angle_deg or 0) > 45.0]
        if chest_collapse:
            cues.append(f"Chest falling forward on rep(s) {', '.join(map(str, chest_collapse))}. Drive upper back into the bar.")

        # 4. Bilateral symmetry cues
        if report.symmetry:
            if report.symmetry.overall_mean_tilt_deg > 2.0:
                cues.append(
                    f"Barbell tilt elevated (avg {report.symmetry.overall_mean_tilt_deg}°). Keep collar heights level."
                )
            if report.symmetry.dominant_side != "balanced":
                cues.append(
                    f"Bilateral drive bias towards {report.symmetry.dominant_side} side. Focus on uniform leg drive."
                )

        # 5. Velocity loss / fatigue management
        if report.overall_velocity_loss_pct >= 30.0:
            cues.append("High neuromuscular fatigue (>30% velocity loss). Consider ending the set or extending rest.")
        elif report.overall_velocity_loss_pct >= 20.0:
            cues.append("Moderate velocity loss (~20%). Prime hypertrophy/strength stimulus threshold reached.")

        if not cues:
            cues.append("Solid set mechanics: Bar path and rep velocities remained stable.")

        return cues