import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import AOIMap from '../components/AOIMap';

export default function MapPage() {
  const navigate = useNavigate();
  const [bounds, setBounds] = useState(null);

  return (
    <div style={{ width: '100vw', height: '100vh', backgroundColor: '#000', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <header style={{ padding: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
        <h1 style={{ color: 'white', margin: 0, fontSize: '1.2rem', fontFamily: 'sans-serif', letterSpacing: '2px' }}>
          SATQUERY <i style={{ color: '#888' }}>AI</i>
        </h1>
        <button 
          onClick={() => navigate('/')}
          style={{ background: 'transparent', color: 'white', border: '1px solid rgba(255,255,255,0.5)', padding: '8px 16px', borderRadius: '4px', cursor: 'pointer' }}
        >
          Back to Home
        </button>
      </header>

      {/* Map Area */}
      <div style={{ flex: 1, position: 'relative' }}>
        <AOIMap onBoundsChange={setBounds} />
        
        {/* Floating Query Box */}
        <div style={{
          position: 'absolute',
          bottom: '40px',
          left: '50%',
          transform: 'translateX(-50%)',
          width: '90%',
          maxWidth: '600px',
          backgroundColor: 'rgba(0,0,0,0.8)',
          backdropFilter: 'blur(10px)',
          padding: '20px',
          borderRadius: '12px',
          border: '1px solid rgba(255,255,255,0.2)',
          display: 'flex',
          gap: '10px'
        }}>
          <input 
            type="text" 
            placeholder="Ask a question about this area (e.g. 'Show me deforestation since 2023')" 
            style={{ flex: 1, background: 'transparent', border: 'none', color: 'white', fontSize: '16px', outline: 'none' }}
          />
          <button style={{ background: 'white', color: 'black', border: 'none', padding: '10px 20px', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' }}>
            Analyze
          </button>
        </div>
      </div>
    </div>
  );
}
