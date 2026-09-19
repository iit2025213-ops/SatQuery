import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import AOIMap from '../components/AOIMap';
import { apiPost, apiGet } from '../utils/api';

// Renders a chat message: detects Cloudinary image URLs and renders them as <img>
// Also handles **bold** markdown and newlines
function MessageContent({ text }) {
  if (!text) return null;

  const lines = text.split('\n');
  const cloudinaryRegex = /https:\/\/res\.cloudinary\.com\/[^\s]+/g;

  return (
    <div>
      {lines.map((line, li) => {
        // Check if line contains a Cloudinary image URL
        const imgMatches = line.match(cloudinaryRegex);
        if (imgMatches) {
          const imgUrl = imgMatches[0];
          // Get label from before the URL
          const label = line.replace(cloudinaryRegex, '').replace(':', '').trim();
          return (
            <div key={li} style={{ marginTop: '10px' }}>
              {label && (
                <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)', marginBottom: '5px' }}>
                  {label}
                </div>
              )}
              <img
                src={imgUrl}
                alt={label || 'Satellite image'}
                style={{
                  width: '100%',
                  borderRadius: '8px',
                  border: '1px solid rgba(255,255,255,0.1)',
                  display: 'block',
                }}
                onError={e => { e.target.style.display = 'none'; }}
              />
              <a
                href={imgUrl}
                target="_blank"
                rel="noopener noreferrer"
                style={{ fontSize: '10px', color: 'rgba(255,255,255,0.35)', textDecoration: 'none', marginTop: '3px', display: 'block' }}
              >
                Open full size ↗
              </a>
            </div>
          );
        }

        // Render **bold** text
        const parts = line.split(/(\*\*[^*]+\*\*)/g);
        return (
          <div key={li} style={{ minHeight: line ? undefined : '8px' }}>
            {parts.map((part, pi) =>
              part.startsWith('**') && part.endsWith('**')
                ? <strong key={pi}>{part.slice(2, -2)}</strong>
                : part
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function MapPage() {
  const navigate = useNavigate();

  // Map state
  const [aoi, setAoi] = useState(null);
  const [drawRef, setDrawRef] = useState(null); // ref to mapbox draw instance to clear polygons

  // Chat state
  const [chatOpen, setChatOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const chatEndRef = useRef(null);
  const pollingRef = useRef(null);

  // Auto scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Poll job status once chat opens
  useEffect(() => {
    if (!jobId) return;
    pollingRef.current = setInterval(async () => {
      try {
        const data = await apiGet(`/jobs/${jobId}`);
        setJobStatus(data.status);
        if (data.status === 'completed' && data.final_answer) {
          setMessages(prev => {
            // Only add if we haven't already added this answer
            const alreadyHas = prev.some(m => m.role === 'assistant' && m.text === data.final_answer);
            if (!alreadyHas) {
              return [...prev, { role: 'assistant', text: data.final_answer, timestamp: new Date() }];
            }
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

  const handleSend = async (queryText) => {
    const text = queryText || inputText;
    if (!text.trim()) {
      setErrorMsg('Please enter a query.');
      return;
    }
    if (!aoi && !chatOpen) {
      setErrorMsg('Please draw a polygon on the map first.');
      return;
    }

    setErrorMsg('');
    setLoading(true);

    // Add user message to chat
    const userMsg = { role: 'user', text: text.trim(), timestamp: new Date() };
    setMessages(prev => [...prev, userMsg]);
    setInputText('');

    // Open chat panel
    setChatOpen(true);

    // Add "Analyzing..." message
    setMessages(prev => [...prev, { role: 'assistant', text: '🛰️ Analyzing your area of interest...', isTyping: true, timestamp: new Date() }]);

    try {
      const result = await apiPost('/queries', {
        query: text.trim(),
        asset_ids: [],
        aoi: aoi || undefined,
        options: {
          generate_artifacts: true,
          generate_report: true,
          include_visualizations: true,
          include_trace: true
        }
      });
      setJobId(result.job_id);
      // Replace typing indicator
      setMessages(prev => prev.map(m => m.isTyping
        ? { role: 'assistant', text: `✅ Job queued (ID: ${result.job_id.slice(0, 8)}...). Waiting for results...`, timestamp: new Date() }
        : m
      ));
    } catch (err) {
      setMessages(prev => prev.map(m => m.isTyping
        ? { role: 'assistant', text: `❌ Error: ${err.message}`, timestamp: new Date() }
        : m
      ));
    } finally {
      setLoading(false);
    }
  };

  const handleDrawNew = () => {
    // Clear the polygon, reset AOI, collapse chat back to initial
    setAoi(null);
    setMessages([]);
    setChatOpen(false);
    setJobId(null);
    setJobStatus(null);
    setErrorMsg('');
    clearInterval(pollingRef.current);
  };

  const formatTime = (d) => d?.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  return (
    <div style={{
      width: '100vw', height: '100vh',
      backgroundColor: '#000',
      display: 'flex', flexDirection: 'column',
      overflow: 'hidden',
      fontFamily: "'Inter', 'Segoe UI', sans-serif"
    }}>
      {/* ── Header ───────────────────────────────────── */}
      <header style={{
        padding: '0 24px',
        height: '56px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        background: 'rgba(0,0,0,0.85)',
        backdropFilter: 'blur(10px)',
        flexShrink: 0,
        zIndex: 10,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={() => navigate('/dashboard')}
            style={{
              background: 'transparent', color: 'rgba(255,255,255,0.6)',
              border: '1px solid rgba(255,255,255,0.12)', padding: '5px 12px',
              borderRadius: '6px', cursor: 'pointer', fontSize: '13px',
            }}
          >
            ← Dashboard
          </button>
          <span style={{ color: 'white', fontWeight: 600, fontSize: '15px', letterSpacing: '1px' }}>
            SATQUERY <span style={{ color: '#888', fontWeight: 400 }}>/ AOI Analysis</span>
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {aoi && (
            <span style={{ color: '#22c55e', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '5px' }}>
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#22c55e', display: 'inline-block' }} />
              AOI Selected
            </span>
          )}
          {chatOpen && (
            <button
              onClick={handleDrawNew}
              style={{
                background: 'rgba(255,255,255,0.08)',
                color: 'white', border: '1px solid rgba(255,255,255,0.15)',
                padding: '6px 14px', borderRadius: '6px', cursor: 'pointer', fontSize: '13px',
                display: 'flex', alignItems: 'center', gap: '6px',
              }}
            >
              <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
                <path d="M2 14l4-1.5L13 5.5 10.5 3 3.5 10 2 14z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
              </svg>
              Draw New Polygon
            </button>
          )}
        </div>
      </header>

      {/* ── Main Content: Map + Chat Panel ───────────── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative' }}>

        {/* Map takes remaining width */}
        <div style={{
          flex: 1,
          position: 'relative',
          transition: 'all 0.4s ease',
        }}>
          <AOIMap onAoiChange={setAoi} />

          {/* Floating composer — shown when chat is NOT open */}
          {!chatOpen && (
            <div style={{
              position: 'absolute', bottom: '40px',
              left: '50%', transform: 'translateX(-50%)',
              width: '90%', maxWidth: '600px',
              background: 'rgba(10,10,15,0.88)',
              backdropFilter: 'blur(16px)',
              padding: '16px 20px',
              borderRadius: '16px',
              border: '1px solid rgba(255,255,255,0.12)',
              boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
              display: 'flex', flexDirection: 'column', gap: '10px',
              zIndex: 5,
            }}>
              {errorMsg && (
                <div style={{ color: '#ef4444', fontSize: '13px' }}>{errorMsg}</div>
              )}
              {!aoi && (
                <div style={{ color: 'rgba(255,255,255,0.35)', fontSize: '12px', textAlign: 'center' }}>
                  🖊 Use the polygon tool (top-right on map) to draw your Area of Interest
                </div>
              )}
              <div style={{ display: 'flex', gap: '10px' }}>
                <input
                  type="text"
                  placeholder={aoi ? "Ask about this area (e.g. 'Show deforestation since 2023')" : "Draw a region first, then ask a question..."}
                  value={inputText}
                  onChange={e => setInputText(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleSend()}
                  disabled={loading}
                  style={{
                    flex: 1, background: 'transparent', border: 'none',
                    color: 'white', fontSize: '15px', outline: 'none',
                  }}
                />
                <button
                  onClick={() => handleSend()}
                  disabled={loading || !aoi}
                  style={{
                    background: aoi ? 'white' : 'rgba(255,255,255,0.15)',
                    color: aoi ? 'black' : 'rgba(255,255,255,0.4)',
                    border: 'none', padding: '10px 20px', borderRadius: '10px',
                    cursor: aoi ? 'pointer' : 'not-allowed', fontWeight: 700, fontSize: '14px',
                    transition: 'all 0.2s',
                  }}
                >
                  {loading ? '...' : 'Analyze →'}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* ── Chat Panel (30% width, slides in) ─────── */}
        <div style={{
          width: chatOpen ? '30%' : '0',
          minWidth: chatOpen ? '300px' : '0',
          overflow: 'hidden',
          transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
          background: 'rgba(8, 8, 14, 0.97)',
          borderLeft: chatOpen ? '1px solid rgba(255,255,255,0.08)' : 'none',
          display: 'flex', flexDirection: 'column',
          flexShrink: 0,
        }}>
          {/* Chat Header */}
          <div style={{
            padding: '16px 20px 12px',
            borderBottom: '1px solid rgba(255,255,255,0.06)',
            flexShrink: 0,
          }}>
            <div style={{ color: 'white', fontWeight: 600, fontSize: '14px' }}>Analysis Chat</div>
            {jobStatus && (
              <div style={{ fontSize: '11px', marginTop: '4px', color: {
                queued: '#f59e0b', running: '#3b82f6', completed: '#22c55e', failed: '#ef4444'
              }[jobStatus] || '#888' }}>
                Status: {jobStatus}
              </div>
            )}
          </div>

          {/* Messages */}
          <div style={{
            flex: 1, overflowY: 'auto', padding: '16px',
            display: 'flex', flexDirection: 'column', gap: '12px',
          }}>
            {messages.map((msg, i) => (
              <div key={i} style={{
                display: 'flex',
                flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
                gap: '8px', alignItems: 'flex-end',
              }}>
                {msg.role === 'assistant' && (
                  <div style={{
                    width: '28px', height: '28px', borderRadius: '50%',
                    background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: '12px', flexShrink: 0,
                  }}>🛰</div>
                )}
                <div style={{
                  maxWidth: '85%',
                  background: msg.role === 'user'
                    ? 'linear-gradient(135deg, #3b82f6, #2563eb)'
                    : 'rgba(255,255,255,0.06)',
                  color: 'white',
                  padding: '10px 14px',
                  borderRadius: msg.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                  fontSize: '13px', lineHeight: '1.7',
                  opacity: msg.isTyping ? 0.6 : 1,
                }}>
                  <MessageContent text={msg.text} />
                  {msg.isTyping && <span style={{ animation: 'pulse 1s infinite' }}>▌</span>}
                  <div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.3)', marginTop: '6px', textAlign: msg.role === 'user' ? 'right' : 'left' }}>
                    {formatTime(msg.timestamp)}
                  </div>
                </div>
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>

          {/* Chat Input */}
          <div style={{
            padding: '12px 16px',
            borderTop: '1px solid rgba(255,255,255,0.06)',
            flexShrink: 0,
          }}>
            <div style={{
              display: 'flex', gap: '8px', alignItems: 'center',
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '12px', padding: '8px 12px',
            }}>
              <input
                type="text"
                placeholder="Ask a follow-up question..."
                value={inputText}
                onChange={e => setInputText(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSend()}
                disabled={loading}
                style={{
                  flex: 1, background: 'transparent', border: 'none',
                  color: 'white', fontSize: '13px', outline: 'none',
                }}
              />
              <button
                onClick={() => handleSend()}
                disabled={loading}
                style={{
                  background: 'linear-gradient(135deg, #3b82f6, #2563eb)',
                  border: 'none', borderRadius: '8px', padding: '6px 12px',
                  color: 'white', cursor: 'pointer', fontSize: '13px', fontWeight: 600,
                }}
              >
                {loading ? '...' : '↑'}
              </button>
            </div>
            <button
              onClick={handleDrawNew}
              style={{
                width: '100%', marginTop: '8px',
                background: 'transparent',
                border: '1px dashed rgba(255,255,255,0.15)',
                color: 'rgba(255,255,255,0.45)', borderRadius: '8px',
                padding: '7px', cursor: 'pointer', fontSize: '12px',
                transition: 'all 0.2s',
              }}
              onMouseEnter={e => {
                e.target.style.borderColor = 'rgba(255,255,255,0.4)';
                e.target.style.color = 'rgba(255,255,255,0.8)';
              }}
              onMouseLeave={e => {
                e.target.style.borderColor = 'rgba(255,255,255,0.15)';
                e.target.style.color = 'rgba(255,255,255,0.45)';
              }}
            >
              🖊 Draw a New Polygon
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
