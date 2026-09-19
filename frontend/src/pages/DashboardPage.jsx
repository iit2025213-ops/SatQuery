import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import DashboardLayout from '../components/DashboardLayout';
import { apiGet, apiPost, apiUpload } from '../utils/api';

export default function DashboardPage() {
  const navigate = useNavigate();

  const [queryText, setQueryText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');

  const [attachedAssets, setAttachedAssets] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const fileInputRef = useRef(null);
  
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef(null);

  const [recentJobs, setRecentJobs] = useState([]);
  const [user, setUser] = useState(() => {
    try {
      const saved = sessionStorage.getItem('satquery_user');
      return saved ? JSON.parse(saved) : null;
    } catch { return null; }
  });
  const [userLoaded, setUserLoaded] = useState(!!user);



  useEffect(() => { 
    fetchJobs(); 
    fetchUser();
  }, []);

  async function fetchUser() {
    try {
      const data = await apiGet('/auth/me');
      setUser(data);
      sessionStorage.setItem('satquery_user', JSON.stringify(data));
      setUserLoaded(true);
    } catch (_) {}
  }

  async function fetchJobs() {
    try {
      const data = await apiGet('/jobs?limit=8');
      setRecentJobs(data.jobs || []);
    } catch (_) {}
  }

  function handleAttachClick() { fileInputRef.current?.click(); }

  async function handleFileChange(e) {
    const files = Array.from(e.target.files);
    if (!files.length) return;
    setUploading(true);
    setUploadError('');
    try {
      const uploaded = [];
      for (const file of files) {
        const fd = new FormData();
        fd.append('file', file);
        fd.append('modality', 'document');
        const result = await apiUpload('/assets', fd);
        uploaded.push({ name: file.name, asset_id: result.asset_id });
      }
      setAttachedAssets(prev => [...prev, ...uploaded]);
    } catch (err) {
      setUploadError(err.message);
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  }

  function removeAsset(id) {
    setAttachedAssets(prev => prev.filter(a => a.asset_id !== id));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!queryText.trim()) return;
    setSubmitting(true);
    setSubmitError('');
    try {
      await apiPost('/queries', {
        query: queryText.trim(),
        asset_ids: attachedAssets.map(a => a.asset_id),
      });
      setQueryText('');
      setAttachedAssets([]);
      fetchJobs();
    } catch (err) {
      setSubmitError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  function toggleListening() {
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert('Your browser does not support Speech Recognition.');
      return;
    }
    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;
    recognition.interimResults = true;
    recognition.continuous = true; // Stay active even during pauses
    
    // Store the text we had before starting
    const initialText = queryText;

    recognition.onstart = () => setIsListening(true);
    
    recognition.onresult = (event) => {
      let transcript = '';
      for (let i = 0; i < event.results.length; ++i) {
        transcript += event.results[i][0].transcript;
      }
      setQueryText(initialText + (initialText && transcript ? ' ' : '') + transcript);
    };

    recognition.onerror = (event) => {
      console.error('Speech recognition error', event.error);
      setIsListening(false);
    };

    recognition.onend = () => setIsListening(false);
    recognition.start();
  }

  function relativeTime(iso) {
    if (!iso) return '';
    const mins = Math.floor((Date.now() - new Date(iso)) / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  }

  function statusDot(s) {
    return { queued: '#6b7280', running: '#f59e0b', completed: '#22c55e', failed: '#ef4444', cancelled: '#9ca3af' }[s] || '#6b7280';
  }

  return (
    <DashboardLayout>
      <div className="frame">

        {/* MAIN — centered composer */}
        <main className="hero" style={{ justifyContent: 'center', marginLeft: '260px' }}>



          {/* Hero text */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: '0px' }}>
            <h1 style={{ 
              fontSize: '3.0rem', 
              fontWeight: 400, 
              fontFamily: '"Outfit", "Inter", -apple-system, sans-serif',
              background: 'linear-gradient(180deg, #FFFFFF 0%, #A1A1AA 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              letterSpacing: '-0.03em', 
              margin: 0,
              whiteSpace: 'nowrap',
              opacity: userLoaded ? 1 : 0,
              transition: 'opacity 0.3s ease'
            }}>
              {user?.display_name ? `What would you like to explore, ${user.display_name.split(' ')[0]}?` : 'What would you like to explore?'}
            </h1>
          </div>

          {/* COMPOSER CARD */}
          <form className="card" onSubmit={handleSubmit} style={{ 
            position: 'relative', width: '850px', maxWidth: '90vw', 
            borderRadius: '32px', height: 'auto', minHeight: attachedAssets.length > 0 ? '140px' : '72px', 
            background: '#1E1F20', display: 'flex', flexDirection: 'column', 
            justifyContent: 'flex-end', padding: '16px', border: 'none', 
            boxShadow: '0 4px 24px rgba(0,0,0,0.5)' 
          }}>
            
            {/* Top area for attachments (if any) */}
            {attachedAssets.length > 0 && (
              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '16px', paddingLeft: '8px' }}>
                {attachedAssets.map(a => (
                  <div key={a.asset_id} style={{
                    width: '80px', height: '80px', background: '#282A2C', borderRadius: '16px',
                    display: 'flex', flexDirection: 'column', padding: '10px', position: 'relative'
                  }}>
                    <span style={{ fontSize: '10px', fontWeight: 600, color: '#a1a1aa' }}>FILE</span>
                    <span style={{ fontSize: '12px', color: '#fff', marginTop: 'auto', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.name}</span>
                    <button type="button" onClick={() => removeAsset(a.asset_id)} style={{ position: 'absolute', top: '4px', right: '4px', background: 'rgba(255,255,255,0.1)', border: 'none', color: '#fff', borderRadius: '50%', width: '20px', height: '20px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', fontSize: '12px', lineHeight: 1 }}>×</button>
                  </div>
                ))}
              </div>
            )}

            {/* Bottom area: input row */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', width: '100%' }}>
              <button type="button" aria-label="Attach file"
                onClick={handleAttachClick} disabled={uploading}
                style={{ 
                  width: '40px', height: '40px', borderRadius: '50%', flexShrink: 0,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: 'transparent', border: 'none', color: '#a1a1aa',
                  cursor: 'pointer', opacity: uploading ? 0.5 : 1
                }}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: '28px', height: '28px' }}>
                  <line x1="12" y1="5" x2="12" y2="19"></line>
                  <line x1="5" y1="12" x2="19" y2="12"></line>
                </svg>
              </button>

              <div style={{ position: 'relative', flex: 1, display: 'flex', alignItems: 'center', height: '40px' }}>
                {queryText === '' && (
                  <p className="ph" aria-hidden="true" style={{ position: 'absolute', left: '4px', top: '50%', transform: 'translateY(-50%)', fontSize: '1.15rem', fontWeight: 400, color: '#a1a1aa', letterSpacing: '0.01em', margin: 0, pointerEvents: 'none' }}>Ask anything about Earth...</p>
                )}
                <textarea
                  value={queryText}
                  onChange={e => setQueryText(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(e); } }}
                  disabled={submitting}
                  rows={1}
                  style={{
                    width: '100%',
                    background: 'transparent', border: 'none', outline: 'none', boxShadow: 'none',
                    resize: 'none', color: '#fff',
                    fontSize: '1.15rem', fontWeight: 400, fontFamily: 'inherit',
                    lineHeight: '24px', letterSpacing: '0.01em', overflowY: 'hidden',
                    whiteSpace: 'nowrap', padding: '8px 4px', height: '40px'
                  }}
                  aria-label="Query input"
                />
              </div>

              <input ref={fileInputRef} type="file" multiple style={{ display: 'none' }} onChange={handleFileChange} accept="image/*,.pdf,.txt,.csv,.json,.geojson,.tif,.tiff" />
              
              <button type="button" aria-label="Toggle microphone" onClick={toggleListening} style={{ background: isListening ? 'rgba(75, 150, 255, 0.2)' : 'transparent', border: 'none', color: isListening ? '#4B96FF' : '#a1a1aa', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '8px', borderRadius: '50%' }}>
                {isListening ? (
                  <div className="mic-wave-container">
                    <div className="mic-wave-bar" style={{ animationDelay: '0.0s' }} />
                    <div className="mic-wave-bar" style={{ animationDelay: '0.1s' }} />
                    <div className="mic-wave-bar" style={{ animationDelay: '0.2s' }} />
                    <div className="mic-wave-bar" style={{ animationDelay: '0.3s' }} />
                  </div>
                ) : (
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: '22px', height: '22px' }}>
                    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                    <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                    <line x1="12" y1="19" x2="12" y2="23"></line>
                    <line x1="8" y1="23" x2="16" y2="23"></line>
                  </svg>
                )}
              </button>
              <button type="submit" className="send-btn" aria-label="Submit query"
                disabled={submitting || !queryText.trim()}
                style={{ position: 'static', width: '40px', height: '40px', borderRadius: '50%', flexShrink: 0, background: queryText.trim() ? '#4B96FF' : 'transparent', opacity: (submitting || !queryText.trim()) ? 0.5 : 1, display: 'flex', alignItems: 'center', justifyContent: 'center', border: 'none', cursor: 'pointer' }}>
                <svg className="arrow" viewBox="0 0 12 14" fill="none" style={{ width: '18px', height: '18px', marginLeft: queryText.trim() ? '2px' : 0 }}>
                  <path d="M6 13V1M6 1L1.5 5.5M6 1l4.5 4.5" stroke={queryText.trim() ? '#fff' : '#fff'} strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </button>
            </div>

            {/* Error messages */}
            {(submitError || uploadError) && (
              <div style={{
                position: 'absolute', top: '-30px', left: 0, right: 0,
                textAlign: 'center', fontSize: '13px', color: '#f87171',
              }}>{submitError || uploadError}</div>
            )}
          </form>
        </main>
      </div>
    </DashboardLayout>
  );
}
