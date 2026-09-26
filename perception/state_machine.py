"""A4 - Set state machine: Set_Start / Set_End + rep segmentation, from pose alone.

Matches the concept: motion begins ("bar unhooks or unweighted hips hinge") ->
Set_Start; re-rack or standing still for STAND_STILL_S -> Set_End, auto-trimmed.
This version drives off hip vertical velocity only (no bar track needed yet) so
A5 (clipper) and B1 (kinematics) can be developed and tested before A3's plate
detector is trained. Once A3 lands, bar-y velocity can be fed in as a second,
more reliable signal (see NOTE at bottom).

Coordinate convention: image y grows downward. Squat descent = hip y increasing
(positive velocity here); standing up = hip y decreasing (negative velocity).

Velocity is normalized by torso length (shoulder-to-hip distance) each frame, so
the same thresholds work regardless of the lifter's distance from the camera --
a lifter twice as far away moves half as many pixels per second for the same
real movement.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

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
    TOP = auto()          # standing / locked out, not mid-rep
    DESCENDING = auto()
    ASCENDING = auto()


class SetStateMachine:
    def __init__(
        self,
        v_thresh: float = 0.15,       # body-lengths/s to count as "moving"
        v_settle: float = 0.05,       # body-lengths/s to count as "settled" (must be < v_thresh, hysteresis)
        settle_hold_s: float = 0.15,  # must be settled this long before a rep is closed
        stand_still_s: float = 3.0,   # concept's ">3 seconds" -> Set_End
        min_rep_gap_s: float = 0.3,   # ignore direction flicker faster than this
    ):
        self.v_thresh, self.v_settle = v_thresh, v_settle
        self.settle_hold_s, self.stand_still_s = settle_hold_s, stand_still_s
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
        self._current_reps: list[RepEvent] = []

    def _scale(self, kp: np.ndarray) -> float:
        sy = (kp[L_SHOULDER, 1] + kp[R_SHOULDER, 1]) / 2
        hy = (kp[L_HIP, 1] + kp[R_HIP, 1]) / 2
        return max(abs(hy - sy), 1e-6)  # avoid div-by-zero on a degenerate pose

    def step(self, t: float, keypoints: np.ndarray) -> list[Event]:
        """Feed one frame's 17x3 keypoints. Returns events emitted this frame
        (usually none, sometimes a RepEvent, rarely a Set_Start/End too)."""
        events: list[Event] = []
        hip_y = (keypoints[L_HIP, 1] + keypoints[R_HIP, 1]) / 2
        scale = self._scale(keypoints)

        if self._prev_t is None or t <= self._prev_t:
            self._prev_t, self._prev_hip_y = t, hip_y
            return events

        dt = t - self._prev_t
        v = ((hip_y - self._prev_hip_y) / dt) / scale
        self._prev_t, self._prev_hip_y = t, hip_y

        moving_down = v > self.v_thresh
        moving_up = v < -self.v_thresh
        settled = abs(v) < self.v_settle

        # -- start of a rep: TOP -> DESCENDING --
        if self._phase == _Phase.TOP and moving_down:
            if self._last_rep_end_t is None or t - self._last_rep_end_t >= self.min_rep_gap_s:
                if not self._active:
                    self._active = True
                    self._current_reps = []
                    events.append(SetStartEvent(t))
                self._phase = _Phase.DESCENDING
                self._rep_start_t = t
                self._settled_since = None

        # -- bottom of the rep: DESCENDING -> ASCENDING --
        elif self._phase == _Phase.DESCENDING and moving_up:
            self._phase = _Phase.ASCENDING
            self._rep_bottom_t = t

        # -- top of the rep: ASCENDING -> TOP, once settled for settle_hold_s --
        elif self._phase == _Phase.ASCENDING:
            if settled:
                if self._settled_since is None:
                    self._settled_since = t
                elif t - self._settled_since >= self.settle_hold_s:
                    self._phase = _Phase.TOP
                    self._rep_idx += 1
                    rep = RepEvent(self._rep_idx, self._rep_start_t, self._rep_bottom_t, t)
                    self._current_reps.append(rep)
                    self._last_rep_end_t = t
                    events.append(rep)
                    self._settled_since = None
            else:
                self._settled_since = None  # moved again before settling; still ascending

        # -- stand-still timer for Set_End (only meaningful once TOP and active) --
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
        """Call after the last frame to close out an open set (e.g. video ends
        mid-set, or the lifter walks off without a full 3s pause in frame)."""
        if self._active:
            ev = SetEndEvent(t, list(self._current_reps))
            self._active = False
            self._rep_idx = 0
            self._current_reps = []
            return [ev]
        return []


# NOTE for later: once A3's bar tracker exists, a second velocity signal from
# bar_left/bar_right y-position (also normalized, this time by px_per_mm) can
# be combined with the hip signal -- e.g. require both to agree before firing
# a phase change -- which should be more robust than pose alone against
# camera-angle and clothing-related keypoint noise.
