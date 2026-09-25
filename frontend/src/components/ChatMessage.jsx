import React, { useState } from 'react';
import VisualEvidence from './VisualEvidence';
import EvidencePanel from './EvidencePanel';
import TimelinePlayer from './TimelinePlayer';

// ── Shared Animations ─────────────────────────────────────────────
const ANIM_STYLE = `
  @keyframes msgIn { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
  @keyframes countIn { from{opacity:0;transform:scaleX(0)} to{opacity:1;transform:scaleX(1)} }
`;

// ── Inline Markdown renderer ──────────────────────────────────────
function inlineMd(str) {
  const bold = str.split(/(\*\*.*?\*\*)/g);
  return bold.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**'))
      return <strong key={i} style={{ color: '#f1f5f9', fontWeight: 600 }}>{part.slice(2, -2)}</strong>;
    return part;
  });
}

function MarkdownContent({ text }) {
  if (!text) return null;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
      {text.split('\n').map((line, i) => {
        if (!line.trim()) return <div key={i} style={{ height: '5px' }} />;

        // Image syntax
        const img = line.match(/!\[([^\]]*)\]\((https?:\/\/[^\s]+)\)/);
        if (img) return (
          <div key={i} style={{ marginTop: '8px', marginBottom: '4px' }}>
            <img src={img[2]} alt={img[1]} loading="lazy" style={{
              width: '100%', borderRadius: '8px',
              border: '1px solid rgba(255,255,255,0.08)', display: 'block',
            }} />
            {img[1] && <div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.35)', marginTop: '4px', textAlign: 'center', fontStyle: 'italic' }}>{img[1]}</div>}
          </div>
        );

        // Headings
        if (line.startsWith('### ')) return <div key={i} style={{ margin: '8px 0 3px', fontSize: '12px', fontWeight: 700, color: '#e2e8f0' }}>{inlineMd(line.slice(4))}</div>;
        if (line.startsWith('## '))  return <div key={i} style={{ margin: '10px 0 4px', fontSize: '13px', fontWeight: 700, color: '#93c5fd' }}>{inlineMd(line.slice(3))}</div>;
        if (line.startsWith('# '))   return <div key={i} style={{ margin: '12px 0 6px', fontSize: '14px', fontWeight: 800, color: '#60a5fa' }}>{inlineMd(line.slice(2))}</div>;

        // Horizontal rule
        if (line.startsWith('---')) return <div key={i} style={{ height: '1px', background: 'rgba(255,255,255,0.07)', margin: '6px 0' }} />;

        // Bullets
        if (line.startsWith('- ') || line.startsWith('* ')) return (
          <div key={i} style={{ display: 'flex', gap: '7px', paddingLeft: '2px' }}>
            <span style={{ color: '#60a5fa', flexShrink: 0, marginTop: '1px', fontSize: '11px' }}>•</span>
            <span style={{ flex: 1, lineHeight: '1.65', fontSize: '13px' }}>{inlineMd(line.slice(2))}</span>
          </div>
        );

        return <div key={i} style={{ lineHeight: '1.7', fontSize: '13px', color: '#cbd5e1' }}>{inlineMd(line)}</div>;
      })}
    </div>
  );
}

// ── Section wrapper with consistent chrome ────────────────────────
function Section({ icon, label, badge, badgeColor = 'rgba(255,255,255,0.5)', badgeBg = 'rgba(255,255,255,0.07)',
  accentColor, collapsible = false, defaultOpen = true, children }) {
  const [open, setOpen] = useState(defaultOpen);

  const header = (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '7px',
      cursor: collapsible ? 'pointer' : 'default',
      padding: collapsible ? '0' : undefined,
      userSelect: 'none',
    }}
    onClick={collapsible ? () => setOpen(o => !o) : undefined}
    >
      {icon && <span style={{ fontSize: '11px', flexShrink: 0 }}>{icon}</span>}
      <span style={{
        fontSize: '10px', fontWeight: 700, letterSpacing: '0.09em',
        textTransform: 'uppercase',
        color: accentColor || 'rgba(255,255,255,0.4)',
      }}>{label}</span>
      {badge != null && (
        <span style={{
          fontSize: '9px', padding: '1px 6px',
          background: badgeBg, color: badgeColor,
          borderRadius: '5px', fontWeight: 700,
        }}>{badge}</span>
      )}
      {collapsible && (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          style={{
            width: '10px', height: '10px', marginLeft: 'auto', color: 'rgba(255,255,255,0.2)',
            transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s',
          }}>
          <polyline points="6 9 12 15 18 9" />
        </svg>
      )}
    </div>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
      {header}
      {(!collapsible || open) && children}
    </div>
  );
}

// ── Satellite image card (for media.images) ───────────────────────
const INDEX_ACCENT = {
  NDVI: '#22c55e', NDWI: '#3b82f6', NDBI: '#f97316',
  NBR: '#ef4444', RGB: '#a78bfa',
};
const INDEX_SWATCHES = {
  NDVI: [
    { color: '#14532d', label: 'Dense forest' }, { color: '#4ade80', label: 'Vegetation' },
    { color: '#fde68a', label: 'Sparse / stressed' }, { color: '#92400e', label: 'Bare soil' }, { color: '#1e40af', label: 'Water' },
  ],
  NDWI: [
    { color: '#1e3a8a', label: 'Deep water' }, { color: '#60a5fa', label: 'High moisture' },
    { color: '#d1d5db', label: 'Dry land' }, { color: '#78350f', label: 'Built-up' },
  ],
  NDBI: [
    { color: '#dc2626', label: 'Dense urban' }, { color: '#fb923c', label: 'Moderate built-up' },
    { color: '#fef08a', label: 'Mixed' }, { color: '#4ade80', label: 'Vegetation' }, { color: '#1e40af', label: 'Water' },
  ],
  NBR: [
    { color: '#14532d', label: 'Unburned' }, { color: '#fde68a', label: 'Low severity' },
    { color: '#f97316', label: 'Moderate' }, { color: '#7f1d1d', label: 'High severity' },
  ],
  RGB: [
    { color: '#4ade80', label: 'Vegetation' }, { color: '#a3a3a3', label: 'Urban / soil' },
    { color: '#1e40af', label: 'Water' }, { color: '#f1f5f9', label: 'Cloud / snow' },
  ],
};

function SatImageCard({ img, compact }) {
  const [err, setErr] = useState(false);
  const [hover, setHover] = useState(false);
  const url = img.url || img.thumbnail_url;
  const label = img.caption || img.index || img.type || 'Satellite image';
  const idxKey = (img.index || '').toUpperCase();
  const accent = INDEX_ACCENT[idxKey] || '#60a5fa';
  if (!url) return null;

  return (
    <div
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        borderRadius: '8px', overflow: 'hidden',
        border: `1px solid ${hover ? 'rgba(255,255,255,0.15)' : 'rgba(255,255,255,0.07)'}`,
        background: 'rgba(0,0,0,0.25)',
        flex: compact ? '1 1 0' : undefined,
        transition: 'border-color 0.2s',
        minWidth: 0,
      }}
    >
      {err ? (
        <div style={{
          aspectRatio: compact ? '1' : '16/9',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: '#06080f', color: 'rgba(255,255,255,0.2)', fontSize: '11px', gap: '6px',
        }}>
          <span style={{ fontSize: '18px', opacity: 0.4 }}>🛰</span> Image unavailable
        </div>
      ) : (
        <img src={url} alt={label} loading="lazy"
          style={{
            width: '100%', display: 'block',
            maxHeight: compact ? '180px' : '260px',
            objectFit: 'cover',
          }}
          onError={() => setErr(true)}
        />
      )}
      <div style={{ padding: '6px 10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '4px' }}>
        <span style={{
          fontSize: '10px', color: 'rgba(255,255,255,0.45)', fontStyle: 'italic',
          flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>{label}</span>
        <a href={url} target="_blank" rel="noopener noreferrer" style={{
          fontSize: '9px', color: accent, textDecoration: 'none', flexShrink: 0,
          background: accent + '18', padding: '2px 7px', borderRadius: '4px',
        }}>View ↗</a>
      </div>
    </div>
  );
}

function ImageGrid({ images }) {
  if (!images?.length) return null;
  const groups = {};
  for (const img of images) {
    const key = (img.index || img.type || 'image').toUpperCase();
    (groups[key] = groups[key] || []).push(img);
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      {Object.entries(groups).map(([idx, imgs]) => {
        const accent = INDEX_ACCENT[idx] || '#60a5fa';
        const swatches = INDEX_SWATCHES[idx] || [];
        const isBefore = imgs.length >= 2;
        return (
          <div key={idx}>
            {/* Index header */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '7px', marginBottom: '7px' }}>
              <span style={{
                fontSize: '10px', fontWeight: 700, letterSpacing: '0.07em',
                color: accent, textTransform: 'uppercase',
                background: accent + '15', padding: '2px 8px', borderRadius: '5px',
              }}>{idx}</span>
              {isBefore && (
                <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.35)', fontStyle: 'italic' }}>
                  Before / After comparison
                </span>
              )}
            </div>

            {isBefore ? (
              <div style={{ display: 'flex', gap: '6px' }}>
                {imgs.slice(0, 2).map((img, i) => <SatImageCard key={i} img={img} compact />)}
              </div>
            ) : (
              <SatImageCard img={imgs[0]} />
            )}

            {/* Colour legend */}
            {swatches.length > 0 && (
              <div style={{
                display: 'flex', flexWrap: 'wrap', gap: '5px',
                marginTop: '7px', padding: '6px 8px',
                background: 'rgba(0,0,0,0.18)', borderRadius: '6px',
              }}>
                {swatches.map((s, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <div style={{
                      width: '9px', height: '9px', borderRadius: '2px',
                      background: s.color, border: '1px solid rgba(255,255,255,0.12)',
                    }} />
                    <span style={{ fontSize: '9px', color: 'rgba(255,255,255,0.5)' }}>{s.label}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Timelapse / video card ────────────────────────────────────────
function VideoCard({ vid }) {
  const isVideo = vid.url?.endsWith('.mp4');
  return (
    <div style={{
      borderRadius: '10px', overflow: 'hidden',
      border: '1px solid rgba(255,255,255,0.08)',
      background: '#000',
    }}>
      <div style={{ position: 'relative' }}>
        {isVideo
          ? <video src={vid.url} autoPlay loop muted playsInline style={{ width: '100%', display: 'block' }} />
          : <img src={vid.url} alt={vid.caption || 'Timelapse'} style={{ width: '100%', display: 'block' }} />
        }
        {/* Overlay badge */}
        <div style={{
          position: 'absolute', top: '8px', left: '8px',
          background: 'rgba(0,0,0,0.65)', borderRadius: '5px', padding: '2px 8px',
          fontSize: '9px', fontWeight: 700, color: '#a78bfa', letterSpacing: '0.07em',
          backdropFilter: 'blur(4px)', border: '1px solid rgba(167,139,250,0.2)',
        }}>TIMELAPSE</div>
      </div>
      <div style={{ padding: '8px 10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.45)', fontStyle: 'italic' }}>
          {vid.caption || 'Satellite timelapse'}
        </span>
        <a href={vid.url} target="_blank" rel="noopener noreferrer" style={{
          fontSize: '9px', color: '#a78bfa', textDecoration: 'none',
          background: 'rgba(167,139,250,0.1)', padding: '3px 8px', borderRadius: '4px',
        }}>Open ↗</a>
      </div>
    </div>
  );
}

// ── No imagery state ──────────────────────────────────────────────
function NoImageryCard({ text }) {
  const body = text.replace(/^⚠️\s*No suitable Sentinel-2[^\n]*\n\n?/, '').trim();
  return (
    <div style={{
      background: 'rgba(245,158,11,0.06)',
      border: '1px solid rgba(245,158,11,0.18)',
      borderRadius: '10px', padding: '14px 16px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
        <span style={{ fontSize: '16px' }}>🌫</span>
        <span style={{ fontWeight: 700, color: '#fbbf24', fontSize: '13px' }}>No clear imagery available</span>
      </div>
      <div style={{ fontSize: '12px', color: '#e5e7eb', lineHeight: '1.65', marginBottom: '10px' }}>
        <MarkdownContent text={body} />
      </div>
      <div style={{ padding: '8px 10px', background: 'rgba(0,0,0,0.2)', borderRadius: '6px' }}>
        <div style={{ fontSize: '9px', fontWeight: 700, color: 'rgba(255,255,255,0.3)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.07em' }}>Try</div>
        <div style={{ fontSize: '11px', color: '#d1d5db', lineHeight: '1.6' }}>
          Expand the date range · Increase the cloud-cover threshold · Use a larger AOI
        </div>
      </div>
    </div>
  );
}

// ── Report card ───────────────────────────────────────────────────
function ReportCard({ url }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '12px',
      padding: '12px 14px',
      background: 'rgba(59,130,246,0.05)',
      border: '1px solid rgba(59,130,246,0.18)',
      borderRadius: '10px',
    }}>
      <div style={{
        width: '34px', height: '34px', borderRadius: '8px', flexShrink: 0,
        background: 'rgba(59,130,246,0.1)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: '16px',
      }}>📄</div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: '12px', fontWeight: 600, color: '#fff', marginBottom: '2px' }}>Analysis Report Generated</div>
        <div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.4)' }}>Full geospatial report · DOCX format</div>
      </div>
      <div style={{ display: 'flex', gap: '6px', flexShrink: 0 }}>
        <a href={url} target="_blank" rel="noopener noreferrer" style={{
          display: 'inline-flex', alignItems: 'center', gap: '4px',
          padding: '6px 12px',
          background: 'rgba(59,130,246,0.12)', border: '1px solid rgba(59,130,246,0.25)',
          borderRadius: '7px', color: '#93c5fd',
          textDecoration: 'none', fontSize: '11px', fontWeight: 600,
        }}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ width: '11px', height: '11px' }}>
            <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6" /><polyline points="15 3 21 3 21 9" /><line x1="10" y1="14" x2="21" y2="3" />
          </svg>
          View
        </a>
        <a href={url} download style={{
          display: 'inline-flex', alignItems: 'center', gap: '4px',
          padding: '6px 12px',
          background: 'transparent', border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: '7px', color: 'rgba(255,255,255,0.5)',
          textDecoration: 'none', fontSize: '11px', fontWeight: 500,
        }}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ width: '11px', height: '11px' }}>
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          Download
        </a>
      </div>
    </div>
  );
}

// ── Quality / confidence card ────────────────────────────────────
function QualityCard({ quality }) {
  if (!quality || quality.status === 'sufficient') return null;
  const issues = quality.issues?.filter(Boolean) || [];
  if (issues.length === 0 && quality.status !== 'insufficient') return null;

  return (
    <div style={{
      background: 'rgba(245,158,11,0.05)',
      border: '1px solid rgba(245,158,11,0.15)',
      borderRadius: '8px', padding: '10px 12px',
      display: 'flex', gap: '8px',
    }}>
      <span style={{ fontSize: '13px', flexShrink: 0 }}>⚠</span>
      <div>
        <div style={{ fontSize: '11px', fontWeight: 600, color: '#fbbf24', marginBottom: '4px' }}>
          Evidence quality: {quality.status}
        </div>
        {issues.map((issue, i) => (
          <div key={i} style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)', lineHeight: '1.5' }}>
            {issue}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Replanning badge ─────────────────────────────────────────────
function ReplanningNote({ replanning }) {
  if (!replanning?.performed || !replanning.count) return null;
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', gap: '5px',
      fontSize: '9px', color: 'rgba(255,255,255,0.3)',
      background: 'rgba(255,255,255,0.03)',
      border: '1px solid rgba(255,255,255,0.06)',
      borderRadius: '5px', padding: '3px 8px',
    }}>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ width: '10px', height: '10px' }}>
        <polyline points="23 4 23 10 17 10" /><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10" />
      </svg>
      Re-analysed {replanning.count} time{replanning.count !== 1 ? 's' : ''} for accuracy
    </div>
  );
}

// ── Tools used footer ────────────────────────────────────────────
const TOOL_LABELS = {
  gee_search_imagery: 'Imagery search',
  gee_calculate_indices: 'Index computation',
  gee_get_zonal_statistics: 'Zonal stats',
  gee_get_temporal_series: 'Temporal series',
  gee_analyze_trend: 'Trend analysis',
  gee_analyze_seasonality: 'Seasonality',
  gee_analyze_change_persistence: 'Change persistence',
  gee_detect_temporal_breaks: 'Change detection',
  gee_compare_periods: 'Period comparison',
  gee_calculate_change_area: 'Change area',
  gee_detect_anomalies: 'Anomaly detection',
  gee_get_subregion_statistics: 'Subregion stats',
  gee_generate_timeline_artifact: 'Timeline',
};

function ToolsFooter({ tools }) {
  if (!tools?.length) return null;
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
      {tools.map((t, i) => (
        <span key={i} style={{
          fontSize: '9px', padding: '2px 6px',
          background: 'rgba(255,255,255,0.03)',
          border: '1px solid rgba(255,255,255,0.05)',
          borderRadius: '4px', color: 'rgba(255,255,255,0.2)',
        }}>
          {TOOL_LABELS[t] || t.replace('gee_', '').replace(/_/g, ' ')}
        </span>
      ))}
    </div>
  );
}

// ════════════════════════════════════════════════════════════════
// Main ChatMessage export
// ════════════════════════════════════════════════════════════════
export default function ChatMessage({ msg, jobId, onTimelineFrame }) {
  // User bubble — handled by MapPage (no change needed here for new layout)
  // This component only renders assistant messages
  if (msg.role === 'user') return null; // MapPage renders user bubbles inline

  // ── Extract all backend fields ────────────────────────────────
  const {
    text, findings = [], visualEvidence = [],
    media = { images: [], videos: [] },
    quality = {}, limitations = [],
    replanning, provenance, provenanceStatus,
    timelineData, documentUrl,
    toolsUsed = [], isTyping, timestamp,
  } = msg;

  const images  = media?.images?.length > 0 ? media.images : visualEvidence;
  const videos  = media?.videos || [];

  const isNoImagery = quality.status === 'insufficient' && text?.startsWith('⚠️ No suitable Sentinel-2');

  // Filter boilerplate limitations that add no user value
  const BOILERPLATE = [
    'No Sentinel-2 scene satisfied', 'Maximum tool calls',
    'seasonality analysis was not feasible', 'data timestamp limitation',
    'interpret with caution', 'permanent versus seasonal',
    'temporal resolution', 'statistical uncertainty',
    'not a substitute for', 'ground-truth verification',
    'cloud cover may have affected',
  ];
  const actionableLimitations = limitations.filter(l =>
    l && !BOILERPLATE.some(p => l.toLowerCase().includes(p.toLowerCase()))
  );
  const showFindings = findings.length >= 2;

  // Split answer from the visual analysis section (appended by backend)
  const [mainAnswer, visualAnalysis] = (() => {
    const sep = '\n\n---\n**🛰 Visual Analysis**\n\n';
    const idx = text?.indexOf(sep);
    if (idx !== undefined && idx >= 0 && text) {
      return [text.slice(0, idx), text.slice(idx + sep.length)];
    }
    return [text || '', null];
  })();

  return (
    <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-start', animation: 'msgIn 0.4s cubic-bezier(0.2, 0.8, 0.2, 1) forwards' }}>
      <style>{ANIM_STYLE}</style>

      {/* Avatar */}
      <div style={{
        width: '22px', height: '22px', borderRadius: '5px', flexShrink: 0,
        background: 'rgba(255,255,255,0.05)',
        border: '1px solid rgba(255,255,255,0.1)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: '11px', marginTop: '2px',
      }}>🛰</div>

      {/* Content column */}
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: '10px' }}>

        {/* ── 1. AI Answer ─────────────────────────────────────── */}
        {isNoImagery ? (
          <NoImageryCard text={text} />
        ) : mainAnswer ? (
          <div style={{
            fontSize: '13px', lineHeight: '1.75', color: '#cbd5e1',
            padding: '12px 14px',
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: '4px 12px 12px 12px',
            wordBreak: 'break-word',
          }}>
            <MarkdownContent text={mainAnswer} />
          </div>
        ) : null}

        {/* ── 2. Key Findings ───────────────────────────────────── */}
        {showFindings && (
          <Section icon="📋" label="Key Findings" badge={findings.length}
            accentColor="rgba(255,255,255,0.35)" collapsible defaultOpen>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {findings.map((f, i) => (
                <div key={i} style={{
                  display: 'flex', gap: '8px',
                  padding: '7px 10px',
                  background: 'rgba(34,197,94,0.04)',
                  border: '1px solid rgba(34,197,94,0.1)',
                  borderRadius: '7px',
                }}>
                  <span style={{ color: '#22c55e', flexShrink: 0, marginTop: '1px', fontSize: '11px' }}>✓</span>
                  <span style={{ fontSize: '12px', color: '#e2e8f0', lineHeight: '1.6', minWidth: 0 }}>{f}</span>
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* ── 3. Timelapse videos (first, above images) ─────────── */}
        {videos.length > 0 && (
          <Section icon="🎬" label="Satellite Timelapse" accentColor="rgba(167,139,250,0.6)">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {videos.map((vid, i) => <VideoCard key={i} vid={vid} />)}
            </div>
          </Section>
        )}

        {/* ── 4. Satellite Images ───────────────────────────────── */}
        {images.length > 0 && (
          <Section icon="🛰" label="Satellite Evidence" badge={images.length}
            accentColor="rgba(255,255,255,0.35)">
            <ImageGrid images={images} />
          </Section>
        )}

        {/* ── 5. Visual Analysis from OpenAI vision ────────────── */}
        {visualAnalysis && (
          <Section icon="🔬" label="Visual Interpretation" accentColor="rgba(96,165,250,0.6)">
            <div style={{
              padding: '10px 12px',
              background: 'rgba(59,130,246,0.04)',
              border: '1px solid rgba(59,130,246,0.12)',
              borderRadius: '8px',
              fontSize: '12px', color: '#94a3b8', lineHeight: '1.7',
            }}>
              <MarkdownContent text={visualAnalysis} />
            </div>
          </Section>
        )}

        {/* ── 6. Visual Evidence from agent (if separate) ──────── */}
        {visualEvidence.length > 0 && images.length === 0 && (
          <Section icon="📸" label="Visual Evidence" badge={visualEvidence.length}
            accentColor="rgba(255,255,255,0.35)">
            <VisualEvidence items={visualEvidence} />
          </Section>
        )}

        {/* ── 7. Quality / Confidence ───────────────────────────── */}
        <QualityCard quality={quality} />

        {/* ── 8. Limitations (actionable only) ─────────────────── */}
        {actionableLimitations.length > 0 && (
          <Section icon="ℹ" label="Analysis Caveats" badge={actionableLimitations.length}
            badgeColor="#fbbf24" badgeBg="rgba(245,158,11,0.1)"
            accentColor="rgba(245,158,11,0.5)" collapsible defaultOpen={false}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '5px', paddingTop: '2px' }}>
              {actionableLimitations.map((lim, i) => (
                <div key={i} style={{
                  display: 'flex', gap: '7px', fontSize: '12px',
                  color: 'rgba(255,255,255,0.55)', lineHeight: '1.6',
                }}>
                  <span style={{ color: '#f59e0b', flexShrink: 0, marginTop: '1px' }}>·</span>
                  {lim}
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* ── 9. Replanning note ────────────────────────────────── */}
        <ReplanningNote replanning={replanning} />

        {/* ── 10. Evidence / Provenance ─────────────────────────── */}
        {(provenance || provenanceStatus) && jobId && (
          <EvidencePanel jobId={jobId} provenance={provenance} provenanceStatus={provenanceStatus} />
        )}

        {/* ── 11. Timeline player ────────────────────────────────── */}
        {timelineData?.frames?.length > 0 && (
          <Section icon="📅" label="Temporal Analysis" accentColor="rgba(255,255,255,0.35)">
            <TimelinePlayer data={timelineData} onFrameChange={onTimelineFrame || (() => {})} />
          </Section>
        )}

        {/* ── 12. Report download ─────────────────────────────────── */}
        {documentUrl && <ReportCard url={documentUrl} />}

        {/* ── 13. Tools used (subtle footer) ─────────────────────── */}
        <ToolsFooter tools={toolsUsed} />

        {/* ── Timestamp ────────────────────────────────────────────── */}
        {timestamp && (
          <div style={{ fontSize: '9px', color: 'rgba(255,255,255,0.18)', marginTop: '-4px' }}>
            {timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>
        )}
      </div>
    </div>
  );
}
