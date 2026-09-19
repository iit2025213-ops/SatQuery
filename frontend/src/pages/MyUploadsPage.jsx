import React, { useState, useEffect, useRef } from 'react';
import DashboardLayout from '../components/DashboardLayout';
import { apiGet, apiUpload, apiPost } from '../utils/api';

export default function MyUploadsPage() {
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [deleting, setDeleting] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => { fetchAssets(); }, []);

  async function fetchAssets() {
    setLoading(true);
    try {
      const data = await apiGet('/assets');
      setAssets(data.assets || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleFileChange(e) {
    const files = Array.from(e.target.files);
    if (!files.length) return;
    setUploading(true);
    setUploadError('');
    try {
      for (const file of files) {
        const fd = new FormData();
        fd.append('file', file);
        fd.append('modality', 'document');
        await apiUpload('/assets', fd);
      }
      fetchAssets();
    } catch (err) {
      setUploadError(err.message);
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  }

  async function handleDelete(asset_id) {
    setDeleting(asset_id);
    try {
      const token = localStorage.getItem('satquery_access_token');
      await fetch(`/api/v1/assets/${asset_id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      setAssets(prev => prev.filter(a => a.asset_id !== asset_id));
    } catch (_) {}
    setDeleting(null);
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

  function fileIcon(filename) {
    const ext = filename?.split('.').pop()?.toLowerCase();
    const icons = {
      pdf: '📄', png: '🖼️', jpg: '🖼️', jpeg: '🖼️',
      tif: '🛰️', tiff: '🛰️', geojson: '🗺️', json: '📋',
      csv: '📊', txt: '📝',
    };
    return icons[ext] || '📎';
  }

  function formatBytes(bytes) {
    if (!bytes) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
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
          display: 'flex', flexDirection: 'column', gap: 'calc(24*var(--u))',
        }}>
          {/* Header row */}
          <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
            <div>
              <h1 style={{ fontSize: 'calc(28*var(--u))', fontWeight: 600, color: '#fff', letterSpacing: '-0.01em', marginBottom: 'calc(6*var(--u))' }}>
                My Uploads
              </h1>
              <p style={{ fontSize: 'calc(13*var(--u))', color: 'rgba(255,255,255,.45)' }}>
                Satellite images, documents and data files you have uploaded.
              </p>
            </div>

            {/* Upload button */}
            <div>
              <input ref={fileInputRef} type="file" multiple style={{ display: 'none' }}
                onChange={handleFileChange}
                accept="image/*,.pdf,.txt,.csv,.json,.geojson,.tif,.tiff" />
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                style={{
                  display: 'flex', alignItems: 'center', gap: 'calc(8*var(--u))',
                  background: uploading ? 'rgba(255,255,255,.06)' : 'rgba(255,255,255,.10)',
                  border: '1px solid rgba(255,255,255,.14)',
                  borderRadius: 'calc(10*var(--u))',
                  color: '#fff', cursor: uploading ? 'wait' : 'pointer',
                  fontSize: 'calc(13*var(--u))', fontWeight: 500,
                  padding: 'calc(10*var(--u)) calc(18*var(--u))',
                  transition: 'background .18s',
                }}
              >
                {uploading ? (
                  <span>Uploading...</span>
                ) : (
                  <>
                    <svg viewBox="0 0 16 16" fill="none" style={{ width: 'calc(14*var(--u))' }}>
                      <path d="M8 11V3M8 3L5 6M8 3l3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                      <path d="M3 13h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                    </svg>
                    Upload Files
                  </>
                )}
              </button>
            </div>
          </div>

          {uploadError && (
            <div style={{ color: '#f87171', fontSize: 'calc(12*var(--u))' }}>{uploadError}</div>
          )}

          {loading && (
            <div style={{ color: 'rgba(255,255,255,.4)', fontSize: 'calc(13*var(--u))' }}>Loading uploads...</div>
          )}

          {error && (
            <div style={{ color: '#f87171', fontSize: 'calc(13*var(--u))' }}>{error}</div>
          )}

          {!loading && assets.length === 0 && (
            <div style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
              gap: 'calc(12*var(--u))', marginTop: 'calc(60*var(--u))',
              color: 'rgba(255,255,255,.30)',
            }}>
              <svg viewBox="0 0 48 48" fill="none" style={{ width: 'calc(48*var(--u))', opacity: 0.25 }}>
                <path d="M24 32V16M24 16L17 23M24 16l7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M8 36h32" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              </svg>
              <p style={{ fontSize: 'calc(14*var(--u))' }}>No files uploaded yet.</p>
              <p style={{ fontSize: 'calc(12*var(--u))' }}>Upload satellite images, PDFs, or data files using the button above.</p>
            </div>
          )}

          {/* Assets grid */}
          {!loading && assets.length > 0 && (
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(calc(240*var(--u)), 1fr))',
              gap: 'calc(10*var(--u))',
            }}>
              {assets.map(asset => (
                <div key={asset.asset_id} style={{
                  background: 'rgba(255,255,255,.05)',
                  border: '1px solid rgba(255,255,255,.09)',
                  borderRadius: 'calc(14*var(--u))',
                  padding: 'calc(16*var(--u))',
                  display: 'flex', flexDirection: 'column', gap: 'calc(8*var(--u))',
                  position: 'relative',
                }}>
                  {/* File icon + name */}
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 'calc(10*var(--u))' }}>
                    <span style={{ fontSize: 'calc(20*var(--u))', lineHeight: 1, flexShrink: 0 }}>
                      {fileIcon(asset.filename)}
                    </span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{
                        fontSize: 'calc(12.5*var(--u))', fontWeight: 500,
                        color: 'rgba(255,255,255,.85)',
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                      }}>
                        {asset.filename}
                      </p>
                      <p style={{ fontSize: 'calc(10.5*var(--u))', color: 'rgba(255,255,255,.35)', marginTop: '2px' }}>
                        {asset.modality} · {formatBytes(asset.file_size_bytes)}
                      </p>
                    </div>
                  </div>

                  {/* Meta */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: 'calc(10.5*var(--u))', color: 'rgba(255,255,255,.28)' }}>
                      {relativeTime(asset.created_at)}
                    </span>
                    <div style={{ display: 'flex', gap: 'calc(6*var(--u))' }}>
                      {asset.file_url && (
                        <a href={asset.file_url} target="_blank" rel="noopener noreferrer" style={{
                          fontSize: 'calc(10.5*var(--u))', color: '#60a5fa',
                          textDecoration: 'none',
                        }}>View</a>
                      )}
                      <button
                        onClick={() => handleDelete(asset.asset_id)}
                        disabled={deleting === asset.asset_id}
                        style={{
                          fontSize: 'calc(10.5*var(--u))', color: 'rgba(248,113,113,.7)',
                          background: 'none', border: 'none', cursor: 'pointer', padding: 0,
                        }}
                      >
                        {deleting === asset.asset_id ? '...' : 'Delete'}
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </main>
      </div>
    </DashboardLayout>
  );
}
