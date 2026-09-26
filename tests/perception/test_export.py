"""Tests export_set_record against a fake PoseEstimator/FrameSource so no real
model or video is needed. Confirms the SetRecord shape is always contract-valid."""
import numpy as np
import pytest

from contracts.models import SetRecord
from perception import export as export_mod
from perception.capture import Frame


class _FakeSource:
    fps = 30.0
    def __init__(self, *_a, **_k):
        self._frames = [Frame(i, i / self.fps, np.zeros((4, 4, 3), np.uint8)) for i in range(5)]
    def __iter__(self):
        return iter(self._frames)
    def release(self):
        pass


class _FakePose:
    def __init__(self, *_a, **_k):
        pass
    def infer(self, _image, _t):
        return np.tile(np.array([1.0, 2.0, 0.9]), (17, 1))


def test_export_produces_valid_set_record(monkeypatch):
    monkeypatch.setattr(export_mod, "FrameSource", _FakeSource)
    monkeypatch.setattr(export_mod, "PoseEstimator", _FakePose)

    record = export_mod.export_set_record("fake.mp4", "back_squat", "side", load_kg=100)

    assert isinstance(record, SetRecord)
    assert record.exercise == "back_squat"
    assert record.fps == 30.0
    assert len(record.frames) == 5
    assert record.frames[0].keypoints[0] == (1.0, 2.0, 0.9)
    # round-trips through JSON the same way contracts expect
    assert SetRecord.model_validate_json(record.model_dump_json()) == record


def test_export_raises_on_no_pose(monkeypatch):
    monkeypatch.setattr(export_mod, "FrameSource", _FakeSource)

    class _NoPose(_FakePose):
        def infer(self, _i, _t):
            return None

    monkeypatch.setattr(export_mod, "PoseEstimator", _NoPose)
    with pytest.raises(RuntimeError):
        export_mod.export_set_record("fake.mp4", "back_squat", "side")
