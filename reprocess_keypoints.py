"""Reprocess a cached SetRecord JSON (already-extracted keypoints) through
SetStateMachine WITHOUT re-running YOLO inference.

This is the fast iteration loop for tuning the state machine: `export.py`
takes minutes (video decode + pose inference); this script takes
milliseconds, because it starts from the keypoints `export.py` already wrote
to disk. Point it at any SetRecord-shaped JSON -- the file `export.py`
produces, or one of data/samples/*.json.

Usage
-----
    # Just see what's detected:
    python -m scripts.reprocess_keypoints data/samples/squat_real_01.json

    # Verify against a known rep count (exits non-zero on mismatch -- wire
    # this into CI or a pre-commit hook on real-footage fixtures):
    python -m scripts.reprocess_keypoints data/samples/squat_real_01.json --expected-reps 3

    # Override any SetStateMachine constructor arg from the CLI to test a
    # tuning change in milliseconds instead of re-exporting:
    python -m scripts.reprocess_keypoints data/samples/squat_real_01.json \\
        --expected-reps 3 --v-thresh 0.12 --min-rom-frac 0.18

    # Grid-search a couple of parameters against a ground-truth count:
    python -m scripts.reprocess_keypoints data/samples/squat_real_01.json \\
        --expected-reps 3 --sweep v_thresh=0.08,0.10,0.12 min_rom_frac=0.12,0.15,0.20
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from perception.state_machine import RepEvent, SetEndEvent, SetStartEvent, SetStateMachine

# Every constructor kwarg on SetStateMachine that it's reasonable to tune
# from the CLI, mapped to its CLI flag spelling.
_TUNABLE_PARAMS = [
    "v_thresh", "v_settle", "settle_hold_s", "stand_still_s", "min_rep_gap_s",
    "pos_tau_s", "vel_window_s", "confirm_duration_s", "min_rom_frac",
    "lockout_pos_tol_frac", "min_rep_duration_s", "top_ref_tau_s", "max_dt_s",
]


def load_frames(json_path: Path) -> tuple[list[float], list[np.ndarray]]:
    data = json.loads(json_path.read_text())
    frames = data.get("frames", [])
    if not frames:
        raise ValueError(f"{json_path} has no 'frames' -- is this a SetRecord export?")

    ts: list[float] = []
    kps: list[np.ndarray] = []
    for f in frames:
        raw_kps = f["keypoints"]
        parsed = np.empty((len(raw_kps), 3), dtype=float)
        for i, kp in enumerate(raw_kps):
            if isinstance(kp, dict):
                parsed[i] = (kp.get("x", 0.0), kp.get("y", 0.0), kp.get("confidence", 1.0))
            else:  # list/tuple [x, y] or [x, y, conf]
                parsed[i, 0] = kp[0]
                parsed[i, 1] = kp[1]
                parsed[i, 2] = kp[2] if len(kp) > 2 else 1.0
        ts.append(float(f["t"]))
        kps.append(parsed)
    return ts, kps


def run_state_machine(ts: list[float], kps: list[np.ndarray], **sm_kwargs) -> dict:
    sm = SetStateMachine(**sm_kwargs)
    reps: list[RepEvent] = []
    starts = ends = 0

    t0 = time.perf_counter()
    for t, kp in zip(ts, kps):
        for ev in sm.step(t, kp):
            if isinstance(ev, RepEvent):
                reps.append(ev)
            elif isinstance(ev, SetStartEvent):
                starts += 1
            elif isinstance(ev, SetEndEvent):
                ends += 1
    for ev in sm.finalize(ts[-1]):
        if isinstance(ev, RepEvent):
            reps.append(ev)
        elif isinstance(ev, SetEndEvent):
            ends += 1
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    return {"reps": reps, "starts": starts, "ends": ends, "elapsed_ms": elapsed_ms}


def print_result(result: dict, verbose: bool = True) -> None:
    reps = result["reps"]
    print(f"Set_Start events: {result['starts']}  |  Set_End events: {result['ends']}  "
          f"|  Reps detected: {len(reps)}  |  Processed in {result['elapsed_ms']:.2f} ms")
    if verbose:
        for r in reps:
            ok = r.start_t < r.bottom_t < r.end_t
            flag = "" if ok else "  [!] bottom not strictly between start/end"
            print(f"  rep {r.rep_idx}: start={r.start_t:6.2f}s  bottom={r.bottom_t:6.2f}s  "
                  f"end={r.end_t:6.2f}s  dur={r.end_t - r.start_t:5.2f}s{flag}")


def parse_sweep_arg(spec: str) -> tuple[str, list[float]]:
    name, _, values = spec.partition("=")
    if name not in _TUNABLE_PARAMS:
        raise argparse.ArgumentTypeError(
            f"unknown sweep parameter {name!r}; choose from {', '.join(_TUNABLE_PARAMS)}"
        )
    return name, [float(v) for v in values.split(",")]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("json_path", type=Path, help="Path to a SetRecord JSON export")
    ap.add_argument("--expected-reps", type=int, default=None,
                     help="Ground-truth rep count. If given, exit code is 0 on match, 1 on mismatch.")
    ap.add_argument("--sweep", nargs="*", type=parse_sweep_arg, metavar="PARAM=V1,V2,...",
                     help="Grid-search these SetStateMachine params (e.g. v_thresh=0.08,0.10,0.12) "
                          "and print every combination's result. Combine with --expected-reps to "
                          "have matches flagged.")
    ap.add_argument("--quiet", action="store_true", help="Only print the summary line, not each rep.")
    for param in _TUNABLE_PARAMS:
        flag = "--" + param.replace("_", "-")
        ap.add_argument(flag, type=float, default=None, help=f"Override SetStateMachine.{param}")
    args = ap.parse_args()

    if not args.json_path.exists():
        print(f"error: {args.json_path} not found", file=sys.stderr)
        return 2

    ts, kps = load_frames(args.json_path)
    print(f"Loaded {len(ts)} cached frames from {args.json_path} "
          f"({ts[-1] - ts[0]:.1f}s of footage, no inference re-run)")

    base_overrides = {p: getattr(args, p) for p in _TUNABLE_PARAMS if getattr(args, p) is not None}

    if args.sweep:
        names = [name for name, _ in args.sweep]
        value_lists = [values for _, values in args.sweep]
        best = None
        for combo in itertools.product(*value_lists):
            overrides = {**base_overrides, **dict(zip(names, combo))}
            result = run_state_machine(ts, kps, **overrides)
            n = len(result["reps"])
            desc = " ".join(f"{k}={v}" for k, v in overrides.items())
            match = ""
            if args.expected_reps is not None:
                match = "  <-- MATCH" if n == args.expected_reps else ""
                if n == args.expected_reps and best is None:
                    best = overrides
            print(f"  {desc:<55s} -> reps={n} starts={result['starts']} ends={result['ends']}"
                  f" ({result['elapsed_ms']:.1f} ms){match}")
        if args.expected_reps is not None:
            if best is not None:
                print(f"\nFirst matching config: {best}")
                return 0
            print(f"\nNo swept combination produced exactly {args.expected_reps} reps.")
            return 1
        return 0

    result = run_state_machine(ts, kps, **base_overrides)
    print_result(result, verbose=not args.quiet)

    if args.expected_reps is not None:
        n = len(result["reps"])
        if n == args.expected_reps:
            print(f"\nPASS: detected {n} reps, matches expected {args.expected_reps}.")
            return 0
        print(f"\nFAIL: detected {n} reps, expected {args.expected_reps}.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
