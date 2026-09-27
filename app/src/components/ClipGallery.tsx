import React, { useState, useEffect } from 'react';
import type { SetReport } from '../types';
import { Film, Dumbbell } from 'lucide-react';

export const ClipGallery: React.FC = () => {
  const [sets, setSets] = useState<SetReport[]>([]);
  const [selectedSet, setSelectedSet] = useState<SetReport | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    fetch('http://127.0.0.1:8000/sets?limit=20')
      .then((res) => res.json())
      .then((data: SetReport[]) => {
        setSets(data);
        if (data.length > 0) setSelectedSet(data[0]);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load clip gallery:', err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <div style={{ padding: '2rem', textAlign: 'center' }}>Loading clip gallery...</div>;
  }

  return (
    <div style={{ padding: '1.5rem', maxWidth: 960, margin: '0 auto', fontFamily: 'system-ui, sans-serif' }}>
      <div style={{ borderBottom: '1px solid #e5e7eb', paddingBottom: '1rem', marginBottom: '1.5rem' }}>
        <h2 style={{ margin: 0, fontSize: '1.5rem', color: '#111827', display: 'flex', alignItems: 'center', gap: 8 }}>
          <Film color="#7c3aed" /> Auto-Clip Gallery
        </h2>
        <p style={{ margin: '0.25rem 0 0', color: '#6b7280', fontSize: '0.9rem' }}>
          Trimmed MP4 recordings generated per set by Role A's auto-clipper module.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: '1.5rem' }}>
        {/* Set Selector List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {sets.map((s) => {
            const isSelected = selectedSet?.set_id === s.set_id;
            return (
              <div
                key={s.set_id}
                onClick={() => setSelectedSet(s)}
                style={{
                  border: isSelected ? '2px solid #7c3aed' : '1px solid #e5e7eb',
                  borderRadius: 8,
                  padding: '1rem',
                  background: isSelected ? '#f5f3ff' : '#ffffff',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease-in-out',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 700, fontSize: '0.95rem', color: '#111827' }}>
                    {s.exercise.replace('_', ' ').toUpperCase()}
                  </span>
                  <span style={{ fontSize: '0.8rem', color: '#6b7280' }}>
                    @{s.estimated_rpe ?? '--'} RPE
                  </span>
                </div>
                <div style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem', fontSize: '0.85rem', color: '#4b5563' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <Dumbbell size={14} /> {s.load_kg} kg
                  </span>
                  <span>{s.total_reps} reps</span>
                  <span>{s.overall_velocity_loss_pct}% loss</span>
                </div>
                <div style={{ marginTop: '0.4rem', fontSize: '0.75rem', color: '#9ca3af' }}>
                  ID: {s.set_id}
                </div>
              </div>
            );
          })}
        </div>

        {/* Video Player & Clip Details */}
        <div>
          {selectedSet ? (
            <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: '1rem', background: '#ffffff' }}>
              <h3 style={{ margin: '0 0 0.75rem', fontSize: '1.1rem', color: '#111827' }}>
                Clip Preview: {selectedSet.set_id}
              </h3>

              {/* HTML5 Video Element */}
              <div
                style={{
                  width: '100%',
                  aspectRatio: '16/9',
                  background: '#0f172a',
                  borderRadius: 6,
                  overflow: 'hidden',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: '1rem',
                }}
              >
                <video
                  key={selectedSet.set_id}
                  controls
                  style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                  src={`http://127.0.0.1:8000/clips/${selectedSet.set_id}.mp4`}
                >
                  <p style={{ color: '#ffffff', fontSize: '0.85rem' }}>
                    Video format not supported or clip file not yet written to clips/ directory.
                  </p>
                </video>
              </div>

              {/* Set Metrics Summary */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem', textAlign: 'center' }}>
                <div style={{ background: '#f9fafb', padding: '0.5rem', borderRadius: 4 }}>
                  <span style={{ fontSize: '0.75rem', color: '#6b7280' }}>Rep 1 Speed</span>
                  <div style={{ fontWeight: 600, color: '#111827' }}>
                    {selectedSet.reps[0]?.mcv_mps ?? 0} m/s
                  </div>
                </div>
                <div style={{ background: '#f9fafb', padding: '0.5rem', borderRadius: 4 }}>
                  <span style={{ fontSize: '0.75rem', color: '#6b7280' }}>Terminal Speed</span>
                  <div style={{ fontWeight: 600, color: '#111827' }}>
                    {selectedSet.reps[selectedSet.reps.length - 1]?.mcv_mps ?? 0} m/s
                  </div>
                </div>
                <div style={{ background: '#f9fafb', padding: '0.5rem', borderRadius: 4 }}>
                  <span style={{ fontSize: '0.75rem', color: '#6b7280' }}>Velocity Loss</span>
                  <div style={{ fontWeight: 600, color: '#111827' }}>
                    {selectedSet.overall_velocity_loss_pct}%
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div style={{ padding: '2rem', textAlign: 'center', color: '#6b7280' }}>
              Select a set from the list to preview the auto-clipped rep video.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};