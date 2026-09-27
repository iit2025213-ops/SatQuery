import React, { useState } from 'react';
import { motion } from 'framer-motion';

export default function UserMessage({ text, timestamp, onEdit, attachedAssets = [] }) {
  const [hovered, setHovered] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(text);
  };

  const isImage = (a) => {
    if (!a.name) return false;
    const ext = a.name.split('.').pop().toLowerCase();
    return ['jpg', 'jpeg', 'png', 'gif', 'webp', 'tif', 'tiff'].includes(ext);
  };

  return (
    <div 
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', marginBottom: '40px', width: '100%' }}
    >
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: 'easeOut' }}
        className="user-message-bubble"
        style={{
          display: 'flex',
          flexDirection: 'column',
          minWidth: 0,
          boxSizing: 'border-box',
          background: '#1A1A1A',
          borderRadius: '26px',
          padding: '16px 20px',
          position: 'relative'
        }}
      >
        {attachedAssets.length > 0 && (
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '12px' }}>
            {attachedAssets.map(a => (
              <div key={a.asset_id || a.name} style={{
                width: '64px', height: '64px', background: '#282A2C', borderRadius: '12px',
                display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden',
                border: '1px solid rgba(255,255,255,0.05)'
              }}>
                {isImage(a) && a.file_url ? (
                  <img src={a.file_url} alt={a.name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                ) : (
                  <div style={{ padding: '6px', display: 'flex', flexDirection: 'column', height: '100%', alignItems: 'center', justifyContent: 'center' }}>
                    <span style={{ fontSize: '16px', fontWeight: 600, color: '#a1a1aa' }}>📄</span>
                    <span style={{ fontSize: '9px', color: '#fff', marginTop: '4px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', width: '100%', textAlign: 'center' }}>{a.name}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        <div style={{
          color: '#F5F5F5',
          fontSize: '16.5px',
          lineHeight: '1.55',
          whiteSpace: 'pre-wrap',
          overflowWrap: 'anywhere',
          wordBreak: 'break-word',
          minWidth: 0
        }}>
          {text}
        </div>
        
        {timestamp && (
          <div style={{ 
            fontSize: '11.5px', 
            color: 'rgba(255,255,255,0.38)', 
            marginTop: '8px', 
            textAlign: 'right',
            lineHeight: 1
          }}>
            {typeof timestamp.toLocaleTimeString === 'function' 
              ? timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
              : String(timestamp)}
          </div>
        )}
      </motion.div>

      {/* Actions (Copy/Edit) */}
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: hovered ? 1 : 0 }}
        transition={{ duration: 0.2 }}
        style={{ 
          display: 'flex', 
          gap: '12px', 
          marginTop: '8px',
          paddingRight: '16px'
        }}
      >
        <button onClick={handleCopy} title="Copy" style={{
          background: 'none', border: 'none', cursor: 'pointer', padding: 0,
          color: '#666', display: 'flex', alignItems: 'center', gap: '4px',
          fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em',
          transition: 'color 0.2s'
        }} onMouseOver={e => e.currentTarget.style.color = '#999'} onMouseOut={e => e.currentTarget.style.color = '#666'}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
          </svg>
          Copy
        </button>
        {onEdit && (
          <button onClick={() => onEdit(text)} title="Edit" style={{
            background: 'none', border: 'none', cursor: 'pointer', padding: 0,
            color: '#666', display: 'flex', alignItems: 'center', gap: '4px',
            fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em',
            transition: 'color 0.2s'
          }} onMouseOver={e => e.currentTarget.style.color = '#999'} onMouseOut={e => e.currentTarget.style.color = '#666'}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 20h9"></path>
              <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
            </svg>
            Edit
          </button>
        )}
      </motion.div>
    </div>
  );
}
