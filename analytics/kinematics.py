from typing import Any, Dict, List, Optional
from contracts.models import RepInterval, RepReport, SetRecord, SetReport
import numpy as np

# COCO-17 Keypoint Indices
LEFT_SHOULDER, RIGHT_SHOULDER = 5, 6
LEFT_WRIST, RIGHT_WRIST = 9, 10
LEFT_HIP, RIGHT_HIP = 11, 12
LEFT_KNEE, RIGHT_KNEE = 13, 14
LEFT_ANKLE, RIGHT_ANKLE = 15, 16


class KinematicsEngine:

  @staticmethod
  def _extract_bar_trajectory(set_record: SetRecord) -> Dict[str, np.ndarray]:
    times: List[float] = []
    x_coords: List[float] = []
    y_coords: List[float] = []

    for frame in set_record.frames:
      coords = frame.bar_left or frame.bar_right

      # Wrist fallback: if bar tracker coordinates are null, use the most confident wrist as proxy
      if not coords and frame.keypoints and len(frame.keypoints) > 10:
        wrist_l = frame.keypoints[LEFT_WRIST]
        wrist_r = frame.keypoints[RIGHT_WRIST]
        wrist = wrist_l if wrist_l.confidence >= wrist_r.confidence else wrist_r
        if wrist.confidence > 0.3:
          coords = [wrist.x, wrist.y]

      if coords:
        times.append(frame.t)
        x_coords.append(coords[0])
        y_coords.append(coords[1])

    return {
        "t": np.array(times, dtype=float),
        "x": np.array(x_coords, dtype=float),
        "y": np.array(y_coords, dtype=float),
    }

  @staticmethod
  def _get_active_joint(frame_keypoints, left_idx: int, right_idx: int):
    if not frame_keypoints or len(frame_keypoints) <= max(left_idx, right_idx):
      return None
    kp_l = frame_keypoints[left_idx]
    kp_r = frame_keypoints[right_idx]
    # Choose keypoint with higher detection confidence
    return kp_l if kp_l.confidence >= kp_r.confidence else kp_r

  @classmethod
  def _calculate_depth_and_trunk(
      cls, set_record: SetRecord, rep: RepInterval
  ) -> Dict[str, Optional[float]]:
    # Find frame closest to the rep turnaround/bottom timestamp
    closest_frame = min(
        set_record.frames,
        key=lambda f: abs(f.t - rep.bottom_t),
        default=None,
    )
    if not closest_frame or not closest_frame.keypoints:
      return {"depth_achieved": None, "max_trunk_angle_deg": None}

    kps = closest_frame.keypoints
    hip = cls._get_active_joint(kps, LEFT_HIP, RIGHT_HIP)
    knee = cls._get_active_joint(kps, LEFT_KNEE, RIGHT_KNEE)
    shoulder = cls._get_active_joint(kps, LEFT_SHOULDER, RIGHT_SHOULDER)

    depth_flag = None
    trunk_angle = None

    if hip and knee:
      # In screen space, y increases downwards; depth is valid if hip crease reaches level or below knee
      depth_flag = bool(hip.y >= knee.y)

    if hip and shoulder:
      # Torso forward lean relative to true vertical axis (0 deg = vertical)
      dx = shoulder.x - hip.x
      dy = hip.y - shoulder.y  # Upward distance
      rad = np.arctan2(abs(dx), max(dy, 1e-5))
      trunk_angle = round(float(np.degrees(rad)), 1)

    return {"depth_achieved": depth_flag, "max_trunk_angle_deg": trunk_angle}

  @classmethod
  def calculate_rep_kinematics(
      cls, set_record: SetRecord, rep: RepInterval
  ) -> RepReport:
    traj = cls._extract_bar_trajectory(set_record)
    t_arr, x_arr, y_arr = traj["t"], traj["x"], traj["y"]

    concentric_mask = (t_arr >= rep.bottom_t) & (t_arr <= rep.end_t)
    biomech = cls._calculate_depth_and_trunk(set_record, rep)

    if np.sum(concentric_mask) < 2:
      return RepReport(
          rep_idx=rep.rep_idx,
          concentric_tut_s=0.0,
          mcv_mps=0.0,
          peak_velocity_mps=0.0,
          velocity_loss_pct=0.0,
          bar_drift_mm=0.0,
          depth_achieved=biomech["depth_achieved"],
          max_trunk_angle_deg=biomech["max_trunk_angle_deg"],
      )

    t_conc = t_arr[concentric_mask]
    x_conc = x_arr[concentric_mask]
    y_conc = y_arr[concentric_mask]

    # Guard against uncalibrated scale factor (fallback to 1.0 px/mm)
    scale = (
        set_record.px_per_mm
        if (set_record.px_per_mm and set_record.px_per_mm > 0)
        else 1.0
    )

    delta_t = float(t_conc[-1] - t_conc[0])
    displacement_px = float(y_conc[0] - y_conc[-1])
    displacement_m = (displacement_px / scale) / 1000.0

    mcv = float(displacement_m / delta_t) if delta_t > 0 else 0.0

    dy = -np.diff(y_conc)
    dt = np.diff(t_conc)
    dt[dt == 0] = 1e-6
    inst_v_mps = (dy / scale / 1000.0) / dt
    peak_v = float(np.max(inst_v_mps)) if len(inst_v_mps) > 0 else mcv

    horizontal_drift_px = float(np.max(x_conc) - np.min(x_conc))
    drift_mm = horizontal_drift_px / scale

    return RepReport(
        rep_idx=rep.rep_idx,
        concentric_tut_s=round(delta_t, 2),
        mcv_mps=round(mcv, 3),
        peak_velocity_mps=round(peak_v, 3),
        velocity_loss_pct=0.0,  # Populated in analyze_set
        bar_drift_mm=round(drift_mm, 1),
        depth_achieved=biomech["depth_achieved"],
        max_trunk_angle_deg=biomech["max_trunk_angle_deg"],
    )

  @classmethod
  def analyze_set(cls, set_record: SetRecord) -> SetReport:
    rep_reports: List[RepReport] = [
        cls.calculate_rep_kinematics(set_record, rep) for rep in set_record.reps
    ]

    first_rep_mcv = rep_reports[0].mcv_mps if rep_reports else 0.0
    for rep_rep in rep_reports:
      if first_rep_mcv > 0:
        loss = ((first_rep_mcv - rep_rep.mcv_mps) / first_rep_mcv) * 100.0
        rep_rep.velocity_loss_pct = round(max(0.0, loss), 1)

    total_loss = rep_reports[-1].velocity_loss_pct if rep_reports else 0.0

    return SetReport(
        set_id=set_record.set_id,
        exercise=set_record.exercise,
        load_kg=set_record.load_kg,
        total_reps=len(rep_reports),
        overall_velocity_loss_pct=total_loss,
        reps=rep_reports,
    )