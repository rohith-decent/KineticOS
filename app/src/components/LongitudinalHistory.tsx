import React, { useState, useEffect } from 'react';
import type { SetReport } from '../types';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { TrendingUp, Dumbbell, Flame } from 'lucide-react';

interface TrendsData {
  exercise: string;
  total_sets_analyzed: number;
  total_reps_completed: number;
  total_tonnage_kg: number;
  avg_velocity_loss_pct: number;
  estimated_1rm_kg: number | null;
  load_velocity_slope: number | null;
  fatigue_flag: string;
}

export const LongitudinalHistory: React.FC = () => {
  const [trends, setTrends] = useState<TrendsData | null>(null);
  const [sets, setSets] = useState<SetReport[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    Promise.all([
      fetch('http://127.0.0.1:8000/analytics/trends/back_squat').then((r) => r.json()),
      fetch('http://127.0.0.1:8000/sets?exercise=back_squat').then((r) => r.json()),
    ])
      .then(([trendsData, setsData]) => {
        setTrends(trendsData);
        setSets(setsData);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Error fetching longitudinal history:', err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <div style={{ padding: '2rem', textAlign: 'center' }}>Loading historical records...</div>;
  }

  // Generate data points for the Load-Velocity Profile: (Load, Rep 1 MCV)
  const lvpPoints = sets
    .filter((s) => s.reps && s.reps.length > 0)
    .map((s) => ({
      load: s.load_kg,
      mcv: s.reps[0].mcv_mps,
      setId: s.set_id,
    }));

  return (
    <div style={{ padding: '1.5rem', maxWidth: 900, margin: '0 auto', fontFamily: 'system-ui, sans-serif' }}>
      <div style={{ borderBottom: '1px solid #e5e7eb', paddingBottom: '1rem', marginBottom: '1.5rem' }}>
        <h2 style={{ margin: 0, fontSize: '1.5rem', color: '#111827', display: 'flex', alignItems: 'center', gap: 8 }}>
          <TrendingUp color="#16a34a" /> Longitudinal Intelligence & Load-Velocity Profile
        </h2>
        <p style={{ margin: '0.25rem 0 0', color: '#6b7280', fontSize: '0.9rem' }}>
          Linear regression across historical sets estimating neuromuscular fatigue and 1RM[cite: 1].
        </p>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
        <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: '1rem', background: '#f9fafb' }}>
          <span style={{ fontSize: '0.85rem', color: '#6b7280', display: 'flex', alignItems: 'center', gap: 4 }}>
            <Dumbbell size={16} /> Estimated 1RM
          </span>
          <h2 style={{ margin: '0.25rem 0 0', color: '#111827' }}>
            {trends?.estimated_1rm_kg ? `${trends.estimated_1rm_kg} kg` : 'Need >1 Load'}
          </h2>
        </div>

        <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: '1rem', background: '#f9fafb' }}>
          <span style={{ fontSize: '0.85rem', color: '#6b7280', display: 'flex', alignItems: 'center', gap: 4 }}>
            <Flame size={16} /> Total Tonnage
          </span>
          <h2 style={{ margin: '0.25rem 0 0', color: '#111827' }}>{trends?.total_tonnage_kg ?? 0} kg</h2>
        </div>

        <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: '1rem', background: '#f9fafb' }}>
          <span style={{ fontSize: '0.85rem', color: '#6b7280' }}>Fatigue Status</span>
          <h2
            style={{
              margin: '0.25rem 0 0',
              textTransform: 'uppercase',
              fontSize: '1.2rem',
              color: trends?.fatigue_flag === 'accumulated_fatigue' ? '#dc2626' : '#16a34a',
            }}
          >
            {trends?.fatigue_flag.replace('_', ' ') ?? 'FRESH'}
          </h2>
        </div>

        <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: '1rem', background: '#f9fafb' }}>
          <span style={{ fontSize: '0.85rem', color: '#6b7280' }}>Total Sets Analyzed</span>
          <h2 style={{ margin: '0.25rem 0 0', color: '#111827' }}>{trends?.total_sets_analyzed ?? 0}</h2>
        </div>
      </div>

      {/* Load-Velocity Scatter Plot */}
      <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: '1.25rem', marginBottom: '1.5rem' }}>
        <h3 style={{ margin: '0 0 1rem', fontSize: '1rem', color: '#111827' }}>
          Load vs. Concentric Velocity (LVP)
        </h3>
        <div style={{ height: 260, width: '100%' }}>
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="load" name="Load" unit=" kg" domain={['dataMin - 10', 'dataMax + 20']} />
              <YAxis dataKey="mcv" name="MCV" unit=" m/s" domain={[0.2, 1.0]} />
              <Tooltip cursor={{ strokeDasharray: '3 3' }} />
              <Scatter name="Sets" data={lvpPoints} fill="#16a34a" />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};