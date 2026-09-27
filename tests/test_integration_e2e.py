import numpy as np
from contracts.models import SetRecord, SetReport
from perception.export import export_set_record
from perception.pose import L_HIP, R_HIP, L_SHOULDER, R_SHOULDER, L_KNEE, R_KNEE
from analytics.report import ReportGenerator
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

class _MockFrame:
    def __init__(self, idx: int, t: float, image: np.ndarray):
        self.idx = idx
        self.t = t
        self.image = image

class _MockSquatSource:
    fps = 30.0

    def __init__(self, *args, **kwargs):
        self.frames = []
        dt = 1.0 / self.fps
        t = 0.0
        idx = 0
        standing_y = 100.0
        bottom_y = 220.0
        knee_y = 200.0  # Hip passing 200 drops below knee (depth achieved)

        # 1. Lead-in standing still (1.5s)
        while t < 1.5:
            self.frames.append(_MockFrame(idx, t, np.zeros((480, 640, 3), dtype=np.uint8)))
            t += dt
            idx += 1

        # 2. Perform 2 reps (each rep 1.6s down-and-up, with 0.4s pause at top)
        for _ in range(2):
            n_motion = int(1.6 * self.fps)
            for i in range(n_motion):
                self.frames.append(_MockFrame(idx, t, np.zeros((480, 640, 3), dtype=np.uint8)))
                t += dt
                idx += 1
            n_pause = int(0.4 * self.fps)
            for _ in range(n_pause):
                self.frames.append(_MockFrame(idx, t, np.zeros((480, 640, 3), dtype=np.uint8)))
                t += dt
                idx += 1

        # 3. Post-set standing still (3.2s -> triggers SetEndEvent)
        end_motion_t = t
        while t < end_motion_t + 3.2:
            self.frames.append(_MockFrame(idx, t, np.zeros((480, 640, 3), dtype=np.uint8)))
            t += dt
            idx += 1

    def __iter__(self):
        return iter(self.frames)

    def release(self):
        pass

class _MockSquatPose:
    def __init__(self, *args, **kwargs):
        self.fps = 30.0

    def infer(self, image: np.ndarray, t: float) -> np.ndarray:
        # Recreate hip and knee positions synchronized with time
        kp = np.zeros((17, 3), dtype=float)
        kp[:, 2] = 0.95  # high confidence

        standing_y = 100.0
        bottom_y = 220.0
        knee_y = 200.0
        shoulder_y = 40.0

        # Torso setup
        kp[L_SHOULDER, 1] = kp[R_SHOULDER, 1] = shoulder_y
        kp[L_SHOULDER, 0] = kp[R_SHOULDER, 0] = 300.0
        kp[L_KNEE, 1] = kp[R_KNEE, 1] = knee_y
        kp[L_KNEE, 0] = kp[R_KNEE, 0] = 300.0

        # Check motion windows
        hip_y = standing_y
        if 1.5 <= t < 3.5:
            phase = (t - 1.5) / 1.6
            if phase <= 1.0:
                hip_y = standing_y + (bottom_y - standing_y) * np.sin(np.pi * phase)
        elif 3.5 <= t < 5.5:
            phase = (t - 3.5) / 1.6
            if phase <= 1.0:
                hip_y = standing_y + (bottom_y - standing_y) * np.sin(np.pi * phase)

        kp[L_HIP, 1] = kp[R_HIP, 1] = hip_y
        kp[L_HIP, 0] = kp[R_HIP, 0] = 300.0

        # Set wrist coordinates near the bar to verify the wrist proxy fallback
        kp[9, 1] = kp[10, 1] = hip_y - 20.0
        kp[9, 0] = kp[10, 0] = 300.0
        return kp

def test_full_pipeline_end_to_end(monkeypatch):
    import perception.export as export_mod
    monkeypatch.setattr(export_mod, "FrameSource", _MockSquatSource)
    monkeypatch.setattr(export_mod, "PoseEstimator", _MockSquatPose)

    # 1. Run perception export on simulated squat video
    record = export_mod.export_set_record(
        source="test_simulated_squat.mp4",
        exercise="back_squat",
        camera_view="side",
        load_kg=120.0,
    )

    # Verify Role A state machine output
    assert isinstance(record, SetRecord)
    assert len(record.frames) > 50
    assert len(record.reps) == 2, f"Expected 2 segmented reps, got {len(record.reps)}"
    assert record.reps[0].start_t < record.reps[0].bottom_t < record.reps[0].end_t

    # 2. Ingest into Role B Analytics & FastAPI backend
    response = client.post("/sets/process", json=record.model_dump())
    assert response.status_code == 200

    report = SetReport(**response.json())
    assert report.total_reps == 2
    assert report.load_kg == 120.0
    assert len(report.reps) == 2

    # Verify Kinematic calculations
    for rep in report.reps:
        assert rep.mcv_mps > 0.0, "Concentric MCV must be positive"
        assert rep.concentric_tut_s > 0.0
        assert rep.depth_achieved is True  # Max depth 220 > knee 200

    # Verify RPE estimation & cues
    assert report.estimated_rpe is not None
    assert len(report.micro_cues) >= 1