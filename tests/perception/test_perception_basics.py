import numpy as np
from perception.capture import RingBuffer
from perception.pose import OneEuroFilter, joint_angle


def test_ring_buffer_drops_old_frames():
    rb = RingBuffer(seconds=2.0, encode=False)
    img = np.zeros((4, 4, 3), np.uint8)
    for i in range(300):               # 5 s at 60 fps
        rb.push(i / 60, img)
    assert rb.span <= 2.0 + 1e-6
    assert len(rb) <= 122


def test_ring_buffer_range_and_encode():
    rb = RingBuffer(seconds=30, encode=True)
    img = np.full((32, 32, 3), 128, np.uint8)
    for i in range(10):
        rb.push(i * 0.1, img)
    got = rb.get_range(0.2, 0.5)
    assert [round(t, 1) for t, _ in got] == [0.2, 0.3, 0.4, 0.5]
    assert got[0][1].shape == (32, 32, 3)


def test_one_euro_reduces_jitter():
    rng = np.random.default_rng(0)
    f = OneEuroFilter(min_cutoff=1.0, beta=0.0)
    noisy = 100 + rng.normal(0, 2, size=(300, 1))
    out = np.array([f(noisy[i], i / 60) for i in range(300)])
    assert out[60:].std() < noisy[60:].std() * 0.5


def test_joint_angle():
    assert abs(joint_angle((1, 0), (0, 0), (0, 1)) - 90) < 1e-6
    assert abs(joint_angle((1, 0), (0, 0), (-1, 0)) - 180) < 1e-6
