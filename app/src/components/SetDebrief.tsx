import React from 'react';
import type { SetReport } from '../types';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import { Activity, AlertTriangle, CheckCircle2, ShieldAlert } from 'lucide-react';

interface Props {
  report: SetReport;
}

export const SetDebrief: React.FC<Props> = ({ report }) => {
  const chartData = report.reps.map((r) => ({
    rep: `Rep ${r.rep_idx}`,
    mcv: r.mcv_mps,
    loss: r.velocity_loss_pct,
    drift: r.bar_drift_mm,
  }));

  return (
    <div style={{ padding: '1.5rem', fontFamily: 'system-ui, sans-serif', maxWidth: 900, margin: '0 auto' }}>
      {/* Top Header */}
      <div style={{ borderBottom: '1px solid #e5e7eb', paddingBottom: '1rem', marginBottom: '1.5rem' }}>
        <h1 style={{ margin: 0, fontSize: '1.75rem', fontWeight: 700, color: '#111827' }}>
          {report.exercise.replace('_', ' ').toUpperCase()} DEBRIEF
        </h1>
        <p style={{ margin: '0.25rem 0 0', color: '#6b7280' }}>
          Set ID: {report.set_id} | Load: <strong>{report.load_kg} kg</strong> | Total Reps: <strong>{report.total_reps}</strong>
        </p>
      </div>

      {/* KPI Stat Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
        <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: '1rem', background: '#f9fafb' }}>
          <span style={{ fontSize: '0.85rem', color: '#6b7280' }}>Rep 1 MCV</span>
          <h2 style={{ margin: '0.25rem 0 0', color: '#111827' }}>{report.reps[0]?.mcv_mps ?? 0} m/s</h2>
        </div>

        <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: '1rem', background: '#f9fafb' }}>
          <span style={{ fontSize: '0.85rem', color: '#6b7280' }}>Velocity Loss</span>
          <h2 style={{ margin: '0.25rem 0 0', color: report.overall_velocity_loss_pct > 25 ? '#dc2626' : '#111827' }}>
            {report.overall_velocity_loss_pct}%
          </h2>
        </div>

        <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: '1rem', background: '#f9fafb' }}>
          <span style={{ fontSize: '0.85rem', color: '#6b7280' }}>Estimated RPE</span>
          <h2 style={{ margin: '0.25rem 0 0', color: '#111827' }}>@{report.estimated_rpe ?? '--'}</h2>
        </div>

        <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: '1rem', background: '#f9fafb' }}>
          <span style={{ fontSize: '0.85rem', color: '#6b7280' }}>Depth Validation</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', marginTop: '0.25rem' }}>
            {report.reps.every((r) => r.depth_achieved !== false) ? (
              <span style={{ color: '#16a34a', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4 }}>
                <CheckCircle2 size={18} /> Valid
              </span>
            ) : (
              <span style={{ color: '#dc2626', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4 }}>
                <AlertTriangle size={18} /> High Reps
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Actionable Micro-Cues Banner */}
      <div style={{ background: '#eff6ff', borderLeft: '4px solid #3b82f6', padding: '1rem', borderRadius: 4, marginBottom: '1.5rem' }}>
        <h3 style={{ margin: '0 0 0.5rem', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: 6, color: '#1e40af' }}>
          <Activity size={18} /> Real-Time Micro-Cues
        </h3>
        <ul style={{ margin: 0, paddingLeft: '1.25rem', color: '#1e3a8a' }}>
          {report.micro_cues.map((cue, idx) => (
            <li key={idx} style={{ marginBottom: '0.25rem' }}>{cue}</li>
          ))}
        </ul>
      </div>

      {/* Concentric Velocity Trend Chart */}
      <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: '1.25rem', marginBottom: '1.5rem' }}>
        <h3 style={{ margin: '0 0 1rem', fontSize: '1rem', color: '#111827' }}>Concentric Velocity by Rep (m/s)</h3>
        <div style={{ height: 240, width: '100%' }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="rep" />
              <YAxis domain={['auto', 'auto']} unit=" m/s" />
              <Tooltip />
              <Line type="monotone" dataKey="mcv" stroke="#2563eb" strokeWidth={3} dot={{ r: 5 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Rep Breakdown Table */}
      <div style={{ overflowX: 'auto', border: '1px solid #e5e7eb', borderRadius: 8, marginBottom: '1.5rem' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
          <thead style={{ background: '#f9fafb', borderBottom: '1px solid #e5e7eb' }}>
            <tr>
              <th style={{ padding: '0.75rem 1rem' }}>Rep</th>
              <th style={{ padding: '0.75rem 1rem' }}>MCV</th>
              <th style={{ padding: '0.75rem 1rem' }}>Peak Vel</th>
              <th style={{ padding: '0.75rem 1rem' }}>V-Loss</th>
              <th style={{ padding: '0.75rem 1rem' }}>Bar Drift</th>
              <th style={{ padding: '0.75rem 1rem' }}>Depth</th>
            </tr>
          </thead>
          <tbody>
            {report.reps.map((rep) => (
              <tr key={rep.rep_idx} style={{ borderBottom: '1px solid #f3f4f6' }}>
                <td style={{ padding: '0.75rem 1rem', fontWeight: 600 }}>#{rep.rep_idx}</td>
                <td style={{ padding: '0.75rem 1rem' }}>{rep.mcv_mps} m/s</td>
                <td style={{ padding: '0.75rem 1rem' }}>{rep.peak_velocity_mps} m/s</td>
                <td style={{ padding: '0.75rem 1rem' }}>{rep.velocity_loss_pct}%</td>
                <td style={{ padding: '0.75rem 1rem' }}>{rep.bar_drift_mm} mm</td>
                <td style={{ padding: '0.75rem 1rem' }}>
                  {rep.depth_achieved ? (
                    <span style={{ color: '#16a34a' }}>Achieved</span>
                  ) : (
                    <span style={{ color: '#dc2626' }}>Missed</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Clinical Disclaimer */}
      <p style={{ fontSize: '0.8rem', color: '#9ca3af', display: 'flex', alignItems: 'center', gap: 5 }}>
        <ShieldAlert size={14} /> {report.disclaimer}
      </p>
    </div>
  );
};