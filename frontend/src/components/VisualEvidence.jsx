import React, { useState } from 'react';

// Normalise the varied shapes the backend may return
function normalizeItem(raw) {
  return {
    label:       raw.index_name || raw.index || raw.label || raw.type || 'Analysis',
    url:         raw.url || raw.thumbnail_url || raw.image_url || null,
    date:        raw.date || raw.acquisition_date || (raw.period && raw.period.start) || null,
    period:      raw.period || null,
    source:      raw.source || 'GEE',
    observation: raw.observation || raw.description || raw.caption || null,
    caption:     raw.caption || null,
  };
}

// Index colour palettes for the legend
const INDEX_META = {
  NDVI: { color: '#22c55e', bg: 'rgba(34,197,94,0.1)',  label: 'Vegetation Index',      unit: '-1→1' },
  NDWI: { color: '#3b82f6', bg: 'rgba(59,130,246,0.1)', label: 'Water Index',            unit: '-1→1' },
  NDBI: { color: '#f97316', bg: 'rgba(249,115,22,0.1)', label: 'Built-up Index',         unit: '-1→1' },
  NBR:  { color: '#ef4444', bg: 'rgba(239,68,68,0.1)',  label: 'Burn Ratio',             unit: '-1→1' },
  RGB:  { color: '#a78bfa', bg: 'rgba(167,139,250,0.1)','label': 'True Colour',           unit: 'Visual' },
};

const INDEX_SWATCHES = {
  NDVI: [
    { color: '#14532d', label: 'Dense forest' },
    { color: '#4ade80', label: 'Vegetation' },
    { color: '#fde68a', label: 'Sparse / stressed' },
    { color: '#92400e', label: 'Bare soil' },
    { color: '#1e40af', label: 'Water' },
  ],
  NDWI: [
    { color: '#1e3a8a', label: 'Deep water' },
    { color: '#60a5fa', label: 'High moisture' },
    { color: '#d1d5db', label: 'Dry land' },
    { color: '#78350f', label: 'Built-up' },
  ],
  NDBI: [
    { color: '#dc2626', label: 'Dense urban' },
    { color: '#fb923c', label: 'Moderate built-up' },
    { color: '#fef08a', label: 'Mixed / sparse' },
    { color: '#4ade80', label: 'Vegetation' },
    { color: '#1e40af', label: 'Water' },
  ],
  NBR: [
    { color: '#14532d', label: 'Unburned' },
    { color: '#fde68a', label: 'Low severity' },
    { color: '#f97316', label: 'Moderate severity' },
    { color: '#7f1d1d', label: 'High severity' },
  ],
  RGB: [
    { color: '#4ade80', label: 'Vegetation' },
    { color: '#a3a3a3', label: 'Urban / soil' },
    { color: '#1e40af', label: 'Water' },
    { color: '#f1f5f9', label: 'Cloud / snow' },
  ],
};

// ── Single visual evidence card ──────────────────────────────────
function EvidenceCard({ item, onClick }) {
  const [imgError, setImgError] = useState(false);
  const [hover, setHover] = useState(false);
  const idxKey = item.label?.toUpperCase().replace(/[^A-Z]/g, '') || '';
  const meta = INDEX_META[idxKey] || { color: '#60a5fa', bg: 'rgba(96,165,250,0.1)', label: item.label };

  return (
    <div
      onClick={() => item.url && !imgError && onClick()}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        borderRadius: '10px',
        border: `1px solid ${hover && item.url ? 'rgba(255,255,255,0.18)' : 'rgba(255,255,255,0.07)'}`,
        background: hover && item.url ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.2)',
        overflow: 'hidden',
        cursor: item.url && !imgError ? 'zoom-in' : 'default',
        transition: 'border-color 0.2s, background 0.2s',
        display: 'flex', flexDirection: 'column',
      }}
    >
      {/* Image area */}
      <div style={{
        position: 'relative', aspectRatio: '4/3',
        background: '#060810', overflow: 'hidden',
      }}>
        {item.url && !imgError ? (
          <>
            <img
              src={item.url}
              alt={item.label}
              loading="lazy"
              style={{
                width: '100%', height: '100%', objectFit: 'cover', display: 'block',
                transition: 'transform 0.3s',
                transform: hover ? 'scale(1.04)' : 'scale(1)',
              }}
              onError={() => setImgError(true)}
            />
            {/* Hover overlay */}
            {hover && (
              <div style={{
                position: 'absolute', inset: 0,
                background: 'rgba(0,0,0,0.3)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <div style={{
                  background: 'rgba(0,0,0,0.7)', borderRadius: '6px',
                  padding: '4px 10px', fontSize: '10px', color: '#fff',
                  border: '1px solid rgba(255,255,255,0.2)',
                }}>Click to enlarge</div>
              </div>
            )}
          </>
        ) : (
          <div style={{
            width: '100%', height: '100%',
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center', gap: '6px',
            color: 'rgba(255,255,255,0.2)',
          }}>
            <div style={{ fontSize: '22px', opacity: 0.4 }}>🛰</div>
            <div style={{ fontSize: '10px' }}>{imgError ? 'Image unavailable' : 'No preview'}</div>
          </div>
        )}

        {/* Index badge */}
        <div style={{
          position: 'absolute', top: '7px', left: '7px',
          background: meta.bg,
          border: `1px solid ${meta.color}30`,
          borderRadius: '5px', padding: '2px 7px',
          fontSize: '9px', fontWeight: 700,
          color: meta.color, letterSpacing: '0.06em',
          backdropFilter: 'blur(4px)',
        }}>
          {item.label?.toUpperCase()}
        </div>
      </div>

      {/* Footer */}
      <div style={{ padding: '8px 10px', display: 'flex', flexDirection: 'column', gap: '3px' }}>
        {(item.caption || item.observation) && (
          <div style={{
            fontSize: '10px', color: 'rgba(255,255,255,0.55)',
            lineHeight: '1.4', overflow: 'hidden',
            display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
          }}>
            {item.caption || item.observation}
          </div>
        )}
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', marginTop: '2px' }}>
          <div style={{ width: '5px', height: '5px', borderRadius: '50%', background: '#22c55e', flexShrink: 0 }} />
          <span style={{ fontSize: '9px', color: 'rgba(255,255,255,0.3)' }}>{item.source}</span>
          {item.date && (
            <>
              <span style={{ color: 'rgba(255,255,255,0.1)', fontSize: '9px' }}>·</span>
              <span style={{ fontSize: '9px', color: 'rgba(255,255,255,0.3)' }}>{item.date}</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Lightbox overlay ─────────────────────────────────────────────
function Lightbox({ item, onClose }) {
  const idxKey = item.label?.toUpperCase().replace(/[^A-Z]/g, '') || '';
  const swatches = INDEX_SWATCHES[idxKey] || [];

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 9999,
        background: 'rgba(0,0,0,0.9)',
        backdropFilter: 'blur(8px)',
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        gap: '16px', cursor: 'zoom-out', padding: '24px',
      }}
    >
      <img
        src={item.url}
        alt={item.label}
        style={{
          maxWidth: '86vw', maxHeight: '70vh',
          borderRadius: '12px',
          border: '1px solid rgba(255,255,255,0.12)',
          boxShadow: '0 24px 80px rgba(0,0,0,0.7)',
        }}
        onClick={e => e.stopPropagation()}
      />

      {/* Caption */}
      <div style={{ textAlign: 'center', maxWidth: '560px' }}>
        <div style={{ fontSize: '14px', fontWeight: 600, color: '#fff', marginBottom: '4px' }}>
          {item.label?.toUpperCase()}
          {item.date && <span style={{ color: 'rgba(255,255,255,0.4)', fontWeight: 400 }}> · {item.date}</span>}
        </div>
        {item.observation && (
          <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)', lineHeight: '1.5' }}>
            {item.observation}
          </div>
        )}
      </div>

      {/* Colour legend */}
      {swatches.length > 0 && (
        <div
          onClick={e => e.stopPropagation()}
          style={{
            display: 'flex', flexWrap: 'wrap', gap: '8px', justifyContent: 'center',
            background: 'rgba(0,0,0,0.5)', borderRadius: '8px', padding: '10px 14px',
          }}
        >
          {swatches.map((s, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <div style={{
                width: '11px', height: '11px', borderRadius: '2px',
                background: s.color, border: '1px solid rgba(255,255,255,0.2)',
              }} />
              <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.6)' }}>{s.label}</span>
            </div>
          ))}
        </div>
      )}

      <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.3)' }}>Click anywhere to close</div>
    </div>
  );
}

// ── Main VisualEvidence export ───────────────────────────────────
export default function VisualEvidence({ items }) {
  const [lightboxItem, setLightboxItem] = useState(null);

  if (!items || items.length === 0) return null;
  const normalized = items.map(normalizeItem);

  return (
    <>
      {/* Use .evidence-grid CSS class — responds to container query (chat panel width) */}
      <div className="evidence-grid">
        {normalized.map((item, i) => (
          <EvidenceCard key={i} item={item} onClick={() => setLightboxItem(item)} />
        ))}
      </div>
      {lightboxItem && <Lightbox item={lightboxItem} onClose={() => setLightboxItem(null)} />}
    </>
  );
}
