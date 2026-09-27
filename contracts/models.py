from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator

class Keypoint(BaseModel):
  x: float
  y: float
  confidence: float = 1.0

  @model_validator(mode="before")
  @classmethod
  def parse_tuple_or_list(cls, data: Any):
    if isinstance(data, (list, tuple)):
      if len(data) >= 3:
        return {
            "x": float(data[0]),
            "y": float(data[1]),
            "confidence": float(data[2]),
        }
      elif len(data) == 2:
        return {"x": float(data[0]), "y": float(data[1]), "confidence": 1.0}
    return data

  def __iter__(self):
    yield self.x
    yield self.y
    yield self.confidence

  def __getitem__(self, item: int) -> float:
    if item == 0:
      return self.x
    elif item == 1:
      return self.y
    elif item == 2:
      return self.confidence
    raise IndexError("Keypoint index out of range (0-2)")

  def __eq__(self, other: Any) -> bool:
    if isinstance(other, (list, tuple)):
      if len(other) == 3:
        return (self.x, self.y, self.confidence) == (
            float(other[0]),
            float(other[1]),
            float(other[2]),
        )
      elif len(other) == 2:
        return (self.x, self.y) == (float(other[0]), float(other[1]))
      return False
    return super().__eq__(other)

class FrameData(BaseModel):
    t: float
    frame_idx: int
    keypoints: List[Keypoint] = Field(
        ..., min_length=17, max_length=17, description="17 COCO keypoints"
    )
    bar_left: Optional[List[float]] = None
    bar_right: Optional[List[float]] = None

class RepInterval(BaseModel):
    rep_idx: int
    start_t: float
    bottom_t: float
    end_t: float

class ChronometerState(str, Enum):
    ACTIVE = "active"
    AMBER = "amber"
    PAUSED = "paused"

class IsometricSample(BaseModel):
    t: float
    angle_error_deg: float
    valid: bool = True

class IsometricReport(BaseModel):
    exercise: str = "plank"
    total_elapsed_s: float
    true_tut_s: float
    paused_duration_s: float
    pause_count: int
    form_adherence_pct: float
    final_state: ChronometerState

class RepReport(BaseModel):
    rep_idx: int
    concentric_tut_s: float
    mcv_mps: float
    peak_velocity_mps: float
    velocity_loss_pct: float
    bar_drift_mm: float
    depth_achieved: Optional[bool] = None
    min_hip_angle_deg: Optional[float] = None
    max_trunk_angle_deg: Optional[float] = None

class RepSymmetryReport(BaseModel):
    rep_idx: int
    mean_bar_tilt_deg: float
    max_bar_tilt_deg: float
    lr_drive_asymmetry_pct: float
    sticking_point_height_pct: Optional[float] = None
    sticking_point_tilt_deg: Optional[float] = None
    phase_asymmetry_heatmap: Dict[str, float] = Field(default_factory=dict)

class SetSymmetryReport(BaseModel):
    overall_mean_tilt_deg: float
    max_tilt_rep_idx: int
    dominant_side: str  # "left", "right", or "balanced"
    reps: List[RepSymmetryReport]

class SetReport(BaseModel):
    schema_version: str = "1.0.0"
    set_id: str
    exercise: str
    load_kg: Optional[float] = None
    total_reps: int
    overall_velocity_loss_pct: float
    estimated_rpe: Optional[float] = None
    micro_cues: List[str] = Field(default_factory=list)
    reps: List[RepReport]
    symmetry: Optional[SetSymmetryReport] = None
    disclaimer: str = (
        "Velocity and RPE metrics are estimated flags and trends, not clinical"
        " diagnostics."
    )

class SetRecord(BaseModel):
    schema_version: str = "1.0.0"
    set_id: str
    exercise: str
    camera_view: str
    fps: float
    start_t: float
    end_t: float
    clip_path: str
    load_kg: Optional[float] = None
    px_per_mm: Optional[float] = None
    reps: List[RepInterval] = Field(default_factory=list)
    frames: List[FrameData] = Field(default_factory=list)