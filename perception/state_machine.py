"""A4 - Set state machine: Set_Start / Set_End + rep segmentation from pose keypoints.

Normalized by 2D Euclidean torso length, with a layered anti-chatter design so a
single rep boundary requires *independent* agreement from four different checks
before it is emitted. See docs/A_state_machine_notes.md for the tuning history.

------------------------------------------------------------------------------
WHY THE ORIGINAL VERSION CHATTERED (root cause, in one line):
    single-frame numerical differentiation of a noisy signal has a noise gain
    of 1/dt, and dt is tiny at 30 fps.
------------------------------------------------------------------------------
The old code computed velocity as a raw one-frame finite difference:

    v = (hip_y[t] - hip_y[t-1]) / dt / scale

At 30 fps, dt ~= 0.033 s. YOLO11-Pose keypoint jitter on real footage is
commonly 1-2 px frame-to-frame even when the lifter is standing still (network
noise, compression artifacts, sub-pixel localization error). With a torso
scale of ~85 px (measured on squat_set1.mp4), a single 2 px jitter step alone
produces:

    v = 2 px / 0.033 s / 85 px  ~=  0.71 body-lengths/s

...which is *7x* the default v_thresh of 0.10. Differentiation is a high-pass
operation: it amplifies noise by a factor inversely proportional to the sample
interval, while real squat velocity (which changes smoothly over ~0.5-1.5 s)
is comparatively unaffected. On the real clip, 65-80% of *all* frames had
|raw_v| > v_thresh from jitter alone (measured empirically) -- the velocity
gate was, in effect, almost always "hot", so the FSM flickered between
DESCENDING/ASCENDING on essentially every settle, and each flicker that
happened to touch a velocity-sign change and then settle again minted a new
"rep". 3 genuine reps interspersed with jitter chatter -> 32 logged reps.

Three compounding structural gaps let that noise turn into phantom reps:
  1. No amplitude/ROM gate: a rep was accepted purely on a velocity sign
     flip, with no check that the lifter's hip had actually traveled a
     meaningful fraction of their torso length. A sub-pixel wobble and a real
     squat looked identical to the FSM.
  2. No real "lockout recovery" check: "settled" meant |v| was small, which
     is also true when the lifter is paused *mid-range* (or the tracker lost
     the person). It never checked that the lifter's position had actually
     returned near the standing/lockout height.
  3. No temporal duration filter: there was nothing stopping a "rep" that
     started and finished 60ms apart from being logged -- physically
     impossible for a human squat, but numerically trivial for pixel jitter.

------------------------------------------------------------------------------
THE FIX: four independent, complementary gates (defense in depth)
------------------------------------------------------------------------------
 (a) Windowed velocity, not single-frame velocity. Position is EMA-smoothed
     (extra safety net on top of whatever upstream filtering perception.pose
     already applied) and velocity is estimated over a `vel_window_s`
     baseline (multiple frames), not a single dt. This directly attacks the
     1/dt noise-gain problem: noise magnitude stays ~constant while the
     effective dt in the denominator grows, so gain shrinks roughly linearly
     with window length. See `_windowed_velocity`.
 (b) Direction hysteresis / debounce (`confirm_duration_s`). A direction
     (down/up) must hold for a minimum duration before a phase transition is
     even considered -- kills single-sample sign flips outright.
 (c) Amplitude/ROM gate (`min_rom_frac`). A rep is only counted if the
     tracked true bottom (a continuously-updated running extremum, not the
     debounce-flip instant) traveled at least `min_rom_frac` of the torso
     length away from where the descent started. Normalized against the
     torso scale measured *at lockout* (`_rep_start_scale`), not at the
     bottom -- trunk lean during a real squat foreshortens the 2D
     shoulder-hip distance in the frame, so using a bottom-of-rep scale would
     bias the ratio and make the gate unreliable.
 (d) Position-based lockout recovery + minimum rep duration
     (`lockout_pos_tol_frac`, `min_rep_duration_s`). "Settled" now requires
     both low velocity *and* the smoothed hip position being back within
     tolerance of a slowly-tracked top-of-rep reference -- not just
     "stopped somewhere". And any candidate rep shorter than
     `min_rep_duration_s` (default 0.35 s -- no human completes a full squat
     rep faster than that) is discarded rather than emitted.

Gates (a)+(b) suppress most jitter before it ever causes a phase transition;
gates (c)+(d) are the backstop that silently absorbs whatever slips through
(e.g. a brief tracker glitch during an occlusion) at rep-completion time,
rather than ever emitting a spurious RepEvent for it.
"""
from __future__ import annotations

import math
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
        v_thresh: float = 0.10,          # Body-lengths/s to count as active rep motion
        v_settle: float = 0.07,          # Body-lengths/s to count as settled/lockout
        settle_hold_s: float = 0.10,     # Required lockout hold duration
        stand_still_s: float = 2.5,      # Inactivity before declaring Set_End
        min_rep_gap_s: float = 0.25,     # Anti-flicker delay between reps
        pos_tau_s: float = 0.08,         # EMA smoothing time-constant on hip position
        vel_window_s: float = 0.12,      # Baseline duration for windowed velocity estimate
        confirm_duration_s: float = 0.08,   # Direction must hold this long before it "counts"
        min_rom_frac: float = 0.15,      # Min bottom depth, as a fraction of torso scale, to count as a real rep
        lockout_pos_tol_frac: float = 0.12,  # Max distance from top-reference (x torso scale) to count as "at lockout"
        min_rep_duration_s: float = 0.35,   # Reps faster than this are discarded as noise, not real lifts
        top_ref_tau_s: float = 1.0,      # Slow EMA time-constant for the standing/lockout reference position
        max_dt_s: float = 0.5,           # dt above this is treated as a tracking gap, not real motion
    ):
        self.v_thresh = v_thresh
        self.v_settle = v_settle
        self.settle_hold_s = settle_hold_s
        self.stand_still_s = stand_still_s
        self.min_rep_gap_s = min_rep_gap_s
        self.pos_tau_s = pos_tau_s
        self.vel_window_s = vel_window_s
        self.confirm_duration_s = confirm_duration_s
        self.min_rom_frac = min_rom_frac
        self.lockout_pos_tol_frac = lockout_pos_tol_frac
        self.min_rep_duration_s = min_rep_duration_s
        self.top_ref_tau_s = top_ref_tau_s
        self.max_dt_s = max_dt_s

        self._phase = _Phase.TOP
        self._active = False
        self._rep_idx = 0
        self._rep_start_t: Optional[float] = None
        self._rep_start_y: Optional[float] = None
        self._rep_start_scale: Optional[float] = None
        self._rep_bottom_t: Optional[float] = None
        self._rep_bottom_y: Optional[float] = None
        self._settled_since: Optional[float] = None
        self._still_since: Optional[float] = None
        self._last_rep_end_t: Optional[float] = None

        self._prev_t: Optional[float] = None
        self._ema_hip: Optional[float] = None
        self._pos_hist: deque[tuple[float, float, float]] = deque()  # (t, ema_hip, scale)
        self._top_ref: Optional[float] = None
        self._scale_ref: Optional[float] = None

        self._dir_candidate: Optional[str] = None       # "down" | "up" | None
        self._dir_candidate_since: Optional[float] = None

        self._current_reps: list[RepEvent] = []

    def _scale(self, kp: np.ndarray) -> float:
        # True 2D Euclidean distance between mid-shoulder and mid-hip
        sx = (kp[L_SHOULDER, 0] + kp[R_SHOULDER, 0]) / 2.0
        sy = (kp[L_SHOULDER, 1] + kp[R_SHOULDER, 1]) / 2.0
        hx = (kp[L_HIP, 0] + kp[R_HIP, 0]) / 2.0
        hy = (kp[L_HIP, 1] + kp[R_HIP, 1]) / 2.0
        dist = float(np.hypot(hx - sx, hy - sy))
        return max(dist, 10.0)

    # -- internal helpers -----------------------------------------------

    def _windowed_velocity(self, t: float) -> Optional[float]:
        """Velocity over a multi-frame baseline instead of a single dt.

        Noise in the underlying position signal has ~constant magnitude
        regardless of how far back we look, but the denominator (elapsed
        time) grows with the window -- so estimated noise in the velocity
        shrinks roughly as 1/window, unlike a single-frame derivative whose
        denominator is pinned at ~1/fps.
        """
        if len(self._pos_hist) < 2:
            return None
        target_t = t - self.vel_window_s
        newest_t, newest_y, newest_scale = self._pos_hist[-1]
        old_t, old_y, old_scale = self._pos_hist[0]
        for sample_t, sample_y, sample_scale in self._pos_hist:
            if sample_t <= target_t:
                old_t, old_y, old_scale = sample_t, sample_y, sample_scale
            else:
                break
        elapsed = newest_t - old_t
        if old_t > target_t and elapsed < self.vel_window_s * 0.5:
            # Not enough history yet to trust a windowed estimate (e.g. right
            # after Set_Start or a tracking-gap reset) -- rather than fall
            # back to a noisy single-frame estimate, report "no signal".
            return None
        if elapsed <= 0:
            return None
        avg_scale = (old_scale + newest_scale) / 2.0
        return (newest_y - old_y) / elapsed / avg_scale

    def _debounce(self, t: float, moving_down: bool, moving_up: bool) -> tuple[bool, bool]:
        direction = "down" if moving_down else ("up" if moving_up else None)
        if direction != self._dir_candidate:
            self._dir_candidate = direction
            self._dir_candidate_since = t
        if direction is None or self._dir_candidate_since is None:
            return False, False
        held_long_enough = (t - self._dir_candidate_since) >= self.confirm_duration_s
        return (held_long_enough and direction == "down"), (held_long_enough and direction == "up")

    def _near_top_ref(self) -> bool:
        if self._top_ref is None:
            return True
        # Use the slowly-tracked scale reference, not the instantaneous
        # per-frame scale: a momentary tracking glitch (occlusion, a missed
        # keypoint) can make the live torso-scale reading collapse for a few
        # frames, which would otherwise make the lockout tolerance
        # (tol_frac * scale) collapse right along with it and make "settled"
        # spuriously unreachable.
        ref_scale = self._scale_ref if self._scale_ref is not None else 10.0
        return abs(self._ema_hip - self._top_ref) <= self.lockout_pos_tol_frac * ref_scale

    def _reset_rep_tracking(self) -> None:
        self._rep_start_t = None
        self._rep_start_y = None
        self._rep_start_scale = None
        self._rep_bottom_t = None
        self._rep_bottom_y = None
        self._settled_since = None

    def _update_bottom_tracking(self, t: float) -> None:
        # hip_y increases downward, so the deepest point is the running max.
        if self._rep_bottom_y is None or self._ema_hip > self._rep_bottom_y:
            self._rep_bottom_y = self._ema_hip
            self._rep_bottom_t = t

    def _rep_passes_gates(self, end_t: float) -> bool:
        """Amplitude/ROM gate + minimum duration gate, applied at completion."""
        if self._rep_start_t is None or self._rep_start_y is None or self._rep_start_scale is None:
            return False
        if end_t - self._rep_start_t < self.min_rep_duration_s:
            return False
        bottom_y = self._rep_bottom_y if self._rep_bottom_y is not None else self._rep_start_y
        depth = bottom_y - self._rep_start_y
        if depth < self.min_rom_frac * self._rep_start_scale:
            return False
        return True

    # -- main API ---------------------------------------------------------

    def step(self, t: float, keypoints) -> list[Event]:
        keypoints = np.asarray(keypoints, dtype=float)
        events: list[Event] = []
        hip_y = (keypoints[L_HIP, 1] + keypoints[R_HIP, 1]) / 2.0
        scale = self._scale(keypoints)

        if self._prev_t is None:
            self._prev_t = t
            self._ema_hip = hip_y
            self._top_ref = hip_y
            self._scale_ref = scale
            self._pos_hist.append((t, hip_y, scale))
            return events

        if t <= self._prev_t:
            return events  # out-of-order / duplicate timestamp

        dt = t - self._prev_t
        if dt > self.max_dt_s:
            # Large gap (dropped frames / occlusion / re-acquisition): don't
            # compute a "velocity" across the gap -- it would be physically
            # meaningless. Reset smoothing & the velocity-window history but
            # leave phase/rep-in-progress state alone; normal gating resumes
            # once enough fresh samples accumulate.
            self._prev_t = t
            self._ema_hip = hip_y
            self._pos_hist.clear()
            self._pos_hist.append((t, hip_y, scale))
            self._dir_candidate = None
            self._dir_candidate_since = None
            return events

        alpha = 1.0 - math.exp(-dt / self.pos_tau_s)
        self._ema_hip = self._ema_hip + alpha * (hip_y - self._ema_hip)
        self._prev_t = t

        self._pos_hist.append((t, self._ema_hip, scale))
        cutoff = t - self.vel_window_s * 3
        while len(self._pos_hist) > 2 and self._pos_hist[0][0] < cutoff:
            self._pos_hist.popleft()

        # Track the "standing" position/scale with an always-on *asymmetric*
        # baseline tracker -- NOT gated on being classified as TOP.
        #
        # An earlier version only updated top_ref/scale_ref while phase ==
        # TOP. That has a deadlock: if the torso-scale estimate collapses for
        # an extended stretch (sustained occlusion, forward lean, a tracking
        # glitch), velocity readings normalized by that shrunken scale get
        # inflated, the FSM never settles long enough to re-enter TOP, and so
        # top_ref/scale_ref -- stuck at their old, now-stale values -- never
        # get the chance to adapt. Chasing your own tail.
        #
        # Fix: update every frame, but asymmetrically. A hip position higher
        # than the current reference (smaller hip_y => more "standing") is
        # adopted quickly, since observing a taller position is strong
        # evidence of where lockout actually is. A lower position is bled in
        # slowly, so a rep-in-progress doesn't drag the reference down with
        # it, while still letting a genuine, sustained change (camera moved,
        # lifter repositioned) eventually get absorbed rather than wedging
        # the FSM open forever. Same logic for scale: a larger (clearer,
        # more upright) reading is trusted quickly; a smaller one (more
        # likely partial occlusion/lean) is bled in slowly.
        fast_alpha = 1.0 - math.exp(-dt / (self.top_ref_tau_s * 0.2))
        slow_alpha = 1.0 - math.exp(-dt / (self.top_ref_tau_s * 5.0))

        if self._top_ref is None:
            self._top_ref = self._ema_hip
        else:
            top_alpha = fast_alpha if self._ema_hip < self._top_ref else slow_alpha
            self._top_ref += top_alpha * (self._ema_hip - self._top_ref)

        if self._scale_ref is None:
            self._scale_ref = scale
        else:
            scale_alpha = fast_alpha if scale > self._scale_ref else slow_alpha
            self._scale_ref += scale_alpha * (scale - self._scale_ref)

        v = self._windowed_velocity(t)
        if v is None:
            return events

        moving_down = v > self.v_thresh
        moving_up = v < -self.v_thresh
        vel_settled = abs(v) < self.v_settle
        confirmed_down, confirmed_up = self._debounce(t, moving_down, moving_up)
        settled = vel_settled and self._near_top_ref()

        if self._phase in (_Phase.DESCENDING, _Phase.ASCENDING):
            self._update_bottom_tracking(t)

        # 1. Initiate Rep Descent (debounced -- a single noisy sample can't trigger this)
        if self._phase == _Phase.TOP and confirmed_down:
            if self._last_rep_end_t is None or t - self._last_rep_end_t >= self.min_rep_gap_s:
                if not self._active:
                    self._active = True
                    self._current_reps = []
                    events.append(SetStartEvent(t))
                self._phase = _Phase.DESCENDING
                # Back-date to when downward motion actually began, not the
                # (later) moment it was confirmed.
                self._rep_start_t = self._dir_candidate_since if self._dir_candidate_since is not None else t
                self._rep_start_y = self._ema_hip
                # Prefer the stable, slowly-tracked scale reference over the
                # live per-frame scale for the same reason as _near_top_ref.
                self._rep_start_scale = self._scale_ref if self._scale_ref is not None else scale
                self._rep_bottom_y = self._ema_hip
                self._rep_bottom_t = self._rep_start_t
                self._settled_since = None

        # 2. Turnaround at bottom (debounced)
        elif self._phase == _Phase.DESCENDING and confirmed_up:
            self._phase = _Phase.ASCENDING

        # 3. Complete Ascending Rep
        elif self._phase == _Phase.ASCENDING:
            if settled:
                if self._settled_since is None:
                    self._settled_since = t
                elif t - self._settled_since >= self.settle_hold_s:
                    if self._rep_passes_gates(t):
                        self._rep_idx += 1
                        bottom = self._rep_bottom_t if self._rep_bottom_t is not None else \
                            (self._rep_start_t + t) / 2
                        rep = RepEvent(self._rep_idx, self._rep_start_t, bottom, t)
                        self._current_reps.append(rep)
                        self._last_rep_end_t = t
                        events.append(rep)
                    # Whether accepted or discarded as noise, we're back at
                    # the top now -- reset and keep watching.
                    self._phase = _Phase.TOP
                    self._reset_rep_tracking()
            # Touch-and-go descent into next rep (no full lockout pause)
            elif confirmed_down and self._rep_bottom_t is not None:
                if self._rep_passes_gates(t):
                    self._rep_idx += 1
                    rep = RepEvent(self._rep_idx, self._rep_start_t, self._rep_bottom_t, t)
                    self._current_reps.append(rep)
                    self._last_rep_end_t = t
                    events.append(rep)
                    self._rep_start_t = t
                    self._rep_start_y = self._ema_hip
                    self._rep_start_scale = self._scale_ref if self._scale_ref is not None else scale
                    self._rep_bottom_y = self._ema_hip
                    self._rep_bottom_t = t
                    self._phase = _Phase.DESCENDING
                    self._settled_since = None
                else:
                    # Too shallow/fast to be a real rep boundary -- most
                    # likely noise right near the bottom. Keep tracking the
                    # same candidate rep rather than splitting it in two.
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
                if self._rep_passes_gates(t):
                    self._rep_idx += 1
                    bottom = self._rep_bottom_t if self._rep_bottom_t is not None else \
                        (self._rep_start_t + t) / 2
                    rep = RepEvent(self._rep_idx, self._rep_start_t, bottom, t)
                    self._current_reps.append(rep)
                    events.append(rep)

            ev = SetEndEvent(t, list(self._current_reps))
            self._active = False
            self._rep_idx = 0
            self._current_reps = []
            events.append(ev)
        return events
