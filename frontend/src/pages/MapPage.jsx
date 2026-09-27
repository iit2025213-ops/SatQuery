import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import AOIMap from '../components/AOIMap';
import TimelinePlayer from '../components/TimelinePlayer';
import ChatMessage from '../components/ChatMessage';
import AnalysisStatus from '../components/AnalysisStatus';
import { apiPost, apiUpload, apiGet, apiPut } from '../utils/api';
import UserMessage from '../components/UserMessage';

// ── Geo-Agent Status Badge ────────────────────────────────────────
function AgentStatusBadge({ loading, messages, errorState, compact }) {
  let state = 'ready';
  if (errorState) state = 'error';
  else if (loading) state = 'analysing';
  else if (messages.some(m => m.role === 'assistant' && !m.isTyping)) state = 'complete';

  const config = {
    ready:     { dot: '#333', label: 'Ready' },
    analysing: { dot: '#555', label: 'Analysing', pulse: true },
    complete:  { dot: '#3A3A3A', label: 'Complete' },
    error:     { dot: '#4A2020', label: 'Error' },
  };
  const c = config[state];

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
      <div style={{
        width: '5px', height: '5px', borderRadius: '50%',
        background: c.dot,
        animation: c.pulse ? 'satPulse 1.6s ease-in-out infinite' : 'none',
      }} />
      <span style={{ fontSize: '11px', color: '#333', letterSpacing: '0.03em' }}>
        {c.label}
      </span>
    </div>
  );
}

// ── Floating AOI Info Card — matches reference exactly ────────────

function AoiInfoCard({ aoi, analysisMode, jobStatus }) {
  if (!aoi) return null;

  const coords = aoi.coordinates?.[0] || [];
  const centroid = coords.length > 0 ? {
    lng: (Math.min(...coords.map(c => c[0])) + Math.max(...coords.map(c => c[0]))) / 2,
    lat: (Math.min(...coords.map(c => c[1])) + Math.max(...coords.map(c => c[1]))) / 2,
  } : null;

  // Approx area in km² from bounding box
  const lngs = coords.map(c => c[0]);
  const lats = coords.map(c => c[1]);
  const dLng = (Math.max(...lngs) - Math.min(...lngs)) * 111.32 * Math.cos((centroid?.lat || 0) * Math.PI / 180);
  const dLat = (Math.max(...lats) - Math.min(...lats)) * 110.57;
  const approxArea = (dLng * dLat).toFixed(1);

  const now = new Date();
  const oneYearAgo = new Date(now);
  oneYearAgo.setFullYear(now.getFullYear() - 1);
  const fmtDate = (d) => d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });

  const vertexCount = Math.max(0, coords.length - 1);

  return (
    <div style={{
      position: 'absolute', top: '130px', left: '16px',
      background: 'rgba(8, 10, 20, 0.88)',
      backdropFilter: 'blur(16px)',
      border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: '8px',
      padding: '0',
      zIndex: 5,
      minWidth: '230px',
      maxWidth: '270px',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '9px 12px 8px',
        borderBottom: '1px solid rgba(255,255,255,0.07)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <span style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '0.12em', color: 'rgba(255,255,255,0.7)', textTransform: 'uppercase' }}>Area of Interest</span>
        <svg viewBox="0 0 16 16" fill="none" style={{ width: '12px', height: '12px', color: 'rgba(255,255,255,0.25)', cursor: 'pointer' }}>
          <path d="M2 14l4-1.5L13 5.5 10.5 3 3.5 10 2 14z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
        </svg>
      </div>

      {/* Location name (centroid label) */}
      {centroid && (
        <div style={{ padding: '10px 12px 4px', display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
          <svg viewBox="0 0 16 16" fill="none" style={{ width: '12px', height: '12px', color: 'rgba(255,255,255,0.3)', flexShrink: 0, marginTop: '1px' }}>
            <circle cx="8" cy="7" r="3" stroke="currentColor" strokeWidth="1.5" />
            <path d="M8 14c2-3 5-4.5 5-7a5 5 0 10-10 0c0 2.5 3 4 5 7z" stroke="currentColor" strokeWidth="1.5" />
          </svg>
          <div>
            <div style={{ fontSize: '12px', fontWeight: 600, color: '#f1f5f9', lineHeight: '1.3' }}>
              {centroid.lat.toFixed(2)}° N, {Math.abs(centroid.lng).toFixed(2)}° {centroid.lng >= 0 ? 'E' : 'W'}
            </div>
          </div>
        </div>
      )}

      {/* Data rows */}
      <div style={{ padding: '8px 0 4px' }}>
        <AoiDataRow label="Area" value={`${approxArea} km²`} />
        <AoiDataRow label="Period" value={`${fmtDate(oneYearAgo)} – ${fmtDate(now)}`} />
        <AoiDataRow label="Imagery" value="Sentinel-2 (10m)" />
        <AoiDataRow label="Vertices" value={`${vertexCount} points`} />
        {jobStatus && (
          <AoiDataRow label="Status" value={jobStatus.charAt(0).toUpperCase() + jobStatus.slice(1)}
            valueColor={jobStatus === 'completed' ? '#22c55e' : jobStatus === 'running' ? '#3b82f6' : jobStatus === 'failed' ? '#ef4444' : '#f59e0b'}
          />
        )}
      </div>
    </div>
  );
}

function AoiDataRow({ label, value, valueColor }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center',
      padding: '5px 12px',
      borderTop: '1px solid rgba(255,255,255,0.04)',
    }}>
      <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.35)', flex: '0 0 70px' }}>{label}</span>
      <span style={{ fontSize: '11px', color: valueColor || 'rgba(255,255,255,0.72)', fontVariantNumeric: 'tabular-nums', fontWeight: 500 }}>{value}</span>
    </div>
  );
}

function InfoRow({ icon, label, value, valueColor }) {
  return (
    <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
      <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.25)', width: '12px', flexShrink: 0 }}>{icon}</span>
      <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.4)', flexShrink: 0 }}>{label}</span>
      <span style={{ fontSize: '10px', color: valueColor || 'rgba(255,255,255,0.75)', marginLeft: 'auto', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{value}</span>
    </div>
  );
}

// ── Error State Card ─────────────────────────────────────────────
function AnalysisErrorCard({ errorText, onRetry }) {
  const cleanError = errorText?.replace(/^❌\s*(Error:\s*)?/i, '') || 'An unexpected error occurred.';
  return (
    <div style={{
      background: 'rgba(239, 68, 68, 0.07)',
      border: '1px solid rgba(239, 68, 68, 0.2)',
      borderRadius: '10px', padding: '14px 16px',
      display: 'flex', flexDirection: 'column', gap: '10px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <div style={{
          width: '28px', height: '28px', borderRadius: '6px',
          background: 'rgba(239,68,68,0.12)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '13px', flexShrink: 0,
        }}>⚠</div>
        <div>
          <div style={{ fontSize: '12px', fontWeight: 600, color: '#fca5a5' }}>Analysis Failed</div>
          <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', marginTop: '2px' }}>{cleanError}</div>
        </div>
      </div>
      {onRetry && (
        <button onClick={onRetry} style={{
          background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.25)',
          color: '#fca5a5', borderRadius: '6px', padding: '6px 14px',
          fontSize: '11px', fontWeight: 600, cursor: 'pointer',
          letterSpacing: '0.04em', width: 'fit-content',
          transition: 'all 0.15s',
        }}>
          ↺ Retry Analysis
        </button>
      )}
    </div>
  );
}

// ── Typing indicator ─────────────────────────────────────────────
function GeoAgentTyping() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 0' }}>
      <div style={{
        width: '22px', height: '22px', borderRadius: '50%', flexShrink: 0,
        background: 'linear-gradient(135deg, #1d4ed8, #7c3aed)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px',
      }}>🛰</div>
      <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
        {[0, 0.15, 0.3].map((d, i) => (
          <div key={i} style={{
            width: '5px', height: '5px', borderRadius: '50%',
            background: 'rgba(59,130,246,0.7)',
            animation: `satBounce 1s ${d}s ease-in-out infinite`,
          }} />
        ))}
        <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.35)', marginLeft: '6px' }}>GEE processing...</span>
      </div>
    </div>
  );
}


// ════════════════════════════════════════════════════════════════
// MapPage — Main Export
// ════════════════════════════════════════════════════════════════
export default function MapPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const urlJobId = new URLSearchParams(location.search).get('jobId');

  // Map state
  const [aoi, setAoi] = useState(null);
  const [drawRef, setDrawRef] = useState(null);

  // Chat state
  const [chatOpen, setChatOpen] = useState(false);
  const [panelWidth, setPanelWidth] = useState(() => {
    const saved = localStorage.getItem('satquery:geo-agent-panel-width');
    return saved ? parseInt(saved, 10) : 420;
  });
  const [isResizing, setIsResizing] = useState(false);

  // Resize Handlers
  const handlePointerDown = useCallback((e) => {
    setIsResizing(true);
    e.target.setPointerCapture(e.pointerId);
  }, []);

  const handlePointerMove = useCallback((e) => {
    if (!isResizing) return;
    const newWidth = window.innerWidth - e.clientX;
    const maxWidth = Math.min(750, window.innerWidth * 0.55);
    const clampedWidth = Math.max(320, Math.min(newWidth, maxWidth));
    setPanelWidth(clampedWidth);
  }, [isResizing]);

  const handlePointerUp = useCallback((e) => {
    if (!isResizing) return;
    setIsResizing(false);
    e.target.releasePointerCapture(e.pointerId);
    localStorage.setItem('satquery:geo-agent-panel-width', panelWidth.toString());
  }, [isResizing, panelWidth]);

  const handleKeyDown = useCallback((e) => {
    if (!chatOpen) return;
    if (e.key === 'ArrowLeft') {
      const maxWidth = Math.min(750, window.innerWidth * 0.55);
      const w = Math.min(maxWidth, panelWidth + 20);
      setPanelWidth(w);
      localStorage.setItem('satquery:geo-agent-panel-width', w.toString());
    } else if (e.key === 'ArrowRight') {
      const w = Math.max(320, panelWidth - 20);
      setPanelWidth(w);
      localStorage.setItem('satquery:geo-agent-panel-width', w.toString());
    }
  }, [chatOpen, panelWidth]);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [lastQuery, setLastQuery] = useState('');

  // Attachments and Mic State
  const [attachedAssets, setAttachedAssets] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const fileInputRef = useRef(null);
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef(null);

  // Analysis Mode State
  const [analysisMode, setAnalysisMode] = useState('spatial');

  // Timeline State
  const [timelineData, setTimelineData] = useState(null);
  const [currentTimelineFrame, setCurrentTimelineFrame] = useState(null);

  const chatEndRef = useRef(null);
  const pollingRef = useRef(null);

  // Auto scroll
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Sync messages
  useEffect(() => {
    if (jobId && messages.length > 0) {
      const cleanMessages = messages.filter(m => !m.isTyping && !m.isError);
      apiPut(`/jobs/${jobId}/messages`, { messages: cleanMessages }).catch(console.error);
    }
  }, [messages, jobId]);

  // Restore job from URL
  useEffect(() => {
    if (urlJobId) {
      setJobId(urlJobId);
      loadJob(urlJobId);
    } else {
      setJobId(null);
      setMessages([]);
      setAoi(null);
      setChatOpen(false);
      setTimelineData(null);
      setCurrentTimelineFrame(null);
    }
  }, [urlJobId]);

  async function loadJob(id) {
    try {
      const data = await apiGet(`/jobs/${id}`);
      if (data) {
        if (data.aoi) setAoi(data.aoi);
        setChatOpen(true);
        if (data.options && data.options.messages && Array.isArray(data.options.messages)) {
          setMessages(data.options.messages.filter(m => m != null).map(m => ({
            ...m,
            timestamp: m.timestamp ? new Date(m.timestamp) : new Date()
          })));
        } else {
          setMessages([
            { role: 'user', text: data.query, timestamp: new Date(data.created_at) },
            { 
              role: 'assistant', 
              text: data.final_answer || 'Analysis in progress...', 
              timestamp: new Date(data.updated_at || data.created_at) 
            }
          ]);
        }
        
        // Also fetch timeline if temporal mode is indicated
        if (data.options?.analysis_mode === 'temporal' || data.query?.toLowerCase().includes('timeline')) {
          setAnalysisMode('temporal');
          try {
            const timelineResult = await apiPost('/timeline', { aoi: data.aoi, job_id: id });
            if (timelineResult?.data) {
              setTimelineData(timelineResult.data);
              if (timelineResult.data.frames?.length > 0) setCurrentTimelineFrame(timelineResult.data.frames[0]);
            }
          } catch (e) {
            console.error('Failed to load timeline on restore', e);
          }
        }
      }
    } catch (e) {
      console.error('Failed to restore job', e);
    }
  }

  // Job status polling
  useEffect(() => {
    if (!jobId) return;
    pollingRef.current = setInterval(async () => {
      try {
        const data = await apiGet(`/jobs/${jobId}`);
        setJobStatus(data.status);
        if (data.status === 'completed' && data.final_answer) {
          setMessages(prev => {
            const alreadyHas = prev.some(m => m.role === 'assistant' && m.text === data.final_answer);
            if (!alreadyHas) return [...prev, { role: 'assistant', text: data.final_answer, timestamp: new Date() }];
            return prev;
          });
          clearInterval(pollingRef.current);
        } else if (data.status === 'failed') {
          setMessages(prev => [...prev, { role: 'assistant', text: '❌ Analysis failed. Please try again.', timestamp: new Date() }]);
          clearInterval(pollingRef.current);
        }
      } catch (_) {}
    }, 3000);
    return () => clearInterval(pollingRef.current);
  }, [jobId]);

  function handleAttachClick() { fileInputRef.current?.click(); }

  async function handleFileChange(e) {
    const files = Array.from(e.target.files);
    if (!files.length) return;
    setUploading(true); setUploadError('');
    try {
      const uploaded = [];
      for (const file of files) {
        const fd = new FormData();
        fd.append('file', file); 
        const isImg = file.type.startsWith('image/');
        fd.append('modality', isImg ? 'RGB' : 'document');
        const result = await apiUpload('/assets', fd);
        uploaded.push({ name: file.name, asset_id: result.asset_id, file_url: result.file_url });
      }
      setAttachedAssets(prev => [...prev, ...uploaded]);
    } catch (err) { setUploadError(err.message); }
    finally { setUploading(false); e.target.value = ''; }
  }

  function removeAsset(id) { setAttachedAssets(prev => prev.filter(a => a.asset_id !== id)); }

  function toggleListening() {
    if (isListening) { recognitionRef.current?.stop(); setIsListening(false); return; }
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) { alert('Speech recognition not supported.'); return; }
    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;
    recognition.interimResults = true; recognition.continuous = true;
    const initialText = inputText;
    recognition.onstart = () => setIsListening(true);
    recognition.onresult = (event) => {
      let t = '';
      for (let i = 0; i < event.results.length; ++i) t += event.results[i][0].transcript;
      setInputText(initialText + (initialText && t ? ' ' : '') + t);
    };
    recognition.onerror = () => setIsListening(false);
    recognition.onend = () => setIsListening(false);
    recognition.start();
  }

  const handleSend = async (queryText) => {
    const text = queryText || inputText;
    if (!text.trim()) { setErrorMsg('Please enter a query.'); return; }
    if (!aoi && !chatOpen) { setErrorMsg('Please draw a polygon on the map first.'); return; }

    setErrorMsg('');
    setLoading(true);
    setLastQuery(text.trim());

    const currentAssets = [...attachedAssets];
    const userMsg = { role: 'user', text: text.trim(), attachedAssets: currentAssets, timestamp: new Date() };
    setMessages(prev => [...prev, userMsg]);
    setInputText('');
    setAttachedAssets([]);
    setChatOpen(true);
    setMessages(prev => [...prev, { role: 'assistant', text: '', isTyping: true, timestamp: new Date() }]);

    const CASUAL_PHRASES = ['hi','hello','hey','thanks','thank you','ok','okay','bye','what can you','what can you do','help','who are you','what are you','good morning','good evening','good afternoon'];
    const ANALYSIS_KEYWORDS = ['analyse','analyze','vegetation','ndvi','ndbi','ndwi','nbr','urban','built-up','water','burn','fire','deforestation','change','trend','timeline','timelapse','temporal','flood','drought','cropland','land use','land cover','hotspot','anomaly','seasonal','compare','report','satellite','sentinel','imagery','show me','what is happening',"what's happening",'how is','has it changed','has that changed'];
    const msgLower = text.trim().toLowerCase();
    const isCasual = CASUAL_PHRASES.some(p => msgLower === p || msgLower.startsWith(p + ' ') || msgLower.startsWith(p + '!')) && !ANALYSIS_KEYWORDS.some(kw => msgLower.includes(kw));
    const hasAnalyticalIntent = ANALYSIS_KEYWORDS.some(kw => msgLower.includes(kw));
    const skipJobCreation = isCasual || (chatOpen && jobId && !hasAnalyticalIntent);

    let mapboxImageBase64 = null;
    if (!skipJobCreation && analysisMode === 'spatial') {
      const canvas = document.querySelector('.mapboxgl-canvas');
      if (canvas) mapboxImageBase64 = canvas.toDataURL('image/jpeg', 0.8);
    }

    try {
      let activeJobId = jobId;

      if (!activeJobId && !skipJobCreation) {
        const result = await apiPost('/queries', {
          query: text.trim(),
          asset_ids: currentAssets.map(a => a.asset_id),
          aoi: aoi || undefined,
          options: { generate_artifacts: true, generate_report: true, include_visualizations: true, include_trace: true, analysis_mode: analysisMode }
        });
        setJobId(result.job_id);
        activeJobId = result.job_id;
      }

      let agentHandledTimeline = false;

      try {
        const chatHistory = messages.filter(m => m.text).map(m => ({ role: m.role, content: m.text })).concat([{ role: 'user', content: text.trim() }]);
        const chatResponse = await apiPost('/chat', {
          messages: chatHistory,
          aoi: aoi || undefined,
          mapbox_image: skipJobCreation ? null : mapboxImageBase64,
          job_id: activeJobId,
          use_agent: !skipJobCreation
        });

        setMessages(prev => prev.map(m => m.isTyping ? {
          role: 'assistant',
          text: chatResponse.reply,
          findings: chatResponse.findings || [],
          visualEvidence: chatResponse.visual_evidence || [],
          media: chatResponse.media || { images: [], videos: [] },
          quality: chatResponse.quality || { status: 'sufficient', issues: [] },
          limitations: chatResponse.limitations || [],
          replanning: chatResponse.replanning || { performed: false, count: 0 },
          provenance: chatResponse.provenance || null,
          provenanceStatus: chatResponse.provenance_status || null,
          timelineData: chatResponse.timeline_data || null,
          documentUrl: chatResponse.document_url,
          toolsUsed: chatResponse.tools_used || [],
          timestamp: new Date(),
          jobId: activeJobId,
          analysisId: chatResponse.provenance?.analysis_id || null
        } : m));

        if (chatResponse.timeline_data) {
          setTimelineData(chatResponse.timeline_data);
          agentHandledTimeline = true;
          if (chatResponse.timeline_data.frames?.length > 0) setCurrentTimelineFrame(chatResponse.timeline_data.frames[0]);
        }
      } catch (chatErr) {
        console.error('Chat error:', chatErr);
        setMessages(prev => prev.map(m => m.isTyping
          ? { role: 'assistant', text: `❌ Error: ${chatErr.message}`, isError: true, timestamp: new Date() }
          : m
        ));
      }

      if (analysisMode === 'temporal' && !agentHandledTimeline) {
        try {
          const timelineResult = await apiPost('/timeline', { aoi, job_id: activeJobId });
          if (timelineResult?.data) {
            setTimelineData(timelineResult.data);
            if (timelineResult.data.frames?.length > 0) setCurrentTimelineFrame(timelineResult.data.frames[0]);
          }
        } catch (err) { console.error('Timeline error:', err); }
      }
    } catch (err) {
      setMessages(prev => prev.map(m => m.isTyping
        ? { role: 'assistant', text: `❌ Error: ${err.message}`, isError: true, timestamp: new Date() }
        : m
      ));
    } finally {
      setLoading(false);
    }
  };

  const handleDrawNew = () => {
    setAoi(null); setMessages([]); setChatOpen(false);
    setJobId(null); setJobStatus(null); setErrorMsg('');
    setTimelineData(null); setCurrentTimelineFrame(null);
    clearInterval(pollingRef.current);
  };

  const handleRetry = () => {
    if (lastQuery) {
      setMessages(prev => prev.filter(m => !m.isError));
      handleSend(lastQuery);
    }
  };

  // ── Render ──────────────────────────────────────────────────────
  return (
    <div style={{
      width: '100vw', height: '100vh',
      background: '#04050d',
      display: 'flex', flexDirection: 'column',
      overflow: 'hidden',
      fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        @keyframes satPulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.5;transform:scale(1.4)} }
        @keyframes spin { to{transform:rotate(360deg)} }
        @keyframes dotPulse { 0%,80%,100%{opacity:0} 40%{opacity:1} }
        .geo-panel-scroll::-webkit-scrollbar { width: 4px; }
        .geo-panel-scroll::-webkit-scrollbar-track { background: transparent; }
        .geo-panel-scroll::-webkit-scrollbar-thumb { background: #222; border-radius: 2px; }
        .sat-nav-btn { transition: all 0.15s; }
        .sat-nav-btn:hover { background: rgba(255,255,255,0.05) !important; }
        .draw-new-btn:hover { color: #ddd !important; }
        .send-chip-btn:hover { color: #888 !important; }
        /* Container query context for evidence grid */
        .chat-panel-content { container-type: inline-size; container-name: chatpanel; }
        .evidence-grid { display: grid; gap: 8px; grid-template-columns: 1fr; width: 100%; min-width: 0; }
        @container chatpanel (min-width: 500px) { .evidence-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
        @container chatpanel (min-width: 720px) { .evidence-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
        /* Hover-reveal action bar */
        .msg-wrapper:hover .msg-action-bar { opacity: 1 !important; }
      `}</style>

      {/* Hidden file input */}
      <input type="file" ref={fileInputRef} style={{ display: 'none' }} multiple onChange={handleFileChange} />

      {/* ── Top Navigation Bar ─────────────────────────────────────── */}
      <nav style={{
        height: '52px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 20px',
        background: 'rgba(4,5,13,0.92)',
        backdropFilter: 'blur(12px)',
        borderBottom: '1px solid rgba(255,255,255,0.055)',
        flexShrink: 0, zIndex: 20,
      }}>
        {/* Left: nav + breadcrumb */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <button className="sat-nav-btn" onClick={() => navigate('/dashboard')} style={{
            background: 'rgba(255,255,255,0.04)', color: 'rgba(255,255,255,0.5)',
            border: '1px solid rgba(255,255,255,0.08)', padding: '5px 11px',
            borderRadius: '7px', cursor: 'pointer', fontSize: '12px', fontWeight: 500,
            display: 'flex', alignItems: 'center', gap: '5px',
          }}>
            <svg viewBox="0 0 16 16" fill="none" style={{ width: '11px', height: '11px' }}>
              <path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Dashboard
          </button>
          <div style={{ width: '1px', height: '18px', background: 'rgba(255,255,255,0.08)' }} />
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '0.12em', color: 'rgba(255,255,255,0.9)', textTransform: 'uppercase' }}>SatQuery</span>
            <span style={{ color: 'rgba(255,255,255,0.2)', fontSize: '12px' }}>/</span>
            <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.35)', fontWeight: 400 }}>Geo-Intelligence Workspace</span>
          </div>
        </div>

        {/* Right: status + actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {aoi && <AgentStatusBadge loading={loading} messages={messages} errorState={!!errorMsg} />}
          {aoi && (
            <div style={{ width: '1px', height: '16px', background: 'rgba(255,255,255,0.07)' }} />
          )}
          {chatOpen && (
            <button className="sat-nav-btn draw-new-btn" onClick={handleDrawNew} style={{
              background: 'transparent', color: 'rgba(255,255,255,0.4)',
              border: '1px solid rgba(255,255,255,0.1)', padding: '5px 11px',
              borderRadius: '7px', cursor: 'pointer', fontSize: '11px', fontWeight: 500,
              display: 'flex', alignItems: 'center', gap: '5px', letterSpacing: '0.02em',
            }}>
              <svg viewBox="0 0 16 16" fill="none" style={{ width: '11px', height: '11px' }}>
                <path d="M2 14l4-1.5L13 5.5 10.5 3 3.5 10 2 14z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
              </svg>
              New Region
            </button>
          )}
        </div>
      </nav>

      {/* ── Workspace Body ─────────────────────────────────────────── */}
        {/* Workspace body */}
        <div className="workspace-body" style={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative', background: '#04050d' }}>

        {/* ── Map Canvas ─────────────────────────────────────────── */}
        <div style={{ flex: 1, position: 'relative', transition: 'all 0.35s ease' }}>
          <AOIMap
            onAoiChange={setAoi}
            imageOverlayUrl={currentTimelineFrame?.thumbnail_url}
            imageOverlayBounds={timelineData?.bbox}
          />

          {/* AOI Info Card (over map) */}
          <AoiInfoCard aoi={aoi} analysisMode={analysisMode} jobStatus={jobStatus} />

          {/* Error message bar */}
          {errorMsg && (
            <div style={{
              position: 'absolute', top: '16px', left: '50%', transform: 'translateX(-50%)',
              background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.25)',
              borderRadius: '8px', padding: '8px 14px',
              color: '#fca5a5', fontSize: '12px', fontWeight: 500,
              zIndex: 10, backdropFilter: 'blur(8px)',
              display: 'flex', alignItems: 'center', gap: '8px',
            }}>
              <span>⚠</span>
              <span>{errorMsg}</span>
              <button onClick={() => setErrorMsg('')} style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.35)', cursor: 'pointer', fontSize: '14px', padding: '0 0 0 6px' }}>×</button>
            </div>
          )}

          {/* Floating Composer — when chat is not open */}
          {!chatOpen && (
            <div className="floating-composer" style={{
              position: 'absolute', bottom: '32px',
              left: '50%', transform: 'translateX(-50%)',
              width: '88%', maxWidth: '580px',
              zIndex: 5,
              boxShadow: '0 8px 40px rgba(0,0,0,0.5)',
              borderRadius: '16px',
            }}>
              {!aoi && (
                <div style={{
                  textAlign: 'center', marginBottom: '12px',
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px',
                }}>
                  <div style={{
                    background: 'rgba(59,130,246,0.08)',
                    border: '1px solid rgba(59,130,246,0.18)',
                    borderRadius: '8px', padding: '7px 14px',
                    display: 'inline-flex', alignItems: 'center', gap: '7px',
                  }}>
                    <div style={{ width: '6px', height: '6px', borderRadius: '1px', background: '#3b82f6', transform: 'rotate(45deg)' }} />
                    <span style={{ fontSize: '11px', color: '#93c5fd', fontWeight: 500 }}>Draw a polygon on the map to define your analysis region</span>
                  </div>
                </div>
              )}
              <ChatComposer
                queryText={inputText} setQueryText={setInputText}
                onSubmit={handleSend} submitting={loading}
                isListening={isListening} toggleListening={toggleListening}
                handleAttachClick={handleAttachClick} uploading={uploading}
                attachedAssets={attachedAssets} removeAsset={removeAsset} uploadError={uploadError}
                fileInputRef={fileInputRef} handleFileChange={handleFileChange}
                placeholder="Ask anything about Earth..."
                hasMessages={false}
                topContent={
                  <div style={{ display: 'flex', gap: '2px', background: '#161616', borderRadius: '6px', padding: '2px', width: 'fit-content' }}>
                    {['spatial', 'temporal'].map(m => (
                      <button key={m} type="button" onClick={() => setAnalysisMode(m)} style={{
                        background: analysisMode === m ? '#222' : 'transparent',
                        color: analysisMode === m ? '#DDD' : '#555',
                        border: 'none',
                        padding: '4px 12px', borderRadius: '4px',
                        fontSize: '10px', fontWeight: 500, cursor: 'pointer',
                        textTransform: 'uppercase', letterSpacing: '0.07em',
                        transition: 'all 0.15s',
                      }}>{m}</button>
                    ))}
                  </div>
                }
              />
            </div>
          )}
        </div>

        {/* ── Resize Handle ────────────────────────────────────────────── */}
        {chatOpen && (
          <div
            role="separator"
            aria-label="Resize Geo-Agent panel"
            tabIndex={0}
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            onPointerCancel={handlePointerUp}
            onKeyDown={handleKeyDown}
            className="group hidden md:flex"
            style={{
              width: '12px',
              cursor: 'col-resize',
              position: 'relative',
              zIndex: 50,
              display: 'flex',
              justifyContent: 'center',
              backgroundColor: 'transparent',
              marginLeft: '-6px',
              marginRight: '-6px',
              outline: 'none',
              touchAction: 'none'
            }}
          >
            <div style={{
              width: '10px',
              height: '100%',
              background: isResizing ? '#333' : '#1A1A1A',
              transition: 'background 0.15s',
              cursor: 'col-resize',
            }} />
          </div>
        )}

        {/* ── Geo-Agent Panel (right) ─────────────────────────────── */}
        <div className={`geo-agent-panel ${chatOpen ? 'open' : 'closed'}`} style={{
          width: chatOpen ? `${panelWidth}px` : '0',
          minWidth: chatOpen ? '320px' : '0',
          maxWidth: chatOpen ? '55vw' : '0',
          overflow: 'hidden',
          flexShrink: 0,
          transition: isResizing ? 'none' : 'width 0.38s cubic-bezier(0.4, 0, 0.2, 1)',
          display: 'flex', flexDirection: 'column',
          background: '#0B0B0B',
        }}>

          {/* Panel Header */}
          <div style={{
            padding: '14px 20px 12px',
            borderBottom: '1px solid #181818',
            flexShrink: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '13px', fontWeight: 600, color: '#888', letterSpacing: '0.04em' }}>Geo-Agent</span>
              <span style={{ fontSize: '11px', color: '#2A2A2A' }}>·</span>
              <AgentStatusBadge loading={loading} messages={messages} errorState={!!errorMsg} compact />
            </div>
            <button
              onClick={() => setChatOpen(false)}
              style={{ background: 'none', border: 'none', color: '#333', cursor: 'pointer', padding: '4px', display: 'flex', fontSize: '14px', lineHeight: 1, transition: 'color 0.15s' }}
              onMouseOver={e => e.currentTarget.style.color = '#666'}
              onMouseOut={e => e.currentTarget.style.color = '#333'}
              title="Close panel"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={{ width: '14px', height: '14px' }}>
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Messages area */}
          <div className="geo-panel-scroll chat-panel-content" style={{
            flex: 1, overflowY: 'auto', overflowX: 'hidden',
            padding: '32px 28px',
            display: 'flex', flexDirection: 'column', gap: '0',
            minWidth: 0,
          }}>
            {messages.length === 0 && (
              <div style={{
                display: 'flex', flexDirection: 'column',
                justifyContent: 'flex-end', height: '100%',
                paddingBottom: '8px',
              }}>
                <div style={{ fontSize: '13px', color: '#2A2A2A', lineHeight: '1.8' }}>
                  Draw a region on the map, then ask a question about it.
                </div>
              </div>
            )}

            {messages.map((msg, i) => {
              if (msg.isTyping) {
                return (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '32px' }}>
                    <span style={{ fontSize: '14px', color: '#555' }}>Analysing your selected area</span>
                    <span style={{ display: 'inline-flex', gap: '3px' }}>
                      {[0, 1, 2].map(d => (
                        <span key={d} style={{
                          width: '4px', height: '4px', borderRadius: '50%', background: '#444',
                          display: 'inline-block',
                          animation: 'dotPulse 1.4s ease-in-out infinite',
                          animationDelay: `${d * 0.2}s`,
                        }} />
                      ))}
                    </span>
                  </div>
                );
              }

              if (msg.isError || msg.text?.startsWith('❌')) {
                const errText = (msg.text || '').replace(/^❌\s*/, '');
                return (
                  <div key={i} style={{ marginBottom: '32px' }}>
                    <div style={{ fontSize: '15px', color: '#888', marginBottom: '8px' }}>Analysis could not be completed.</div>
                    {errText && <div style={{ fontSize: '13px', color: '#555', lineHeight: '1.6', marginBottom: '14px' }}>{errText}</div>}
                    <button onClick={handleRetry} style={{
                      background: 'none', border: '1px solid #2A2A2A', borderRadius: '8px',
                      padding: '6px 14px', fontSize: '13px', color: '#666', cursor: 'pointer',
                      transition: 'all 0.15s',
                    }}
                      onMouseOver={e => { e.currentTarget.style.borderColor = '#444'; e.currentTarget.style.color = '#999'; }}
                      onMouseOut={e => { e.currentTarget.style.borderColor = '#2A2A2A'; e.currentTarget.style.color = '#666'; }}
                    >Retry</button>
                  </div>
                );
              }

              if (msg.role === 'user') {
                return (
                  <UserMessage
                    key={i}
                    text={msg.text}
                    timestamp={msg.timestamp}
                    attachedAssets={msg.attachedAssets}
                    onEdit={(text) => {
                      setInputText(text);
                    }}
                  />
                );
              }

              // Assistant message
              return (
                <div key={i} style={{ marginBottom: '40px' }}>
                  <ChatMessage
                    msg={msg}
                    jobId={msg.jobId || jobId}
                    analysisId={msg.analysisId}
                    onTimelineFrame={setCurrentTimelineFrame}
                  />
                </div>
              );
            })}

            {/* Standalone timeline */}
            {timelineData && !messages.some(m => m.timelineData) && (
              <TimelinePlayer data={timelineData} onFrameChange={setCurrentTimelineFrame} />
            )}

            <div ref={chatEndRef} />
          </div>

          {/* Panel Footer: Composer */}
          <div style={{
            padding: '0 20px 20px',
            flexShrink: 0,
            display: 'flex', flexDirection: 'column', gap: '10px',
          }}>
            <ChatComposer
              queryText={inputText} setQueryText={setInputText}
              onSubmit={handleSend} submitting={loading}
              isListening={isListening} toggleListening={toggleListening}
              handleAttachClick={handleAttachClick} uploading={uploading}
              attachedAssets={attachedAssets} removeAsset={removeAsset} uploadError={uploadError}
              fileInputRef={fileInputRef} handleFileChange={handleFileChange}
              placeholder="Ask a follow-up..."
              compact={true}
              hasMessages={true}
              topContent={
                <div style={{ display: 'flex', gap: '2px', background: '#161616', borderRadius: '6px', padding: '2px', width: 'fit-content' }}>
                  {['spatial', 'temporal'].map(m => (
                    <button key={m} type="button" onClick={() => setAnalysisMode(m)} style={{
                      background: analysisMode === m ? '#222' : 'transparent',
                      color: analysisMode === m ? '#DDD' : '#555',
                      border: 'none',
                      padding: '4px 12px', borderRadius: '4px',
                      fontSize: '10px', fontWeight: 500, cursor: 'pointer',
                      textTransform: 'uppercase', letterSpacing: '0.07em',
                      transition: 'all 0.15s',
                    }}>{m}</button>
                  ))}
                </div>
              }
            />

            {/* Quick action chips */}
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {['Temporal trend', 'Compare periods', 'Generate report'].map(chip => (
                <button
                  key={chip}
                  className="send-chip-btn"
                  onClick={() => { setInputText(chip); }}
                  style={{
                    background: 'none', border: 'none',
                    fontSize: '12px', color: '#333',
                    cursor: 'pointer', transition: 'color 0.15s',
                    padding: '2px 0',
                    fontWeight: 400,
                  }}
                >
                  {chip}
                </button>
              ))}
              <button
                className="draw-new-btn"
                onClick={handleDrawNew}
                style={{
                  background: 'none', border: 'none',
                  fontSize: '12px', color: '#2A2A2A',
                  cursor: 'pointer', transition: 'color 0.15s',
                  padding: '2px 0',
                  marginLeft: 'auto',
                }}
              >
                New region
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
