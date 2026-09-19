import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import './EarthHero.css';

export default function EarthHero({ activeTab, eyebrowText, titleText, ledeText, ctaText }) {
  const navigate = useNavigate();
  const [animClass, setAnimClass] = useState('anim');
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    // Entrance animation logic
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setAnimClass('');
      return;
    }

    const timer1 = setTimeout(() => {
      setAnimClass('anim play');
      const timer2 = setTimeout(() => {
        setAnimClass(''); // Clean up classes after animation finishes (2150ms)
      }, 2150);
      return () => clearTimeout(timer2);
    }, 100); // slight delay to ensure render

    return () => clearTimeout(timer1);
  }, []);

  return (
    <div className={`earth-hero-container ${animClass}`}>
      <div className="stage">
        <div className="sky">
          <video 
            className="is-active" 
            autoPlay 
            muted 
            loop 
            playsInline 
            preload="auto"
            src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260827_202422_3ffb4889-c520-432d-8458-038009eb40df.mp4" 
            poster="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260827_202133_508c64b8-a31e-4290-bdfc-1187df70e0a6.png"  
            aria-hidden="true"
          ></video>
        </div>
        <div className="ui">
          <header className="navbar">
            <div className="navrow" data-open={menuOpen ? "true" : "false"}>
              <Link to="/" className="logo">
                SatQuery <em>AI</em>
              </Link>
              <nav className="links" id="site-nav">
                <Link to="/how-it-works" aria-current={activeTab === 'how-it-works' ? "page" : undefined}>How it works</Link>
                <Link to="/architecture" aria-current={activeTab === 'architecture' ? "page" : undefined}>Architecture</Link>
                <Link to="/capabilities" aria-current={activeTab === 'capabilities' ? "page" : undefined}>Capabilities</Link>
                <button className="enroll" onClick={() => navigate('/')}>Back</button>
              </nav>
              <button 
                className="burger" 
                type="button" 
                aria-label={menuOpen ? "Close navigation" : "Open navigation"}
                aria-expanded={menuOpen} 
                aria-controls="site-nav"
                onClick={() => setMenuOpen(!menuOpen)}
              >
                <span></span><span></span><span></span>
              </button>
            </div>
          </header>
          <div className="copy">
            <div className="col eyebrow"><span className="ent-mask"><span className="ent-line">{eyebrowText}</span></span></div>
            <h1 className="col title"><span className="ent-mask"><span className="ent-line">{titleText}</span></span></h1>
            {titleText && <div className="col rule"><span></span></div>}
            <p className="col lede">{ledeText}</p>
            {ctaText && (
              <div className="col cta">
                <button className="cta-btn" type="button">
                  {ctaText}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
