import { useState } from 'react';
import Map, { NavigationControl, Source } from 'react-map-gl/mapbox';
import 'mapbox-gl/dist/mapbox-gl.css';

export default function AOIMap({ onBoundsChange }) {
  const [viewState, setViewState] = useState({
    longitude: 77.2090, // Delhi, India
    latitude: 28.6139,
    zoom: 11,
    pitch: 60, // Pitched for 3D view
    bearing: 0
  });

  const [showLabels, setShowLabels] = useState(true);
  const [is3D, setIs3D] = useState(true);

  // We now expect VITE_MAPBOX_TOKEN instead of VITE_MAPTILER_KEY
  const mapboxToken = import.meta.env.VITE_MAPBOX_TOKEN;

  if (!mapboxToken) {
    return <div style={{ color: 'white', padding: '20px' }}>Error: Please add VITE_MAPBOX_TOKEN to frontend/.env</div>;
  }

  // Use Mapbox official styles
  const mapStyle = showLabels 
    ? "mapbox://styles/mapbox/satellite-streets-v12"
    : "mapbox://styles/mapbox/satellite-v9";

  return (
    <div style={{ width: '100%', height: '500px', borderRadius: '12px', overflow: 'hidden', position: 'relative' }}>
      <Map
        {...viewState}
        onMove={evt => {
          setViewState(evt.viewState);
          if (onBoundsChange && evt.target) {
            const bounds = evt.target.getBounds();
            onBoundsChange(bounds);
          }
        }}
        mapboxAccessToken={mapboxToken}
        mapStyle={mapStyle}
        terrain={is3D ? { source: 'mapbox-dem', exaggeration: 1.5 } : undefined}
      >
        <NavigationControl position="top-right" />
        
        {is3D && (
          <Source
            id="mapbox-dem"
            type="raster-dem"
            url="mapbox://mapbox.mapbox-terrain-dem-v1"
            tileSize={512}
            maxzoom={14}
          />
        )}
      </Map>

      {/* Map Controls */}
      <div style={{
        position: 'absolute',
        top: '10px',
        left: '10px',
        backgroundColor: 'rgba(0,0,0,0.8)',
        padding: '10px',
        borderRadius: '8px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        border: '1px solid rgba(255,255,255,0.2)',
        color: 'white',
        fontFamily: 'sans-serif',
        fontSize: '14px'
      }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
          <input 
            type="checkbox" 
            checked={showLabels} 
            onChange={(e) => setShowLabels(e.target.checked)} 
          />
          Show Place Names
        </label>
        
        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
          <input 
            type="checkbox" 
            checked={is3D} 
            onChange={(e) => {
              const newIs3D = e.target.checked;
              setIs3D(newIs3D);
              // Reset pitch to 0 when going to 2D, pitch to 60 when going to 3D
              setViewState(prev => ({ ...prev, pitch: newIs3D ? 60 : 0 }));
            }} 
          />
          Enable 3D Terrain
        </label>
      </div>
    </div>
  );
}
