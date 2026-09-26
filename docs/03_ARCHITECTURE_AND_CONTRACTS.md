# 03 - Architecture and Contracts

```
Camera/Video -A1-> RingBuffer -A2-> Pose(17kp) ---+
                             \-A3-> Bar L/R tracks-+-> A4 StateMachine -> SetRecord -> B1,B2,B3 -> SetReport -> B5 DB -> B6 UI
                             \-A6-> Isometric angle error -> B4 Chronometer
A5 Clipper (uses Set_Start/End) -> clip.mp4 -------------------------------------------------> B5/B6
```

## FrameData (A -> B)
t, frame_idx, keypoints (17 x [x_px, y_px, conf]), bar_left, bar_right (or null).

## SetRecord (main hand-off)
set_id, exercise, camera_view (side|front|rear), fps, start_t, end_t, clip_path, load_kg (user-entered), px_per_mm, reps[{rep_idx,start_t,bottom_t,end_t}], frames[].

## SetReport (B output)
Per-rep MCV, velocity loss %, true TUT, bar drift, depth flags, tilt delta, asymmetry %, est. RPE, micro-cue, confidence per metric.

## IsometricSample (A6 -> B4)
{t, angle_error_deg, valid} at >= 30 Hz. B4 applies the 8 deg threshold with hysteresis (pause if >8 deg for 150 ms; resume after <6 deg for 300 ms).

Contracts live in `contracts/` (JSON Schema + Pydantic `models.py`), versioned with `schema_version`.
