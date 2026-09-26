from typing import List, Optional
import numpy as np
from contracts.models import SetRecord, RepInterval, RepSymmetryReport, SetSymmetryReport

class SymmetryEngine:
    @staticmethod
    def calculate_tilt_deg(bar_left: List[float], bar_right: List[float]) -> float:
        dx = bar_right[0] - bar_left[0]
        dy = bar_right[1] - bar_left[1]
        if dx == 0:
            return 0.0
        angle_rad = np.arctan2(dy, dx)
        return float(np.degrees(angle_rad))

    @classmethod
    def analyze_rep_symmetry(
        cls, set_record: SetRecord, rep: RepInterval
    ) -> Optional[RepSymmetryReport]:
        conc_frames = [
            f for f in set_record.frames
            if rep.bottom_t <= f.t <= rep.end_t and f.bar_left and f.bar_right
        ]
        if len(conc_frames) < 2:
            return None

        tilts: List[float] = []
        l_hip_v: List[float] = []
        r_hip_v: List[float] = []
        concentric_progress: List[float] = []

        y_start = (conc_frames[0].bar_left[1] + conc_frames[0].bar_right[1]) / 2.0
        y_end = (conc_frames[-1].bar_left[1] + conc_frames[-1].bar_right[1]) / 2.0
        total_rom = max(abs(y_start - y_end), 1.0)

        for i, f in enumerate(conc_frames):
            tilt = cls.calculate_tilt_deg(f.bar_left, f.bar_right)
            tilts.append(abs(tilt))

            cur_y = (f.bar_left[1] + f.bar_right[1]) / 2.0
            progress = min(100.0, max(0.0, abs(y_start - cur_y) / total_rom * 100.0))
            concentric_progress.append(progress)

            if i > 0:
                prev_f = conc_frames[i - 1]
                dt = max(f.t - prev_f.t, 1e-5)
                if len(f.keypoints) > 12 and len(prev_f.keypoints) > 12:
                    vl = (prev_f.keypoints[11].y - f.keypoints[11].y) / dt
                    vr = (prev_f.keypoints[12].y - f.keypoints[12].y) / dt
                    l_hip_v.append(vl)
                    r_hip_v.append(vr)

        mean_tilt = float(np.mean(tilts)) if tilts else 0.0
        max_tilt = float(np.max(tilts)) if tilts else 0.0

        mean_vl = float(np.mean(l_hip_v)) if l_hip_v else 0.0
        mean_vr = float(np.mean(r_hip_v)) if r_hip_v else 0.0
        avg_v = (abs(mean_vl) + abs(mean_vr)) / 2.0
        asymmetry_pct = round(((mean_vr - mean_vl) / avg_v * 100.0), 1) if avg_v > 1e-4 else 0.0

        max_tilt_idx = int(np.argmax(tilts))
        sticking_height = round(concentric_progress[max_tilt_idx], 1)
        sticking_tilt = round(tilts[max_tilt_idx], 1)

        bottom_tilts = [tilts[idx] for idx in range(len(tilts)) if concentric_progress[idx] <= 33.3]
        mid_tilts = [tilts[idx] for idx in range(len(tilts)) if 33.3 < concentric_progress[idx] <= 66.6]
        lockout_tilts = [tilts[idx] for idx in range(len(tilts)) if concentric_progress[idx] > 66.6]

        heatmap = {
            "bottom_zone_tilt_deg": round(float(np.mean(bottom_tilts)), 1) if bottom_tilts else 0.0,
            "mid_zone_tilt_deg": round(float(np.mean(mid_tilts)), 1) if mid_tilts else 0.0,
            "lockout_zone_tilt_deg": round(float(np.mean(lockout_tilts)), 1) if lockout_tilts else 0.0,
        }

        return RepSymmetryReport(
            rep_idx=rep.rep_idx,
            mean_bar_tilt_deg=round(mean_tilt, 1),
            max_bar_tilt_deg=round(max_tilt, 1),
            lr_drive_asymmetry_pct=asymmetry_pct,
            sticking_point_height_pct=sticking_height,
            sticking_point_tilt_deg=sticking_tilt,
            phase_asymmetry_heatmap=heatmap,
        )

    @classmethod
    def analyze_set_symmetry(cls, set_record: SetRecord) -> Optional[SetSymmetryReport]:
        rep_reports: List[RepSymmetryReport] = []
        for rep in set_record.reps:
            r_sym = cls.analyze_rep_symmetry(set_record, rep)
            if r_sym:
                rep_reports.append(r_sym)

        if not rep_reports:
            return None

        overall_tilt = float(np.mean([r.mean_bar_tilt_deg for r in rep_reports]))
        worst_rep = max(rep_reports, key=lambda r: r.max_bar_tilt_deg)
        mean_asym = float(np.mean([r.lr_drive_asymmetry_pct for r in rep_reports]))

        if mean_asym > 5.0:
            dominant = "right"
        elif mean_asym < -5.0:
            dominant = "left"
        else:
            dominant = "balanced"

        return SetSymmetryReport(
            overall_mean_tilt_deg=round(overall_tilt, 1),
            max_tilt_rep_idx=worst_rep.rep_idx,
            dominant_side=dominant,
            reps=rep_reports,
        )