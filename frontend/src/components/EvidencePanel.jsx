import React, { useState, useRef } from 'react';
import { apiGet } from '../utils/api';

// Safe tool name → readable label, no internal function names exposed
const TOOL_DISPLAY = {
  gee_search_imagery:           'Imagery search',
  gee_calculate_indices:        'Spectral index computation',
  gee_get_zonal_statistics:     'Zonal statistics',
  gee_get_temporal_series:      'Temporal series',
  gee_analyze_trend:            'Trend analysis',
  gee_analyze_seasonality:      'Seasonality analysis',
  gee_analyze_change_persistence:'Change persistence',
  gee_detect_temporal_breaks:   'Change-point detection',
  gee_compare_periods:          'Period comparison',
  gee_get_raster:               'Raster retrieval',
  gee_calculate_change_area:    'Change area calculation',
  gee_detect_anomalies:         'Anomaly detection',
  gee_get_subregion_statistics: 'Subregion statistics',
  gee_calculate_overlap:        'Feature overlap',
  gee_analyze_event_window:     'Event window analysis',
  gee_generate_timeline_artifact:'Timeline generation',
};

function safeToolLabel(name) {
  return TOOL_DISPLAY[name] || name?.replace(/gee_/i, '').replace(/_/g, ' ') || 'Analysis step';
}

// Provenance status config
const PROV_CONFIG = {
  complete:    { color: '#22c55e', label: 'Verified' },
  partial:     { color: '#f59e0b', label: 'Partial'  },
  degraded:    { color: '#f59e0b', label: 'Degraded' },
  unavailable: { color: '#ef4444', label: 'Unavailable' },
};

// ── Single evidence record card ──────────────────────────────────
function EvidenceRecord({ ev, index }) {
  const [open, setOpen] = useState(false);
  const shortId = ev.evidence_id ? `EV-${ev.evidence_id.substring(0, 6).toUpperCase()}` : `EV-${index + 1}`;

  // Extract displayable parameters (exclude raw internal data)
  const params = ev.parameters || {};
  const displayParams = Object.entries(params)
    .filter(([k]) => !['raw_data', 'mapbox_image', 'messages'].includes(k))
    .slice(0, 8);

  const rawData = params.raw_data || {};
  const metric  = params.metric || ev.metric;
  const value   = params.value  ?? ev.value;
  const startDate = params.start_date || rawData.start_date;
  const endDate   = params.end_date   || rawData.end_date;

  return (
    <div style={{
      borderRadius: '8px',
      border: '1px solid rgba(255,255,255,0.06)',
      background: 'rgba(0,0,0,0.15)',
      overflow: 'hidden',
    }}>
      {/* Record header */}
      <button onClick={() => setOpen(o => !o)} style={{
        width: '100%', display: 'flex', alignItems: 'center', gap: '8px',
        padding: '9px 12px', background: 'none', border: 'none',
        cursor: 'pointer', textAlign: 'left',
      }}>
        {/* Short ID */}
        <code style={{
          fontSize: '9px', color: 'rgba(255,255,255,0.25)',
          background: 'rgba(255,255,255,0.05)', borderRadius: '4px',
          padding: '2px 6px', fontFamily: 'monospace', flexShrink: 0,
        }}>{shortId}</code>

        {/* Tool name */}
        <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.65)', flex: 1, minWidth: 0 }}>
          {safeToolLabel(ev.tool_name)}
        </span>

        {/* Metric chip */}
        {metric && (
          <span style={{
            fontSize: '9px', padding: '1px 6px',
            background: 'rgba(59,130,246,0.1)', color: '#93c5fd',
            borderRadius: '4px', fontWeight: 600, flexShrink: 0,
          }}>{metric.toUpperCase()}</span>
        )}

        {/* Chevron */}
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          style={{ width: '10px', height: '10px', flexShrink: 0, color: 'rgba(255,255,255,0.2)',
            transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}>
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {/* Expanded details */}
      {open && (
        <div style={{
          padding: '2px 12px 12px',
          borderTop: '1px solid rgba(255,255,255,0.04)',
          display: 'flex', flexDirection: 'column', gap: '5px',
        }}>
          {/* Value row */}
          {value !== undefined && value !== null && (
            <DataRow label="Value" value={
              typeof value === 'number' ? value.toFixed(5) : String(value)
            } accent />
          )}
          {/* Date period */}
          {(startDate || endDate) && (
            <DataRow label="Period" value={[startDate, endDate].filter(Boolean).join(' → ')} />
          )}
          {/* Source */}
          {ev.source && <DataRow label="Source" value={ev.source} />}
          {/* Scenes */}
          {ev.scene_ids?.length > 0 && (
            <DataRow label="Scenes" value={`${ev.scene_ids.length} Sentinel-2 scene${ev.scene_ids.length > 1 ? 's' : ''}`} />
          )}
          {/* Other params (safe ones) */}
          {displayParams.filter(([k]) => !['metric','value','unit','start_date','end_date'].includes(k))
            .map(([k, v]) => (
              typeof v === 'string' || typeof v === 'number'
                ? <DataRow key={k} label={k.replace(/_/g, ' ')} value={String(v)} />
                : null
            ))
          }
        </div>
      )}
    </div>
  );
}

function DataRow({ label, value, accent }) {
  return (
    <div style={{ display: 'flex', gap: '8px', fontSize: '11px' }}>
      <span style={{ color: 'rgba(255,255,255,0.3)', minWidth: '55px', flexShrink: 0 }}>{label}</span>
      <span style={{
        color: accent ? '#93c5fd' : 'rgba(255,255,255,0.6)',
        fontVariantNumeric: 'tabular-nums',
        wordBreak: 'break-all',
      }}>{value}</span>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════
// Main EvidencePanel export
// ════════════════════════════════════════════════════════════════
export default function EvidencePanel({ jobId, provenance, provenanceStatus }) {
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const cacheRef = useRef(null);

  const evidenceIds = provenance?.evidence_ids || [];
  const evidenceCount = evidenceIds.length || (cacheRef.current?.evidence?.length || 0);
  const provCfg = PROV_CONFIG[provenanceStatus] || PROV_CONFIG.complete;

  async function handleToggle() {
    const next = !expanded;
    setExpanded(next);
    if (next && !cacheRef.current && jobId) {
      setLoading(true); setError(null);
      try {
        const data = await apiGet(`/jobs/${jobId}/evidence`);
        cacheRef.current = data;
      } catch {
        setError('Unable to load evidence details.');
      } finally {
        setLoading(false);
      }
    }
  }

  const cached = cacheRef.current;
  const rawEvidence = cached?.evidence || [];
  const evidenceItems = evidenceIds.length > 0
    ? rawEvidence.filter(ev => evidenceIds.includes(ev.evidence_id))
    : rawEvidence;

  return (
    <div style={{
      borderRadius: '10px',
      border: '1px solid rgba(255,255,255,0.06)',
      background: 'rgba(255,255,255,0.025)',
      overflow: 'hidden',
    }}>
      {/* Collapsed header */}
      <button onClick={handleToggle} style={{
        width: '100%', display: 'flex', alignItems: 'center', gap: '9px',
        padding: '10px 14px', background: 'none', border: 'none',
        cursor: 'pointer', textAlign: 'left',
      }}>
        {/* Icon */}
        <div style={{
          width: '20px', height: '20px', borderRadius: '5px',
          background: 'rgba(59,130,246,0.1)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '10px', flexShrink: 0,
        }}>🔍</div>

        <span style={{ fontSize: '11px', fontWeight: 600, color: 'rgba(255,255,255,0.7)', flex: 1 }}>
          Evidence &amp; Sources
        </span>

        {/* Count badge */}
        {evidenceCount > 0 && (
          <span style={{
            fontSize: '9px', padding: '2px 7px',
            background: 'rgba(59,130,246,0.1)', color: '#93c5fd',
            borderRadius: '6px', fontWeight: 600,
          }}>{evidenceCount}</span>
        )}

        {/* Provenance status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <div style={{
            width: '5px', height: '5px', borderRadius: '50%', background: provCfg.color,
          }} />
          <span style={{ fontSize: '9px', color: provCfg.color, fontWeight: 600 }}>
            {provCfg.label}
          </span>
        </div>

        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          style={{ width: '11px', height: '11px', color: 'rgba(255,255,255,0.25)',
            transform: expanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s', flexShrink: 0 }}>
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {/* Expanded body */}
      {expanded && (
        <div style={{
          padding: '0 12px 12px',
          borderTop: '1px solid rgba(255,255,255,0.05)',
          display: 'flex', flexDirection: 'column', gap: '8px',
        }}>
          {loading && (
            <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.3)', padding: '10px 0' }}>
              Loading evidence…
            </div>
          )}
          {error && (
            <div style={{ fontSize: '11px', color: '#f87171', padding: '10px 0' }}>{error}</div>
          )}
          {!loading && !error && evidenceItems.length === 0 && (
            <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.25)', padding: '10px 0' }}>
              {provenanceStatus === 'unavailable'
                ? 'Provenance tracking unavailable for this session.'
                : 'No evidence records found for this analysis.'}
            </div>
          )}
          {!loading && evidenceItems.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '5px', paddingTop: '6px' }}>
              <div style={{
                fontSize: '9px', fontWeight: 700, textTransform: 'uppercase',
                letterSpacing: '0.08em', color: 'rgba(255,255,255,0.25)', paddingBottom: '3px',
              }}>
                {evidenceItems.length} analysis record{evidenceItems.length !== 1 ? 's' : ''}
              </div>
              {evidenceItems.map((ev, i) => (
                <EvidenceRecord key={ev.evidence_id || i} ev={ev} index={i} />
              ))}
            </div>
          )}

          {/* Provenance note — never expose internal details */}
          <div style={{
            fontSize: '9px', color: 'rgba(255,255,255,0.2)',
            borderTop: '1px solid rgba(255,255,255,0.04)',
            paddingTop: '8px', lineHeight: '1.5',
          }}>
            All measurements computed via Google Earth Engine · Sentinel-2 MSI · ESA Copernicus
          </div>
        </div>
      )}
    </div>
  );
}
