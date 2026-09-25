import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import DashboardLayout from '../components/DashboardLayout';
import { apiGet, apiPost, apiUpload } from '../utils/api';

export default function DashboardPage() {
  const navigate = useNavigate();

  const [messages, setMessages] = useState([]);
  const hasMessages = messages.length > 0;
  const messagesEndRef = useRef(null);

  const [queryText, setQueryText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');

  const [attachedAssets, setAttachedAssets] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const fileInputRef = useRef(null);
  const textareaRef = useRef(null);
  
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

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

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

  const resizeTextarea = () => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = 'auto';
    const nextHeight = Math.min(textarea.scrollHeight, 200);
    textarea.style.height = `${nextHeight}px`;
    textarea.style.overflowY = textarea.scrollHeight > 200 ? 'auto' : 'hidden';
  };

  useEffect(() => {
    resizeTextarea();
  }, [queryText]);

  async function handleSubmit(e) {
    if (e && e.preventDefault) e.preventDefault();
    if (!queryText.trim()) return;
    
    const text = queryText.trim();
    
    // Optimistic user message immediately transitions the UI
    setMessages(prev => [...prev, { role: 'user', text, timestamp: new Date() }]);
    
    setSubmitting(true);
    setSubmitError('');
    setQueryText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = '28px';
      textareaRef.current.style.overflowY = 'hidden';
    }
    
    const currentAssets = [...attachedAssets];
    setAttachedAssets([]);

    try {
      const res = await apiPost('/queries', {
        query: text,
        asset_ids: currentAssets.map(a => a.asset_id),
      });
      
      // Update assistant message with job id status
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        type: 'job_status',
        jobId: res.job_id || 'Queued',
        text: 'Query submitted successfully', 
        timestamp: new Date() 
      }]);
      fetchJobs();
    } catch (err) {
      setSubmitError(err.message);
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        text: `Error: ${err.message}`, 
        timestamp: new Date() 
      }]);
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
      <div className="frame dashboard-frame" style={{ display: 'flex', flexDirection: 'column', height: '100dvh', overflow: 'hidden', padding: 0 }}>

        {/* MAIN — chat workspace */}
        <main className="dashboard-chat-workspace" style={{ 
          flex: 1, 
          display: 'flex', 
          flexDirection: 'column', 
          position: 'relative',
          height: '100%'
        }}>

          <AnimatePresence>
            {!hasMessages && (
              <motion.div
                key="hero"
                initial={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.5, ease: 'easeOut' }}
                style={{ 
                  flex: 1, 
                  display: 'flex', 
                  flexDirection: 'column', 
                  alignItems: 'center', 
                  justifyContent: 'flex-end',
                  paddingBottom: '32px'
                }}
              >
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
              </motion.div>
            )}
          </AnimatePresence>

          <AnimatePresence>
            {hasMessages && (
              <motion.div
                key="messages-scroll"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.5, delay: 0.2 }}
                style={{
                  flex: 1,
                  overflowY: 'auto',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center', /* Centers the chat-column within the main dashboard area */
                  position: 'relative',
                  width: '100%'
                }}
              >
                {/* DEDICATED CHAT COLUMN */}
                <div className="chat-column" style={{
                  width: '100%',
                  maxWidth: '900px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '24px',
                  padding: 'clamp(48px, 8vh, 110px) 24px 150px 24px', // Space at the top and bottom
                  margin: '0 auto',
                  minWidth: 0,
                  boxSizing: 'border-box'
                }}>
                  {messages.map((msg, i) => (
                    <motion.div 
                      key={i} 
                      className={`message-row ${msg.role}`}
                      initial={{ opacity: 0, y: 8 }} 
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
                      style={{
                        display: 'flex',
                        width: '100%',
                        justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                        gap: '12px', 
                        alignItems: 'flex-start',
                        minWidth: 0,
                        boxSizing: 'border-box'
                      }}
                    >
                      {msg.role === 'assistant' && (
                        <div style={{
                          width: '28px', height: '28px', borderRadius: '50%',
                          background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          fontSize: '12px', flexShrink: 0, marginTop: '2px'
                        }}>🛰</div>
                      )}
                      
                      {msg.role === 'user' ? (
                        <div style={{
                          width: 'fit-content',
                          maxWidth: 'min(70%, 680px)',
                          minWidth: 0,
                          boxSizing: 'border-box',
                          background: '#2F6FED',
                          color: '#FFFFFF',
                          padding: '12px 16px',
                          borderRadius: '18px 18px 4px 18px',
                          fontSize: '14px', lineHeight: '1.5',
                          boxShadow: '0 4px 16px rgba(0,0,0,0.16)',
                          display: 'flex', flexDirection: 'column'
                        }}>
                          <div style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', wordBreak: 'break-word', minWidth: 0 }}>{msg.text}</div>
                          <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.55)', marginTop: '4px', textAlign: 'right' }}>
                            {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </div>
                        </div>
                      ) : (
                        <div style={{
                          width: '100%',
                          maxWidth: '82%',
                          minWidth: 0,
                          boxSizing: 'border-box',
                          color: 'rgba(255,255,255,0.92)',
                          padding: '4px 16px',
                          fontSize: '14px', lineHeight: '1.6',
                          display: 'flex', flexDirection: 'column'
                        }}>
                          {msg.type === 'job_status' ? (
                            <div>
                              <div style={{ fontWeight: 500, fontSize: '15px', color: '#fff', marginBottom: '8px' }}>
                                {msg.text}
                              </div>
                              <div style={{ color: 'rgba(255,255,255,0.7)', marginBottom: '12px' }}>
                                Your analysis has been queued and is now being processed.
                              </div>
                              <div style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'rgba(255,255,255,0.5)', marginBottom: '4px' }}>
                                Job ID
                              </div>
                              <div style={{ fontFamily: 'monospace', color: 'rgba(255,255,255,0.6)', background: 'rgba(255,255,255,0.05)', padding: '6px 10px', borderRadius: '6px', width: 'fit-content', marginBottom: '12px' }}>
                                {msg.jobId}
                              </div>
                              <div style={{ color: 'rgba(255,255,255,0.6)', fontSize: '13px' }}>
                                Track progress from the Area of Interest tab.
                              </div>
                            </div>
                          ) : (
                            <div style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', wordBreak: 'break-word', minWidth: 0 }}>{msg.text}</div>
                          )}
                          <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.55)', marginTop: '6px', textAlign: 'left', whiteSpace: 'nowrap' }}>
                            {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </div>
                        </div>
                      )}
                    </motion.div>
                  ))}
                  <div ref={messagesEndRef} />
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <motion.div
            layout
            transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
            style={{
              position: hasMessages ? 'absolute' : 'relative',
              bottom: hasMessages ? '24px' : 'auto',
              left: 0,
              right: 0,
              display: 'flex',
              justifyContent: 'center',
              padding: '0 24px',
              flex: !hasMessages ? 1 : 'none',
              alignItems: !hasMessages ? 'flex-start' : 'center',
              zIndex: 10
            }}
          >
            <motion.form 
              layout
              transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
              className="card chatbar-composer" 
              onSubmit={handleSubmit} 
              style={{ 
                position: 'relative', 
                width: '100%', 
                maxWidth: hasMessages ? '900px' : '850px', 
                borderRadius: hasMessages ? '24px' : '32px', 
                height: 'auto', 
                minHeight: attachedAssets.length > 0 ? '140px' : (hasMessages ? '64px' : '72px'), 
                background: 'rgba(25, 25, 28, 0.88)', 
                backdropFilter: 'blur(18px) saturate(120%)',
                border: '1px solid rgba(255,255,255,0.08)',
                boxShadow: '0 8px 40px rgba(0,0,0,0.30)',
                display: 'flex', flexDirection: 'column', 
                justifyContent: 'flex-end', padding: '12px 16px', 
              }}
            >
              
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
              <div style={{ display: 'flex', alignItems: 'flex-end', gap: '12px', width: '100%' }}>
                <button type="button" aria-label="Attach file"
                  onClick={handleAttachClick} disabled={uploading}
                  style={{ 
                    width: uploading ? '110px' : '40px', height: '40px', borderRadius: uploading ? '20px' : '50%', flexShrink: 0,
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
                    background: uploading ? 'rgba(75, 150, 255, 0.1)' : 'transparent', border: 'none', color: uploading ? '#4B96FF' : 'rgba(255,255,255,0.7)',
                    cursor: uploading ? 'not-allowed' : 'pointer', opacity: 1,
                    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                    marginBottom: '2px'
                  }}>
                  {uploading ? (
                    <>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: '16px', height: '16px', animation: 'spin 1s linear infinite' }}>
                        <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
                      </svg>
                      <span style={{ fontSize: '12px', fontWeight: 600 }}>Uploading...</span>
                    </>
                  ) : (
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: '24px', height: '24px' }}>
                      <line x1="12" y1="5" x2="12" y2="19"></line>
                      <line x1="5" y1="12" x2="19" y2="12"></line>
                    </svg>
                  )}
                </button>

                <div style={{ position: 'relative', flex: 1, display: 'flex', alignItems: 'center', minWidth: 0, padding: '6px 0' }}>
                  {queryText === '' && (
                    <p className="ph" aria-hidden="true" style={{ position: 'absolute', left: '4px', top: '9px', fontSize: '16px', fontWeight: 400, color: 'rgba(255,255,255,0.55)', letterSpacing: '0.01em', margin: 0, pointerEvents: 'none' }}>Ask anything about Earth...</p>
                  )}
                  <textarea
                    ref={textareaRef}
                    value={queryText}
                    onChange={e => setQueryText(e.target.value)}
                    onKeyDown={e => { 
                      if (e.nativeEvent.isComposing) return;
                      if (e.key === 'Enter' && !e.shiftKey) { 
                        e.preventDefault(); 
                        handleSubmit(e); 
                      } 
                    }}
                    disabled={submitting}
                    rows={1}
                    style={{
                      width: '100%',
                      minWidth: 0,
                      background: 'transparent', border: 'none', outline: 'none', boxShadow: 'none',
                      resize: 'none', color: '#FFFFFF',
                      fontSize: '16px', fontWeight: 400, fontFamily: 'inherit',
                      lineHeight: '1.5', letterSpacing: '0.01em', overflowX: 'hidden',
                      whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', wordBreak: 'break-word',
                      padding: '4px 4px', minHeight: '28px', maxHeight: '200px', boxSizing: 'border-box'
                  }}
                  aria-label="Query input"
                />
              </div>

              <input ref={fileInputRef} type="file" multiple style={{ display: 'none' }} onChange={handleFileChange} accept="image/*,.pdf,.txt,.csv,.json,.geojson,.tif,.tiff" />
              
              <button type="button" aria-label="Toggle microphone" onClick={toggleListening} style={{ background: isListening ? 'rgba(75, 150, 255, 0.2)' : 'transparent', border: 'none', color: isListening ? '#4B96FF' : 'rgba(255,255,255,0.7)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '8px', borderRadius: '50%', transition: 'all 0.2s', marginBottom: '4px' }}>
                {isListening ? (
                  <div className="mic-wave-container">
                    <div className="mic-wave-bar" style={{ animationDelay: '0.0s' }} />
                    <div className="mic-wave-bar" style={{ animationDelay: '0.1s' }} />
                    <div className="mic-wave-bar" style={{ animationDelay: '0.2s' }} />
                    <div className="mic-wave-bar" style={{ animationDelay: '0.3s' }} />
                  </div>
                ) : (
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: '20px', height: '20px' }}>
                    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                    <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                    <line x1="12" y1="19" x2="12" y2="23"></line>
                    <line x1="8" y1="23" x2="16" y2="23"></line>
                  </svg>
                )}
              </button>
              <button type="submit" className="send-btn" aria-label="Submit query"
                disabled={submitting || !queryText.trim()}
                style={{ 
                  position: 'static', width: '38px', height: '38px', borderRadius: '50%', flexShrink: 0, 
                  background: queryText.trim() ? '#E5E7EB' : 'rgba(255,255,255,0.1)', 
                  display: 'flex', alignItems: 'center', justifyContent: 'center', 
                  border: 'none', cursor: 'pointer', transition: 'all 0.2s',
                  transform: submitting ? 'scale(0.96)' : 'scale(1)',
                  marginBottom: '3px'
                }}
                onMouseDown={e => e.currentTarget.style.transform = 'scale(0.96)'}
                onMouseUp={e => e.currentTarget.style.transform = 'scale(1)'}
                onMouseLeave={e => e.currentTarget.style.transform = 'scale(1)'}
              >
                <svg className="arrow" viewBox="0 0 12 14" fill="none" style={{ width: '16px', height: '16px', marginLeft: queryText.trim() ? '2px' : 0 }}>
                  <path d="M6 13V1M6 1L1.5 5.5M6 1l4.5 4.5" stroke={queryText.trim() ? '#111827' : 'rgba(255,255,255,0.5)'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
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
          </motion.form>
          </motion.div>
        </main>
      </div>
    </DashboardLayout>
  );
}
