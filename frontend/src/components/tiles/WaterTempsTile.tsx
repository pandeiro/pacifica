import { useState } from 'react';
import { useWaterTemp } from '../../hooks/useWaterTemp';
import './WaterTempsTile.css';

interface WaterTempsTileProps {
  locationId: number;
}

export function WaterTempsTile({ locationId }: WaterTempsTileProps) {
  const { data, isLoading, error } = useWaterTemp(locationId);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  if (isLoading) {
    return (
      <div className="tile water-temps" data-testid="water-temps-tile">
        <div className="tile__header">
          <div className="tile__title">Water Temp</div>
        </div>
        <div className="tile__content" data-testid="tile-loading">
          <div className="loading-state">Loading...</div>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="tile water-temps tile--error" data-testid="water-temps-tile">
        <div className="tile__header">
          <div className="tile__title">Water Temp</div>
        </div>
        <div className="tile__content" data-testid="tile-error">
          <div className="error-state">Data unavailable</div>
        </div>
      </div>
    );
  }

  const { current_temp_f, current_temp_c, history } = data;

  // Generate sparkline data from history (show last 48 points max for visual clarity)
  const sparklineData = history.slice(0, 48).reverse();
  const maxTemp = Math.max(...sparklineData.map(d => d.temperature_f));
  const minTemp = Math.min(...sparklineData.map(d => d.temperature_f));
  const tempRange = maxTemp - minTemp || 1;

  // Format time for hover display
  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
      timeZone: 'America/Los_Angeles'
    }).toLowerCase();
  };

  return (
    <div className="tile water-temps" data-testid="water-temps-tile">
      <div className="tile__header">
        <div className="tile__title">Water Temp</div>
      </div>
      
      <div className="tile__content">
        <div className="water-temps__display">
          {current_temp_f ? (
            <>
              <div className="water-temps__current">
                <span className="water-temps__value">{Math.round(current_temp_f)}</span>
                <span className="water-temps__unit">°F</span>
              </div>
              {current_temp_c && (
                <div className="water-temps__secondary">
                  {Math.round(current_temp_c)}°C
                </div>
              )}
            </>
          ) : (
            <div className="water-temps__no-data">No data</div>
          )}
        </div>

        {sparklineData.length > 0 && (
          <div className="water-temps__sparkline-container">
            <div className="water-temps__sparkline">
              {sparklineData.map((reading, i) => {
                const height = ((reading.temperature_f - minTemp) / tempRange) * 100;
                return (
                  <div
                    key={i}
                    className="water-temps__sparkline-bar"
                    style={{ height: `${Math.max(height, 10)}%` }}
                    onMouseEnter={() => setHoveredIndex(i)}
                    onMouseLeave={() => setHoveredIndex(null)}
                  />
                );
              })}
            </div>
            {hoveredIndex !== null && (
              <div className="water-temps__sparkline-value">
                {sparklineData[hoveredIndex].temperature_f.toFixed(1)}°F at {formatTime(sparklineData[hoveredIndex].timestamp)}
              </div>
            )}
          </div>
        )}


      </div>
    </div>
  );
}
