import json
from pathlib import Path
import sys

# Ensure the repository root directory is on the Python path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import numpy as np

from perception.state_machine import (
    RepEvent,
    SetEndEvent,
    SetStartEvent,
    SetStateMachine,
)

path = ROOT_DIR / "data" / "samples" / "squat_real_01.json"

if not path.exists():
    print(f"Error: {path} not found")
    sys.exit(1)

with open(path, "r") as f:
    data = json.load(f)

sm = SetStateMachine()

reps = []
set_start_t = None
set_end_t = None

for fr in data["frames"]:
    keypoints = []

    for point in fr["keypoints"]:
        if isinstance(point, dict):
            keypoints.append([
                point["x"],
                point["y"],
                point.get("confidence", point.get("conf", 1.0))
            ])
        else:
            keypoints.append(point)

    kp = np.asarray(keypoints, dtype=float)

    for ev in sm.step(fr["t"], kp):

        if isinstance(ev, SetStartEvent) and set_start_t is None:
            set_start_t = ev.t

        elif isinstance(ev, RepEvent):
            reps.append({
                "rep_idx": ev.rep_idx,
                "start_t": round(float(ev.start_t), 3),
                "bottom_t": round(float(ev.bottom_t), 3),
                "end_t": round(float(ev.end_t), 3),
            })

        elif isinstance(ev, SetEndEvent):
            set_end_t = ev.t

if data["frames"]:

    for ev in sm.finalize(data["frames"][-1]["t"]):

        if isinstance(ev, RepEvent):
            reps.append({
                "rep_idx": ev.rep_idx,
                "start_t": round(float(ev.start_t), 3),
                "bottom_t": round(float(ev.bottom_t), 3),
                "end_t": round(float(ev.end_t), 3),
            })

        elif isinstance(ev, SetEndEvent) and set_end_t is None:
            set_end_t = ev.t

data["reps"] = reps

if set_start_t is not None:
    data["start_t"] = set_start_t

if set_end_t is not None:
    data["end_t"] = set_end_t

with open(path, "w") as f:
    json.dump(data, f, indent=2)

print(f"Successfully saved {len(reps)} reps into {path}!")

for r in reps:
    dur = r["end_t"] - r["start_t"]

    print(
        f"  Rep #{r['rep_idx']}: "
        f"start={r['start_t']}s | "
        f"bottom={r['bottom_t']}s | "
        f"end={r['end_t']}s "
        f"(Duration: {dur:.2f}s)"
    )