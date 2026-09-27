"""A4 - Set state machine: Set_Start / Set_End + rep segmentation from pose keypoints.

Normalized by 2D Euclidean torso length with velocity window smoothing to handle
real-world keypoint jitter.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional
from collections import deque
import numpy as np

from perception.pose import L_HIP, R_HIP, L_SHOULDER, R_SHOULDER


@dataclass
class RepEvent:
    rep_idx: int
    start_t: float
    bottom_t: float
    end_t: float


@dataclass
class SetStartEvent:
    t: float


@dataclass
class SetEndEvent:
    t: float
    reps: list[RepEvent] = field(default_factory=list)


Event = SetStartEvent | RepEvent | SetEndEvent


class _Phase(Enum):
    TOP = auto()
    DESCENDING = auto()
    ASCENDING = auto()


class SetStateMachine:
    def __init__(
        self,
        v_thresh: float = 0.10,       # Body-lengths/s to count as active rep motion
        v_settle: float = 0.08,       # Body-lengths/s to count as settled/lockout
        settle_hold_s: float = 0.10,  # Required lockout hold duration
        stand_still_s: float = 2.5,   # Inactivity before declaring Set_End
        min_rep_gap_s: float = 0.25,  # Anti-flicker delay between reps
    ):
        self.v_thresh = v_thresh
        self.v_settle = v_settle
        self.settle_hold_s = settle_hold_s
        self.stand_still_s = stand_still_s
        self.min_rep_gap_s = min_rep_gap_s

        self._phase = _Phase.TOP
        self._active = False
        self._rep_idx = 0
        self._rep_start_t: Optional[float] = None
        self._rep_bottom_t: Optional[float] = None
        self._settled_since: Optional[float] = None
        self._still_since: Optional[float] = None
        self._last_rep_end_t: Optional[float] = None

        self._prev_t: Optional[float] = None
        self._prev_hip_y: Optional[float] = None
        self._v_history = deque(maxlen=3)
        self._current_reps: list[RepEvent] = []

    def _scale(self, kp: np.ndarray) -> float:
        # True 2D Euclidean distance between mid-shoulder and mid-hip
        sx = (kp[L_SHOULDER, 0] + kp[R_SHOULDER, 0]) / 2.0
        sy = (kp[L_SHOULDER, 1] + kp[R_SHOULDER, 1]) / 2.0
        hx = (kp[L_HIP, 0] + kp[R_HIP, 0]) / 2.0
        hy = (kp[L_HIP, 1] + kp[R_HIP, 1]) / 2.0
        dist = float(np.hypot(hx - sx, hy - sy))
        return max(dist, 10.0)

    def step(self, t: float, keypoints: np.ndarray) -> list[Event]:
        events: list[Event] = []
        hip_y = (keypoints[L_HIP, 1] + keypoints[R_HIP, 1]) / 2.0
        scale = self._scale(keypoints)

        if self._prev_t is None or t <= self._prev_t:
            self._prev_t, self._prev_hip_y = t, hip_y
            return events

        dt = t - self._prev_t
        raw_v = ((hip_y - self._prev_hip_y) / dt) / scale
        self._v_history.append(raw_v)
        v = float(np.mean(self._v_history))

        self._prev_t, self._prev_hip_y = t, hip_y

        moving_down = v > self.v_thresh
        moving_up = v < -self.v_thresh
        settled = abs(v) < self.v_settle

        # 1. Initiate Rep Descent
        if self._phase == _Phase.TOP and moving_down:
            if self._last_rep_end_t is None or t - self._last_rep_end_t >= self.min_rep_gap_s:
                if not self._active:
                    self._active = True
                    self._current_reps = []
                    events.append(SetStartEvent(t))
                self._phase = _Phase.DESCENDING
                self._rep_start_t = t
                self._settled_since = None

        # 2. Turnaround at Bottom
        elif self._phase == _Phase.DESCENDING and moving_up:
            self._phase = _Phase.ASCENDING
            self._rep_bottom_t = t

        # 3. Complete Ascending Rep
        elif self._phase == _Phase.ASCENDING:
            # Reached lockout and settled
            if settled:
                if self._settled_since is None:
                    self._settled_since = t
                elif t - self._settled_since >= self.settle_hold_s:
                    self._phase = _Phase.TOP
                    self._rep_idx += 1
                    bottom = self._rep_bottom_t if self._rep_bottom_t is not None else (self._rep_start_t + t) / 2
                    rep = RepEvent(self._rep_idx, self._rep_start_t, bottom, t)
                    self._current_reps.append(rep)
                    self._last_rep_end_t = t
                    events.append(rep)
                    self._settled_since = None
            # Touch-and-go descent into next rep
            elif moving_down and self._rep_bottom_t is not None:
                self._rep_idx += 1
                rep = RepEvent(self._rep_idx, self._rep_start_t, self._rep_bottom_t, t)
                self._current_reps.append(rep)
                self._last_rep_end_t = t
                events.append(rep)
                self._rep_start_t = t
                self._rep_bottom_t = None
                self._phase = _Phase.DESCENDING
                self._settled_since = None
            else:
                self._settled_since = None

        # 4. Set Termination Timer
        if self._active and self._phase == _Phase.TOP:
            if settled:
                if self._still_since is None:
                    self._still_since = t
                elif t - self._still_since >= self.stand_still_s:
                    events.append(SetEndEvent(t, list(self._current_reps)))
                    self._active = False
                    self._rep_idx = 0
                    self._current_reps = []
                    self._still_since = None
            else:
                self._still_since = None
        else:
            self._still_since = None

        return events

    def finalize(self, t: float) -> list[Event]:
        events: list[Event] = []
        if self._active:
            if self._phase == _Phase.ASCENDING and self._rep_start_t is not None:
                self._rep_idx += 1
                bottom = self._rep_bottom_t if self._rep_bottom_t is not None else (self._rep_start_t + t) / 2
                rep = RepEvent(self._rep_idx, self._rep_start_t, bottom, t)
                self._current_reps.append(rep)
                events.append(rep)

            ev = SetEndEvent(t, list(self._current_reps))
            self._active = False
            self._rep_idx = 0
            self._current_reps = []
            events.append(ev)
        return events