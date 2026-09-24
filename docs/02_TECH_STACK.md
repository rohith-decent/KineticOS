# 02 - Tech Stack and Why

| Layer | Choice | Why | Rejected |
|---|---|---|---|
| Language | Python 3.11 (core), TypeScript (app) | CV/ML ecosystem is Python; fast prototyping; typed UI | Native C++/Kotlin: too slow to build for a semester |
| Pose | **Ultralytics YOLO11-Pose (17 kp)** primary; **MediaPipe BlazePose (33 lm)** fallback | Concept specifies 17 keypoints = COCO = YOLO11-Pose; fast; exports to ONNX/TFLite. MediaPipe adds heel/foot and runs well on CPU/mobile | OpenPose (heavy), MMPose (setup overhead) |
| Bar detection | **Fine-tuned YOLO11n** + **ByteTrack** | Plates are round, high-contrast, known 450 mm -> easy calibration; nano is fast; ByteTrack handles brief occlusion | Color tracking (fragile), SAM (heavy) |
| Signal processing | **NumPy, SciPy** (Savitzky-Golay, peak finding), One-Euro filter | Velocity from noisy positions needs smoothing | Raw differentiation |
| State machine | **Rule-based FSM first** (bar velocity + hip/knee angle + hysteresis); small 1D-CNN/LSTM later if needed | Deterministic, debuggable, needs no big dataset | End-to-end action classifier from day 1 |
| Video | **OpenCV** (I/O), **FFmpeg** (trim/compress/watermark) | Standard and fast | MoviePy (slow) |
| Inference | **ONNX Runtime**; TFLite/CoreML later | One export format for laptop/edge/phone | Raw PyTorch on device |
| Backend | **FastAPI + Pydantic v2** + WebSocket | Async, auto docs; same Pydantic models are the A<->B contract | Django (heavy), Flask (no validation) |
| Database | **SQLite -> PostgreSQL** (SQLAlchemy), pandas for trends | Zero setup now, same code on Postgres; data is relational | MongoDB |
| Frontend | **React + Vite + TS PWA**, Recharts/D3 | Runs in phone browser, installable, camera via getUserMedia | Flutter/native |
| Labeling/experiments | Roboflow or CVAT; MLflow or W&B (optional) | Fast labeling, reproducible training | Manual tracking |
| Dev | Git/GitHub, pytest, ruff, pre-commit, GitHub Actions | Two-person integration needs CI and a stable main | - |

## Deployment path
1. Weeks 1-6: laptop on recorded video (deterministic, easy to debug).
2. Weeks 7-9: phone = camera + UI, streams frames to laptop over WebSocket.
3. Stretch: on-device inference (TFLite / MediaPipe Tasks) for the "edge" claim.

## Why overall
Python-first means fast iteration; everything is open-source and well documented; one set of Pydantic models defines the contract between the two halves; and each piece has an upgrade path (SQLite->Postgres, server->on-device), so we ship a working MVP first and the ambitious edge story later.
