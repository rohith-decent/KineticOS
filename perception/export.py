"""A - export a recorded video's pose (and, later, bar) track into a SetRecord.

This is the hand-off artifact for Role B: run it on any clip and you get a JSON
file that matches contracts.models.SetRecord, so B can build kinematics/report
code against real data before A4 (state machine) or A3 (bar tracker) exist.

Until A4 exists, reps=[] and the whole clip is treated as one "set" (start_t=0,
end_t=last frame). Fill in --load-kg / --exercise by hand since the phone/app
UI doesn't exist yet either.

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

from contracts.models import FrameData, SetRecord
from perception.capture import FrameSource
from perception.pose import PoseEstimator


def export_set_record(
    source: str,
    exercise: str,
    camera_view: str,
    load_kg: Optional[float] = None,
    weights: str = "yolo11n-pose.pt",
    resize_width: Optional[int] = 1280,
    max_frames: Optional[int] = None,
) -> SetRecord:
    src = FrameSource(source, resize_width=resize_width)
    pose = PoseEstimator(weights)
    frames: list[FrameData] = []

    for fr in src:
        kp = pose.infer(fr.image, fr.t)
        if kp is None:
            continue  # A4 will later mark these as "lost track" instead of dropping
        frames.append(FrameData(
            t=fr.t,
            frame_idx=fr.idx,
            keypoints=[tuple(map(float, row)) for row in kp],
            bar_left=None,   # filled in once A3 (bar tracker) exists
            bar_right=None,
        ))
        if max_frames and len(frames) >= max_frames:
            break
    src.release()

    if not frames:
        raise RuntimeError(f"No pose detected in {source!r}; check the video/model.")

    return SetRecord(
        set_id=str(uuid.uuid4()),
        exercise=exercise,
        camera_view=camera_view,
        fps=src.fps,
        start_t=frames[0].t,
        end_t=frames[-1].t,
        clip_path=str(source),
        load_kg=load_kg,
        px_per_mm=None,   # filled in once A3 (plate calibration) exists
        reps=[],          # filled in once A4 (state machine) exists
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
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    record = export_set_record(
        a.source, a.exercise, a.view, a.load_kg, a.weights, a.width, a.max_frames,
    )
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(record.model_dump_json(indent=2))
    print(f"Wrote {len(record.frames)} frames -> {a.out}")


if __name__ == "__main__":
    main()
