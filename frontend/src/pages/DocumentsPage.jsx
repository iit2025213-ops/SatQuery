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

      // Fetch documents for each completed job in parallel
      const completedJobs = allJobs.filter(j => j.status === 'completed');
      const docPromises = completedJobs.map(async (job) => {
        try {
          const docData = await apiGet(`/jobs/${job.job_id}/documents`);
          return (docData.documents || []).map(doc => ({
            ...doc,
            jobQuery: job.query,
            jobCreatedAt: job.created_at
          }));
        } catch (_) {
          return [];
        }
      });

      const docsArrays = await Promise.all(docPromises);
      setDocuments(docsArrays.flat());
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

  function docTypeLabel(docType) {
    const map = {
      'timeline_report': '📊 Timeline Analysis Report',
      'spatial_report': '🗺️ Spatial Analysis Report',
      'analysis_report': '📋 Analysis Report',
      'report_docx': '📄 Analysis Report',
      'temporal_report': '📊 Temporal Report',
      'change_report': '🔄 Change Detection Report',
    };
    return map[docType] || docType?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) || 'Document';
  }

  function formatBadgeColor(fmt) {
    const f = (fmt || '').toLowerCase();
    if (f === 'docx') return '#2563eb';
    if (f === 'pdf') return '#ef4444';
    if (f === 'md') return '#8b5cf6';
    return '#6b7280';
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
              gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
              gap: '16px',
            }}>
              {documents.map(doc => {
                const fmt = (doc.format || '').toUpperCase();
                const badgeColor = formatBadgeColor(doc.format);
                const downloadUrl = doc.cloudinary_url || doc.url || doc.file_url;
                
                return (
                  <div key={doc.document_id} style={{
                    background: 'rgba(255, 255, 255, 0.03)',
                    border: '1px solid rgba(255, 255, 255, 0.06)',
                    borderRadius: '16px',
                    padding: '16px 20px',
                    display: 'flex', flexDirection: 'column',
                    position: 'relative',
                    transition: 'border-color 0.2s',
                  }}
                    onMouseEnter={e => e.currentTarget.style.borderColor = 'rgba(255,255,255,0.15)'}
                    onMouseLeave={e => e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)'}
                  >
                    {/* File icon + name */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                      <div style={{
                        width: '40px', height: '40px', borderRadius: '10px', flexShrink: 0,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        background: badgeColor, color: '#fff'
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
                          {docTypeLabel(doc.doc_type)}
                        </p>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
                          <span style={{
                            fontSize: '10px', fontWeight: 700, padding: '2px 6px',
                            background: `${badgeColor}22`, color: badgeColor,
                            borderRadius: '4px', letterSpacing: '0.04em',
                          }}>
                            {fmt || 'FILE'}
                          </span>
                          <span style={{ fontSize: '12px', color: '#9ca3af' }}>
                            {relativeTime(doc.created_at || doc.jobCreatedAt)}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Query source */}
                    <div style={{ display: 'flex', flexDirection: 'column', marginTop: '16px', gap: '12px' }}>
                      {doc.jobQuery && (
                        <p style={{ fontSize: '12px', color: 'rgba(255,255,255,.45)', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={doc.jobQuery}>
                          Query: {doc.jobQuery}
                        </p>
                      )}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        {downloadUrl && (
                          <>
                            <a href={downloadUrl} target="_blank" rel="noopener noreferrer" style={{
                              fontSize: '13px', fontWeight: 500, color: '#3b82f6', textDecoration: 'none',
                              display: 'flex', alignItems: 'center', gap: '4px',
                            }}>
                              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: '13px', height: '13px' }}>
                                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                                <polyline points="15 3 21 3 21 9" />
                                <line x1="10" y1="14" x2="21" y2="3" />
                              </svg>
                              View
                            </a>
                            <a href={downloadUrl} download style={{
                              fontSize: '13px', fontWeight: 500, color: '#22c55e', textDecoration: 'none',
                              display: 'flex', alignItems: 'center', gap: '4px',
                            }}>
                              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: '13px', height: '13px' }}>
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                                <polyline points="7 10 12 15 17 10" />
                                <line x1="12" y1="15" x2="12" y2="3" />
                              </svg>
                              Download
                            </a>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {!loading && documents.length === 0 && (
          <div style={{
            textAlign: 'center', padding: '60px 20px',
            color: 'rgba(255,255,255,0.35)',
          }}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: '48px', height: '48px', margin: '0 auto 16px', opacity: 0.3 }}>
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
            <p style={{ fontSize: '15px', fontWeight: 500, margin: '0 0 6px' }}>No documents yet</p>
            <p style={{ fontSize: '13px', margin: 0 }}>Analysis reports will appear here after completing a query on the Analysis page.</p>
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
