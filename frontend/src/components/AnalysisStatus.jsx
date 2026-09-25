import React, { useState, useEffect, useRef } from 'react';

// Realistic pipeline stages — order reflects actual GEE backend flow
const STAGES = [
  { id: 'search',   icon: '🔍', label: 'Searching satellite imagery',    sub: 'Sentinel-2 · Google Earth Engine' },
  { id: 'query',    icon: '🛰', label: 'Querying GEE analysis tools',    sub: 'Computing spectral indices' },
  { id: 'evidence', icon: '📊', label: 'Generating visual evidence',     sub: 'Rendering index thumbnails' },
  { id: 'validate', icon: '✓',  label: 'Validating evidence quality',    sub: 'Cross-checking measurements' },
  { id: 'report',   icon: '📄', label: 'Preparing analysis report',      sub: 'Structuring findings' },
];

export default function AnalysisStatus() {
  const [stageIndex, setStageIndex] = useState(0);
  const intervalRef = useRef(null);

  useEffect(() => {
    intervalRef.current = setInterval(() => {
      setStageIndex(prev => Math.min(prev + 1, STAGES.length - 1));
    }, 5000);
    return () => clearInterval(intervalRef.current);
  }, []);

  const current = STAGES[stageIndex];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
      <style>{`
        @keyframes radarPing { 0%{transform:scale(0.8);opacity:1} 100%{transform:scale(2.2);opacity:0} }
        @keyframes stageIn { from{opacity:0;transform:translateY(4px)} to{opacity:1;transform:translateY(0)} }
        @keyframes dotBounce { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-4px)} }
      `}</style>

      {/* Current active stage */}
      <div style={{
        display: 'flex', alignItems: 'flex-start', gap: '10px',
        animation: 'stageIn 0.35s ease',
        key: stageIndex,
      }}>
        {/* Radar icon */}
        <div style={{ position: 'relative', width: '28px', height: '28px', flexShrink: 0 }}>
          <div style={{
            position: 'absolute', inset: 0, borderRadius: '50%',
            background: 'rgba(59,130,246,0.15)',
            border: '1px solid rgba(59,130,246,0.35)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '11px',
          }}>{current.icon}</div>
          <div style={{
            position: 'absolute', inset: 0, borderRadius: '50%',
            border: '1px solid rgba(59,130,246,0.6)',
            animation: 'radarPing 1.8s ease-out infinite',
          }} />
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          {/* Stage label */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'rgba(255,255,255,0.85)' }}>
              {current.label}
            </span>
            <div style={{ display: 'flex', gap: '3px', alignItems: 'center' }}>
              {[0, 0.15, 0.3].map((d, i) => (
                <div key={i} style={{
                  width: '3px', height: '3px', borderRadius: '50%',
                  background: '#60a5fa',
                  animation: `dotBounce 0.9s ${d}s ease-in-out infinite`,
                }} />
              ))}
            </div>
          </div>
          <div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.35)', marginTop: '2px' }}>
            {current.sub}
          </div>
        </div>
      </div>

      {/* Stage progress indicators */}
      <div style={{ display: 'flex', gap: '4px', paddingLeft: '38px' }}>
        {STAGES.map((stage, i) => (
          <div key={stage.id} style={{
            flex: 1, height: '2px', borderRadius: '2px',
            background: i < stageIndex
              ? '#3b82f6'
              : i === stageIndex
                ? 'rgba(59,130,246,0.5)'
                : 'rgba(255,255,255,0.07)',
            transition: 'background 0.5s ease',
          }} />
        ))}
      </div>

      {/* Previous completed stages (subtle) */}
      {stageIndex > 0 && (
        <div style={{ paddingLeft: '38px', display: 'flex', flexDirection: 'column', gap: '3px' }}>
          {STAGES.slice(0, stageIndex).map(stage => (
            <div key={stage.id} style={{
              display: 'flex', alignItems: 'center', gap: '6px',
              fontSize: '10px', color: 'rgba(255,255,255,0.25)',
            }}>
              <div style={{
                width: '10px', height: '10px', borderRadius: '50%',
                background: 'rgba(34,197,94,0.15)',
                border: '1px solid rgba(34,197,94,0.3)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '7px', color: '#22c55e', flexShrink: 0,
              }}>✓</div>
              {stage.label}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
