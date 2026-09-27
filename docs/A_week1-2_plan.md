# Role A - Weeks 1-2 Plan (Perception)

## Git setup (do this first)
```
git pull origin main
git checkout -b feat/a-capture-pose
# unzip roleA_starter.zip over the repo root (it only adds perception/, tests/perception/, docs/A_*.md)
pip install -r requirements.txt
pytest tests/perception
```
Do NOT edit contracts/ or analytics/, api/, app/ (Role B's). Open a PR; Role B reviews.
The repo is public: never commit raw videos (already in .gitignore) and keep footage of other people private.

## Week 1 - A1 done, A2 started
- [x] A1 `perception/capture.py`: FrameSource + RingBuffer (tested)
- [x] A2 `perception/pose.py`: OneEuroFilter, joint_angle, PoseEstimator (needs real-video test)
- [ ] Run `python -m perception.demo --source <video> --out out.mp4` on 3 videos; watch for wrong-person picks, flickering joints, FPS
- [ ] Record first data set (protocol below)
- [ ] Write `docs/A_pose_notes.md`: FPS on your machine, which joints are unreliable, chosen smoothing values
- [ ] Agree with Role B on `SetRecord` (contracts/models.py) and export one recorded video as `data/samples/*.json` so B can start on real shape

## Week 2 - finish A2, prepare A3
- [ ] Add a helper that converts (t, keypoints) -> `contracts.models.FrameData` and dumps a `SetRecord` JSON (with empty reps for now)
- [ ] Compare YOLO11n-pose vs YOLO11s-pose vs MediaPipe on the same 3 clips (FPS + jitter); keep the winner
- [ ] Start plate labeling in Roboflow/CVAT: class `plate` (and `collar` if visible), 150+ images from your own clips
- [ ] Try baseline plate detection with plain `yolo11n.pt` + Hough circles to see how hard it is

## Recording protocol (for Role A and B data)
- Phone on tripod at hip height, landscape, 60 FPS, 1080p, locked exposure/focus.
- SIDE view: perpendicular to the lifter, both plates ideally visible, full body + bar in frame, ~3 m away.
- FRONT view (later): straight-on, same distance.
- Per exercise record 5-8 sets with different loads and rep counts; include some deliberately bad reps (shallow depth, uneven bar) and one failed rep.
- Include the walk-out, setup, and re-rack so the state machine has real "dead time" to reject.
- File name: `squat_side_140kg_5reps_01.mp4`; keep a `data/raw/labels.csv` with: file, exercise, view, load_kg, reps, notes.
- Get verbal consent from anyone visible; prefer a quiet gym corner.

## Known design notes
- Raw 1080p60 for 30 s is about 10 GB, so RingBuffer JPEG-encodes frames (about 180 MB). Keep `encode=True` for live use.
- File sources use `t = idx / fps` so results are reproducible; camera sources use the monotonic clock.
- Pose picks the largest person in frame. If gym background people cause trouble, add an ROI or track-by-previous-hip-position.
