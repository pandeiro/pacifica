import { useState, useMemo, useCallback } from 'react';
import { useTides } from '../../hooks/useTides';
import './TidesTile.css';

interface TidesTileProps {
  locationId: number;
}

function formatTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleTimeString('en-US', { 
    hour: 'numeric', 
    minute: '2-digit',
    hour12: true,
    timeZone: 'America/Los_Angeles'
  }).toLowerCase();
}

/**
 * Cosine interpolation between two tide events.
 * Tides follow a sinusoidal pattern between high and low points.
 */
function interpolateTideHeight(
  time: number,
  event1: { timestamp: string; height: number; type: string },
  event2: { timestamp: string; height: number; type: string }
): number {
  const t1 = new Date(event1.timestamp).getTime();
  const t2 = new Date(event2.timestamp).getTime();
  
  if (time <= t1) return event1.height;
  if (time >= t2) return event2.height;
  
  // Normalized time between 0 and 1
  const t = (time - t1) / (t2 - t1);
  
  // Cosine interpolation for smooth tide curve
  // Using cosine to create the characteristic tide curve shape
  const h1 = event1.height;
  const h2 = event2.height;
  
  // Cosine interpolation: h1 + (h2 - h1) * (1 - cos(π * t)) / 2
  return h1 + (h2 - h1) * (1 - Math.cos(Math.PI * t)) / 2;
}

export function TidesTile({ locationId }: TidesTileProps) {
  const { tides, isLoading, error } = useTides(locationId);
  const [hoverPos, setHoverPos] = useState<{ x: number; time: number; height: number } | null>(null);
  
  const width = 300;
  const height = 80;
  
  // Generate sorted graph data
  const graphData = useMemo(() => {
    if (!tides?.events) return [];
    return tides.events
      .map(event => ({
        timestamp: event.timestamp,
        height: event.height_ft,
        type: event.type
      }))
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
  }, [tides]);
  
  // Calculate scales for the graph
  const { minHeight, startTime, endTime, timeRange, heightRange } = useMemo(() => {
    if (graphData.length === 0) {
      return { minHeight: 0, startTime: 0, endTime: 1, timeRange: 1, heightRange: 1 };
    }
    const heights = graphData.map(e => e.height);
    const minH = Math.min(...heights);
    const maxH = Math.max(...heights);
    const start = new Date(graphData[0].timestamp).getTime();
    const end = new Date(graphData[graphData.length - 1].timestamp).getTime();
    return {
      minHeight: minH,
      startTime: start,
      endTime: end,
      timeRange: end - start || 1,
      heightRange: maxH - minH || 1
    };
  }, [graphData]);
  
  // Generate interpolated curve path using cosine interpolation
  const curvePath = useMemo(() => {
    if (graphData.length < 2) return '';
    
    const numPoints = 100; // Number of points for smooth curve
    let path = '';
    
    for (let i = 0; i <= numPoints; i++) {
      const t = i / numPoints;
      const time = startTime + t * timeRange;
      
      // Find which segment this time falls into
      let interpolatedHeight: number;
      for (let j = 0; j < graphData.length - 1; j++) {
        const t1 = new Date(graphData[j].timestamp).getTime();
        const t2 = new Date(graphData[j + 1].timestamp).getTime();
        if (time >= t1 && time <= t2) {
          interpolatedHeight = interpolateTideHeight(time, graphData[j], graphData[j + 1]);
          break;
        }
      }
      interpolatedHeight ??= graphData[0].height;
      
      const x = t * width;
      const normalizedHeight = (interpolatedHeight - minHeight) / heightRange;
      const y = height - (normalizedHeight * (height - 20) + 10);
      
      if (i === 0) {
        path = `M ${x},${y}`;
      } else {
        path += ` L ${x},${y}`;
      }
    }
    
    return path;
  }, [graphData, startTime, timeRange, minHeight, heightRange]);
  
  // Calculate current position on the curve
  const currentPos = useMemo(() => {
    if (!tides?.current_height_ft || graphData.length === 0) return null;
    
    const now = Date.now();
    if (now < startTime || now > endTime) return null;
    
    const x = ((now - startTime) / timeRange) * width;
    const normalizedHeight = (tides.current_height_ft - minHeight) / heightRange;
    const y = height - (normalizedHeight * (height - 20) + 10);
    
    return { x, y };
  }, [tides, graphData, startTime, endTime, timeRange, minHeight, heightRange]);
  
  // Handle mouse move for hover
  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (graphData.length < 2) return;
    
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const t = Math.max(0, Math.min(1, x / rect.width));
    const time = startTime + t * timeRange;
    
    // Find which segment and interpolate
    let interpolatedHeight = graphData[0].height;
    for (let j = 0; j < graphData.length - 1; j++) {
      const t1 = new Date(graphData[j].timestamp).getTime();
      const t2 = new Date(graphData[j + 1].timestamp).getTime();
      if (time >= t1 && time <= t2) {
        interpolatedHeight = interpolateTideHeight(time, graphData[j], graphData[j + 1]);
        break;
      }
    }
    
    setHoverPos({ x, time, height: interpolatedHeight });
  }, [graphData, startTime, timeRange]);
  
  const handleMouseLeave = useCallback(() => {
    setHoverPos(null);
  }, []);
  
  if (isLoading) {
    return (
      <div className="tile tides-tile" data-testid="tides-tile">
        <div className="tile__header">
          <div className="tile__title">Next Tides</div>
        </div>
        <div className="tile__content" data-testid="tile-loading">
          <div className="loading-state">Loading tide data...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="tile tides-tile tile--error" data-testid="tides-tile">
        <div className="tile__header">
          <div className="tile__title">Next Tides</div>
        </div>
        <div className="tile__content" data-testid="tile-error">
          <div className="error-state">Tide data unavailable</div>
        </div>
      </div>
    );
  }
  
  return (
    <div className="tile tides-tile" data-testid="tides-tile">
      <div className="tile__header">
        <div className="tile__title">Next Tides</div>
      </div>
      {tides?.station_info && (
        <div className="tile__subtitle">
          {tides.station_info.name} ({tides.station_info.distance_miles} mi {tides.station_info.direction})
        </div>
      )}

      <div className="tile__content">
        <div className="tides-tile__display">
          {tides?.next_low && (
            <div className="tides-tile__time-block tides-tile__low">
              <span className="tides-tile__time" data-testid="next-low">
                {formatTime(tides.next_low.timestamp)}
              </span>
              <span className="tides-tile__label">Low {tides.next_low.height_ft.toFixed(1)}ft</span>
            </div>
          )}
          
          <div className="tides-tile__arrow">→</div>
          
          {tides?.next_high && (
            <div className="tides-tile__time-block tides-tile__high">
              <span className="tides-tile__time" data-testid="next-high">
                {formatTime(tides.next_high.timestamp)}
              </span>
              <span className="tides-tile__label">High {tides.next_high.height_ft.toFixed(1)}ft</span>
            </div>
          )}
        </div>
        
        {graphData.length > 0 && (
          <div className="tides-tile__chart-container">
            <div 
              className="tide-curve" 
              data-testid="tides-curve"
              onMouseMove={handleMouseMove}
              onMouseLeave={handleMouseLeave}
            >
              <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
                {curvePath && (
                  <>
                    <path className="tide-curve__path" d={curvePath} fill="none" />
                    {currentPos && (
                      <circle 
                        className="tide-curve__current" 
                        cx={currentPos.x} 
                        cy={currentPos.y} 
                        r="4" 
                      />
                    )}
                    {/* Hover line */}
                    {hoverPos && (
                      <>
                        <line
                          className="tide-curve__hover-line"
                          x1={hoverPos.x}
                          y1="0"
                          x2={hoverPos.x}
                          y2={height}
                        />
                        <circle
                          className="tide-curve__hover-point"
                          cx={hoverPos.x}
                          cy={height - ((hoverPos.height - minHeight) / heightRange * (height - 20) + 10)}
                          r="3"
                        />
                      </>
                    )}
                  </>
                )}
              </svg>
            </div>
            {hoverPos && (
              <div className="tides-tile__hover-info">
                {formatTime(new Date(hoverPos.time).toISOString())} — {hoverPos.height.toFixed(1)}ft
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
