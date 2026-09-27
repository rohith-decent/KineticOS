import json
import sys
from pathlib import Path
import numpy as np

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from perception.state_machine import SetStateMachine, RepEvent, SetStartEvent, SetEndEvent

json_path = Path("data/samples/squat_real_01.json")
if not json_path.exists():
    print(f"File not found: {json_path}")
    exit(1)

with open(json_path, "r") as f:
    data = json.load(f)

frames = data.get("frames", [])
print(f"Total frames loaded: {len(frames)}")

def parse_keypoints(raw_kps) -> np.ndarray:
    parsed = []
    for kp in raw_kps:
        if isinstance(kp, dict):
            parsed.append([float(kp.get("x", 0.0)), float(kp.get("y", 0.0)), float(kp.get("confidence", 1.0))])
        elif isinstance(kp, (list, tuple)):
            parsed.append([float(kp[0]), float(kp[1]), float(kp[2]) if len(kp) > 2 else 1.0])
        else:
            parsed.append([0.0, 0.0, 0.0])
    return np.array(parsed, dtype=float)

# Extract timestamps, hip_y, and torso scale
ts = [f["t"] for f in frames]
hip_ys = []
torso_lens = []

for f in frames:
    kps = parse_keypoints(f["keypoints"])
    l_hip, r_hip = kps[11], kps[12]
    l_sh, r_sh = kps[5], kps[6]
    
    hy = (l_hip[1] + r_hip[1]) / 2.0
    sy = (l_sh[1] + r_sh[1]) / 2.0
    
    # 2D Euclidean torso distance
    hx = (l_hip[0] + r_hip[0]) / 2.0
    sx = (l_sh[0] + r_sh[0]) / 2.0
    torso_len = np.hypot(hx - sx, hy - sy)
    
    hip_ys.append(hy)
    torso_lens.append(max(torso_len, 10.0))

hip_ys = np.array(hip_ys)
rom = np.max(hip_ys) - np.min(hip_ys)
avg_torso = np.mean(torso_lens)

print(f"Vertical Hip Displacement Range (ROM): {rom:.1f} px")
print(f"Average Torso Length: {avg_torso:.1f} px")
print(f"ROM / Torso Ratio: {rom / avg_torso:.2f}")

# Test with relaxed thresholds on real-world video
print("\n--- Testing State Machine with Realistic Thresholds ---")
for v_thresh, v_settle in [(0.12, 0.08), (0.10, 0.07), (0.08, 0.05)]:
    sm = SetStateMachine(
        v_thresh=v_thresh,
        v_settle=v_settle,
        settle_hold_s=0.10,
        stand_still_s=2.5
    )
    detected_reps = []
    for f in frames:
        t = f["t"]
        kps = parse_keypoints(f["keypoints"])
        evs = sm.step(t, kps)
        for e in evs:
            if isinstance(e, RepEvent):
                detected_reps.append(e)
    
    fin = sm.finalize(ts[-1])
    for e in fin:
        if isinstance(e, RepEvent):
            detected_reps.append(e)

    print(f"Params (v_thresh={v_thresh}, v_settle={v_settle}) -> Detected: {len(detected_reps)} reps")
    for r in detected_reps:
        print(f"   Rep #{r.rep_idx}: start={r.start_t:.2f}s, bottom={r.bottom_t:.2f}s, end={r.end_t:.2f}s")