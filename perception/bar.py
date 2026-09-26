"""A3 - Barbell plate detection, left/right tracking, and px->mm calibration.

Two detector backends, same output shape:
  - HoughPlateDetector : zero training needed, works today. Finds circular plates
    with cv2.HoughCircles. Less robust (lighting, cluttered gym background).
  - YoloPlateDetector  : fine-tuned YOLO on your own labeled data (see
    docs/A_plate_labeling.md). Use Ultralytics' built-in .track() for a free
    ByteTrack-based tracker across frames.

Both return a list of PlateDetection; pick_left_right() then decides which
detection is the left/right end of the bar for a given frame.

Calibration: a standard Olympic bumper/steel plate is 450 mm in diameter, so
px_per_mm = detected_diameter_px / 450. Average this over several frames/plates
for stability -- don't trust a single frame.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

PLATE_DIAMETER_MM = 450.0  # standard 20/15/10 kg bumper & most steel plates


@dataclass
class PlateDetection:
    cx: float
    cy: float
    diameter_px: float
    conf: float
    track_id: Optional[int] = None


def pick_left_right(
    detections: list[PlateDetection],
) -> tuple[Optional[PlateDetection], Optional[PlateDetection]]:
    """Of all plate detections in a frame, keep the two most confident and
    return them ordered (left, right) by x position. With <2 detections,
    missing side(s) are None (e.g. one plate occluded)."""
    if not detections:
        return None, None
    top2 = sorted(detections, key=lambda d: d.conf, reverse=True)[:2]
    top2.sort(key=lambda d: d.cx)
    if len(top2) == 1:
        return (top2[0], None)  # caller decides side from previous frame / camera_view
    return top2[0], top2[1]


def calibrate_px_per_mm(
    detections: list[PlateDetection], plate_diameter_mm: float = PLATE_DIAMETER_MM
) -> Optional[float]:
    """Average px/mm across all detections in a frame (or batch). Call across
    many frames and average again -- a single frame is noisy (motion blur,
    partial occlusion, off-axis viewing angle)."""
    diam = [d.diameter_px for d in detections if d.conf > 0]
    if not diam:
        return None
    return float(np.mean(diam)) / plate_diameter_mm


class HoughPlateDetector:
    """No-training baseline: detects circular plates via Hough transform.
    Good enough to unblock A4/A5 development and to bootstrap auto-labeling
    (run it on your clips, then hand-correct its boxes in CVAT -- much faster
    than labeling from scratch)."""

    def __init__(self, min_radius_px: int = 40, max_radius_px: int = 220,
                 dp: float = 1.2, min_dist_px: int = 200):
        self.min_radius_px, self.max_radius_px = min_radius_px, max_radius_px
        self.dp, self.min_dist_px = dp, min_dist_px

    def detect(self, frame: np.ndarray) -> list[PlateDetection]:
        import cv2
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.medianBlur(gray, 5)
        circles = cv2.HoughCircles(
            gray, cv2.HOUGH_GRADIENT, dp=self.dp, minDist=self.min_dist_px,
            param1=100, param2=40,
            minRadius=self.min_radius_px, maxRadius=self.max_radius_px,
        )
        if circles is None:
            return []
        out = []
        for cx, cy, r in circles[0]:
            # Hough gives no real confidence; treat "found" as a flat prior.
            out.append(PlateDetection(cx=float(cx), cy=float(cy), diameter_px=float(2 * r), conf=0.5))
        return out


class YoloPlateDetector:
    """Fine-tuned YOLO detector + built-in ByteTrack, once you have weights.
    Train with Ultralytics CLI on your labeled CVAT/Roboflow export:
      yolo detect train data=plates.yaml model=yolo11n.pt epochs=100 imgsz=960
    See docs/A_plate_labeling.md."""

    def __init__(self, weights: str, conf_thr: float = 0.4, imgsz: int = 960):
        from ultralytics import YOLO
        self.model = YOLO(weights)
        self.conf_thr, self.imgsz = conf_thr, imgsz

    def detect(self, frame: np.ndarray, track: bool = True) -> list[PlateDetection]:
        if track:
            res = self.model.track(frame, imgsz=self.imgsz, conf=self.conf_thr,
                                    persist=True, verbose=False)[0]
        else:
            res = self.model.predict(frame, imgsz=self.imgsz, conf=self.conf_thr, verbose=False)[0]
        if res.boxes is None or len(res.boxes) == 0:
            return []
        boxes = res.boxes.xyxy.cpu().numpy()
        confs = res.boxes.conf.cpu().numpy()
        ids = (res.boxes.id.cpu().numpy().astype(int).tolist()
               if getattr(res.boxes, "id", None) is not None else [None] * len(boxes))
        out = []
        for (x1, y1, x2, y2), c, tid in zip(boxes, confs, ids):
            diam = max(x2 - x1, y2 - y1)  # plate may be partly occluded on one axis
            out.append(PlateDetection(cx=float((x1 + x2) / 2), cy=float((y1 + y2) / 2),
                                       diameter_px=float(diam), conf=float(c), track_id=tid))
        return out
