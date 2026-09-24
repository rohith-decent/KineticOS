# 01 - Roles and Workload (6 modules each, ~equal effort)

Effort points: S=1, M=2, L=3.

## Role A - Perception & Real-Time Engine ("eyes")
Get clean, reliable data out of video.
| ID | Module | Pts | File |
|---|---|---|---|
| A1 | Capture + 30 s RAM ring buffer, FPS handling | 2 | perception/capture.py |
| A2 | Pose wrapper (YOLO11-Pose, MediaPipe fallback), smoothing, confidence gating | 2 | perception/pose.py |
| A3 | Plate/collar detector (fine-tune YOLO11n) + tracker + px->mm calibration | 3 | perception/bar.py |
| A4 | Set state machine (unrack/re-rack, >3 s stand) + rep segmentation | 3 | perception/state_machine.py |
| A5 | Auto-clipper: FFmpeg trim, naming, watermark, compression | 2 | perception/clipper.py |
| A6 | Isometric alignment detector (ankle-hip-shoulder collinearity) | 2 | perception/isometric.py |
| | **Total** | **14** | |
Also owns: bar/plate labeling, model training + ONNX export, FPS/latency benchmarks.

## Role B - Biomechanics, Analytics & Product ("brain + face")
Turn tracks into insight and a usable product.
| ID | Module | Pts | File |
|---|---|---|---|
| B1 | Kinematics: MCV, peak velocity, velocity loss, bar drift, depth, trunk angle | 3 | analytics/kinematics.py |
| B2 | Symmetry engine: tilt delta, L/R drive asymmetry, sticking-point analysis, heatmap data | 3 | analytics/symmetry.py |
| B3 | Report generator + micro-cue rules + RPE estimate | 2 | analytics/report.py, cues.py |
| B4 | True-Time chronometer (pause/resume hysteresis, amber state) | 1 | analytics/chronometer.py |
| B5 | Backend API + DB (users/sessions/sets/reps, trends, fatigue fingerprint v1) | 3 | api/ |
| B6 | Frontend PWA: live status, debrief, history, heatmap, clip gallery | 3 | app/ |
| | **Total** | **15** | |
Also owns: metric ground-truth measurement and accuracy study. To even out, A takes the
front-view camera-mode work in Week 8 (+1 for A), giving 15 / 15.

## Shared (50/50)
Data collection (each records half), labeling days, integration tests, demo video, final report, slides, cross-review of PRs.

## Interface rule
A produces `SetRecord` (docs/03). B only consumes it. Until A's pipeline works, B develops on JSON in `data/samples/`; A works on raw video without needing B.
