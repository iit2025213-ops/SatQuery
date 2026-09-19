// Shared sidebar + background layout for all dashboard pages
import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import '../styles/Dashboard.css';
import dashboardBg from '../../../ChatGPT Image Sep 18, 2026, 10_02_53 PM.png';
import { apiGet } from '../utils/api';

export default function DashboardLayout({ children }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [recentJobs, setRecentJobs] = useState([]);

  useEffect(() => {
    fetchJobs();
  }, [location.pathname]); // refresh when navigating between pages

  async function fetchJobs() {
    try {
      const data = await apiGet('/jobs?limit=6');
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
          <>
            <div className="sidebar-divider" aria-hidden="true"></div>

            <div style={{ padding: '0 4px', flex: 1, overflowY: 'auto' }}>
              {/* Section label */}
              <div style={{
                display: 'flex', alignItems: 'center', gap: '6px',
                padding: '2px 8px 8px',
              }}>
                <svg viewBox="0 0 16 16" fill="none" style={{ width: '11px', opacity: 0.4, flexShrink: 0 }}>
                  <circle cx="8" cy="8" r="5.5" stroke="currentColor" strokeWidth="1.5"/>
                  <path d="M8 5v3.5l2.5 1.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                <span style={{
                  fontSize: '10px', fontWeight: 500, letterSpacing: '.10em',
                  color: 'rgba(255,255,255,.30)', textTransform: 'uppercase',
                }}>
                  Recent Cases
                </span>
              </div>

              {/* Job list */}
              {recentJobs.map(job => (
                <button
                  key={job.job_id}
                  className="sidebar-item"
                  onClick={() => navigate('/documents')}
                  style={{ flexDirection: 'column', alignItems: 'flex-start', gap: '2px', padding: '8px 10px' }}
                  title={job.query}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', width: '100%' }}>
                    <span style={{
                      width: '6px', height: '6px', borderRadius: '50%',
                      background: statusDot(job.status), flexShrink: 0,
                    }}/>
                    <span className="sidebar-item-label" style={{
                      fontSize: '12px',
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                      display: 'block', maxWidth: '170px',
                    }}>
                      {job.query}
                    </span>
                  </div>
                  <span className="sidebar-item-label" style={{
                    fontSize: '10px', color: 'rgba(255,255,255,.28)', paddingLeft: '12px',
                  }}>
                    {relativeTime(job.created_at)} · {job.status}
                  </span>
                </button>
              ))}
            </div>
          </>
        )}

        <div className="sidebar-divider" aria-hidden="true"></div>

        <div className="sidebar-settings">
          <button className="sidebar-item" onClick={() => navigate('/auth')}>
            <svg className="sidebar-icon" viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="2.2" stroke="currentColor" strokeWidth="1.4"/>
              <path d="M8 1.5v1.2M8 13.3v1.2M1.5 8h1.2M13.3 8h1.2 M3.4 3.4l.85.85M11.75 11.75l.85.85 M3.4 12.6l.85-.85M11.75 4.25l.85-.85" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
            </svg>
            <span className="sidebar-item-label">Settings</span>
          </button>
        </div>
      </aside>

      {/* Persistent background */}
      <img className="stage-image" src={dashboardBg} alt="" aria-hidden="true" />
      <div className="stage-overlay"></div>

      {/* Page content injected here */}
      {children}
    </div>
  );
}
