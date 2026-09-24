"""Shared data contract. Change only with both teammates' approval."""
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field

SCHEMA_VERSION = "0.1"
Point = tuple[float, float, float]  # x_px, y_px, confidence

class FrameData(BaseModel):
    t: float
    frame_idx: int
    keypoints: list[Point] = Field(min_length=17, max_length=17)
    bar_left: Optional[Point] = None
    bar_right: Optional[Point] = None

class Rep(BaseModel):
    rep_idx: int
    start_t: float
    bottom_t: float
    end_t: float

class SetRecord(BaseModel):
    schema_version: str = SCHEMA_VERSION
    set_id: str
    exercise: str
    camera_view: Literal["side", "front", "rear"]
    fps: float
    start_t: float
    end_t: float
    clip_path: Optional[str] = None
    load_kg: Optional[float] = None
    px_per_mm: Optional[float] = None
    reps: list[Rep]
    frames: list[FrameData]

class IsometricSample(BaseModel):
    t: float
    angle_error_deg: float
    valid: bool = True

class RepMetrics(BaseModel):
    rep_idx: int
    mcv_ms: float
    peak_v_ms: float
    depth_cm: Optional[float] = None
    bar_drift_cm: Optional[float] = None

class SetReport(BaseModel):
    set_id: str
    reps: list[RepMetrics]
    velocity_loss_pct: float
    true_tut_s: float
    tilt_delta_deg: Optional[float] = None
    asymmetry_pct: Optional[float] = None
    est_rpe: Optional[float] = None
    micro_cue: Optional[str] = None
    confidence: dict[str, float] = {}
