import React, { useState, useEffect } from 'react';
import DashboardLayout from '../components/DashboardLayout';
import { apiGet } from '../utils/api';

export default function DocumentsPage() {
  const [jobs, setJobs] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchAll();
  }, []);

  async function fetchAll() {
    setLoading(true);
    try {
      // Fetch all jobs first
      const jobData = await apiGet('/jobs?limit=50');
      const allJobs = jobData.jobs || [];
      setJobs(allJobs);

      // Fetch documents for each completed job
      const allDocs = [];
      for (const job of allJobs.filter(j => j.status === 'completed')) {
        try {
          const docData = await apiGet(`/jobs/${job.job_id}/documents`);
          for (const doc of docData.documents || []) {
            allDocs.push({ ...doc, jobQuery: job.query, jobCreatedAt: job.created_at });
          }
        } catch (_) {}
      }
      setDocuments(allDocs);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
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

  function statusColor(status) {
    return { queued: '#6b7280', running: '#f59e0b', completed: '#22c55e', failed: '#ef4444', cancelled: '#9ca3af' }[status] || '#6b7280';
  }

  return (
    <DashboardLayout>
      <div className="frame" style={{ overflowY: 'auto' }}>
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

        <main style={{
          flex: 1, overflowY: 'auto',
          padding: 'calc(32*var(--u)) calc(40*var(--u)) calc(48*var(--u))',
          display: 'flex', flexDirection: 'column', gap: 'calc(32*var(--u))',
        }}>
          {/* Title */}
          <div>
            <h1 style={{ fontSize: 'calc(28*var(--u))', fontWeight: 600, color: '#fff', letterSpacing: '-0.01em', marginBottom: 'calc(6*var(--u))' }}>
              Documents
            </h1>
            <p style={{ fontSize: 'calc(13*var(--u))', color: 'rgba(255,255,255,.45)' }}>
              Analysis reports and generated documents from your satellite queries.
            </p>
          </div>

          {loading && (
            <div style={{ color: 'rgba(255,255,255,.4)', fontSize: 'calc(13*var(--u))' }}>Loading documents...</div>
          )}

          {error && (
            <div style={{ color: '#f87171', fontSize: 'calc(13*var(--u))' }}>{error}</div>
          )}

          {/* All Jobs section */}
          {!loading && (
            <div>
              <p style={{ fontSize: 'calc(10.5*var(--u))', fontWeight: 500, letterSpacing: '.10em', color: 'rgba(255,255,255,.30)', textTransform: 'uppercase', marginBottom: 'calc(12*var(--u))' }}>
                All Analysis Jobs
              </p>

              {jobs.length === 0 && (
                <p style={{ fontSize: 'calc(13*var(--u))', color: 'rgba(255,255,255,.35)' }}>No queries submitted yet.</p>
              )}

              <div style={{ display: 'flex', flexDirection: 'column', gap: 'calc(6*var(--u))' }}>
                {jobs.map(job => (
                  <div key={job.job_id} style={{
                    background: 'rgba(255,255,255,.05)',
                    border: '1px solid rgba(255,255,255,.09)',
                    borderRadius: 'calc(12*var(--u))',
                    padding: 'calc(14*var(--u)) calc(18*var(--u))',
                    display: 'flex', alignItems: 'center', gap: 'calc(12*var(--u))',
                  }}>
                    <span style={{ width: 'calc(8*var(--u))', height: 'calc(8*var(--u))', borderRadius: '50%', background: statusColor(job.status), flexShrink: 0 }}/>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{ fontSize: 'calc(13*var(--u))', color: 'rgba(255,255,255,.80)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {job.query}
                      </p>
                      <p style={{ fontSize: 'calc(11*var(--u))', color: 'rgba(255,255,255,.30)', marginTop: '2px' }}>
                        {job.status} · {relativeTime(job.created_at)}
                      </p>
                    </div>
                    {job.final_answer && (
                      <div style={{
                        fontSize: 'calc(10.5*var(--u))', color: 'rgba(255,255,255,.55)',
                        maxWidth: 'calc(200*var(--u))', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                      }}>
                        {job.final_answer}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Generated Documents section */}
          {!loading && documents.length > 0 && (
            <div>
              <p style={{ fontSize: 'calc(10.5*var(--u))', fontWeight: 500, letterSpacing: '.10em', color: 'rgba(255,255,255,.30)', textTransform: 'uppercase', marginBottom: 'calc(12*var(--u))' }}>
                Generated Reports
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'calc(6*var(--u))' }}>
                {documents.map(doc => (
                  <div key={doc.document_id} style={{
                    background: 'rgba(255,255,255,.05)',
                    border: '1px solid rgba(255,255,255,.09)',
                    borderRadius: 'calc(12*var(--u))',
                    padding: 'calc(14*var(--u)) calc(18*var(--u))',
                    display: 'flex', alignItems: 'center', gap: 'calc(12*var(--u))',
                  }}>
                    <svg viewBox="0 0 16 16" fill="none" style={{ width: 'calc(16*var(--u))', flexShrink: 0, opacity: 0.6 }}>
                      <path d="M3 2h7l3 3v9H3V2z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
                      <path d="M10 2v3h3" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
                    </svg>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{ fontSize: 'calc(13*var(--u))', color: 'rgba(255,255,255,.80)' }}>
                        {doc.doc_type} · <span style={{ color: 'rgba(255,255,255,.45)' }}>{doc.format?.toUpperCase()}</span>
                      </p>
                      <p style={{ fontSize: 'calc(11*var(--u))', color: 'rgba(255,255,255,.30)', marginTop: '2px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        From: {doc.jobQuery}
                      </p>
                    </div>
                    {doc.url && (
                      <a href={doc.url} target="_blank" rel="noopener noreferrer" style={{
                        fontSize: 'calc(11*var(--u))', color: '#60a5fa',
                        textDecoration: 'none', border: '1px solid rgba(96,165,250,.25)',
                        borderRadius: 'calc(6*var(--u))', padding: 'calc(4*var(--u)) calc(10*var(--u))',
                        flexShrink: 0,
                      }}>
                        Open ↗
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </main>
      </div>
    </DashboardLayout>
  );
}
