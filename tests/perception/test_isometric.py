import math
import numpy as np
from perception.isometric import alignment_error_deg, IsometricStream
from perception.pose import L_SHOULDER, R_SHOULDER, L_HIP, R_HIP, L_ANKLE, R_ANKLE


def _plank_kp(hip_sag: float = 0.0, conf: float = 0.9) -> np.ndarray:
    """Straight line shoulder(0,0) -- hip(50,hip_sag) -- ankle(100,0), left side only
    confident. hip_sag=0 -> perfectly straight (180 deg, error 0)."""
    kp = np.zeros((17, 3))
    kp[L_SHOULDER] = (0, 0, conf)
    kp[L_HIP] = (50, hip_sag, conf)
    kp[L_ANKLE] = (100, 0, conf)
    kp[R_SHOULDER] = (0, 0, 0.05)   # low-confidence right side, should be ignored
    kp[R_HIP] = (50, hip_sag, 0.05)
    kp[R_ANKLE] = (100, 0, 0.05)
    return kp


def test_perfect_plank_has_near_zero_error():
    err = alignment_error_deg(_plank_kp(hip_sag=0.0))
    assert err < 1e-6


def test_sagging_hips_produce_positive_error():
    err = alignment_error_deg(_plank_kp(hip_sag=20.0))
    assert err > 5.0


def test_more_sag_means_more_error():
    small = alignment_error_deg(_plank_kp(hip_sag=10.0))
    large = alignment_error_deg(_plank_kp(hip_sag=30.0))
    assert large > small


def test_returns_none_when_both_sides_low_confidence():
    kp = _plank_kp(hip_sag=0.0)
    kp[L_SHOULDER, 2] = kp[L_HIP, 2] = kp[L_ANKLE, 2] = 0.05  # now both sides weak
    assert alignment_error_deg(kp) is None


def test_isometric_stream_marks_invalid_when_no_confident_side():
    kp = _plank_kp(hip_sag=0.0)
    kp[L_SHOULDER, 2] = kp[L_HIP, 2] = kp[L_ANKLE, 2] = 0.05
    sample = IsometricStream().step(1.23, kp)
    assert sample.valid is False
    assert math.isnan(sample.angle_error_deg)


def test_isometric_stream_valid_sample_shape():
    sample = IsometricStream().step(1.23, _plank_kp(hip_sag=15.0))
    assert sample.valid is True
    assert sample.t == 1.23
    assert sample.angle_error_deg > 0
