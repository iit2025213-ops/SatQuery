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
      <div style={{ flex: 1, overflowY: 'auto', padding: '40px 48px', display: 'flex', flexDirection: 'column' }}>
        
        {/* Header row */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '32px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <svg viewBox="0 0 24 24" fill="none" stroke="#60a5fa" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ width: '32px', height: '32px' }}>
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
              </svg>
              <h1 style={{ fontSize: '28px', fontWeight: 600, color: '#fff', letterSpacing: '-0.01em', margin: 0 }}>
                My Uploads
              </h1>
            </div>
            <p style={{ fontSize: '14px', color: '#a1a1aa', margin: 0 }}>
              Manage your satellite images, documents, and data files.
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
                display: 'flex', alignItems: 'center', gap: '8px',
                background: 'linear-gradient(135deg, #4F46E5 0%, #3B82F6 100%)',
                border: 'none', borderRadius: '999px',
                color: '#fff', cursor: uploading ? 'wait' : 'pointer',
                fontSize: '14px', fontWeight: 500,
                padding: '10px 20px',
                boxShadow: '0 4px 14px rgba(59, 130, 246, 0.4)',
                transition: 'opacity .2s',
                opacity: uploading ? 0.7 : 1
              }}
            >
              {uploading ? (
                <span>Uploading...</span>
              ) : (
                <>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: '16px' }}><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                  Upload Files
                </>
              )}
            </button>
          </div>
        </div>

        {uploadError && (
          <div style={{ color: '#f87171', fontSize: '14px', marginBottom: '16px' }}>{uploadError}</div>
        )}

        {loading && (
          <div style={{ color: 'rgba(255,255,255,.4)', fontSize: '14px' }}>Loading uploads...</div>
        )}

        {error && (
          <div style={{ color: '#f87171', fontSize: '14px' }}>{error}</div>
        )}

        {!loading && assets.length === 0 && (
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
            gap: '12px', marginTop: '60px', color: 'rgba(255,255,255,.30)',
          }}>
            <svg viewBox="0 0 48 48" fill="none" style={{ width: '48px', opacity: 0.25 }}>
              <path d="M24 32V16M24 16L17 23M24 16l7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M8 36h32" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
            <p style={{ fontSize: '14px', margin: 0 }}>No files uploaded yet.</p>
          </div>
        )}

        {/* Assets grid */}
        {!loading && assets.length > 0 && (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
            gap: '16px',
          }}>
            {assets.map(asset => {
              const isPdf = asset.filename.toLowerCase().endsWith('.pdf');
              const iconColor = isPdf ? '#ef4444' : '#14b8a6';
              const ext = asset.filename.split('.').pop().toUpperCase();
              
              return (
                <div key={asset.asset_id} style={{
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
                      {isPdf ? (
                        <svg viewBox="0 0 24 24" fill="currentColor" style={{ width: '20px' }}>
                          <path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>
                        </svg>
                      ) : (
                        <svg viewBox="0 0 24 24" fill="currentColor" style={{ width: '20px' }}>
                          <path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"/>
                        </svg>
                      )}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{
                        fontSize: '14px', fontWeight: 500, color: '#f3f4f6', margin: 0,
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'
                      }}>
                        {asset.filename}
                      </p>
                      <p style={{ fontSize: '12px', color: '#9ca3af', margin: '4px 0 0 0' }}>
                        {ext} · {formatBytes(asset.file_size_bytes)}
                      </p>
                    </div>
                  </div>

                  {/* Meta Footer */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '24px' }}>
                    <span style={{ fontSize: '12px', color: '#9ca3af' }}>
                      {relativeTime(asset.created_at)}
                    </span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      {asset.file_url && (
                        <a href={asset.file_url} target="_blank" rel="noopener noreferrer" style={{
                          fontSize: '13px', fontWeight: 500, color: '#3b82f6', textDecoration: 'none'
                        }}>View</a>
                      )}
                      {/* Replace 3 dots menu with Delete button */}
                      <button
                        onClick={() => handleDelete(asset.asset_id)}
                        disabled={deleting === asset.asset_id}
                        title="Delete file"
                        style={{
                          background: 'none', border: 'none', padding: 0,
                          color: '#ef4444', cursor: 'pointer', fontSize: '13px', fontWeight: 500
                        }}
                      >
                         {deleting === asset.asset_id ? '...' : 'Delete'}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
