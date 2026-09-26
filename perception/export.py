"""A - export a recorded video's pose (and barbell plate) track into a SetRecord.

Wires together PoseEstimator (A2), SetStateMachine (A4), and HoughPlateDetector
(A3) to generate a fully segmented SetRecord JSON ready for Role B analytics.

Usage:
    python -m perception.export --source data/raw/squat_side_01.mp4 \
        --exercise back_squat --view side --load-kg 100 \
        --out data/samples/squat_side_01.json
"""
from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path
from typing import Optional

import numpy as np

from contracts.models import FrameData, RepInterval, SetRecord
from perception.bar import (
    HoughPlateDetector,
    PlateDetection,
    calibrate_px_per_mm,
    pick_left_right,
)
from perception.capture import FrameSource
from perception.pose import PoseEstimator
from perception.state_machine import (
    RepEvent,
    SetEndEvent,
    SetStartEvent,
    SetStateMachine,
)


def export_set_record(
    source: str,
    exercise: str,
    camera_view: str,
    load_kg: Optional[float] = None,
    weights: str = "yolo11n-pose.pt",
    resize_width: Optional[int] = 1280,
    max_frames: Optional[int] = None,
    detect_bar: bool = False,
) -> SetRecord:
    src = FrameSource(source, resize_width=resize_width)
    pose = PoseEstimator(weights)
    sm = SetStateMachine()
    bar_detector = HoughPlateDetector() if detect_bar else None

    frames: list[FrameData] = []
    reps: list[RepInterval] = []
    all_plate_detections: list[PlateDetection] = []
    set_start_t: Optional[float] = None
    set_end_t: Optional[float] = None

    for fr in src:
        kp = pose.infer(fr.image, fr.t)
        if kp is None:
            continue  # Pose lost or below confidence threshold

        # 1. Repetition and Set State Machine Evaluation
        kp_np = np.asarray(kp, dtype=float)
        events = sm.step(fr.t, kp_np)
        for ev in events:
            if isinstance(ev, SetStartEvent):
                if set_start_t is None:
                    set_start_t = ev.t
            elif isinstance(ev, RepEvent):
                reps.append(
                    RepInterval(
                        rep_idx=ev.rep_idx,
                        start_t=round(float(ev.start_t), 3),
                        bottom_t=round(float(ev.bottom_t), 3),
                        end_t=round(float(ev.end_t), 3),
                    )
                )
            elif isinstance(ev, SetEndEvent):
                set_end_t = ev.t

        # 2. Barbell Plate Detection & Left/Right Tracking (if enabled)
        bar_l, bar_r = None, None
        if bar_detector and getattr(fr, "image", None) is not None:
            try:
                plates = bar_detector.detect(fr.image)
                if plates:
                    all_plate_detections.extend(plates)
                    pl, pr = pick_left_right(plates)
                    if pl:
                        bar_l = [round(float(pl.cx), 1), round(float(pl.cy), 1)]
                    if pr:
                        bar_r = [round(float(pr.cx), 1), round(float(pr.cy), 1)]
            except Exception:
                pass

        frames.append(
            FrameData(
                t=fr.t,
                frame_idx=fr.idx,
                keypoints=[tuple(map(float, row)) for row in kp],
                bar_left=bar_l,
                bar_right=bar_r,
            )
        )
        if max_frames and len(frames) >= max_frames:
            break
    src.release()

    if not frames:
        raise RuntimeError(f"No pose detected in {source!r}; check the video/model.")

    # 3. Finalize State Machine in case video ends mid-set without a full 3s still pause
    fin_events = sm.finalize(frames[-1].t)
    for ev in fin_events:
        if isinstance(ev, SetEndEvent) and set_end_t is None:
            set_end_t = ev.t

    # 4. Compute Spatial Calibration (px / mm) from all detected plates
    px_per_mm = None
    if all_plate_detections:
        calib = calibrate_px_per_mm(all_plate_detections)
        if calib is not None:
            px_per_mm = round(float(calib), 4)

    return SetRecord(
        set_id=str(uuid.uuid4()),
        exercise=exercise,
        camera_view=camera_view,
        fps=src.fps,
        start_t=set_start_t if set_start_t is not None else frames[0].t,
        end_t=set_end_t if set_end_t is not None else frames[-1].t,
        clip_path=str(source),
        load_kg=load_kg,
        px_per_mm=px_per_mm,
        reps=reps,
        frames=frames,
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--exercise", required=True)
    ap.add_argument("--view", choices=["side", "front", "rear"], default="side")
    ap.add_argument("--load-kg", type=float, default=None)
    ap.add_argument("--weights", default="yolo11n-pose.pt")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--max-frames", type=int, default=None)
    ap.add_argument(
        "--detect-bar",
        action="store_true",
        help="Run Hough circle plate detection and calibrate px/mm",
    )
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    record = export_set_record(
        a.source,
        a.exercise,
        a.view,
        a.load_kg,
        a.weights,
        a.width,
        a.max_frames,
        detect_bar=a.detect_bar,
    )
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(record.model_dump_json(indent=2))
    print(
        f"Wrote {len(record.frames)} frames and {len(record.reps)} detected reps -> {a.out}"
    )


if __name__ == "__main__":
    main()