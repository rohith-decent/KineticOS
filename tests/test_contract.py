from contracts.models import FrameData

def test_frame_requires_17_keypoints():
    f = FrameData(t=0, frame_idx=0, keypoints=[(0, 0, 1)] * 17)
    assert len(f.keypoints) == 17
