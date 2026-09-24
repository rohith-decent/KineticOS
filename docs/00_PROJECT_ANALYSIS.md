# 00 - Project Analysis

## 1. What KineticOS really is
One perception layer feeding five modules:
1. **Rolling buffer + state machine** - records only while a set is happening.
2. **Dual tracking** - 17 body keypoints + both barbell collars (dynamic lifts); joint-plane geometry (isometrics).
3. **Optimal-Rep Auto-Clipper** - trimmed, named MP4 per set.
4. **True-Time Chronometer** - isometric timer that pauses when alignment error > 8 deg.
5. **Bilateral Symmetry Heatmapper** - L/R velocity and tilt differences tracked across weeks.

On top: a **post-set report** (MCV, velocity loss, bar path, depth, symmetry, micro-cue) and **longitudinal intelligence** (fatigue fingerprint, work capacity, PR portfolio).

## 2. Layered view
Capture -> Perception (pose, bar) -> Event logic (set/rep) -> Kinematics -> Report/Insight -> Storage -> UI.
Layers 1-3 = Role A. Layers 4-7 = Role B. The contract sits between layers 3 and 4.

## 3. Technical reality check (fix these in the design early)
| Claim in concept | Issue | What we do |
|---|---|---|
| One camera measures L/R asymmetry AND bar path | Side view gives bar path/depth but not left vs right; front/rear view sees L/R but not depth/bar path | Two **camera modes**: SIDE (path, depth, velocity, trunk) and FRONT/REAR (tilt, symmetry). MVP = SIDE, then FRONT. State this in the report. |
| "40 ms" velocity differences | At 60 FPS one frame = 16.7 ms; keypoint jitter is larger | Report symmetry as % difference over rep windows, smoothed, with confidence. 40 ms is a stretch target. |
| Real units (m/s, cm) from pixels | Needs scale | Calibrate with the plate (standard plate diameter 450 mm) plus a short camera-tilt check. |
| Sub-degree angles (1.8 deg tilt, 4 deg lumbar) | 2D pose noise is several degrees | Show ranges + confidence; validate against manual reference; report accuracy honestly. |
| RPE estimation | Not directly measurable | Estimate from velocity loss and MCV vs the lifter's own load-velocity profile; label "estimated". |
| Lumbar / cervical spine | COCO-17 has no spine points | Use MediaPipe 33 landmarks or a trunk-angle proxy (hip-shoulder-ear). Do not claim true lumbar measurement. |
| Report in < 2 s | Feasible post-set on laptop; harder on phone | Target <2 s laptop, <5 s phone/edge. |
| "Before they cause injury" | Not clinically validated | Word as "flags" and "trends"; add a disclaimer. |

## 4. Scope
**MVP:** video -> pose + bar tracking -> set start/end -> rep count -> MCV, velocity loss, bar path, depth -> auto-clip -> report page -> stored history.
**Version 2:** isometric True-Time timer (plank/wall-sit), front-view symmetry, micro-cues, long-term heatmap.
**Stretch:** real-time on phone, smartwatch, fatigue-fingerprint ML, PR portfolio, exercise classifier.
First lifts: back squat, deadlift (side view), plank (isometric).

## 5. Data plan
- Record 40-60 sets: squat/deadlift (side + front), planks; 60 FPS; tripod; plates visible.
- Label: plate/collar boxes (100-300 images to start), set start/end times, rep boundaries, depth ground truth for ~20 reps.
- Get consent from everyone filmed; keep data private.

## 6. Success metrics (for the final report)
Rep-count accuracy, set-boundary error (s), bar-tracking error (cm), MCV error vs reference, depth-call agreement, latency, FPS.
