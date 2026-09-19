import React from 'react';
import { useNavigate } from 'react-router-dom';

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="relative w-screen h-screen overflow-hidden bg-black">
      {/* 
        This iframe loads the exact 2.8MB WebGL landing page from your public folder.
        We do this because standard React cannot easily compile 2.8MB of raw inline WebGL code.
      */}
      <iframe 
        src="/globe.html" 
        className="absolute inset-0 w-full h-full border-none"
        title="SatQuery 3D Globe"
      />

      {/* 
        We overlay a seamless React navigation header on top of the WebGL iframe. 
        This ensures that when you click "Sign In", React Router handles it instantly
        without the iframe causing page reloads or cross-origin errors!
      */}
      <div className="absolute top-0 left-0 w-full p-6 flex justify-between items-center pointer-events-none z-50">
        <div className="flex items-center gap-3">
          <span className="font-bold text-xl tracking-wider text-white font-mono uppercase drop-shadow-md">SATQUERY</span>
        </div>
        
        <div className="flex items-center gap-8 pointer-events-auto">
          <button 
            onClick={() => navigate('/auth')}
            className="px-6 py-2 rounded-full bg-white/10 hover:bg-white/20 text-white text-sm font-semibold backdrop-blur-md border border-white/20 transition-all shadow-lg"
          >
            Sign In to Dashboard
          </button>
        </div>
      </div>
      
      {/* 
        Optional: Bottom gradient to blend the iframe nicely if needed, 
        or a central call-to-action button right over the globe.
      */}
      <div className="absolute bottom-10 left-1/2 -translate-x-1/2 pointer-events-auto z-50">
        <button 
          onClick={() => navigate('/auth')}
          className="px-8 py-3.5 rounded-full bg-blue-600 hover:bg-blue-500 text-white font-semibold shadow-[0_0_30px_rgba(37,99,235,0.4)] transition-all hover:scale-105 active:scale-95 flex items-center gap-2"
        >
          Initialize Telemetry
          <span className="material-symbols-outlined text-[18px]">rocket_launch</span>
        </button>
      </div>
    </div>
  );
}
