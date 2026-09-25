import React, { useState, useEffect, useRef } from 'react';

const TimelinePlayer = ({ data, onFrameChange }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [activeMetric, setActiveMetric] = useState('ndvi_mean');
  const playInterval = useRef(null);

  const frames = data?.frames || [];
  const videoUrl = data?.video_url;
  const analytics = data?.analytics;

  // Automatically cycle frames when playing
  useEffect(() => {
    if (isPlaying) {
      playInterval.current = setInterval(() => {
        setCurrentIndex((prev) => (prev + 1) % frames.length);
      }, 1000); // 1 second per frame
    } else {
      clearInterval(playInterval.current);
    }
    return () => clearInterval(playInterval.current);
  }, [isPlaying, frames.length]);

  // Notify parent when frame changes
  useEffect(() => {
    if (frames[currentIndex]) {
      onFrameChange(frames[currentIndex]);
    }
  }, [currentIndex, frames, onFrameChange]);

  if (!frames || frames.length === 0) return null;

  const metricLabels = {
    'ndvi_mean': 'Vegetation (NDVI)',
    'ndwi_mean': 'Water (NDWI)',
    'ndbi_mean': 'Urban (NDBI)',
    'nbr_mean': 'Burn (NBR)',
  };

  const metricColors = {
    'ndvi_mean': '#10b981',
    'ndwi_mean': '#3b82f6',
    'ndbi_mean': '#f59e0b',
    'nbr_mean': '#ef4444',
  };

  // Chart Dimensions
  const chartHeight = 80;
  const chartWidth = 400; // Arbitrary wide width for SVG viewBox
  const minVal = -0.2; // typical min
  const maxVal = 1.0;  // typical max
  const activeColor = metricColors[activeMetric];

  const points = frames.map((f, i) => {
    const x = frames.length > 1 ? (i / (frames.length - 1)) * chartWidth : 0;
    const val = f[activeMetric] !== undefined && f[activeMetric] !== null ? f[activeMetric] : 0;
    const y = chartHeight - ((val - minVal) / (maxVal - minVal)) * chartHeight;
    return `${x},${y}`;
  }).join(' ');

  return (
    <div style={{
      width: '100%',
      background: 'rgba(255,255,255,0.06)',
      borderRadius: '16px',
      border: '1px solid rgba(255, 255, 255, 0.1)',
      padding: '16px',
      display: 'flex',
      flexDirection: 'column',
      gap: '12px',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <select 
          value={activeMetric}
          onChange={(e) => setActiveMetric(e.target.value)}
          style={{
            background: 'transparent',
            color: 'white',
            border: 'none',
            fontSize: '16px',
            fontWeight: 600,
            cursor: 'pointer',
            outline: 'none'
          }}
        >
          {Object.entries(metricLabels).map(([key, label]) => (
            <option key={key} value={key} style={{ background: '#1e1e1e' }}>{label}</option>
          ))}
        </select>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {frames[currentIndex].cloud_cover !== undefined && (
            <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: '12px' }}>
              ☁️ {Math.round(frames[currentIndex].cloud_cover)}%
            </span>
          )}
          <span style={{ color: activeColor, fontWeight: 600, fontSize: '14px', background: `${activeColor}1A`, padding: '4px 12px', borderRadius: '12px' }}>
            {frames[currentIndex].date}
          </span>
        </div>
      </div>

      {/* SVG Line Chart */}
      <div style={{ position: 'relative', width: '100%', height: `${chartHeight}px`, marginTop: '8px' }}>
        <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} preserveAspectRatio="none" style={{ width: '100%', height: '100%', overflow: 'visible' }}>
          {/* Grid lines */}
          <line x1="0" y1={chartHeight} x2={chartWidth} y2={chartHeight} stroke="rgba(255,255,255,0.1)" strokeWidth="1" />
          <line x1="0" y1={chartHeight/2} x2={chartWidth} y2={chartHeight/2} stroke="rgba(255,255,255,0.05)" strokeWidth="1" strokeDasharray="4 4" />
          <line x1="0" y1="0" x2={chartWidth} y2="0" stroke="rgba(255,255,255,0.05)" strokeWidth="1" strokeDasharray="4 4" />
          
          {/* Data Line */}
          <polyline
            fill="none"
            stroke={activeColor}
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
            points={points}
            style={{ filter: `drop-shadow(0 4px 6px ${activeColor}4D)` }}
          />

          {/* Current Frame Indicator */}
          <circle
            cx={frames.length > 1 ? (currentIndex / (frames.length - 1)) * chartWidth : 0}
            cy={chartHeight - (((frames[currentIndex][activeMetric] || 0) - minVal) / (maxVal - minVal)) * chartHeight}
            r="6"
            fill="#fff"
            stroke={activeColor}
            strokeWidth="3"
            style={{ transition: 'all 0.3s ease' }}
          />
        </svg>
      </div>

      {/* Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginTop: '8px' }}>
        <button
          onClick={() => setIsPlaying(!isPlaying)}
          style={{
            width: '40px', height: '40px', borderRadius: '50%',
            background: isPlaying ? 'rgba(239, 68, 68, 0.2)' : activeColor,
            color: isPlaying ? '#ef4444' : '#fff',
            border: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer', flexShrink: 0, transition: 'all 0.2s'
          }}
        >
          {isPlaying ? (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>
          ) : (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style={{ marginLeft: '2px' }}><polygon points="5 3 19 12 5 21 5 3"/></svg>
          )}
        </button>

        <input
          type="range"
          min={0}
          max={frames.length - 1}
          value={currentIndex}
          onChange={(e) => {
            setIsPlaying(false);
            setCurrentIndex(parseInt(e.target.value));
          }}
          style={{
            flex: 1,
            accentColor: activeColor,
            cursor: 'pointer'
          }}
        />
      </div>

      {/* Optional Phase 6 Analytics block */}
      {analytics && Object.keys(analytics).length > 0 && (
        <div style={{ 
          marginTop: '12px', 
          padding: '12px', 
          background: 'rgba(0,0,0,0.2)', 
          borderRadius: '12px',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px'
        }}>
          <h4 style={{ margin: 0, color: 'rgba(255,255,255,0.7)', fontSize: '12px', textTransform: 'uppercase' }}>Temporal Analytics</h4>
          
          {analytics.trend && (
            <div style={{ fontSize: '13px', color: '#fff' }}>
              <span style={{ color: '#8b5cf6', fontWeight: 600 }}>Trend: </span>
              {analytics.trend.data?.slope > 0.001 ? '📈 Increasing' : analytics.trend.data?.slope < -0.001 ? '📉 Decreasing' : '➡️ Stable'}
              <span style={{ color: 'rgba(255,255,255,0.5)', marginLeft: '8px', fontSize: '11px' }}>
                (p: {analytics.trend.data?.p_value?.toFixed(3) || 'N/A'})
              </span>
            </div>
          )}
          
          {analytics.temporal_breaks && (
            <div style={{ fontSize: '13px', color: '#fff' }}>
              <span style={{ color: '#f59e0b', fontWeight: 600 }}>Breaks Detected: </span>
              {analytics.temporal_breaks.data?.break_count || 0}
            </div>
          )}
        </div>
      )}

      {/* Optional GEE Timelapse Video */}
      {videoUrl && (
        <div style={{ marginTop: '12px' }}>
          <h4 style={{ margin: '0 0 8px 0', color: 'rgba(255,255,255,0.7)', fontSize: '12px', textTransform: 'uppercase' }}>Timelapse (GEE Native)</h4>
          <img src={videoUrl} alt="GEE Timelapse" style={{ width: '100%', borderRadius: '8px' }} />
        </div>
      )}
    </div>
  );
};

export default TimelinePlayer;
