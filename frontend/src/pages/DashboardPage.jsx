import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import DashboardLayout from '../components/DashboardLayout';
import { apiGet, apiPost, apiUpload, apiPut } from '../utils/api';
import { useBackground } from '../context/BackgroundContext';
import UserMessage from '../components/UserMessage';
import ChatComposer from '../components/ChatComposer';

export default function DashboardPage() {
  const navigate = useNavigate();
  const { setHasConversation } = useBackground();

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



  const location = useLocation();
  const urlJobId = new URLSearchParams(location.search).get('jobId');
  const [conversationId, setConversationId] = useState(null);

  useEffect(() => { 
    fetchJobs(); 
    fetchUser();
  }, []);

  useEffect(() => {
    if (urlJobId) {
      loadJob(urlJobId);
    } else {
      setConversationId(null);
      setMessages([]);
      setHasConversation(false);
    }
  }, [urlJobId]);

  async function loadJob(id) {
    try {
      const data = await apiGet(`/jobs/${id}`);
      if (data) {
        setConversationId(data.job_id);
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
              text: data.final_answer || 'Analysis in progress or no final answer recorded.', 
              timestamp: new Date(data.updated_at || data.created_at) 
            }
          ]);
        }
      }
    } catch (err) {
      console.error("Failed to load job", err);
    }
  }

  // Signal background transition when first message arrives
  useEffect(() => {
    if (messages.length > 0) {
      setHasConversation(true);
    }
  }, [messages.length, setHasConversation]);


  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  useEffect(() => {
    if (conversationId && messages.length > 0) {
      const cleanMessages = messages.filter(m => !m.isPolling && !m.isError && m.type !== 'job_status');
      apiPut(`/jobs/${conversationId}/messages`, { messages: cleanMessages }).catch(console.error);
    }
  }, [messages, conversationId]);

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
        const isImg = file.type.startsWith('image/');
        fd.append('modality', isImg ? 'RGB' : 'document');
        const result = await apiUpload('/assets', fd);
        uploaded.push({ name: file.name, asset_id: result.asset_id, file_url: result.file_url });
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
    
    const currentAssets = [...attachedAssets];
    // 1. Show user message immediately
    const userMsg = { role: 'user', text, attachedAssets: currentAssets, timestamp: new Date() };
    setMessages(prev => [...prev, userMsg]);
    
    setSubmitting(true);
    setSubmitError('');
    setQueryText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = '28px';
      textareaRef.current.style.overflowY = 'hidden';
    }
    
    setAttachedAssets([]);

    try {
      // 2. Build conversation history from current messages + new user message
      //    (setMessages above is async, so we build history manually)
      const historyForBrain = [
        ...messages
          .filter(m => !m.isError && !m.isPolling && m.type !== 'job_status')
          .map(m => ({ role: m.role, content: m.text || m.content || '' })),
        { role: 'user', content: text },
      ];

      // 3. POST to our backend /api/v1/brain which returns { brain_job_id }
      const res = await apiPost('/brain', {
        conversation_id: conversationId,
        query: text,
        messages: historyForBrain,
        asset_ids: currentAssets.map(a => a.asset_id),
      });
      
      const brainJobId = res.brain_job_id;
      if (!brainJobId) throw new Error("Did not receive a job ID from Brain.");
      
      if (!conversationId) setConversationId(brainJobId);

      // Add polling message
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        text: 'Analyzing your query (this may take a few minutes)...',
        isPolling: true,
        jobId: brainJobId,
        timestamp: new Date(),
      }]);

      // 4. Poll until complete
      let finalData = null;
      while (true) {
        await new Promise(r => setTimeout(r, 4000)); // poll every 4s
        try {
          const pollRes = await apiGet(`/brain/status/${brainJobId}`);
          if (pollRes.status === 'complete') {
            finalData = pollRes;
            break;
          } else if (pollRes.status === 'failed' || pollRes.status === 'error') {
            throw new Error(pollRes.error || "Analysis failed.");
          }
          // else status is 'polling', continue...
        } catch (pollErr) {
           if (pollErr.status === 404) throw new Error("Brain job expired or not found.");
           console.warn("Poll error, retrying...", pollErr);
        }
      }

      // 5. Replace polling message with final response
      setMessages(prev => {
        const newMsgs = [...prev];
        const lastIdx = newMsgs.map(m => m.jobId).lastIndexOf(brainJobId);
        if (lastIdx !== -1) {
          newMsgs[lastIdx] = { 
            role: 'assistant', 
            text: finalData.reply || 'No response from Brain.',
            artifact_ids: finalData.artifact_ids || [],
            confidence: finalData.confidence ?? null,
            timestamp: new Date(),
          };
        } else {
          // Fallback if the user navigated away and back?
          newMsgs.push({
            role: 'assistant', 
            text: finalData.reply || 'No response from Brain.',
            artifact_ids: finalData.artifact_ids || [],
            confidence: finalData.confidence ?? null,
            timestamp: new Date(),
          });
        }
        return newMsgs;
      });

      fetchJobs(); // Refresh recent queries in sidebar
    } catch (err) {
      const errorText = err.message || 'Something went wrong. Please try again.';
      setSubmitError(errorText);
      setMessages(prev => [...prev, { 
        role: 'assistant',
        isError: true,
        text: `⚠️ ${errorText}`, 
        timestamp: new Date(),
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
                      {/* No avatar — content leads */}
                      
                      {msg.role === 'user' ? (
                        <UserMessage 
                          text={msg.text}
                          timestamp={msg.timestamp}
                          attachedAssets={msg.attachedAssets}
                          onEdit={(text) => {
                            setQueryText(text);
                            if (textareaRef.current) {
                              textareaRef.current.focus();
                            }
                          }}
                        />
                      ) : (
                        <div style={{
                          width: '100%',
                          maxWidth: '100%',
                          minWidth: 0,
                          boxSizing: 'border-box',
                          color: '#EDEDED',
                          padding: '2px 0',
                          fontSize: '16px', lineHeight: '1.72',
                          display: 'flex', flexDirection: 'column',
                          overflowWrap: 'anywhere', wordBreak: 'break-word',
                        }}>
                          {msg.isError ? (
                            <div style={{ fontSize: '15px', color: '#888', lineHeight: '1.6' }}>
                              {(msg.text || '').replace(/^⚠️\s*/, '')}
                            </div>
                          ) : msg.isPolling ? (
                            <motion.div 
                              animate={{ opacity: [0.5, 1, 0.5] }}
                              transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                              style={{ color: '#888', fontStyle: 'italic', fontSize: '15px' }}
                            >
                              {msg.text}
                            </motion.div>
                          ) : msg.type === 'job_status' ? (
                            <div>
                              <div style={{ fontWeight: 500, fontSize: '16px', color: '#DDD', marginBottom: '8px' }}>{msg.text}</div>
                              <div style={{ color: '#777', marginBottom: '12px', fontSize: '15px' }}>Your query has been queued for processing.</div>
                              <div style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#444', marginBottom: '4px' }}>Job ID</div>
                              <div style={{ fontFamily: 'monospace', color: '#555', background: '#111', padding: '6px 10px', borderRadius: '6px', width: 'fit-content', marginBottom: '12px', fontSize: '13px' }}>{msg.jobId}</div>
                              <div style={{ color: '#555', fontSize: '14px' }}>Track progress from the Area of Interest tab.</div>
                            </div>
                          ) : (
                            <div style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', wordBreak: 'break-word', minWidth: 0 }}>{msg.text}</div>
                          )}

                          {/* Artifacts — download buttons */}
                          {msg.artifact_ids && msg.artifact_ids.length > 0 && (
                            <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                              <div style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#333', marginBottom: '2px' }}>
                                Generated Artifacts
                              </div>
                              {msg.artifact_ids.map((artifactPath, ai) => {
                                const filename = artifactPath.split('/').pop() || `artifact_${ai + 1}`;
                                const backendBase = import.meta.env.VITE_API_URL || 'http://localhost:8000';
                                const downloadUrl = (artifactPath.startsWith('http://') || artifactPath.startsWith('https://'))
                                  ? artifactPath 
                                  : `${backendBase}/api/v1/brain/artifacts/${encodeURIComponent(artifactPath)}`;
                                const isImage = ['.png', '.jpg', '.jpeg', '.tif', '.tiff', '.webp', '.gif'].some(ext => filename.toLowerCase().endsWith(ext));
                                return (
                                  <div key={ai} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                    {isImage ? (
                                      <a href={downloadUrl} target="_blank" rel="noopener noreferrer">
                                        <img 
                                          src={downloadUrl} 
                                          alt={`AI Generated Mask - ${filename}`} 
                                          style={{ maxWidth: '100%', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.1)' }}
                                        />
                                      </a>
                                    ) : (
                                      <a
                                        href={downloadUrl}
                                        download={filename}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        style={{
                                          display: 'inline-flex', alignItems: 'center', gap: '8px',
                                          background: '#111', border: '1px solid #222',
                                          borderRadius: '8px', padding: '8px 14px',
                                          color: '#888', fontSize: '13px',
                                          textDecoration: 'none', width: 'fit-content',
                                          transition: 'border-color 0.15s, color 0.15s',
                                        }}
                                        onMouseOver={e => { e.currentTarget.style.borderColor = '#333'; e.currentTarget.style.color = '#BBB'; }}
                                        onMouseOut={e => { e.currentTarget.style.borderColor = '#222'; e.currentTarget.style.color = '#888'; }}
                                      >
                                        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ width: '13px', height: '13px', flexShrink: 0 }}>
                                          <path d="M8 2v8M5 7l3 3 3-3" strokeLinecap="round" strokeLinejoin="round" />
                                          <path d="M2 13h12" strokeLinecap="round" />
                                        </svg>
                                        {filename}
                                      </a>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          )}

                          {/* Confidence score */}
                          {msg.confidence != null && (
                            <div style={{ marginTop: '10px', fontSize: '11px', color: '#2A2A2A' }}>
                              Confidence: {(msg.confidence * 100).toFixed(0)}%
                            </div>
                          )}
                          {msg.timestamp && (
                            <div style={{ fontSize: '10px', color: '#2A2A2A', marginTop: '8px', textAlign: 'left', whiteSpace: 'nowrap' }}>
                              {typeof msg.timestamp.toLocaleTimeString === 'function'
                                ? msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                                : new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </div>
                          )}
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
            <ChatComposer 
              queryText={queryText}
              setQueryText={setQueryText}
              onSubmit={handleSubmit}
              submitting={submitting}
              attachedAssets={attachedAssets}
              removeAsset={removeAsset}
              handleAttachClick={handleAttachClick}
              uploading={uploading}
              uploadError={uploadError}
              isListening={isListening}
              toggleListening={toggleListening}
              fileInputRef={fileInputRef}
              handleFileChange={handleFileChange}
              textareaRef={textareaRef}
              isDashboard={true}
              hasMessages={hasMessages}
            />
          </motion.div>
        </main>
      </div>
    </DashboardLayout>
  );
}
