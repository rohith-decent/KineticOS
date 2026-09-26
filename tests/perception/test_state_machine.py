import numpy as np
from perception.state_machine import SetStateMachine, SetStartEvent, RepEvent, SetEndEvent
from perception.pose import L_HIP, R_HIP, L_SHOULDER, R_SHOULDER


def make_kp(hip_y: float, shoulder_y: float = 0.0) -> np.ndarray:
    kp = np.zeros((17, 3))
    kp[:, 2] = 1.0
    kp[L_HIP, 1] = kp[R_HIP, 1] = hip_y
    kp[L_SHOULDER, 1] = kp[R_SHOULDER, 1] = shoulder_y
    kp[L_HIP, 0], kp[R_HIP, 0] = -20, 20   # arbitrary x, unused by the state machine
    return kp


def synth_squat_trajectory(n_reps: int, fps: float = 30.0, rep_down_up_s: float = 1.6,
                            top_pause_s: float = 0.3, standing_hip_y: float = 100.0,
                            bottom_hip_y: float = 160.0, lead_in_s: float = 3.5, trail_s: float = 3.5):
    """torso length fixed at 100 (standing_hip_y - shoulder_y=0). Each rep is a
    half-sine down-and-up with a brief lockout pause before the next rep, which
    is how real lifting actually looks (bar-touch-and-go aside) -- chaining reps
    with zero pause at the top would never let the state machine see a settled
    TOP phase between them."""
    dt = 1.0 / fps
    ts, hips = [], []
    t = 0.0
    while t < lead_in_s:
        ts.append(t); hips.append(standing_hip_y); t += dt
    for _ in range(n_reps):
        n_motion = int(rep_down_up_s * fps)
        for i in range(n_motion):
            phase = i / n_motion
            y = standing_hip_y + (bottom_hip_y - standing_hip_y) * np.sin(np.pi * phase)
            hips.append(y); ts.append(t); t += dt
        n_pause = int(top_pause_s * fps)
        for _ in range(n_pause):
            hips.append(standing_hip_y); ts.append(t); t += dt
    end_of_motion_t = t
    while t < end_of_motion_t + trail_s:
        ts.append(t); hips.append(standing_hip_y); t += dt
    return ts, hips


def run(sm: SetStateMachine, ts, hips):
    all_events = []
    for t, hy in zip(ts, hips):
        all_events += sm.step(t, make_kp(hy))
    all_events += sm.finalize(ts[-1])
    return all_events


def test_detects_set_start_reps_and_set_end():
    ts, hips = synth_squat_trajectory(n_reps=3)
    sm = SetStateMachine()
    events = run(sm, ts, hips)

    starts = [e for e in events if isinstance(e, SetStartEvent)]
    reps = [e for e in events if isinstance(e, RepEvent)]
    ends = [e for e in events if isinstance(e, SetEndEvent)]

    assert len(starts) == 1
    assert len(reps) == 3
    assert [r.rep_idx for r in reps] == [1, 2, 3]
    assert len(ends) == 1
    assert ends[0].t > starts[0].t
    # bottom must fall strictly between start and end for every rep
    for r in reps:
        assert r.start_t < r.bottom_t < r.end_t


def test_no_movement_emits_nothing():
    ts = list(np.arange(0, 5, 1 / 30))
    hips = [100.0] * len(ts)
    sm = SetStateMachine()
    events = run(sm, ts, hips)
    assert events == []


def test_two_separate_sets_are_not_merged():
    ts1, hips1 = synth_squat_trajectory(n_reps=2, lead_in_s=1.0, trail_s=3.5)
    gap_t = ts1[-1] + 1 / 30
    ts2_raw, hips2 = synth_squat_trajectory(n_reps=2, lead_in_s=1.0, trail_s=1.0)
    ts2 = [gap_t + t for t in ts2_raw]

    sm = SetStateMachine()
    events = run(sm, ts1 + ts2, hips1 + hips2)
    ends = [e for e in events if isinstance(e, SetEndEvent)]
    starts = [e for e in events if isinstance(e, SetStartEvent)]
    assert len(starts) == 2
    assert len(ends) == 2
    assert len(ends[0].reps) == 2
