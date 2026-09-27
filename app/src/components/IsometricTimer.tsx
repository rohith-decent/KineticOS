import React, { useState } from 'react';
import type { IsometricReport } from '../types';
import { Timer, Clock } from 'lucide-react';

export const IsometricTimer: React.FC = () => {
  const [report, setReport] = useState<IsometricReport | null>(null);
  const [isRunning, setIsRunning] = useState<boolean>(false);

  const runSampleIsometricSession = async () => {
    setIsRunning(true);
    // Simulating a 10-second plank test stream with intermittent form deviation
    const sampleStream = [
      { t: 0.0, angle_error_deg: 2.1, valid: true },
      { t: 1.0, angle_error_deg: 3.4, valid: true },
      { t: 2.0, angle_error_deg: 4.8, valid: true },
      { t: 3.0, angle_error_deg: 9.5, valid: true }, // Spike
      { t: 3.2, angle_error_deg: 9.8, valid: true }, // Sustained > 150 ms -> Paused
      { t: 4.0, angle_error_deg: 8.5, valid: true },
      { t: 5.0, angle_error_deg: 4.2, valid: true }, // Resuming (< 6 deg)
      { t: 5.4, angle_error_deg: 3.8, valid: true }, // Resumed after 300 ms
      { t: 6.0, angle_error_deg: 2.5, valid: true },
      { t: 7.0, angle_error_deg: 3.0, valid: true },
    ];

    try {
      const res = await fetch('http://127.0.0.1:8000/isometric/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sampleStream),
      });
      const data: IsometricReport = await res.json();
      setReport(data);
    } catch (err) {
      console.error('Failed to process isometric stream', err);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div style={{ padding: '1.5rem', maxWidth: 800, margin: '0 auto', fontFamily: 'system-ui, sans-serif' }}>
      <div style={{ borderBottom: '1px solid #e5e7eb', paddingBottom: '1rem', marginBottom: '1.5rem' }}>
        <h2 style={{ margin: 0, fontSize: '1.5rem', color: '#111827', display: 'flex', alignItems: 'center', gap: 8 }}>
          <Timer color="#2563eb" /> True-Time Chronometer (Plank / Isometric)
        </h2>
        <p style={{ margin: '0.25rem 0 0', color: '#6b7280', fontSize: '0.9rem' }}>
          Automated hysteresis tracking: Pauses clock when alignment error exceeds 8° for &gt;150 ms.
        </p>
      </div>

      <button
        onClick={runSampleIsometricSession}
        disabled={isRunning}
        style={{
          background: '#2563eb',
          color: '#ffffff',
          border: 'none',
          padding: '0.65rem 1.25rem',
          borderRadius: 6,
          fontWeight: 600,
          cursor: isRunning ? 'not-allowed' : 'pointer',
          marginBottom: '1.5rem',
        }}
      >
        {isRunning ? 'Processing Stream...' : 'Simulate 10s Isometric Stream'}
      </button>

      {report && (
        <div>
          {/* Main Large Clock */}
          <div
            style={{
              border: '2px solid #e5e7eb',
              borderRadius: 12,
              padding: '2rem',
              textAlign: 'center',
              background: '#f9fafb',
              marginBottom: '1.5rem',
            }}
          >
            <span style={{ fontSize: '0.9rem', color: '#6b7280', textTransform: 'uppercase', letterSpacing: 1 }}>
              True Time Under Tension (True TUT)
            </span>
            <h1 style={{ margin: '0.5rem 0', fontSize: '3.5rem', fontWeight: 800, color: '#111827' }}>
              {report.true_tut_s}s
            </h1>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: '0.95rem', color: '#4b5563' }}>
              <Clock size={16} /> Total Wall Clock: <strong>{report.total_elapsed_s}s</strong>
            </div>
          </div>

          {/* Chronometer KPI Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
            <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: '1rem', background: '#ffffff' }}>
              <span style={{ fontSize: '0.85rem', color: '#6b7280' }}>Form Adherence</span>
              <h3 style={{ margin: '0.25rem 0 0', color: report.form_adherence_pct >= 85 ? '#16a34a' : '#ea580c' }}>
                {report.form_adherence_pct}%
              </h3>
            </div>

            <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: '1rem', background: '#ffffff' }}>
              <span style={{ fontSize: '0.85rem', color: '#6b7280' }}>Pause Interruptions</span>
              <h3 style={{ margin: '0.25rem 0 0', color: '#111827' }}>{report.pause_count} times</h3>
            </div>

            <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: '1rem', background: '#ffffff' }}>
              <span style={{ fontSize: '0.85rem', color: '#6b7280' }}>Time Discarded (Error &gt; 8°)</span>
              <h3 style={{ margin: '0.25rem 0 0', color: '#dc2626' }}>{report.paused_duration_s}s</h3>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};