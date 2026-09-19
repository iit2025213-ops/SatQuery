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
      <div style={{ flex: 1, overflowY: 'auto', padding: '40px 48px', display: 'flex', flexDirection: 'column', gap: '48px' }}>
        
        {/* Header row */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <svg viewBox="0 0 24 24" fill="none" stroke="#60a5fa" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ width: '32px', height: '32px' }}>
                 <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline>
              </svg>
              <h1 style={{ fontSize: '28px', fontWeight: 600, color: '#fff', letterSpacing: '-0.01em', margin: 0 }}>
                Documents
              </h1>
            </div>
            <p style={{ fontSize: '14px', color: '#a1a1aa', margin: 0 }}>
              Analysis reports and generated documents from your satellite queries.
            </p>
          </div>
        </div>

        {loading && (
          <div style={{ color: 'rgba(255,255,255,.4)', fontSize: '14px' }}>Loading documents...</div>
        )}

        {error && (
          <div style={{ color: '#f87171', fontSize: '14px' }}>{error}</div>
        )}

        {/* Generated Documents section (Grid Layout matching My Uploads) */}
        {!loading && documents.length > 0 && (
          <div>
            <p style={{ fontSize: '12px', fontWeight: 500, letterSpacing: '.10em', color: 'rgba(255,255,255,.30)', textTransform: 'uppercase', marginBottom: '20px', margin: '0 0 20px 0' }}>
              Generated Reports
            </p>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
              gap: '16px',
            }}>
              {documents.map(doc => {
                const isPdf = doc.format?.toLowerCase() === 'pdf';
                const iconColor = isPdf ? '#ef4444' : '#60a5fa';
                
                return (
                  <div key={doc.document_id} style={{
                    background: 'rgba(255, 255, 255, 0.03)',
                    border: '1px solid rgba(255, 255, 255, 0.06)',
                    borderRadius: '16px',
                    padding: '16px 20px',
                    display: 'flex', flexDirection: 'column',
                    position: 'relative',
                  }}>
                    {/* File icon + name */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                      <div style={{
                        width: '40px', height: '40px', borderRadius: '10px', flexShrink: 0,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        background: iconColor, color: '#fff'
                      }}>
                        <svg viewBox="0 0 24 24" fill="currentColor" style={{ width: '20px' }}>
                          <path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>
                        </svg>
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <p style={{
                          fontSize: '14px', fontWeight: 500, color: '#f3f4f6', margin: 0,
                          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'
                        }} title={doc.doc_type}>
                          {doc.doc_type || 'Document'}
                        </p>
                        <p style={{ fontSize: '12px', color: '#9ca3af', margin: '4px 0 0 0' }}>
                          {doc.format?.toUpperCase() || 'FILE'}
                        </p>
                      </div>
                    </div>

                    {/* Meta Footer */}
                    <div style={{ display: 'flex', flexDirection: 'column', marginTop: '20px', gap: '16px' }}>
                      <p style={{ fontSize: '12px', color: 'rgba(255,255,255,.5)', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={doc.jobQuery}>
                        From: {doc.jobQuery}
                      </p>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span style={{ fontSize: '12px', color: '#9ca3af' }}>
                          {relativeTime(doc.jobCreatedAt)}
                        </span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                          {doc.url && (
                            <a href={doc.url} target="_blank" rel="noopener noreferrer" style={{
                              fontSize: '13px', fontWeight: 500, color: '#3b82f6', textDecoration: 'none'
                            }}>View</a>
                          )}
                          {/* Delete button (functionality to be added later if needed) */}
                          <button style={{
                            background: 'none', border: 'none', padding: 0,
                            color: '#ef4444', cursor: 'pointer', fontSize: '13px', fontWeight: 500
                          }}>
                            Delete
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* All Jobs section (Glassmorphic List) */}
        {!loading && (
          <div>
            <p style={{ fontSize: '12px', fontWeight: 500, letterSpacing: '.10em', color: 'rgba(255,255,255,.30)', textTransform: 'uppercase', margin: '0 0 20px 0' }}>
              All Analysis Jobs
            </p>

            {jobs.length === 0 && (
              <p style={{ fontSize: '14px', color: 'rgba(255,255,255,.35)' }}>No queries submitted yet.</p>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {jobs.map(job => (
                <div key={job.job_id} style={{
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid rgba(255, 255, 255, 0.06)',
                  borderRadius: '16px',
                  padding: '16px 20px',
                  display: 'flex', alignItems: 'center', gap: '16px',
                }}>
                  <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: statusColor(job.status), flexShrink: 0 }}/>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ fontSize: '14px', fontWeight: 500, color: '#f3f4f6', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {job.query}
                    </p>
                    <p style={{ fontSize: '12px', color: '#9ca3af', margin: '4px 0 0 0' }}>
                      {job.status.charAt(0).toUpperCase() + job.status.slice(1)} · {relativeTime(job.created_at)}
                    </p>
                  </div>
                  {job.final_answer && (
                    <div style={{
                      fontSize: '13px', color: 'rgba(255,255,255,.6)',
                      maxWidth: '400px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>
                      {job.final_answer}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
