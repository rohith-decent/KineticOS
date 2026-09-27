import React, { useRef, useState } from 'react';
import { UploadCloud, CheckCircle2, AlertCircle } from 'lucide-react';
import type { SetReport } from '../types';

interface Props {
  onSetUploaded: (report: SetReport) => void;
}

export const SetUploader: React.FC<Props> = ({ onSetUploaded }) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isError, setIsError] = useState(false);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setStatusMessage(null);
    setIsError(false);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('http://127.0.0.1:8000/sets/upload', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Upload failed');
      }

      const report: SetReport = await res.json();
      setStatusMessage(`Successfully processed set: ${report.set_id}`);
      setIsError(false);
      onSetUploaded(report);
    } catch (err: any) {
      setStatusMessage(err.message || 'Error uploading file');
      setIsError(true);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <div
      style={{
        border: '2px dashed #cbd5e1',
        borderRadius: 8,
        padding: '1.25rem',
        textAlign: 'center',
        background: '#ffffff',
        marginBottom: '1.5rem',
      }}
    >
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept=".json"
        style={{ display: 'none' }}
      />
      <UploadCloud size={32} color="#64748b" style={{ margin: '0 auto 0.5rem' }} />
      <h4 style={{ margin: '0 0 0.25rem', color: '#1e293b', fontSize: '0.95rem' }}>
        Ingest Perception Data (SetRecord JSON)
      </h4>
      <p style={{ margin: '0 0 0.75rem', color: '#64748b', fontSize: '0.8rem' }}>
        Upload output from Role A's tracker to run kinematic and symmetry evaluation.
      </p>

      <button
        type="button"
        disabled={uploading}
        onClick={() => fileInputRef.current?.click()}
        style={{
          background: '#0f172a',
          color: '#ffffff',
          border: 'none',
          padding: '0.5rem 1rem',
          borderRadius: 6,
          fontSize: '0.85rem',
          fontWeight: 600,
          cursor: uploading ? 'not-allowed' : 'pointer',
        }}
      >
        {uploading ? 'Analyzing Kinematics...' : 'Select JSON File'}
      </button>

      {statusMessage && (
        <div
          style={{
            marginTop: '0.75rem',
            fontSize: '0.85rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 6,
            color: isError ? '#dc2626' : '#16a34a',
          }}
        >
          {isError ? <AlertCircle size={16} /> : <CheckCircle2 size={16} />}
          {statusMessage}
        </div>
      )}
    </div>
  );
};