"""Tests select_person_idx directly -- no real model needed. Reproduces the
exact real-world bug found on real footage: a closer lifter whose box briefly
shrinks (e.g. squat bottom) should NOT lose the track to a farther, steadier
background person."""
import numpy as np
from perception.pose import select_person_idx, L_HIP, R_HIP


def _make_kp(hip_xy):
    kp = np.zeros((17, 3))
    kp[L_HIP, :2] = hip_xy
    kp[R_HIP, :2] = hip_xy
    return kp


def test_first_frame_picks_largest_box_with_no_history():
    boxes = np.array([[0, 0, 100, 100], [0, 0, 400, 400]])  # 2nd is bigger
    kpts = np.stack([_make_kp((50, 50)), _make_kp((200, 200))])
    idx = select_person_idx(boxes, kpts, last_kp=None, frame_wh=(1280, 720))
    assert idx == 1


def test_sticks_to_previous_track_even_if_smaller_box():
    # lifter (idx 0) was at (100,100), their box shrinks (squat bottom);
    # background person (idx 1) is far away with a bigger box
    boxes = np.array([[80, 80, 130, 160], [900, 500, 1100, 700]])
    kpts = np.stack([_make_kp((105, 120)), _make_kp((1000, 600))])
    last_kp = _make_kp((100, 100))
    idx = select_person_idx(boxes, kpts, last_kp=last_kp, frame_wh=(1280, 720))
    assert idx == 0  # stays on the lifter, not the bigger far-away box


def test_reacquires_largest_box_when_track_is_truly_lost():
    # nobody is anywhere near where the lifter last was (e.g. a hard cut)
    boxes = np.array([[900, 500, 1000, 650], [950, 500, 1200, 700]])
    kpts = np.stack([_make_kp((950, 575)), _make_kp((1075, 600))])
    last_kp = _make_kp((100, 100))
    idx = select_person_idx(boxes, kpts, last_kp=last_kp, frame_wh=(1280, 720))
    assert idx == 1  # falls back to the larger box since both are "lost" anyway


def test_single_candidate_always_wins():
    boxes = np.array([[0, 0, 50, 50]])
    kpts = np.stack([_make_kp((25, 25))])
    idx = select_person_idx(boxes, kpts, last_kp=_make_kp((500, 500)), frame_wh=(1280, 720))
    assert idx == 0
