import React, { useEffect, useRef, useState } from 'react';
import '../styles/LandingPage.css';

const LandingPage = () => {
  const [navOpen, setNavOpen] = useState(false);
  const canvasRef = useRef(null);
  const videoRef = useRef(null);


  useEffect(() => {
    let timeoutIds = [];
    const runAnimations = () => {
      document.documentElement.classList.add('anim');
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          document.documentElement.classList.add('play');
          if (videoRef.current) {
            videoRef.current.classList.add('is-active');
          }
          const id = setTimeout(() => {
            document.documentElement.classList.remove('anim', 'play');
          }, 2150);
          timeoutIds.push(id);
        });
      });
    };

    if (window.matchMedia && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      if (document.fonts && document.fonts.ready) {
        Promise.race([
          document.fonts.ready,
          new Promise(r => setTimeout(r, 500))
        ]).then(runAnimations);
      } else {
        const id = setTimeout(runAnimations, 100);
        timeoutIds.push(id);
      }
    } else {
      if (videoRef.current) {
        videoRef.current.classList.add('is-active');
      }
    }

    return () => {
      timeoutIds.forEach(clearTimeout);
      document.documentElement.classList.remove('anim', 'play');
    };
  }, []);

  // Starfield Animation Loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationFrameId;

    const numStars = 250;
    const stars = [];

    const resizeCanvas = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    
    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();

    for (let i = 0; i < numStars; i++) {
      stars.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        size: Math.random() * 1.5 + 0.3,
        speed: Math.random() * 0.3 + 0.1
      });
    }

    const drawStars = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = '#ffffff';
      
      for (let i = 0; i < numStars; i++) {
        let s = stars[i];
        ctx.beginPath();
        ctx.globalAlpha = (s.size / 1.8);
        ctx.arc(s.x, s.y, s.size, 0, 2 * Math.PI);
        ctx.fill();
        
        s.x += s.speed;
        
        if (s.x > canvas.width) {
          s.x = 0;
          s.y = Math.random() * canvas.height;
        }
      }
      animationFrameId = requestAnimationFrame(drawStars);
    };

    drawStars();

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  // Handlers for closing nav
  useEffect(() => {
    const handleGlobalClick = (e) => {
      if (navOpen && !e.target.closest('.links') && !e.target.closest('.burger')) {
        setNavOpen(false);
      }
    };
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && navOpen) {
        setNavOpen(false);
      }
    };
    document.addEventListener('click', handleGlobalClick);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('click', handleGlobalClick);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [navOpen]);

  return (
    <div className="stage">
      <div className="sky" id="sky-bg">
        <canvas id="starfield" ref={canvasRef}></canvas>
        <video 
          ref={videoRef}
          data-planet="earth" 
          autoPlay 
          muted 
          loop 
          playsInline 
          src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260827_202422_3ffb4889-c520-432d-8458-038009eb40df.mp4" 
          poster="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260827_202133_508c64b8-a31e-4290-bdfc-1187df70e0a6.png" 
          aria-hidden="true"
        />
      </div>
      
      <div className="ui">
        <header className="navbar">
          <div className="navrow" data-open={navOpen}>
            <a className="logo" href="/">SATQUERY <i>AI</i></a>
            <nav className="links" onClick={(e) => { if (e.target.tagName === 'A') setNavOpen(false); }}>
              <a href="#how-it-works" aria-current="page">How It Works</a>
              <a href="#capabilities">Capabilities</a>
              <a href="/analysis">Intelligence</a>
              <a href="#evidence">Evidence</a>
              <a className="enroll" href="/signin">Sign In</a>
            </nav>
            <button 
              className="burger" 
              type="button" 
              aria-label={navOpen ? "Close navigation" : "Open navigation"} 
              aria-expanded={navOpen} 
              onClick={() => setNavOpen(!navOpen)}
            >
              <span></span><span></span><span></span>
            </button>
          </div>
        </header>
        
        <div className="copy">
          <div className="col eyebrow">
            <span className="ent-mask"><span className="ent-line">AGENTIC EARTH OBSERVATION</span></span>
          </div>
          <h1 className="col title">
            <span className="ent-mask">
              <span className="ent-line">ASK EARTH.<br />GET EVIDENCE.</span>
            </span>
          </h1>
          <div className="col rule"><span></span></div>
          <div className="col cta">
            <a href="/analysis">START ANALYSIS</a>
          </div>
        </div>
      </div>
      

    </div>
  );
};

export default LandingPage;
// Done landing page
