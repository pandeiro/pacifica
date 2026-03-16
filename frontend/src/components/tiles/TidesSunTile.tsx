import { useTides } from '../../hooks/useTides';
import './TidesSunTile.css';

interface TidesSunTileProps {
  locationId: number;
  stationId: string;
}

function formatTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleTimeString('en-US', { 
    hour: 'numeric', 
    minute: '2-digit',
    hour12: true 
  }).toLowerCase();
}

function generateTideCurvePath(events: Array<{ timestamp: string; height_ft: number }>, width: number, height: number): string {
  if (events.length === 0) return '';
  
  // Sort events by timestamp
  const sortedEvents = [...events].sort((a, b) => 
    new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );
  
  // Find min and max heights for scaling
  const heights = sortedEvents.map(e => e.height_ft);
  const minHeight = Math.min(...heights);
  const maxHeight = Math.max(...heights);
  const heightRange = maxHeight - minHeight || 1;
  
  // Time range
  const startTime = new Date(sortedEvents[0].timestamp).getTime();
  const endTime = new Date(sortedEvents[sortedEvents.length - 1].timestamp).getTime();
  const timeRange = endTime - startTime || 1;
  
  // Generate points
  const points = sortedEvents.map(event => {
    const time = new Date(event.timestamp).getTime();
    const x = ((time - startTime) / timeRange) * width;
    // Invert Y because SVG Y=0 is at top
    const normalizedHeight = (event.height_ft - minHeight) / heightRange;
    const y = height - (normalizedHeight * (height - 20) + 10); // Leave padding
    return { x, y };
  });
  
  // Create smooth curve using Catmull-Rom spline converted to cubic bezier
  if (points.length < 2) return '';
  
  let path = `M ${points[0].x},${points[0].y}`;
  
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[Math.max(0, i - 1)];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[Math.min(points.length - 1, i + 2)];
    
    const cp1x = p1.x + (p2.x - p0.x) / 6;
    const cp1y = p1.y + (p2.y - p0.y) / 6;
    const cp2x = p2.x - (p3.x - p1.x) / 6;
    const cp2y = p2.y - (p3.y - p1.y) / 6;
    
    path += ` C ${cp1x},${cp1y} ${cp2x},${cp2y} ${p2.x},${p2.y}`;
  }
  
  return path;
}

function getCurrentPosition(events: Array<{ timestamp: string; height_ft: number }>, width: number, height: number, currentHeight: number | null): { x: number; y: number } | null {
  if (!currentHeight || events.length === 0) return null;
  
  const sortedEvents = [...events].sort((a, b) => 
    new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );
  
  const heights = sortedEvents.map(e => e.height_ft);
  const minHeight = Math.min(...heights);
  const maxHeight = Math.max(...heights);
  const heightRange = maxHeight - minHeight || 1;
  
  const startTime = new Date(sortedEvents[0].timestamp).getTime();
  const endTime = new Date(sortedEvents[sortedEvents.length - 1].timestamp).getTime();
  const timeRange = endTime - startTime || 1;
  
  const now = Date.now();
  const x = ((now - startTime) / timeRange) * width;
  const normalizedHeight = (currentHeight - minHeight) / heightRange;
  const y = height - (normalizedHeight * (height - 20) + 10);
  
  return { x, y };
}

export function TidesSunTile({ locationId, stationId }: TidesSunTileProps) {
  const { tides, sun, isLoading, error } = useTides(locationId, stationId);
  
  const width = 300;
  const height = 80;
  
  if (isLoading) {
    return (
      <div className="tile tides-sun" data-testid="tides-tile">
        <div className="tile__header">
          <div className="tile__title">
            <span className="tile__title-icon">🌙</span>
            Tides & Sun
          </div>
        </div>
        <div className="tile__content" data-testid="tile-loading">
          <div className="loading-state">Loading tide data...</div>
        </div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="tile tides-sun tile--error" data-testid="tides-tile">
        <div className="tile__header">
          <div className="tile__title">
            <span className="tile__title-icon">🌙</span>
            Tides & Sun
          </div>
        </div>
        <div className="tile__content" data-testid="tile-error">
          <div className="error-state">Tide data unavailable</div>
        </div>
      </div>
    );
  }
  
  const curvePath = tides?.events ? generateTideCurvePath(tides.events, width, height) : '';
  const currentPos = tides?.events && tides.current_height_ft 
    ? getCurrentPosition(tides.events, width, height, tides.current_height_ft)
    : null;
  
  return (
    <div className="tile tides-sun" data-testid="tides-tile">
      <div className="tile__header">
        <div className="tile__title">
          <span className="tile__title-icon">🌙</span>
          Tides & Sun
        </div>
        <div className="tile__location">{tides?.location_name || 'Unknown'}</div>
      </div>
      
      <div className="tile__content">
        <div className="tides-sun__chart">
          <div className="tide-curve" data-testid="tides-curve">
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
                </>
              )}
            </svg>
          </div>
        </div>
        
        <div className="tides-sun__info">
          {tides?.next_low && (
            <div className="tide-info" data-testid="next-low">
              <span className="tide-info__label">Next Low</span>
              <span className="tide-info__value">{formatTime(tides.next_low.timestamp)}</span>
              <span className="tide-info__sub">{tides.next_low.height_ft.toFixed(1)} ft</span>
            </div>
          )}
          {tides?.next_high && (
            <div className="tide-info" data-testid="next-high">
              <span className="tide-info__label">Next High</span>
              <span className="tide-info__value">{formatTime(tides.next_high.timestamp)}</span>
              <span className="tide-info__sub">{tides.next_high.height_ft.toFixed(1)} ft</span>
            </div>
          )}
        </div>
        
        {sun && (
          <div className="sun-info">
            <div className="sun-info__item" data-testid="sunrise">
              <span className="sun-info__icon">🌅</span>
              <span className="sun-info__label">Sunrise</span>
              <span className="sun-info__time">{formatTime(sun.sunrise)}</span>
            </div>
            <div className="sun-info__item" data-testid="sunset">
              <span className="sun-info__icon">🌇</span>
              <span className="sun-info__label">Sunset</span>
              <span className="sun-info__time">{formatTime(sun.sunset)}</span>
            </div>
            <div className="sun-info__item" data-testid="golden-hour">
              <span className="sun-info__icon">✨</span>
              <span className="sun-info__label">Golden Hour</span>
              <span className="sun-info__time">
                {formatTime(sun.golden_hour_evening_start)} – {formatTime(sun.golden_hour_evening_end)}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
