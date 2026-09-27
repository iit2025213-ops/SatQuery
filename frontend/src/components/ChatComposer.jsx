import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export default function ChatComposer({
  // Inputs/State
  queryText, setQueryText,
  onSubmit, submitting,
  
  // Attachments
  attachedAssets = [],
  removeAsset,
  handleAttachClick,
  uploading, uploadError,
  fileInputRef, handleFileChange,
  
  // Audio
  isListening, toggleListening,
  
  // Other
  textareaRef,
  isDashboard = false,
  hasMessages = true,
  
  // Map page extras
  topContent = null, // e.g. analysis mode toggle
  compact = false,
  placeholder = "Ask anything about Earth..."
}) {

  const isImage = (a) => {
    if (!a.name) return false;
    const ext = a.name.split('.').pop().toLowerCase();
    return ['jpg', 'jpeg', 'png', 'gif', 'webp', 'tif', 'tiff'].includes(ext);
  };

  return (
    <motion.form 
      layout
      transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
      className={`chatbar-composer ${isDashboard ? 'card' : ''}`} 
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit(queryText);
      }} 
      style={{ 
        position: 'relative', 
        width: '100%', 
        maxWidth: isDashboard ? (hasMessages ? '900px' : '850px') : '100%', 
        borderRadius: isDashboard ? (hasMessages ? '24px' : '32px') : (compact ? '12px' : '16px'), 
        height: 'auto', 
        minHeight: attachedAssets.length > 0 ? '140px' : (isDashboard ? (hasMessages ? '64px' : '72px') : 'auto'), 
        background: isDashboard ? 'rgba(25, 25, 28, 0.88)' : '#191919', 
        backdropFilter: isDashboard ? 'blur(18px) saturate(120%)' : 'none',
        border: isDashboard ? '1px solid rgba(255,255,255,0.08)' : '1px solid #2A2A2A',
        boxShadow: isDashboard ? '0 8px 40px rgba(0,0,0,0.30)' : 'none',
        display: 'flex', flexDirection: 'column', 
        justifyContent: 'flex-end', 
        padding: compact ? '10px 14px' : '12px 16px',
        gap: '8px'
      }}
    >
      {topContent}

      {/* Top area for attachments (if any) */}
      <AnimatePresence>
        {attachedAssets.length > 0 && (
          <motion.div 
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '4px', paddingLeft: '8px', overflow: 'hidden' }}
          >
            {attachedAssets.map(a => (
              <motion.div 
                key={a.asset_id}
                initial={{ opacity: 0, scale: 0.96, y: 4 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.9, y: 4 }}
                transition={{ duration: 0.25, ease: 'easeOut' }}
                style={{
                  width: compact ? '56px' : '72px', 
                  height: compact ? '56px' : '72px', 
                  background: '#282A2C', 
                  borderRadius: '16px',
                  display: 'flex', 
                  flexDirection: 'column', 
                  position: 'relative',
                  overflow: 'hidden',
                  border: '1px solid rgba(255,255,255,0.1)'
                }}
              >
                {isImage(a) && a.file_url ? (
                  <img src={a.file_url} alt={a.name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                ) : (
                  <div style={{ padding: '8px', display: 'flex', flexDirection: 'column', height: '100%', alignItems: 'center', justifyContent: 'center' }}>
                    <span style={{ fontSize: '18px', fontWeight: 600, color: '#a1a1aa' }}>📄</span>
                    <span style={{ fontSize: '9px', color: '#fff', marginTop: '6px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', width: '100%', textAlign: 'center' }}>{a.name}</span>
                  </div>
                )}
                
                <button type="button" onClick={() => removeAsset(a.asset_id)} style={{ 
                  position: 'absolute', top: '4px', right: '4px', 
                  background: 'rgba(0,0,0,0.5)', border: 'none', color: '#fff', 
                  borderRadius: '50%', width: '18px', height: '18px', 
                  display: 'flex', alignItems: 'center', justifyContent: 'center', 
                  cursor: 'pointer', fontSize: '11px', lineHeight: 1,
                  backdropFilter: 'blur(4px)',
                  transition: 'background 0.2s'
                }}
                onMouseOver={e => e.currentTarget.style.background = 'rgba(0,0,0,0.8)'}
                onMouseOut={e => e.currentTarget.style.background = 'rgba(0,0,0,0.5)'}
                >×</button>
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {uploadError && <div style={{ color: '#ef4444', fontSize: '11px', paddingLeft: '8px' }}>{uploadError}</div>}

      {/* Bottom area: input row */}
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: '12px', width: '100%' }}>
        <button type="button" aria-label="Attach file"
          onClick={handleAttachClick} disabled={uploading}
          style={{ 
            width: uploading ? '110px' : '36px', height: '36px', borderRadius: uploading ? '18px' : '50%', flexShrink: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
            background: 'transparent', border: 'none', color: '#555',
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
            <p className="ph" aria-hidden="true" style={{ position: 'absolute', left: '4px', top: '9px', fontSize: '16px', fontWeight: 400, color: 'rgba(255,255,255,0.55)', letterSpacing: '0.01em', margin: 0, pointerEvents: 'none' }}>{placeholder}</p>
          )}
          <textarea
            ref={textareaRef}
            value={queryText}
            onChange={e => setQueryText(e.target.value)}
            onKeyDown={e => { 
              if (e.nativeEvent.isComposing) return;
              if (e.key === 'Enter' && !e.shiftKey) { 
                e.preventDefault(); 
                onSubmit(queryText); 
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
        
        <button type="button" aria-label="Toggle microphone" onClick={toggleListening} style={{ background: isListening ? '#1E1E1E' : 'transparent', border: 'none', color: isListening ? '#888' : '#555', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '8px', borderRadius: '50%', transition: 'all 0.2s', marginBottom: '4px' }}>
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

    </motion.form>
  );
}
