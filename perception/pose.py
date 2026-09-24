"""A2 - Pose estimation wrapper + smoothing + confidence gating.

Output for every frame: np.ndarray (17, 3) = [x_px, y_px, confidence] in COCO order.
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np

# COCO-17 indices
NOSE, L_EYE, R_EYE, L_EAR, R_EAR = 0, 1, 2, 3, 4
L_SHOULDER, R_SHOULDER, L_ELBOW, R_ELBOW, L_WRIST, R_WRIST = 5, 6, 7, 8, 9, 10
L_HIP, R_HIP, L_KNEE, R_KNEE, L_ANKLE, R_ANKLE = 11, 12, 13, 14, 15, 16

SKELETON = [(5, 6), (5, 7), (7, 9), (6, 8), (8, 10), (5, 11), (6, 12), (11, 12),
            (11, 13), (13, 15), (12, 14), (14, 16), (0, 1), (0, 2), (1, 3), (2, 4)]


def joint_angle(a, b, c) -> float:
    """Angle at point b (degrees) formed by a-b-c. Inputs are (x, y)."""
    a, b, c = (np.asarray(p, dtype=float)[:2] for p in (a, b, c))
    v1, v2 = a - b, c - b
    n = np.linalg.norm(v1) * np.linalg.norm(v2)
    if n == 0:
        return float("nan")
    return float(np.degrees(np.arccos(np.clip(np.dot(v1, v2) / n, -1.0, 1.0))))


class OneEuroFilter:
    """One-Euro filter (Casiez et al. 2012): low jitter when still, low lag when moving.
    Works on numpy arrays of any shape. Tune min_cutoff (jitter) and beta (lag)."""

    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.02, d_cutoff: float = 1.0):
        self.min_cutoff, self.beta, self.d_cutoff = min_cutoff, beta, d_cutoff
        self._x = None
        self._dx = None
        self._t = None

    @staticmethod
    def _alpha(cutoff: float, dt: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def reset(self) -> None:
        self._x = self._dx = self._t = None

    def __call__(self, x: np.ndarray, t: float) -> np.ndarray:
        x = np.asarray(x, dtype=float)
        if self._x is None:
            self._x, self._dx, self._t = x.copy(), np.zeros_like(x), t
            return x
        dt = t - self._t
        if dt <= 0:
            return self._x
        dx = (x - self._x) / dt
        a_d = self._alpha(self.d_cutoff, dt)
        dx_hat = a_d * dx + (1 - a_d) * self._dx
        cutoff = self.min_cutoff + self.beta * np.abs(dx_hat)
        tau = 1.0 / (2.0 * math.pi * cutoff)
        a = 1.0 / (1.0 + tau / dt)
        x_hat = a * x + (1 - a) * self._x
        self._x, self._dx, self._t = x_hat, dx_hat, t
        return x_hat


class PoseEstimator:
    """YOLO11-Pose wrapper. Picks the largest person (the lifter nearest the camera),
    smooths keypoints, and holds the last good position for low-confidence joints."""

    def __init__(self, weights: str = "yolo11n-pose.pt", conf_thr: float = 0.3,
                 imgsz: int = 640, device: Optional[str] = None, smooth: bool = True,
                 min_cutoff: float = 1.0, beta: float = 0.02):
        from ultralytics import YOLO  # lazy import: keeps unit tests light
        self.model = YOLO(weights)
        self.conf_thr, self.imgsz, self.device = conf_thr, imgsz, device
        self.filter = OneEuroFilter(min_cutoff, beta) if smooth else None
        self._last: Optional[np.ndarray] = None

    def reset(self) -> None:
        if self.filter:
            self.filter.reset()
        self._last = None

    def infer(self, frame: np.ndarray, t: float) -> Optional[np.ndarray]:
        res = self.model.predict(frame, imgsz=self.imgsz, device=self.device, verbose=False)[0]
        if res.keypoints is None or res.boxes is None or len(res.boxes) == 0:
            return None
        boxes = res.boxes.xyxy.cpu().numpy()
        areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
        kp = res.keypoints.data.cpu().numpy()[int(np.argmax(areas))].copy()  # (17, 3)

        if self._last is not None:                       # confidence gating: hold last good xy
            weak = kp[:, 2] < self.conf_thr
            kp[weak, :2] = self._last[weak, :2]
        if self.filter is not None:
            kp[:, :2] = self.filter(kp[:, :2], t)
        self._last = kp.copy()
        return kp
