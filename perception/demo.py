"""Run pose on a video/webcam and save an annotated copy.

  python -m perception.demo --source data/raw/squat_side_01.mp4 --out out.mp4
  python -m perception.demo --source 0 --show
"""
import argparse
import time

import cv2

from perception.capture import FrameSource, RingBuffer
from perception.pose import PoseEstimator, SKELETON


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="0", help="camera index or video path")
    ap.add_argument("--out", default=None)
    ap.add_argument("--weights", default="yolo11n-pose.pt")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--no-smooth", action="store_true")
    a = ap.parse_args()

    src = FrameSource(int(a.source) if a.source.isdigit() else a.source, resize_width=a.width)
    pose = PoseEstimator(a.weights, smooth=not a.no_smooth)
    buf = RingBuffer(seconds=30)
    writer, n, t_start = None, 0, time.time()

    for fr in src:
        buf.push(fr.t, fr.image)
        kp = pose.infer(fr.image, fr.t)
        vis = fr.image.copy()
        if kp is not None:
            for i, j in SKELETON:
                cv2.line(vis, tuple(map(int, kp[i, :2])), tuple(map(int, kp[j, :2])), (0, 255, 0), 2)
            for x, y, c in kp:
                cv2.circle(vis, (int(x), int(y)), 4, (0, 0, 255) if c < pose.conf_thr else (255, 255, 0), -1)
        n += 1
        fps = n / max(time.time() - t_start, 1e-6)
        cv2.putText(vis, f"{fps:4.1f} FPS  buf {buf.span:4.1f}s", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        if a.out:
            if writer is None:
                h, w = vis.shape[:2]
                writer = cv2.VideoWriter(a.out, cv2.VideoWriter_fourcc(*"mp4v"), src.fps, (w, h))
            writer.write(vis)
        if a.show:
            cv2.imshow("KineticOS pose", vis)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    src.release()
    if writer:
        writer.release()
    print(f"{n} frames, avg {n / max(time.time() - t_start, 1e-6):.1f} FPS")


if __name__ == "__main__":
    main()
