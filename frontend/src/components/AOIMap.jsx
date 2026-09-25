import { useState, useCallback, useRef, useEffect } from 'react';
import Map, { NavigationControl, Source, Layer, useMap } from 'react-map-gl/mapbox';
import 'mapbox-gl/dist/mapbox-gl.css';
import '@mapbox/mapbox-gl-draw/dist/mapbox-gl-draw.css';
import '@mapbox/mapbox-gl-geocoder/dist/mapbox-gl-geocoder.css';
import DrawControl from './DrawControl';
import GeocoderControl from './GeocoderControl';

export default function AOIMap({ onBoundsChange, onAoiChange, imageOverlayUrl, imageOverlayBounds }) {
  const [viewState, setViewState] = useState({
    longitude: 78.9629, // Center of India
    latitude: 20.5937,
    zoom: 2.5, // Zoomed out to see the globe
    pitch: 0, // 2D view by default
    bearing: 0
  });

  const [showLabels, setShowLabels] = useState(true);
  const [is3D, setIs3D] = useState(false);
  const [features, setFeatures] = useState({});
  const mapRef = useRef(null);

  const mapboxToken = import.meta.env.VITE_MAPBOX_TOKEN;

  // Cinematic fitBounds function
  const fitAoiBounds = (geometry) => {
    if (!geometry || !geometry.coordinates || !geometry.coordinates[0]) return;
    const coords = geometry.coordinates[0];
    let minLng = 180, minLat = 90, maxLng = -180, maxLat = -90;
    coords.forEach(pt => {
      if (pt[0] < minLng) minLng = pt[0];
      if (pt[0] > maxLng) maxLng = pt[0];
      if (pt[1] < minLat) minLat = pt[1];
      if (pt[1] > maxLat) maxLat = pt[1];
    });
    if (mapRef.current) {
      mapRef.current.fitBounds([[minLng, minLat], [maxLng, maxLat]], {
        padding: 100,
        duration: 2500, // Smooth cinematic 2.5s flight
        pitch: 20, // Add slight tilt for drama
        essential: true
      });
    }
  };

  const onUpdate = useCallback(e => {
    setFeatures(currFeatures => {
      const newFeatures = {...currFeatures};
      for (const f of e.features) {
        newFeatures[f.id] = f;
      }
      // Pass the last drawn feature to the parent as the AOI
      const featureList = Object.values(newFeatures);
      if (featureList.length > 0 && onAoiChange) {
        const geom = featureList[featureList.length - 1].geometry;
        onAoiChange(geom);
        fitAoiBounds(geom);
      } else if (featureList.length === 0 && onAoiChange) {
        onAoiChange(null);
      }
      return newFeatures;
    });
  }, [onAoiChange]);

  const onDelete = useCallback(e => {
    setFeatures(currFeatures => {
      const newFeatures = {...currFeatures};
      for (const f of e.features) {
        delete newFeatures[f.id];
      }
      // Pass the last remaining feature to the parent as the AOI, or null if none
      const featureList = Object.values(newFeatures);
      if (featureList.length > 0 && onAoiChange) {
        onAoiChange(featureList[featureList.length - 1].geometry);
      } else if (onAoiChange) {
        onAoiChange(null);
      }
      return newFeatures;
    });
  }, [onAoiChange]);

  if (!mapboxToken) {
    return <div style={{ color: 'white', padding: '20px' }}>Error: Please add VITE_MAPBOX_TOKEN to frontend/.env</div>;
  }

  // Use Mapbox official styles
  const mapStyle = showLabels 
    ? "mapbox://styles/mapbox/satellite-streets-v12"
    : "mapbox://styles/mapbox/satellite-v9";

  // Dimming mask
  const currentAoi = Object.values(features).pop()?.geometry;
  const maskGeoJSON = currentAoi ? {
    type: "Feature",
    geometry: {
      type: "Polygon",
      coordinates: [
        [[-180, -90], [180, -90], [180, 90], [-180, 90], [-180, -90]], // World ring
        currentAoi.coordinates[0] // Inner hole
      ]
    }
  } : null;

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      <Map
        ref={mapRef}
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
        projection="globe"
        preserveDrawingBuffer={true}
        terrain={is3D ? { source: 'mapbox-dem', exaggeration: 1.5 } : undefined}
      >
        {maskGeoJSON && (
          <Source id="dim-mask" type="geojson" data={maskGeoJSON}>
            <Layer 
              id="dim-mask-layer" 
              type="fill" 
              paint={{ 'fill-color': '#04050d', 'fill-opacity': 0.65 }} 
            />
          </Source>
        )}
        <NavigationControl position="top-right" />
        
        {/* Search Bar (Geocoder) */}
        <GeocoderControl mapboxAccessToken={mapboxToken} position="top-left" />

        {/* Drawing Tools */}
        <DrawControl
          position="top-right"
          displayControlsDefault={false}
          controls={{
            polygon: true,
            trash: true
          }}
          defaultMode="draw_polygon"
          onCreate={onUpdate}
          onUpdate={onUpdate}
          onDelete={onDelete}
        />
        
        {imageOverlayUrl && imageOverlayBounds && (
          <>
            <Source
              id="timeline-overlay"
              type="image"
              url={imageOverlayUrl}
              coordinates={[
                [imageOverlayBounds[0], imageOverlayBounds[3]], // top-left
                [imageOverlayBounds[2], imageOverlayBounds[3]], // top-right
                [imageOverlayBounds[2], imageOverlayBounds[1]], // bottom-right
                [imageOverlayBounds[0], imageOverlayBounds[1]]  // bottom-left
              ]}
            />
            <Layer
              id="timeline-overlay-layer"
              type="raster"
              source="timeline-overlay"
              paint={{
                'raster-opacity': 1,
                'raster-fade-duration': 0
              }}
            />
          </>
        )}
        
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
        top: '60px', /* Shifted down to make room for Geocoder */
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
          Enable 3D View
        </label>
      </div>
    </div>
  );
}
