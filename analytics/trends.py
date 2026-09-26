from typing import List, Dict, Any, Optional
import numpy as np
from pydantic import BaseModel
from contracts.models import SetReport

class LongitudinalTrends(BaseModel):
    exercise: str
    total_sets_analyzed: int
    total_reps_completed: int
    total_tonnage_kg: float
    avg_velocity_loss_pct: float
    estimated_1rm_kg: Optional[float] = None
    load_velocity_slope: Optional[float] = None
    fatigue_flag: str  # "fresh", "optimal", "accumulated_fatigue"

class TrendsEngine:
    MVT_SQUAT_MPS = 0.30  # Minimum velocity threshold at 1RM for squats

    @classmethod
    def analyze_exercise_history(
        cls, exercise: str, set_reports: List[SetReport]
    ) -> LongitudinalTrends:
        if not set_reports:
            return LongitudinalTrends(
                exercise=exercise,
                total_sets_analyzed=0,
                total_reps_completed=0,
                total_tonnage_kg=0.0,
                avg_velocity_loss_pct=0.0,
                estimated_1rm_kg=None,
                load_velocity_slope=None,
                fatigue_flag="fresh"
            )

        total_reps = sum(s.total_reps for s in set_reports)
        total_tonnage = sum(s.load_kg * s.total_reps for s in set_reports)
        avg_v_loss = float(np.mean([s.overall_velocity_loss_pct for s in set_reports]))

        # Extract points for Load-Velocity Profile: (Load, Rep 1 MCV)
        loads = []
        rep1_velocities = []

        for s in set_reports:
            if s.reps and s.reps[0].mcv_mps > 0:
                loads.append(s.load_kg)
                rep1_velocities.append(s.reps[0].mcv_mps)

        estimated_1rm = None
        slope = None

        # Need at least 2 distinct loads to compute a linear regression
        if len(set(loads)) >= 2:
            x = np.array(loads, dtype=float)
            y = np.array(rep1_velocities, dtype=float)
            # y = a * x + b
            a, b = np.polyfit(x, y, 1)
            slope = round(float(a), 4)

            # Barbell velocity decreases as load increases (a < 0)
            if a < 0:
                calc_1rm = (cls.MVT_SQUAT_MPS - b) / a
                if calc_1rm > 0:
                    estimated_1rm = round(float(calc_1rm), 1)

        # Fatigue Fingerprint categorization
        if avg_v_loss >= 28.0:
            fatigue_flag = "accumulated_fatigue"
        elif avg_v_loss >= 15.0:
            fatigue_flag = "optimal"
        else:
            fatigue_flag = "fresh"

        return LongitudinalTrends(
            exercise=exercise,
            total_sets_analyzed=len(set_reports),
            total_reps_completed=total_reps,
            total_tonnage_kg=round(total_tonnage, 1),
            avg_velocity_loss_pct=round(avg_v_loss, 1),
            estimated_1rm_kg=estimated_1rm,
            load_velocity_slope=slope,
            fatigue_flag=fatigue_flag
        )