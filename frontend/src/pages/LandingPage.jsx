import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

export default function LandingPage() {
  const navigate = useNavigate();

  useEffect(() => {
    const handleMessage = (event) => {
      if (event.data === 'NAVIGATE_AUTH') {
        navigate('/auth');
      } else if (event.data === 'NAVIGATE_HOW_IT_WORKS') {
        navigate('/how-it-works');
      } else if (event.data === 'NAVIGATE_ARCHITECTURE') {
        navigate('/architecture');
      } else if (event.data === 'NAVIGATE_CAPABILITIES') {
        navigate('/capabilities');
      }
    };
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [navigate]);

  return (
    <div className="relative w-screen h-screen overflow-hidden bg-black">
      {/* 
        This iframe loads the exact 2.8MB WebGL landing page from your public folder.
        We do this because standard React cannot easily compile 2.8MB of raw inline WebGL code.
      */}
      <iframe 
        src={`/globe_v2.html?v=${Date.now()}`} 
        className="absolute inset-0 w-full h-full border-none"
        title="SatQuery 3D Globe"
      />

      {/* 
        We overlay a seamless React navigation header on top of the WebGL iframe. 
        This ensures that when you click "Sign In", React Router handles it instantly
        without the iframe causing page reloads or cross-origin errors!
      */}
      <div className="absolute top-0 left-0 w-full p-6 flex justify-between items-center pointer-events-none z-50">
        <div className="flex items-center gap-3 pointer-events-auto ml-6 mt-4">
          <a href="#hero" onClick={(e) => e.preventDefault()} style={{
            fontFamily: '"Playfair Display", serif',
            fontSize: '28px',
            fontWeight: 800,
            letterSpacing: '-.03em',
            color: '#fff',
            textDecoration: 'none',
            lineHeight: 1,
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            textShadow: '0 1px 4px rgba(0,0,0,0.8)'
          }}>
            SatQuery <em style={{
              fontStyle: 'normal',
              fontWeight: 600,
              fontSize: '15px',
              letterSpacing: '.12em',
              textTransform: 'uppercase',
              background: 'linear-gradient(90deg, #9ae6f2, #63c9de)',
              WebkitBackgroundClip: 'text',
              backgroundClip: 'text',
              color: 'transparent'
            }}>AI</em>
          </a>
        </div>
      </div>
    </div>
  );
}
