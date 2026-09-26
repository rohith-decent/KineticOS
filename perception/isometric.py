"""A6 - Isometric alignment detector, for planks/holds.

Unlike squats/deadlifts (A4's state machine), an isometric hold has no
up/down rep cycle to detect -- the entire point is to STAY in one position.
So instead of detecting reps, this measures how far the body deviates from a
straight ankle-hip-shoulder line, every single frame, in degrees of error
from 180 degrees (a perfectly straight plank line).

This module's job stops at producing an honest per-frame angle-error number.
It feeds contracts.models.IsometricSample -> Role B's True-Time chronometer
(B4), which owns the actual 8-degree threshold and the pause/resume/hysteresis
logic for the on-screen timer (see docs/03_ARCHITECTURE_AND_CONTRACTS.md,
Contract 4). Keeping that logic in B4 means the threshold can be tuned without
touching this file, and B4 can combine it with other signals later.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from perception.pose import L_SHOULDER, R_SHOULDER, L_HIP, R_HIP, L_ANKLE, R_ANKLE, joint_angle


def alignment_error_deg(keypoints: np.ndarray, min_conf: float = 0.3) -> Optional[float]:
    """Degrees of deviation from a straight ankle-hip-shoulder line
    (0 = perfect plank; larger = hips sagging or piking up). Returns None if
    neither side has confident-enough keypoints to trust.

    Uses whichever side (left/right) has the higher average confidence rather
    than averaging both -- in a side-view plank the far side is often
    partially hidden behind the near side, so averaging a good reading with a
    bad one is worse than just trusting the good one.
    """
    candidates = []
    for shoulder, hip, ankle in ((L_SHOULDER, L_HIP, L_ANKLE), (R_SHOULDER, R_HIP, R_ANKLE)):
        conf = (keypoints[shoulder, 2] + keypoints[hip, 2] + keypoints[ankle, 2]) / 3
        if conf >= min_conf:
            angle = joint_angle(keypoints[shoulder, :2], keypoints[hip, :2], keypoints[ankle, :2])
            candidates.append((conf, angle))
    if not candidates:
        return None
    candidates.sort(key=lambda c: c[0], reverse=True)
    best_angle = candidates[0][1]
    return abs(180.0 - best_angle)


class IsometricStream:
    """Stateful per-frame wrapper: feed frames in, get contract-shaped
    IsometricSample objects out, ready to hand to Role B's chronometer."""

    def __init__(self, min_conf: float = 0.3):
        self.min_conf = min_conf

    def step(self, t: float, keypoints: np.ndarray):
        from contracts.models import IsometricSample
        err = alignment_error_deg(keypoints, self.min_conf)
        if err is None:
            return IsometricSample(t=t, angle_error_deg=float("nan"), valid=False)
        return IsometricSample(t=t, angle_error_deg=err, valid=True)
