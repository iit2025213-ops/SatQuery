import React, { useState } from 'react';
import VisualEvidence from './VisualEvidence';
import EvidencePanel from './EvidencePanel';
import TimelinePlayer from './TimelinePlayer';

// ── Animation ───────────────────────────────────────────────────────
const ANIM_STYLE = `
  @keyframes msgIn { from{opacity:0;transform:translateY(6px)} to{opacity:1;transform:translateY(0)} }
  @keyframes blink { 0%,80%,100%{opacity:0} 40%{opacity:1} }
`;

// ── Inline Markdown ─────────────────────────────────────────────────
function inlineMd(str) {
  // Bold, italic, inline code
  const parts = str.split(/(\*\*.*?\*\*|__.*?__|\*.*?\*|`[^`]+`)/g);
  return parts.map((p, i) => {
    if (p.startsWith('**') || p.startsWith('__'))
      return <strong key={i} style={{ color: '#F5F5F5', fontWeight: 600 }}>{p.slice(2, -2)}</strong>;
    if (p.startsWith('*') && p.endsWith('*'))
      return <em key={i}>{p.slice(1, -1)}</em>;
    if (p.startsWith('`'))
      return <code key={i} style={{ fontFamily: 'monospace', fontSize: '0.92em', background: '#1E1E1E', padding: '1px 5px', borderRadius: '3px', color: '#E5E5E5' }}>{p.slice(1, -1)}</code>;
    return p;
  });
}

// ── Full Markdown content renderer ──────────────────────────────────
function MarkdownContent({ text, large }) {
  if (!text) return null;

  const baseFontSize = large ? '17px' : '15px';
  const baseLineHeight = large ? '1.72' : '1.68';
  const baseColor = '#EDEDED';

  const lines = text.split('\n');
  const elements = [];
  let listBuffer = [];
  let numListBuffer = [];
  let inCodeBlock = false;
  let codeLines = [];
  let codeLang = '';

  const flushList = () => {
    if (listBuffer.length) {
      elements.push(
        <ul key={elements.length} style={{ margin: '8px 0', paddingLeft: '0', display: 'flex', flexDirection: 'column', gap: '5px', listStyle: 'none' }}>
          {listBuffer.map((item, i) => (
            <li key={i} style={{ display: 'flex', gap: '10px', fontSize: baseFontSize, color: baseColor, lineHeight: baseLineHeight }}>
              <span style={{ color: '#666', flexShrink: 0, userSelect: 'none', marginTop: '2px' }}>○</span>
              <span style={{ flex: 1, minWidth: 0 }}>{inlineMd(item)}</span>
            </li>
          ))}
        </ul>
      );
      listBuffer = [];
    }
    if (numListBuffer.length) {
      elements.push(
        <ol key={elements.length} style={{ margin: '8px 0', paddingLeft: '0', display: 'flex', flexDirection: 'column', gap: '5px', listStyle: 'none' }}>
          {numListBuffer.map((item, i) => (
            <li key={i} style={{ display: 'flex', gap: '10px', fontSize: baseFontSize, color: baseColor, lineHeight: baseLineHeight }}>
              <span style={{ color: '#666', flexShrink: 0, userSelect: 'none', minWidth: '18px' }}>{i + 1}.</span>
              <span style={{ flex: 1, minWidth: 0 }}>{inlineMd(item)}</span>
            </li>
          ))}
        </ol>
      );
      numListBuffer = [];
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Code block toggle
    if (line.startsWith('```')) {
      if (!inCodeBlock) {
        flushList();
        inCodeBlock = true;
        codeLang = line.slice(3).trim();
        codeLines = [];
      } else {
        inCodeBlock = false;
        elements.push(
          <pre key={elements.length} style={{
            background: '#141414', border: '1px solid #2A2A2A',
            borderRadius: '8px', padding: '14px 16px', margin: '10px 0',
            fontSize: '13px', color: '#D4D4D4', overflowX: 'auto',
            fontFamily: "'Fira Code', 'Cascadia Code', monospace", lineHeight: '1.55',
            whiteSpace: 'pre',
          }}>
            {codeLang && <div style={{ fontSize: '10px', color: '#555', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{codeLang}</div>}
            {codeLines.join('\n')}
          </pre>
        );
        codeLines = [];
        codeLang = '';
      }
      continue;
    }
    if (inCodeBlock) { codeLines.push(line); continue; }

    // Image
    const imgMatch = line.match(/!\[([^\]]*)\]\((https?:\/\/[^\s)]+)\)/);
    if (imgMatch) {
      flushList();
      elements.push(
        <div key={elements.length} style={{ margin: '12px 0' }}>
          <img src={imgMatch[2]} alt={imgMatch[1]} loading="lazy" style={{ width: '100%', borderRadius: '6px', display: 'block' }} />
          {imgMatch[1] && <div style={{ fontSize: '11px', color: '#555', marginTop: '5px', textAlign: 'center', fontStyle: 'italic' }}>{imgMatch[1]}</div>}
        </div>
      );
      continue;
    }

    // HR
    if (/^---+$/.test(line.trim())) {
      flushList();
      elements.push(<div key={elements.length} style={{ height: '1px', background: '#222', margin: '16px 0' }} />);
      continue;
    }

    // Headings
    if (line.startsWith('#### ')) {
      flushList();
      elements.push(<div key={elements.length} style={{ fontSize: '14px', fontWeight: 600, color: '#F5F5F5', margin: '16px 0 6px' }}>{inlineMd(line.slice(5))}</div>);
      continue;
    }
    if (line.startsWith('### ')) {
      flushList();
      elements.push(<div key={elements.length} style={{ fontSize: large ? '16px' : '14px', fontWeight: 600, color: '#F5F5F5', margin: '20px 0 8px' }}>{inlineMd(line.slice(4))}</div>);
      continue;
    }
    if (line.startsWith('## ')) {
      flushList();
      elements.push(<div key={elements.length} style={{ fontSize: large ? '18px' : '16px', fontWeight: 700, color: '#F5F5F5', margin: '22px 0 8px' }}>{inlineMd(line.slice(3))}</div>);
      continue;
    }
    if (line.startsWith('# ')) {
      flushList();
      elements.push(<div key={elements.length} style={{ fontSize: large ? '21px' : '18px', fontWeight: 700, color: '#FFFFFF', margin: '24px 0 10px' }}>{inlineMd(line.slice(2))}</div>);
      continue;
    }

    // Bullets
    if (line.startsWith('- ') || line.startsWith('* ') || line.startsWith('• ')) {
      numListBuffer.length && flushList();
      listBuffer.push(line.slice(2));
      continue;
    }

    // Numbered
    const numMatch = line.match(/^(\d+)\.\s+(.*)/);
    if (numMatch) {
      listBuffer.length && flushList();
      numListBuffer.push(numMatch[2]);
      continue;
    }

    // Blank line
    if (!line.trim()) {
      flushList();
      elements.push(<div key={elements.length} style={{ height: '10px' }} />);
      continue;
    }

    // Paragraph
    flushList();
    elements.push(
      <p key={elements.length} style={{ margin: 0, fontSize: baseFontSize, color: baseColor, lineHeight: baseLineHeight, wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
        {inlineMd(line)}
      </p>
    );
  }

  flushList();
  return <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', minWidth: 0 }}>{elements}</div>;
}

// ── Satellite image card ─────────────────────────────────────────────
const INDEX_ACCENT = { NDVI: '#22c55e', NDWI: '#3b82f6', NDBI: '#f97316', NBR: '#ef4444', RGB: '#a78bfa' };
const INDEX_SWATCHES = {
  NDVI:  [{ color: '#14532d', label: 'Dense forest' }, { color: '#4ade80', label: 'Vegetation' }, { color: '#fde68a', label: 'Sparse' }, { color: '#92400e', label: 'Bare soil' }],
  NDWI:  [{ color: '#1e3a8a', label: 'Deep water' }, { color: '#60a5fa', label: 'High moisture' }, { color: '#d1d5db', label: 'Dry land' }],
  NDBI:  [{ color: '#dc2626', label: 'Dense urban' }, { color: '#fb923c', label: 'Built-up' }, { color: '#fef08a', label: 'Mixed' }, { color: '#4ade80', label: 'Vegetation' }],
  NBR:   [{ color: '#14532d', label: 'Unburned' }, { color: '#fde68a', label: 'Low severity' }, { color: '#7f1d1d', label: 'High severity' }],
  RGB:   [{ color: '#4ade80', label: 'Vegetation' }, { color: '#a3a3a3', label: 'Urban' }, { color: '#1e40af', label: 'Water' }],
};

function SatImageCard({ img, compact }) {
  const [err, setErr] = useState(false);
  const url = img.url || img.thumbnail_url;
  const label = img.caption || img.index || img.type || 'Satellite image';
  const idxKey = (img.index || '').toUpperCase();
  const accent = INDEX_ACCENT[idxKey] || '#888';
  if (!url) return null;

  return (
    <div style={{ borderRadius: '8px', overflow: 'hidden', background: '#111', flex: compact ? '1 1 0' : undefined, minWidth: 0 }}>
      {err ? (
        <div style={{ aspectRatio: '16/9', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#0D0D0D', color: '#444', fontSize: '12px', gap: '6px' }}>
          No image
        </div>
      ) : (
        <img src={url} alt={label} loading="lazy"
          style={{ width: '100%', display: 'block', maxHeight: compact ? '200px' : '280px', objectFit: 'cover' }}
          onError={() => setErr(true)}
        />
      )}
      <div style={{ padding: '8px 10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px' }}>
        <div>
          <div style={{ fontSize: '11px', fontWeight: 600, color: accent, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{idxKey || label}</div>
          <div style={{ fontSize: '10px', color: '#555', marginTop: '1px', fontStyle: 'italic', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '200px' }}>{label}</div>
        </div>
        <a href={url} target="_blank" rel="noopener noreferrer"
          style={{ fontSize: '10px', color: '#555', textDecoration: 'none', flexShrink: 0 }}
          title="Open full image">↗</a>
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
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {Object.entries(groups).map(([idx, imgs]) => {
        const swatches = INDEX_SWATCHES[idx] || [];
        const isBefore = imgs.length >= 2;
        return (
          <div key={idx}>
            <div style={{ fontSize: '11px', fontWeight: 600, color: '#666', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: '8px' }}>
              {idx}{isBefore ? ' · Before / After' : ''}
            </div>
            {isBefore ? (
              <div style={{ display: 'flex', gap: '6px' }}>
                {imgs.slice(0, 2).map((img, i) => <SatImageCard key={i} img={img} compact />)}
              </div>
            ) : (
              <SatImageCard img={imgs[0]} />
            )}
            {swatches.length > 0 && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '8px' }}>
                {swatches.map((s, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                    <div style={{ width: '8px', height: '8px', borderRadius: '2px', background: s.color, border: '1px solid rgba(255,255,255,0.1)' }} />
                    <span style={{ fontSize: '10px', color: '#555' }}>{s.label}</span>
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

// ── Timelapse card ──────────────────────────────────────────────────
function VideoCard({ vid }) {
  const isVideo = vid.url?.endsWith('.mp4');
  return (
    <div style={{ borderRadius: '8px', overflow: 'hidden', background: '#111' }}>
      {isVideo
        ? <video src={vid.url} autoPlay loop muted playsInline style={{ width: '100%', display: 'block' }} />
        : <img src={vid.url} alt={vid.caption || 'Timelapse'} style={{ width: '100%', display: 'block' }} />}
      <div style={{ padding: '8px 10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '11px', color: '#555', fontStyle: 'italic' }}>{vid.caption || 'Satellite timelapse'}</span>
        <a href={vid.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: '10px', color: '#555', textDecoration: 'none' }}>↗</a>
      </div>
    </div>
  );
}

// ── Section label ───────────────────────────────────────────────────
function SectionLabel({ label, collapsible, open, onToggle }) {
  return (
    <div
      onClick={collapsible ? onToggle : undefined}
      style={{
        fontSize: '11px', fontWeight: 600, color: '#555',
        textTransform: 'uppercase', letterSpacing: '0.09em',
        cursor: collapsible ? 'pointer' : 'default',
        userSelect: 'none', display: 'flex', alignItems: 'center', gap: '6px',
        marginBottom: '10px',
      }}
    >
      {label}
      {collapsible && (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          style={{ width: '10px', height: '10px', transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}>
          <polyline points="6 9 12 15 18 9" />
        </svg>
      )}
    </div>
  );
}

function CollapsibleSection({ label, defaultOpen = true, children }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div style={{ marginTop: '22px' }}>
      <SectionLabel label={label} collapsible open={open} onToggle={() => setOpen(o => !o)} />
      {open && children}
    </div>
  );
}

// ── No imagery state ────────────────────────────────────────────────
function NoImageryState({ text }) {
  const body = text.replace(/^⚠️\s*No suitable Sentinel-2[^\n]*\n\n?/, '').trim();
  return (
    <div>
      <div style={{ fontSize: '15px', color: '#888', marginBottom: '10px' }}>No clear imagery available for this area and time period.</div>
      <div style={{ fontSize: '14px', color: '#666', lineHeight: '1.65' }}>
        <MarkdownContent text={body} />
      </div>
      <div style={{ marginTop: '14px', fontSize: '13px', color: '#555' }}>
        Try expanding the date range, increasing the cloud-cover threshold, or selecting a larger area.
      </div>
    </div>
  );
}

// ── Report row ──────────────────────────────────────────────────────
function ReportRow({ url }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '22px', paddingTop: '18px', borderTop: '1px solid #1A1A1A' }}>
      <span style={{ fontSize: '13px', color: '#555' }}>Analysis Report</span>
      <a href={url} target="_blank" rel="noopener noreferrer"
        style={{ fontSize: '12px', color: '#888', textDecoration: 'none', marginLeft: 'auto' }}>
        View ↗
      </a>
      <a href={url} download
        style={{ fontSize: '12px', color: '#555', textDecoration: 'none' }}>
        Download
      </a>
    </div>
  );
}

// ── Tools footer ────────────────────────────────────────────────────
const TOOL_LABELS = {
  gee_search_imagery: 'Imagery search', gee_calculate_indices: 'Index computation',
  gee_get_zonal_statistics: 'Zonal stats', gee_get_temporal_series: 'Temporal series',
  gee_analyze_trend: 'Trend analysis', gee_analyze_seasonality: 'Seasonality',
  gee_analyze_change_persistence: 'Change persistence', gee_detect_temporal_breaks: 'Change detection',
  gee_compare_periods: 'Period comparison', gee_calculate_change_area: 'Change area',
  gee_detect_anomalies: 'Anomaly detection', gee_generate_timeline_artifact: 'Timeline',
};

function ToolsRow({ tools }) {
  if (!tools?.length) return null;
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '16px', paddingTop: '14px', borderTop: '1px solid #181818' }}>
      {tools.map((t, i) => (
        <span key={i} style={{ fontSize: '10px', color: '#3A3A3A', letterSpacing: '0.03em' }}>
          {TOOL_LABELS[t] || t.replace('gee_', '').replace(/_/g, ' ')}
          {i < tools.length - 1 ? ' ·' : ''}
        </span>
      ))}
    </div>
  );
}

// ── Copy / action bar ───────────────────────────────────────────────
function ActionBar({ text }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard?.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    });
  };
  return (
    <div className="msg-action-bar" style={{
      display: 'flex', alignItems: 'center', gap: '12px',
      marginTop: '10px', opacity: 0, transition: 'opacity 0.15s',
    }}>
      <button onClick={handleCopy} title="Copy" style={{
        background: 'none', border: 'none', cursor: 'pointer', padding: '4px',
        color: copied ? '#888' : '#3A3A3A', display: 'flex', alignItems: 'center', gap: '4px',
        fontSize: '11px', transition: 'color 0.15s',
      }}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={{ width: '13px', height: '13px' }}>
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
          <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
        </svg>
        {copied ? 'Copied' : 'Copy'}
      </button>
      <style>{`.msg-action-bar { opacity: 0; } .msg-wrapper:hover .msg-action-bar { opacity: 1; }`}</style>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════
// Main ChatMessage export
// ════════════════════════════════════════════════════════════════════
export default function ChatMessage({ msg, jobId, onTimelineFrame }) {
  if (msg.role === 'user') return null;

  const {
    text, findings = [], visualEvidence = [],
    media = { images: [], videos: [] },
    quality = {}, limitations = [],
    replanning, provenance, provenanceStatus,
    timelineData, documentUrl,
    toolsUsed = [], isTyping, timestamp,
  } = msg;

  const images = media?.images?.length > 0 ? media.images : visualEvidence;
  const videos = media?.videos || [];
  const isNoImagery = quality.status === 'insufficient' && text?.startsWith('⚠️ No suitable Sentinel-2');

  const BOILERPLATE = [
    'No Sentinel-2 scene satisfied', 'Maximum tool calls', 'seasonality analysis was not feasible',
    'data timestamp limitation', 'interpret with caution', 'permanent versus seasonal',
    'temporal resolution', 'statistical uncertainty', 'not a substitute for',
    'ground-truth verification', 'cloud cover may have affected',
  ];
  const actionableLimitations = limitations.filter(l =>
    l && !BOILERPLATE.some(p => l.toLowerCase().includes(p.toLowerCase()))
  );
  const showFindings = findings.length >= 2;

  const [mainAnswer, visualAnalysis] = (() => {
    const sep = '\n\n---\n**🛰 Visual Analysis**\n\n';
    const idx = text?.indexOf(sep);
    if (idx !== undefined && idx >= 0 && text) return [text.slice(0, idx), text.slice(idx + sep.length)];
    return [text || '', null];
  })();

  return (
    <div className="msg-wrapper" style={{ animation: 'msgIn 0.4s ease forwards', minWidth: 0 }}>
      <style>{ANIM_STYLE}</style>

      {/* ── 1. Main answer — plain on background, no card ─────────── */}
      {isNoImagery ? (
        <NoImageryState text={text} />
      ) : mainAnswer ? (
        <div style={{ minWidth: 0 }}>
          <MarkdownContent text={mainAnswer} large />
        </div>
      ) : null}

      {/* Visual analysis from OpenAI vision */}
      {visualAnalysis && (
        <div style={{ marginTop: '18px' }}>
          <SectionLabel label="Visual Interpretation" />
          <div style={{ fontSize: '15px', color: '#AAAAAA', lineHeight: '1.68' }}>
            <MarkdownContent text={visualAnalysis} />
          </div>
        </div>
      )}

      {/* ── 2. Key Findings ─────────────────────────────────────────── */}
      {showFindings && (
        <div style={{ marginTop: '24px' }}>
          <SectionLabel label="Key Findings" />
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {findings.map((f, i) => (
              <div key={i} style={{ display: 'flex', gap: '10px', fontSize: '15px', color: '#EDEDED', lineHeight: '1.65' }}>
                <span style={{ color: '#3A3A3A', flexShrink: 0, marginTop: '2px', userSelect: 'none' }}>○</span>
                <span style={{ flex: 1, minWidth: 0, overflowWrap: 'anywhere' }}>{f}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── 3. Timelapse videos ──────────────────────────────────────── */}
      {videos.length > 0 && (
        <CollapsibleSection label="Satellite Timelapse">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {videos.map((vid, i) => <VideoCard key={i} vid={vid} />)}
          </div>
        </CollapsibleSection>
      )}

      {/* ── 4. Satellite Images ──────────────────────────────────────── */}
      {images.length > 0 && (
        <div style={{ marginTop: '24px' }}>
          <SectionLabel label="Satellite Evidence" />
          <ImageGrid images={images} />
        </div>
      )}

      {/* ── 5. Visual Evidence from agent ───────────────────────────── */}
      {visualEvidence.length > 0 && images.length === 0 && (
        <div style={{ marginTop: '24px' }}>
          <SectionLabel label="Visual Evidence" />
          <VisualEvidence items={visualEvidence} />
        </div>
      )}

      {/* ── 6. Quality (only if insufficient) ───────────────────────── */}
      {quality?.status && quality.status !== 'sufficient' && (
        <div style={{ marginTop: '22px' }}>
          <SectionLabel label="Data Quality" />
          <div style={{ fontSize: '14px', color: '#666', lineHeight: '1.6' }}>
            {quality.status.charAt(0).toUpperCase() + quality.status.slice(1)}.
            {quality.issues?.filter(Boolean).map((issue, i) => (
              <div key={i} style={{ marginTop: '4px' }}>{issue}</div>
            ))}
          </div>
        </div>
      )}

      {/* ── 7. Limitations ──────────────────────────────────────────── */}
      {actionableLimitations.length > 0 && (
        <CollapsibleSection label="Caveats" defaultOpen={false}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
            {actionableLimitations.map((lim, i) => (
              <div key={i} style={{ display: 'flex', gap: '8px', fontSize: '14px', color: '#666', lineHeight: '1.6' }}>
                <span style={{ color: '#3A3A3A', flexShrink: 0 }}>·</span>
                <span style={{ flex: 1, minWidth: 0, overflowWrap: 'anywhere' }}>{lim}</span>
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* ── 8. Replanning note ───────────────────────────────────────── */}
      {replanning?.performed && replanning.count > 0 && (
        <div style={{ fontSize: '11px', color: '#3A3A3A', marginTop: '14px' }}>
          Re-analysed {replanning.count} time{replanning.count !== 1 ? 's' : ''} for accuracy
        </div>
      )}

      {/* ── 9. Evidence / Provenance (collapsible) ──────────────────── */}
      {(provenance || provenanceStatus) && jobId && (
        <CollapsibleSection label="Evidence & Sources" defaultOpen={false}>
          <EvidencePanel jobId={jobId} provenance={provenance} provenanceStatus={provenanceStatus} />
        </CollapsibleSection>
      )}

      {/* ── 10. Timeline player ─────────────────────────────────────── */}
      {timelineData?.frames?.length > 0 && (
        <CollapsibleSection label="Temporal Analysis">
          <TimelinePlayer data={timelineData} onFrameChange={onTimelineFrame || (() => {})} />
        </CollapsibleSection>
      )}

      {/* ── 11. Report ──────────────────────────────────────────────── */}
      {documentUrl && <ReportRow url={documentUrl} />}

      {/* ── 12. Tools used ──────────────────────────────────────────── */}
      <ToolsRow tools={toolsUsed} />

      {/* ── 13. Copy action + timestamp ─────────────────────────────── */}
      <ActionBar text={mainAnswer || text || ''} />
      {timestamp && (
        <div style={{ fontSize: '10px', color: '#2A2A2A', marginTop: '6px' }}>
          {typeof timestamp.toLocaleTimeString === 'function' 
            ? timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            : new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          }
        </div>
      )}
    </div>
  );
}
