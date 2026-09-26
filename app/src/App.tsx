import React, { useState, useEffect } from 'react';
import type { SetReport } from './types';
import { SetDebrief } from './components/SetDebrief';
import { SymmetryHeatmap } from './components/SymmetryHeatmap';
import { IsometricTimer } from './components/IsometricTimer';
import { LongitudinalHistory } from './components/LongitudinalHistory';
import { ClipGallery } from './components/ClipGallery';
import { SetUploader } from './components/SetUploader';
import { Dumbbell, Timer, LineChart, Film } from 'lucide-react';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'debrief' | 'isometric' | 'trends' | 'clips'>('debrief');
  const [report, setReport] = useState<SetReport | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchLatestSet = () => {
    fetch('http://127.0.0.1:8000/sets?limit=1')
      .then((res) => res.json())
      .then((data: SetReport[]) => {
        if (data && data.length > 0) {
          setReport(data[0]);
        }
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load sets', err);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchLatestSet();
  }, []);

  return (
    <div style={{ minHeight: '100vh', background: '#f8fafc', fontFamily: 'system-ui, sans-serif' }}>
      <header style={{ background: '#ffffff', borderBottom: '1px solid #e2e8f0', padding: '0.75rem 1.5rem' }}>
        <div style={{ maxWidth: 1020, margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: '1.25rem', fontWeight: 800, color: '#0f172a', letterSpacing: -0.5 }}>
              Kinetic<span style={{ color: '#2563eb' }}>OS</span>
            </span>
            <span style={{ fontSize: '0.75rem', background: '#eff6ff', color: '#1d4ed8', padding: '0.15rem 0.5rem', borderRadius: 4, fontWeight: 600 }}>
              ROLE B ENGINE
            </span>
          </div>

          <nav style={{ display: 'flex', gap: '0.35rem' }}>
            <button
              onClick={() => setActiveTab('debrief')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '0.5rem 0.75rem',
                border: 'none',
                borderRadius: 6,
                fontWeight: 600,
                fontSize: '0.85rem',
                cursor: 'pointer',
                background: activeTab === 'debrief' ? '#eff6ff' : 'transparent',
                color: activeTab === 'debrief' ? '#1d4ed8' : '#64748b',
              }}
            >
              <Dumbbell size={16} /> Lift Debrief
            </button>

            <button
              onClick={() => setActiveTab('clips')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '0.5rem 0.75rem',
                border: 'none',
                borderRadius: 6,
                fontWeight: 600,
                fontSize: '0.85rem',
                cursor: 'pointer',
                background: activeTab === 'clips' ? '#eff6ff' : 'transparent',
                color: activeTab === 'clips' ? '#1d4ed8' : '#64748b',
              }}
            >
              <Film size={16} /> Clip Gallery
            </button>

            <button
              onClick={() => setActiveTab('isometric')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '0.5rem 0.75rem',
                border: 'none',
                borderRadius: 6,
                fontWeight: 600,
                fontSize: '0.85rem',
                cursor: 'pointer',
                background: activeTab === 'isometric' ? '#eff6ff' : 'transparent',
                color: activeTab === 'isometric' ? '#1d4ed8' : '#64748b',
              }}
            >
              <Timer size={16} /> True-Time Timer
            </button>

            <button
              onClick={() => setActiveTab('trends')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '0.5rem 0.75rem',
                border: 'none',
                borderRadius: 6,
                fontWeight: 600,
                fontSize: '0.85rem',
                cursor: 'pointer',
                background: activeTab === 'trends' ? '#eff6ff' : 'transparent',
                color: activeTab === 'trends' ? '#1d4ed8' : '#64748b',
              }}
            >
              <LineChart size={16} /> Fatigue & Trends
            </button>
          </nav>
        </div>
      </header>

      <main style={{ maxWidth: 1020, margin: '1.5rem auto', padding: '0 1rem' }}>
        {activeTab === 'debrief' && (
          <>
            <SetUploader onSetUploaded={(newReport) => setReport(newReport)} />
            {loading ? (
              <div style={{ textAlign: 'center', padding: '2rem' }}>Loading set debrief...</div>
            ) : report ? (
              <>
                <SetDebrief report={report} />
                {report.symmetry && <SymmetryHeatmap symmetry={report.symmetry} />}
              </>
            ) : (
              <div style={{ textAlign: 'center', padding: '2rem' }}>No set records found.</div>
            )}
          </>
        )}

        {activeTab === 'clips' && <ClipGallery />}

        {activeTab === 'isometric' && <IsometricTimer />}

        {activeTab === 'trends' && <LongitudinalHistory />}
      </main>
    </div>
  );
};

export default App;