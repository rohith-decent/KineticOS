export interface RepReport {
  rep_idx: number;
  concentric_tut_s: number;
  mcv_mps: number;
  peak_velocity_mps: number;
  velocity_loss_pct: number;
  bar_drift_mm: number;
  depth_achieved: boolean | null;
  min_hip_angle_deg: number | null;
  max_trunk_angle_deg: number | null;
}

export interface RepSymmetryReport {
  rep_idx: number;
  mean_bar_tilt_deg: number;
  max_bar_tilt_deg: number;
  lr_drive_asymmetry_pct: number;
  sticking_point_height_pct: number | null;
  sticking_point_tilt_deg: number | null;
  phase_asymmetry_heatmap: Record<string, number>;
}

export interface SetSymmetryReport {
  overall_mean_tilt_deg: number;
  max_tilt_rep_idx: number;
  dominant_side: 'left' | 'right' | 'balanced';
  reps: RepSymmetryReport[];
}

export interface SetReport {
  schema_version: string;
  set_id: string;
  exercise: string;
  load_kg: number;
  total_reps: number;
  overall_velocity_loss_pct: number;
  estimated_rpe: number | null;
  micro_cues: string[];
  reps: RepReport[];
  symmetry?: SetSymmetryReport | null;
  disclaimer: string;
}

export interface IsometricReport {
  exercise: string;
  total_elapsed_s: number;
  true_tut_s: number;
  paused_duration_s: number;
  pause_count: number;
  form_adherence_pct: number;
  final_state: 'active' | 'amber' | 'paused';
}