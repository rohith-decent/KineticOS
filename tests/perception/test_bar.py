import numpy as np
from perception.bar import (
    PlateDetection, calibrate_px_per_mm, pick_left_right,
)


def _det(cx, diam=100.0, conf=0.9):
    return PlateDetection(cx=cx, cy=0.0, diameter_px=diam, conf=conf)


def test_pick_left_right_orders_by_x():
    left, right = pick_left_right([_det(500, conf=0.9), _det(50, conf=0.8)])
    assert left.cx == 50 and right.cx == 500


def test_pick_left_right_keeps_two_most_confident():
    dets = [_det(10, conf=0.9), _det(20, conf=0.95), _det(999, conf=0.1)]
    left, right = pick_left_right(dets)
    assert {left.cx, right.cx} == {10, 20}   # the low-confidence outlier is dropped


def test_pick_left_right_empty():
    assert pick_left_right([]) == (None, None)


def test_pick_left_right_single_detection():
    left, right = pick_left_right([_det(42)])
    assert left.cx == 42 and right is None


def test_calibrate_px_per_mm():
    # 450 mm plate rendered at 90 px diameter -> 0.2 px/mm
    px_per_mm = calibrate_px_per_mm([_det(0, diam=90.0)], plate_diameter_mm=450.0)
    assert abs(px_per_mm - 0.2) < 1e-9


def test_calibrate_px_per_mm_averages_multiple():
    dets = [_det(0, diam=90.0), _det(0, diam=110.0)]
    px_per_mm = calibrate_px_per_mm(dets, plate_diameter_mm=450.0)
    assert abs(px_per_mm - (100.0 / 450.0)) < 1e-9


def test_calibrate_px_per_mm_no_detections():
    assert calibrate_px_per_mm([]) is None


def test_hough_detector_finds_synthetic_circle():
    from perception.bar import HoughPlateDetector
    import cv2
    img = np.zeros((480, 640, 3), np.uint8)
    cv2.circle(img, (200, 240), 60, (255, 255, 255), -1, lineType=cv2.LINE_AA)
    cv2.circle(img, (440, 240), 60, (255, 255, 255), -1, lineType=cv2.LINE_AA)
    dets = HoughPlateDetector(min_radius_px=30, max_radius_px=100).detect(img)
    assert len(dets) >= 1  # Hough on synthetic flat circles is a smoke test, not accuracy proof
