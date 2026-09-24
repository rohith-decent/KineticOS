# 04 - 10-Week Roadmap (A and B in parallel)

| Week | Role A (Perception) | Role B (Analytics/Product) | Shared |
|---|---|---|---|
| 1 | A1 capture + buffer; repo/CI | Metric definitions, DB schema | Agree contracts, record first 10 sets |
| 2 | A2 pose + smoothing | B1 MCV/velocity on sample JSON | Sanity-label pose frames |
| 3 | A3 label plates, first detector | B1 bar path, depth, trunk angle | Record more data (side + front) |
| 4 | A3 tracker + px->mm calibration | B5 FastAPI + DB, SetReport | Mid-review |
| 5 | A4 state machine v1 (rules) | B3 report generator + RPE estimate | End-to-end video -> report (CLI) |
| 6 | A5 auto-clipper; A4 tuning | B6 PWA upload + report page | **MVP demo (squat, side view)** |
| 7 | A6 isometric detector | B4 chronometer + UI timer | Plank data |
| 8 | Front-view mode, validate metrics | B2 symmetry engine + micro-cues | Accuracy study |
| 9 | Live streaming (WebSocket), ONNX export | B6 heatmap, history; B5 longitudinal | Bug bash |
| 10 | Benchmarks (FPS, latency) | UI polish, fatigue fingerprint v1 | Final report, slides, demo video |

Definition of done per module: code + unit test + short doc paragraph + metric measured on our own data.
