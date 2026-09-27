# A3 - Plate Labeling & Training Guide

## Why label at all
`HoughPlateDetector` (in `perception/bar.py`) works today with zero training, but it's
fooled by gym clutter, non-circular plates, and lighting. The fine-tuned YOLO
detector is the real deliverable for A3 -- Hough is only there to unblock A4/A5
and to auto-bootstrap your labels (see step 3).

## 1. Collect frames
Pull frames from your recorded squat/deadlift clips (both views), not stock photos --
your gym, your plates, your camera. Aim for 150-300 images covering:
- different loads (bar-only, light, heavy -- plate stack changes appearance)
- both plate colors/types if your gym has more than one
- partial occlusion by hands/legs at top and bottom of the lift
- both camera views (side and front)

Extract with ffmpeg, e.g. one frame every 10th frame:
```
ffmpeg -i data/raw/squat_side_01.mp4 -vf "select=not(mod(n\,10))" -vsync vfr data/labels/frames/sq01_%04d.jpg
```

## 2. Classes
- `plate` (every visible plate, both ends of the bar)
- `collar` (optional, if visible/relevant -- can skip for v1 and add later)

## 3. Bootstrap with Hough to go faster
Run `HoughPlateDetector` over your frames and dump pre-filled boxes (script below);
then just correct mistakes in CVAT/Roboflow instead of drawing every box from scratch.
```python
import cv2, json
from perception.bar import HoughPlateDetector

det = HoughPlateDetector()
img = cv2.imread("data/labels/frames/sq01_0010.jpg")
for d in det.detect(img):
    print(d.cx - d.diameter_px/2, d.cy - d.diameter_px/2, d.diameter_px, d.diameter_px)
```
Hough will miss/mislabel plenty -- expect to add and fix boxes by hand.

## 4. Label
Use CVAT (self-hosted or cvat.ai) or Roboflow (free tier). Export in YOLO format:
```
plates/
  images/{train,val}/*.jpg
  labels/{train,val}/*.txt      # class cx cy w h, normalized 0-1
plates.yaml
```
`plates.yaml`:
```yaml
path: plates
train: images/train
val: images/val
names: [plate]     # add "collar" as index 1 if you're labeling it
```
Split roughly 85/15 train/val, and make sure both views appear in val too.

## 5. Train
```
pip install ultralytics
yolo detect train data=plates.yaml model=yolo11n.pt epochs=100 imgsz=960 patience=20
```
Nano model is enough for one clear object class. Training runs fine on CPU for this
dataset size, just slowly (expect 1-3 hrs); a free Colab GPU is much faster if available.

## 6. Evaluate and plug in
```
yolo detect val data=plates.yaml model=runs/detect/train/weights/best.pt
```
Then point the real detector at it:
```python
from perception.bar import YoloPlateDetector
det = YoloPlateDetector("runs/detect/train/weights/best.pt")
detections = det.detect(frame)          # tracked automatically (persist=True)
```
Report mAP50 and a couple of example frames with boxes drawn in `docs/A_pose_notes.md`
(or a new `docs/A_bar_notes.md`) -- this is evidence for the project report.

## 7. Calibration sanity check
Once detection works, verify `calibrate_px_per_mm()` against a real known distance
(e.g. measure the actual plate diameter or bar length in your gym and compare).
Average over at least 10-20 frames per set -- single-frame calibration is noisy.
