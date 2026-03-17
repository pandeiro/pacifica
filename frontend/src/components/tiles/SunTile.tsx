import { useSun } from '../../hooks/useSun';
import './SunTile.css';

interface SunTileProps {
  locationId: number;
}

function formatTime(isoString: string): string {
  const date = new Date(isoString);
  const time = date.toLocaleTimeString('en-US', { 
    hour: 'numeric', 
    minute: '2-digit',
    hour12: true,
    timeZone: 'America/Los_Angeles'
  });
  return time.replace(/\s*[ap]m/i, '');
}

export function SunTile({ locationId }: SunTileProps) {
  const { sun, isLoading, error } = useSun(locationId);
  
  if (isLoading) {
    return (
      <div className="tile sun-tile" data-testid="sun-tile">
        <div className="tile__header">
          <div className="tile__title">Sun</div>
        </div>
        <div className="tile__content" data-testid="tile-loading">
          <div className="loading-state">Loading...</div>
        </div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="tile sun-tile tile--error" data-testid="sun-tile">
        <div className="tile__header">
          <div className="tile__title">Sun</div>
        </div>
        <div className="tile__content" data-testid="tile-error">
          <div className="error-state">Sun data unavailable</div>
        </div>
      </div>
    );
  }
  
  return (
    <div className="tile sun-tile" data-testid="sun-tile">
      <div className="tile__header">
        <div className="tile__title">Sun</div>
      </div>
      
      <div className="tile__content">
        {sun ? (
          <div className="sun-tile__display">
            <div className="sun-tile__time-block sun-tile__sunrise">
              <span className="sun-tile__time" data-testid="sunrise">
                {formatTime(sun.sunrise)}
              </span>
              <span className="sun-tile__label">Sunrise</span>
            </div>
            
            <div className="sun-tile__arrow">→</div>
            
            <div className="sun-tile__time-block sun-tile__sunset">
              <span className="sun-tile__time" data-testid="sunset">
                {formatTime(sun.sunset)}
              </span>
              <span className="sun-tile__label">Sunset</span>
            </div>
          </div>
        ) : (
          <div className="sun-tile__no-data">No sun data available</div>
        )}
      </div>
    </div>
  );
}
