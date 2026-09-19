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

  const [recentJobs, setRecentJobs] = useState([]);

  useEffect(() => {
    document.documentElement.classList.add('anim', 'play');
    const t = setTimeout(() => document.documentElement.classList.remove('anim', 'play'), 2600);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => { fetchJobs(); }, []);

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
        {/* NAV */}
        <header className="nav">
          <a href="#" className="brand" aria-label="SatQuery home">
            <svg className="brand-mark" viewBox="0 0 34 34" fill="none">
              <circle cx="17" cy="17" r="17" fill="#9C86CE"/>
              <circle cx="17" cy="17" r="8.6" fill="#FFFFFF"/>
              <circle cx="17" cy="17" r="3.7" fill="#151519"/>
            </svg>
            <span className="brand-word">SatQuery</span>
          </a>
        </header>

        {/* MAIN — centered composer */}
        <main className="hero" style={{ justifyContent: 'center' }}>

          {/* Recent Cases — shown above the composer if any exist */}
          {recentJobs.length > 0 && (
            <div style={{ width: 'calc(708*var(--u))', maxWidth: '100%', marginBottom: 'calc(8*var(--u))' }}>
              <p style={{ fontSize: 'calc(10.5*var(--u))', fontWeight: 500, letterSpacing: '.10em', color: 'rgba(255,255,255,.35)', textTransform: 'uppercase', marginBottom: 'calc(6*var(--u))' }}>
                Recent Cases
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'calc(4*var(--u))' }}>
                {recentJobs.map(job => (
                  <div key={job.job_id} style={{
                    display: 'flex', alignItems: 'center', gap: 'calc(8*var(--u))',
                    background: 'rgba(255,255,255,.04)',
                    border: '1px solid rgba(255,255,255,.07)',
                    borderRadius: 'calc(8*var(--u))',
                    padding: 'calc(7*var(--u)) calc(12*var(--u))',
                  }}>
                    <span style={{ width: 'calc(7*var(--u))', height: 'calc(7*var(--u))', borderRadius: '50%', background: statusDot(job.status), flexShrink: 0 }}/>
                    <span style={{ fontSize: 'calc(12*var(--u))', color: 'rgba(255,255,255,.72)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {job.query}
                    </span>
                    <span style={{ fontSize: 'calc(10*var(--u))', color: 'rgba(255,255,255,.30)', flexShrink: 0 }}>
                      {relativeTime(job.created_at)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Hero text */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 'calc(10*var(--u))', marginBottom: 'calc(20*var(--u))' }}>
            <h1 className="h1">Query the Earth</h1>
            <p className="h-sub" style={{ marginTop: 0 }}>
              From raw satellite data to real-world answers.<br/>Natural language. Real evidence.
            </p>
          </div>

          {/* COMPOSER CARD */}
          <form className="card" onSubmit={handleSubmit} style={{ position: 'relative' }}>

            {queryText === '' && (
              <p className="ph" aria-hidden="true">Ask anything about Earth...</p>
            )}

            <textarea
              value={queryText}
              onChange={e => setQueryText(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(e); } }}
              disabled={submitting}
              rows={1}
              style={{
                position: 'absolute',
                left: 'calc(27*var(--u))', top: 'calc(18*var(--u))',
                right: 'calc(24*var(--u))', bottom: 'calc(52*var(--u))',
                background: 'transparent', border: 'none', outline: 'none',
                resize: 'none', color: '#fff',
                fontSize: 'calc(15*var(--u))', fontFamily: 'inherit',
                lineHeight: '1.35', letterSpacing: '0.007em', overflowY: 'auto',
              }}
              aria-label="Query input"
            />

            {/* Attached file chips */}
            {attachedAssets.length > 0 && (
              <div style={{
                position: 'absolute',
                left: 'calc(19*var(--u))', bottom: 'calc(44*var(--u))',
                display: 'flex', gap: 'calc(5*var(--u))', flexWrap: 'wrap',
              }}>
                {attachedAssets.map(a => (
                  <span key={a.asset_id} style={{
                    display: 'inline-flex', alignItems: 'center', gap: '3px',
                    background: 'rgba(255,255,255,.10)', border: '1px solid rgba(255,255,255,.15)',
                    borderRadius: '5px', padding: '1px 5px',
                    fontSize: 'calc(9*var(--u))', color: 'rgba(255,255,255,.72)',
                    maxWidth: '110px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}>
                    📎 {a.name}
                    <button type="button" onClick={() => removeAsset(a.asset_id)}
                      style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,.45)', cursor: 'pointer', padding: 0, lineHeight: 1 }}>×</button>
                  </span>
                ))}
              </div>
            )}

            {/* Error messages */}
            {(submitError || uploadError) && (
              <div style={{
                position: 'absolute', top: 'calc(-26*var(--u))', left: 0, right: 0,
                textAlign: 'center', fontSize: 'calc(11*var(--u))', color: '#f87171',
              }}>{submitError || uploadError}</div>
            )}

            <div className="tools">
              <div className="chips">
                <button type="button" className="chip"><span className="chip-label">Sources</span></button>
                <button type="button" className="chip"><span className="chip-label">Advanced</span></button>
              </div>
              <div className="right">
                <input ref={fileInputRef} type="file" multiple style={{ display: 'none' }}
                  onChange={handleFileChange}
                  accept="image/*,.pdf,.txt,.csv,.json,.geojson,.tif,.tiff" />

                <button type="button" className="attach" aria-label="Attach file"
                  onClick={handleAttachClick} disabled={uploading}
                  style={{ opacity: uploading ? 0.5 : 1 }}>
                  <svg viewBox="0 0 20 24" fill="none">
                    <path d="M17.657 10.757L9.9 18.515a5 5 0 0 1-7.071-7.072l9.193-9.192a3 3 0 0 1 4.243 4.243L7.607 14.75a1 1 0 0 1-1.415-1.414l8.486-8.486" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </button>

                <button type="submit" className="send-btn" aria-label="Submit query"
                  disabled={submitting || !queryText.trim()}
                  style={{ opacity: (submitting || !queryText.trim()) ? 0.5 : 1 }}>
                  <svg className="arrow" viewBox="0 0 12 14" fill="none">
                    <path d="M6 13V1M6 1L1.5 5.5M6 1l4.5 4.5" stroke="#fff" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </button>
              </div>
            </div>
          </form>
        </main>
      </div>
    </DashboardLayout>
  );
}
