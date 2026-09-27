// Shared sidebar + background layout for all dashboard pages
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import '../styles/Dashboard.css';
import dashboardBg from '../../../ChatGPT Image Sep 18, 2026, 10_02_53 PM.png';
import { apiGet } from '../utils/api';
import { useBackground } from '../context/BackgroundContext';

function MenuButton({ icon, label, onClick, hasArrow }) {
  return (
    <button 
      onClick={onClick}
      style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '12px', background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer', borderRadius: '8px', textAlign: 'left', width: '100%' }}
      onMouseOver={e => e.currentTarget.style.background = 'rgba(255,255,255,0.1)'} 
      onMouseOut={e => e.currentTarget.style.background = 'transparent'}
    >
      <div style={{ width: '32px', color: '#ececec', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        {icon}
      </div>
      <div style={{ flex: 1, fontSize: '14px' }}>{label}</div>
      {hasArrow && (
        <svg viewBox="0 0 16 16" fill="none" style={{ width: '16px', opacity: 0.5 }}>
          <path d="M6 12L10 8L6 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      )}
    </button>
  );
}

let cachedRecentJobs = [];
let cachedUser = null;
try {
  const saved = sessionStorage.getItem('satquery_user');
  if (saved) cachedUser = JSON.parse(saved);
} catch {}
let cachedSidebarCollapsed = false;

export default function DashboardLayout({ children }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { hasConversation } = useBackground();
  
  const [sidebarCollapsed, setSidebarCollapsedState] = useState(cachedSidebarCollapsed);
  const [recentJobs, setRecentJobsState] = useState(cachedRecentJobs);
  const [user, setUserState] = useState(cachedUser);
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
  const profileMenuRef = useRef(null);

  // Custom setters to update both local state and module cache
  const setSidebarCollapsed = (val) => {
    let newVal = typeof val === 'function' ? val(sidebarCollapsed) : val;
    cachedSidebarCollapsed = newVal;
    setSidebarCollapsedState(newVal);
  };
  const setRecentJobs = (val) => {
    cachedRecentJobs = val;
    setRecentJobsState(val);
  };
  const setUser = (val) => {
    cachedUser = val;
    setUserState(val);
  };

  useEffect(() => {
    function handleClickOutside(event) {
      if (profileMenuRef.current && !profileMenuRef.current.contains(event.target)) {
        setIsProfileMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    fetchJobs();
    fetchUser();
  }, [location.pathname]); // refresh when navigating between pages

  async function fetchUser() {
    try {
      const data = await apiGet('/auth/me');
      setUser(data);
      sessionStorage.setItem('satquery_user', JSON.stringify(data));
    } catch (_) {}
  }

  async function fetchJobs() {
    try {
      const data = await apiGet('/jobs?limit=20');
      setRecentJobs(data.jobs || []);
    } catch (_) {}
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
    return {
      queued: '#6b7280',
      running: '#f59e0b',
      completed: '#22c55e',
      failed: '#ef4444',
      cancelled: '#9ca3af',
    }[s] || '#6b7280';
  }

  const navItems = [
    {
      label: 'Query Builder',
      path: '/dashboard',
      icon: (
        <svg className="sidebar-icon" viewBox="0 0 16 16" fill="none">
          <circle cx="6.5" cy="6.5" r="4" stroke="currentColor" strokeWidth="1.5"/>
          <path d="M10 10l3.5 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          <path d="M4.5 6.5h4M6.5 4.5v4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
        </svg>
      ),
    },
    {
      label: 'Area of Interest (AOI)',
      path: '/analysis',
      icon: (
        <svg className="sidebar-icon" viewBox="0 0 16 16" fill="none">
          <path d="M8 2L2 5.5v5L8 14l6-3.5v-5L8 2z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
          <path d="M2 5.5l6 3.5 6-3.5" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
          <line x1="8" y1="9" x2="8" y2="14" stroke="currentColor" strokeWidth="1.5"/>
        </svg>
      ),
    },
    {
      label: 'Documents',
      path: '/documents',
      icon: (
        <svg className="sidebar-icon" viewBox="0 0 16 16" fill="none">
          <path d="M3 2h7l3 3v9H3V2z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
          <path d="M10 2v3h3" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
          <line x1="5.5" y1="7.5" x2="10.5" y2="7.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
          <line x1="5.5" y1="10" x2="10.5" y2="10" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
        </svg>
      ),
    },
    {
      label: 'My Uploads',
      path: '/uploads',
      icon: (
        <svg className="sidebar-icon" viewBox="0 0 16 16" fill="none">
          <path d="M8 11V3M8 3L5 6M8 3l3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M3 13h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
        </svg>
      ),
    },
  ];

  return (
    <div className="stage">
      {/* Persistent sidebar - fixed position handled by Dashboard.css */}
      <aside className={`sidebar ${sidebarCollapsed ? 'collapsed' : ''}`} aria-label="SatQuery navigation">
        <div className="sidebar-header">
          <span className="sidebar-label">Navigation</span>
          <button
            className="sidebar-toggle"
            onClick={() => setSidebarCollapsed(c => !c)}
            aria-label="Collapse navigation"
          >
            <svg className="chev-icon" viewBox="0 0 14 14" fill="none">
              <path d="M8.5 2.5L4 7l4.5 4.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        </div>

        {/* Main nav items */}
        <div className="sidebar-main">
          {navItems.map(item => (
            <button
              key={item.path}
              className={`sidebar-item ${location.pathname === item.path ? 'active' : ''}`}
              onClick={() => navigate(item.path)}
            >
              {item.icon}
              <span className="sidebar-item-label">{item.label}</span>
            </button>
          ))}
        </div>

        {/* Recent Cases section */}
        {recentJobs.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', marginTop: '24px', flex: 1, minHeight: 0 }}>
            <div style={{ padding: '0 12px', marginBottom: '8px' }}>
              <span className="sidebar-label" style={{ fontSize: '11px', fontWeight: 600, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Recent Queries
              </span>
            </div>

            <div className="sidebar-scrollable" style={{ 
              display: 'flex', flexDirection: 'column', 
              overflowY: 'auto', 
              maxHeight: '200px', // Fixed height to show ~4 cases
            }}>
              {recentJobs.map(job => (
                <button
                  key={job.job_id}
                  className="sidebar-item"
                  onClick={() => {
                    if (job.aoi) navigate(`/analysis?jobId=${job.job_id}`);
                    else navigate(`/dashboard?jobId=${job.job_id}`);
                  }}
                  title={job.query}
                  style={{ 
                    padding: '10px 12px', minHeight: 'auto', borderRadius: '8px',
                    display: 'flex', alignItems: 'flex-start', gap: '12px',
                    flexShrink: 0
                  }}
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: '14px', marginTop: '2px', color: '#9ca3af', flexShrink: 0 }}>
                    <circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline>
                  </svg>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '2px', overflow: 'hidden' }}>
                    <span style={{ color: '#ececec', fontSize: '13px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', width: '100%', textAlign: 'left' }}>
                      {job.query}
                    </span>
                    <span style={{ color: '#9ca3af', fontSize: '11px' }}>
                      {relativeTime(job.updated_at || job.created_at)}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="sidebar-divider" aria-hidden="true"></div>

        <div className="sidebar-settings" style={{ paddingBottom: '12px' }}>
          {/* User Profile Popover Anchor */}
          <div ref={profileMenuRef} style={{ position: 'relative', marginTop: '6px' }}>
            <button 
              className="sidebar-item" 
              style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '6px 8px', height: 'auto', background: isProfileMenuOpen ? 'rgba(255,255,255,.1)' : 'transparent', width: '100%', border: 'none', cursor: 'pointer', borderRadius: '8px', textAlign: 'left', color: 'inherit' }}
              onClick={() => setIsProfileMenuOpen(!isProfileMenuOpen)}
              onMouseOver={e => !isProfileMenuOpen && (e.currentTarget.style.background = 'rgba(255,255,255,0.05)')}
              onMouseOut={e => !isProfileMenuOpen && (e.currentTarget.style.background = 'transparent')}
            >
              {/* Profile Avatar */}
              <div style={{ 
                width: '32px', height: '32px', borderRadius: '50%', background: '#ff80bf', 
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                color: '#fff', fontSize: '12px', fontWeight: '500', letterSpacing: '0.5px'
              }}>
                {user?.display_name ? user.display_name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() : 'U'}
              </div>
              
              {/* Profile Name */}
              <div className="sidebar-item-label" style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', flex: 1, overflow: 'hidden' }}>
                <span style={{ fontSize: '13px', fontWeight: 500, color: '#ececec', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', width: '100%', textAlign: 'left' }}>
                  {user?.display_name ? user.display_name.toUpperCase() : 'USER'}
                </span>
              </div>

              {/* iOS Settings/Gear Icon */}
              <svg viewBox="0 0 24 24" fill="none" style={{ width: '18px', color: 'rgba(255,255,255,0.6)', flexShrink: 0 }}>
                <path d="M12 15a3 3 0 100-6 3 3 0 000 6z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>

            {/* Profile Popover Menu */}
            {isProfileMenuOpen && (
              <div style={{
                position: 'absolute',
                bottom: 'calc(100% + 8px)',
                left: 0,
                width: '100%',
                background: '#202123',
                borderRadius: '12px',
                padding: '8px',
                boxShadow: '0 10px 40px rgba(0,0,0,0.5)',
                zIndex: 100,
                border: '1px solid rgba(255,255,255,0.1)',
                display: 'flex',
                flexDirection: 'column',
                color: '#ececec'
              }}>
                {/* Header row */}
                <button style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '12px', background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer', borderRadius: '8px', textAlign: 'left' }} onMouseOver={e => e.currentTarget.style.background = 'rgba(255,255,255,0.1)'} onMouseOut={e => e.currentTarget.style.background = 'transparent'}>
                  <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: '#ff80bf', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, color: '#fff', fontSize: '14px', fontWeight: '500' }}>
                    {user?.display_name ? user.display_name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() : 'U'}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '14px', fontWeight: 500 }}>{user?.display_name ? user.display_name.toUpperCase() : 'USER'}</div>
                  </div>
                  <svg viewBox="0 0 16 16" fill="none" style={{ width: '16px', opacity: 0.5 }}>
                    <path d="M6 12L10 8L6 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </button>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                  
                  {/* Language */}
                  <div 
                    style={{ display: 'flex', alignItems: 'center', padding: '12px', borderRadius: '8px', cursor: 'pointer', transition: 'background 0.2s', gap: '12px' }}
                    onMouseOver={e => e.currentTarget.style.background = 'rgba(255,255,255,0.08)'}
                    onMouseOut={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <div style={{ width: '32px', color: '#ececec', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <svg viewBox="0 0 24 24" fill="none" style={{ width: '16px' }}><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.5"/><path d="M2 12h20M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" stroke="currentColor" strokeWidth="1.5"/></svg>
                    </div>
                    <div style={{ color: '#ececec', fontSize: '14px', flex: 1 }}>Language</div>
                    <select style={{ background: 'transparent', border: 'none', color: 'rgba(255,255,255,0.6)', outline: 'none', cursor: 'pointer', fontSize: '14px', textAlign: 'right', appearance: 'none', padding: 0 }}>
                      <option value="en" style={{ color: '#000' }}>English</option>
                      <option value="es" style={{ color: '#000' }}>Español</option>
                      <option value="fr" style={{ color: '#000' }}>Français</option>
                    </select>
                  </div>
                  
                  {/* Map Style */}
                  <div 
                    style={{ display: 'flex', alignItems: 'center', padding: '12px', borderRadius: '8px', cursor: 'pointer', transition: 'background 0.2s', gap: '12px' }}
                    onMouseOver={e => e.currentTarget.style.background = 'rgba(255,255,255,0.08)'}
                    onMouseOut={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <div style={{ width: '32px', color: '#ececec', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <svg viewBox="0 0 24 24" fill="none" style={{ width: '16px' }}><path d="M9 4L4 7v13l5-3 6 3 5-3V4l-5 3-6-3z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/><path d="M9 4v13M15 7v13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
                    </div>
                    <div style={{ color: '#ececec', fontSize: '14px', flex: 1 }}>Map Style</div>
                    <select style={{ background: 'transparent', border: 'none', color: 'rgba(255,255,255,0.6)', outline: 'none', cursor: 'pointer', fontSize: '14px', textAlign: 'right', appearance: 'none', padding: 0 }}>
                      <option value="satellite" style={{ color: '#000' }}>Satellite</option>
                      <option value="dark" style={{ color: '#000' }}>Dark Mode</option>
                      <option value="street" style={{ color: '#000' }}>Streets</option>
                    </select>
                  </div>

                  {/* Delete Account */}
                  <div 
                    style={{ display: 'flex', alignItems: 'center', padding: '12px', borderRadius: '8px', cursor: 'pointer', transition: 'background 0.2s', gap: '12px' }}
                    onMouseOver={e => e.currentTarget.style.background = 'rgba(255,68,68,0.1)'}
                    onMouseOut={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <div style={{ width: '32px', color: '#ff4444', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <svg viewBox="0 0 24 24" fill="none" style={{ width: '16px' }}><path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
                    </div>
                    <div style={{ color: '#ff4444', fontSize: '14px', flex: 1 }}>Delete Account</div>
                  </div>

                </div>

                <div style={{ height: '1px', background: 'rgba(255,255,255,0.1)', margin: '8px 0' }} />

                <MenuButton icon={<svg viewBox="0 0 16 16" fill="none" style={{ width: '16px' }}><path d="M6 14H3a2 2 0 01-2-2V4a2 2 0 012-2h3M11 12l4-4-4-4M15 8H5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>} label="Log out" onClick={() => navigate('/auth')} />
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Persistent background — galaxy fades to plain black once conversation starts */}

      {/* Layer 0: plain conversation background (fades IN when hasConversation) */}
      <motion.div
        aria-hidden="true"
        initial={{ opacity: 0 }}
        animate={{ opacity: hasConversation ? 1 : 0 }}
        transition={{ duration: 1.4, ease: [0.22, 1, 0.36, 1] }}
        style={{
          position: 'absolute', inset: 0,
          background: '#050505',
          zIndex: 0,
          pointerEvents: 'none',
        }}
      />

      {/* Layer 1: galaxy image (fades OUT when hasConversation) */}
      <motion.img
        className="stage-image"
        src={dashboardBg}
        alt=""
        aria-hidden="true"
        initial={{ opacity: 1, filter: 'blur(0px)' }}
        animate={{
          opacity: hasConversation ? 0 : 1,
          filter: hasConversation ? 'blur(3px)' : 'blur(0px)',
        }}
        transition={{ duration: 1.4, ease: [0.22, 1, 0.36, 1] }}
      />

      {/* Layer 2: dark scrim overlay (fades OUT with galaxy) */}
      <motion.div
        className="stage-overlay"
        aria-hidden="true"
        initial={{ opacity: 1 }}
        animate={{ opacity: hasConversation ? 0 : 1 }}
        transition={{ duration: 1.4, ease: [0.22, 1, 0.36, 1] }}
      />

      {/* Page content injected here */}
      <div style={{ 
        position: 'absolute',
        top: 0,
        right: 0,
        bottom: 0,
        left: location.pathname === '/dashboard' ? '0px' : (sidebarCollapsed ? '140px' : '316px'),
        transition: 'left 280ms cubic-bezier(.16,1,.3,1)',
        overflow: 'hidden'
      }}>
        {children}
      </div>
    </div>
  );
}
