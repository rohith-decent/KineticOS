"""A5 - Auto-clipper: trims raw footage to just the working set and names it.

Takes the Set_Start / Set_End timestamps that A4's state machine produces and
cuts a clean clip via ffmpeg -- no re-recording, no manual scrubbing. Matches
the concept's naming convention, e.g. "Squat_Set3_140kg_RPE8.5.mp4".

Two cut modes:
  reencode=False (default) - "stream copy": fast, lossless, but ffmpeg can only
    cut exactly on a keyframe, so the real start may drift by up to ~1-2s
    depending on the source's keyframe interval. Fine for a quick preview.
  reencode=True - frame-accurate cut (slower, re-encodes video). Use this for
    the clip that actually gets saved/shared, and it's required whenever a
    watermark is burned in (drawtext can't be applied during a stream copy).
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

# common exercise names -> short label used in the filename
_EXERCISE_LABELS = {
    "back_squat": "Squat", "front_squat": "Squat", "squat": "Squat",
    "deadlift": "Deadlift", "sumo_deadlift": "Deadlift",
    "bench_press": "Bench", "overhead_press": "OHP",
    "plank": "Plank", "wall_sit": "WallSit",
}


def _fmt_num(x: float) -> str:
    """8.5 -> '8.5', 8.0 -> '8', 140.0 -> '140' -- avoids ugly trailing zeros."""
    s = f"{x:g}"
    return s


def build_clip_filename(
    exercise: str, set_number: int, load_kg: Optional[float] = None,
    rpe: Optional[float] = None, ext: str = ".mp4",
) -> str:
    """e.g. build_clip_filename("back_squat", 3, 140, 8.5) -> 'Squat_Set3_140kg_RPE8.5.mp4'"""
    label = _EXERCISE_LABELS.get(exercise.lower(), exercise.replace("_", " ").title().replace(" ", ""))
    parts = [label, f"Set{set_number}"]
    if load_kg is not None:
        parts.append(f"{_fmt_num(load_kg)}kg")
    if rpe is not None:
        parts.append(f"RPE{_fmt_num(rpe)}")
    return "_".join(parts) + ext


def clip_set(
    source_path: str,
    start_t: float,
    end_t: float,
    out_path: str,
    pre_roll_s: float = 1.0,
    post_roll_s: float = 0.5,
    reencode: bool = False,
    watermark_text: Optional[str] = None,
    ffmpeg_bin: str = "ffmpeg",
) -> Path:
    """Cut [start_t - pre_roll_s, end_t + post_roll_s] out of source_path.

    pre_roll_s exists because A4 only fires Set_Start a few frames *after* the
    bar/hips actually start moving (velocity has to cross the threshold first),
    so without a small pre-roll the very start of rep 1 gets clipped off.
    """
    t0 = max(0.0, start_t - pre_roll_s)
    duration = max(0.0, (end_t + post_roll_s) - t0)
    if duration <= 0:
        raise ValueError(f"Non-positive clip duration ({duration:.3f}s) - check start_t/end_t")

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    cmd = [ffmpeg_bin, "-y", "-ss", f"{t0:.3f}", "-i", str(source_path), "-t", f"{duration:.3f}"]

    if watermark_text:
        reencode = True  # burning in text requires decoding+re-encoding, can't stream-copy
        safe_text = watermark_text.replace(":", r"\:").replace("'", r"\'")
        cmd += ["-vf", f"drawtext=text='{safe_text}':x=10:y=h-th-10:fontsize=24:"
                        f"fontcolor=white@0.85:box=1:boxcolor=black@0.4:boxborderw=6"]

    if reencode:
        cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac"]
    else:
        cmd += ["-c", "copy"]

    cmd += [str(out)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed ({result.returncode}): {result.stderr[-2000:]}")
    return out


def clip_from_set_end(
    source_path: str,
    start_t: float,
    end_t: float,
    out_dir: str,
    exercise: str,
    set_number: int,
    load_kg: Optional[float] = None,
    rpe: Optional[float] = None,
    **clip_kwargs,
) -> Path:
    """Convenience wrapper: builds the filename and cuts the clip in one call.
    Typical use, once A4 emits a SetEndEvent:

        events = state_machine.step(t, kp)
        for e in events:
            if isinstance(e, SetEndEvent):
                clip_from_set_end(video_path, set_start_t, e.t, "data/clips",
                                   exercise="back_squat", set_number=3, load_kg=140)
    """
    name = build_clip_filename(exercise, set_number, load_kg, rpe)
    out_path = str(Path(out_dir) / name)
    return clip_set(source_path, start_t, end_t, out_path, **clip_kwargs)
