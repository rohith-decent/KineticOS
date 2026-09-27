import React from 'react';
import type { SetSymmetryReport } from '../types';
import { Scale, Target } from 'lucide-react';

interface Props {
  symmetry: SetSymmetryReport;
}

export const SymmetryHeatmap: React.FC<Props> = ({ symmetry }) => {
  return (
    <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: '1.25rem', background: '#ffffff', marginBottom: '1.5rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
        <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#111827', display: 'flex', alignItems: 'center', gap: 8 }}>
          <Scale size={20} color="#4f46e5" /> Bilateral Symmetry Analysis (Front View)
        </h3>
        <span
          style={{
            fontSize: '0.8rem',
            padding: '0.2rem 0.6rem',
            borderRadius: 999,
            fontWeight: 600,
            background: symmetry.dominant_side === 'balanced' ? '#dcfce7' : '#fee2e2',
            color: symmetry.dominant_side === 'balanced' ? '#15803d' : '#b91c1c',
          }}
        >
          {symmetry.dominant_side.toUpperCase()} DRIVE BIAS
        </span>
      </div>

      {/* Summary KPI Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
        <div style={{ background: '#f9fafb', padding: '0.75rem', borderRadius: 6, border: '1px solid #f3f4f6' }}>
          <span style={{ fontSize: '0.8rem', color: '#6b7280' }}>Mean Bar Tilt</span>
          <p style={{ margin: '0.2rem 0 0', fontSize: '1.2rem', fontWeight: 700, color: '#111827' }}>
            {symmetry.overall_mean_tilt_deg}°
          </p>
        </div>

        <div style={{ background: '#f9fafb', padding: '0.75rem', borderRadius: 6, border: '1px solid #f3f4f6' }}>
          <span style={{ fontSize: '0.8rem', color: '#6b7280' }}>Highest Tilt Rep</span>
          <p style={{ margin: '0.2rem 0 0', fontSize: '1.2rem', fontWeight: 700, color: '#111827' }}>
            Rep #{symmetry.max_tilt_rep_idx}
          </p>
        </div>

        <div style={{ background: '#f9fafb', padding: '0.75rem', borderRadius: 6, border: '1px solid #f3f4f6' }}>
          <span style={{ fontSize: '0.8rem', color: '#6b7280' }}>Drive Imbalance</span>
          <p style={{ margin: '0.2rem 0 0', fontSize: '1.2rem', fontWeight: 700, color: '#111827' }}>
            {symmetry.reps[0]?.lr_drive_asymmetry_pct ?? 0}%
          </p>
        </div>
      </div>

      {/* Rep-by-Rep Phase Heatmap Breakdown */}
      <h4 style={{ margin: '0 0 0.75rem', fontSize: '0.95rem', color: '#374151' }}>
        Phase Asymmetry & Sticking Point Heatmap
      </h4>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {symmetry.reps.map((rep) => {
          const heatmap = rep.phase_asymmetry_heatmap;
          return (
            <div key={rep.rep_idx} style={{ border: '1px solid #e5e7eb', borderRadius: 6, padding: '0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.85rem' }}>
                <span style={{ fontWeight: 600 }}>Rep #{rep.rep_idx}</span>
                <span style={{ color: '#4b5563', display: 'flex', alignItems: 'center', gap: 4 }}>
                  <Target size={14} /> Sticking Point at {rep.sticking_point_height_pct}% ROM ({rep.sticking_point_tilt_deg}°)
                </span>
              </div>

              {/* 3-Zone Phase Heatmap Visualizer */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.5rem', textAlign: 'center' }}>
                <div
                  style={{
                    padding: '0.5rem',
                    borderRadius: 4,
                    background: (heatmap.bottom_zone_tilt_deg || 0) > 2.0 ? '#fecaca' : '#e0e7ff',
                    color: (heatmap.bottom_zone_tilt_deg || 0) > 2.0 ? '#991b1b' : '#3730a3',
                    fontSize: '0.8rem',
                  }}
                >
                  <div style={{ fontWeight: 600 }}>Bottom (0-33%)</div>
                  <div>{heatmap.bottom_zone_tilt_deg ?? 0}° tilt</div>
                </div>

                <div
                  style={{
                    padding: '0.5rem',
                    borderRadius: 4,
                    background: (heatmap.mid_zone_tilt_deg || 0) > 2.0 ? '#fecaca' : '#e0e7ff',
                    color: (heatmap.mid_zone_tilt_deg || 0) > 2.0 ? '#991b1b' : '#3730a3',
                    fontSize: '0.8rem',
                  }}
                >
                  <div style={{ fontWeight: 600 }}>Mid-Drive (33-66%)</div>
                  <div>{heatmap.mid_zone_tilt_deg ?? 0}° tilt</div>
                </div>

                <div
                  style={{
                    padding: '0.5rem',
                    borderRadius: 4,
                    background: (heatmap.lockout_zone_tilt_deg || 0) > 2.0 ? '#fecaca' : '#e0e7ff',
                    color: (heatmap.lockout_zone_tilt_deg || 0) > 2.0 ? '#991b1b' : '#3730a3',
                    fontSize: '0.8rem',
                  }}
                >
                  <div style={{ fontWeight: 600 }}>Lockout (66-100%)</div>
                  <div>{heatmap.lockout_zone_tilt_deg ?? 0}° tilt</div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};