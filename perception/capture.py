"""A1 - Frame capture and rolling RAM buffer.

FrameSource : webcam / video-file iterator with a reliable timeline.
RingBuffer  : keeps only the last N seconds of frames (JPEG-encoded to save RAM).
"""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Iterator, Optional, Union

import cv2
import numpy as np


@dataclass
class Frame:
    idx: int
    t: float            # seconds. Files: idx / fps (deterministic). Camera: monotonic clock.
    image: np.ndarray   # BGR


class FrameSource:
    """Iterate frames from a camera index or a video file path."""

    def __init__(self, source: Union[int, str], request_fps: float = 60.0,
                 resize_width: Optional[int] = None):
        self.source = source
        self.is_file = isinstance(source, str)
        self.cap = cv2.VideoCapture(source)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open video source: {source!r}")
        if not self.is_file:
            self.cap.set(cv2.CAP_PROP_FPS, request_fps)
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.fps = float(fps) if fps and fps > 1 else request_fps
        self.resize_width = resize_width

    def __iter__(self) -> Iterator[Frame]:
        idx = 0
        t0 = time.monotonic()
        while True:
            ok, img = self.cap.read()
            if not ok:
                break
            if self.resize_width and img.shape[1] > self.resize_width:
                scale = self.resize_width / img.shape[1]
                img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            t = idx / self.fps if self.is_file else time.monotonic() - t0
            yield Frame(idx, t, img)
            idx += 1

    def release(self) -> None:
        self.cap.release()


class RingBuffer:
    """Time-bounded frame buffer.

    Raw 1080p60 for 30 s is ~10 GB, so frames are stored as JPEG bytes (~100 KB each,
    ~180 MB per 30 s). Set encode=False for tests or small resolutions.
    """

    def __init__(self, seconds: float = 30.0, encode: bool = True, jpeg_quality: int = 85):
        self.seconds = seconds
        self.encode = encode
        self.jpeg_quality = jpeg_quality
        self._q: deque = deque()
        self._lock = threading.Lock()

    def push(self, t: float, image: np.ndarray) -> None:
        item = image
        if self.encode:
            ok, buf = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
            if not ok:
                raise RuntimeError("JPEG encode failed")
            item = buf
        with self._lock:
            self._q.append((t, item))
            while self._q and t - self._q[0][0] > self.seconds:
                self._q.popleft()

    def _decode(self, item):
        return cv2.imdecode(item, cv2.IMREAD_COLOR) if self.encode else item

    def get_range(self, t0: float, t1: float) -> list[tuple[float, np.ndarray]]:
        """Frames with t0 <= t <= t1 (used to grab pre-roll before Set_Start)."""
        with self._lock:
            items = [(t, it) for t, it in self._q if t0 <= t <= t1]
        return [(t, self._decode(it)) for t, it in items]

    def clear(self) -> None:
        with self._lock:
            self._q.clear()

    def __len__(self) -> int:
        return len(self._q)

    @property
    def span(self) -> float:
        with self._lock:
            return (self._q[-1][0] - self._q[0][0]) if len(self._q) > 1 else 0.0
