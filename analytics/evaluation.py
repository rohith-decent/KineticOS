from typing import List, Dict, Any, Optional
import numpy as np
from pydantic import BaseModel
from contracts.models import SetReport

class RepGroundTruth(BaseModel):
    rep_idx: int
    true_mcv_mps: float
    true_depth_achieved: bool
    true_bar_tilt_deg: Optional[float] = None

class AccuracyBenchmarkResult(BaseModel):
    total_reps_evaluated: int
    mcv_mape_pct: float             # Mean Absolute Percentage Error
    mcv_mae_mps: float              # Mean Absolute Error
    depth_agreement_pct: float      # Accuracy of depth call (0 - 100%)
    mean_tilt_error_deg: Optional[float] = None
    passed_validation: bool

class AccuracyStudyHarness:
    MCV_ERROR_TOLERANCE_PCT = 10.0   # Target: MCV error < 10% vs reference
    DEPTH_AGREEMENT_TARGET_PCT = 90.0 # Target: >= 90% depth agreement

    @classmethod
    def evaluate_set(
        cls, set_report: SetReport, ground_truth: List[RepGroundTruth]
    ) -> AccuracyBenchmarkResult:
        gt_dict = {gt.rep_idx: gt for gt in ground_truth}
        
        mcv_errors_pct = []
        mcv_abs_diffs = []
        depth_agreements = []
        tilt_errors = []

        for rep in set_report.reps:
            if rep.rep_idx not in gt_dict:
                continue

            gt = gt_dict[rep.rep_idx]

            # 1. MCV Accuracy
            if gt.true_mcv_mps > 0:
                abs_diff = abs(rep.mcv_mps - gt.true_mcv_mps)
                mcv_abs_diffs.append(abs_diff)
                err_pct = (abs_diff / gt.true_mcv_mps) * 100.0
                mcv_errors_pct.append(err_pct)

            # 2. Depth Agreement
            if rep.depth_achieved is not None:
                match = 1.0 if rep.depth_achieved == gt.true_depth_achieved else 0.0
                depth_agreements.append(match)

        # 3. Bar Tilt Accuracy (if front view and symmetry available)
        if set_report.symmetry:
            sym_dict = {r.rep_idx: r for r in set_report.symmetry.reps}
            for rep_idx, gt in gt_dict.items():
                if gt.true_bar_tilt_deg is not None and rep_idx in sym_dict:
                    measured_tilt = sym_dict[rep_idx].mean_bar_tilt_deg
                    tilt_errors.append(abs(measured_tilt - gt.true_bar_tilt_deg))

        total_reps = len(mcv_errors_pct)
        if total_reps == 0:
            return AccuracyBenchmarkResult(
                total_reps_evaluated=0,
                mcv_mape_pct=0.0,
                mcv_mae_mps=0.0,
                depth_agreement_pct=0.0,
                mean_tilt_error_deg=None,
                passed_validation=False
            )

        mape = float(np.mean(mcv_errors_pct))
        mae = float(np.mean(mcv_abs_diffs))
        depth_pct = float(np.mean(depth_agreements)) * 100.0
        mean_tilt_err = float(np.mean(tilt_errors)) if tilt_errors else None

        passed = bool(
            mape <= cls.MCV_ERROR_TOLERANCE_PCT and 
            depth_pct >= cls.DEPTH_AGREEMENT_TARGET_PCT
        )

        return AccuracyBenchmarkResult(
            total_reps_evaluated=total_reps,
            mcv_mape_pct=round(mape, 2),
            mcv_mae_mps=round(mae, 3),
            depth_agreement_pct=round(depth_pct, 1),
            mean_tilt_error_deg=round(mean_tilt_err, 2) if mean_tilt_err is not None else None,
            passed_validation=passed
        )