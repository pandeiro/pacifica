import { useState } from 'react';
import './Dashboard.css';
import { MapTile } from './tiles/MapTile';
import { ActivityScoresTile } from './tiles/ActivityScoresTile';
import { LiveCamTile } from './tiles/LiveCamTile';
import { WaterTempsTile } from './tiles/WaterTempsTile';
import { WildlifeIntelTile } from './tiles/WildlifeIntelTile';
import { SunTile } from './tiles/SunTile';
import { TidesTile } from './tiles/TidesTile';
import { DriveTimesTile } from './tiles/DriveTimesTile';
import { SeasonalTimelineTile } from './tiles/SeasonalTimelineTile';
import { useLocations } from '../hooks/useLocations';

// Default to Santa Monica (closest to us)
const DEFAULT_LOCATION_ID = 3;

export function Dashboard() {
  const [locationId, setLocationId] = useState(DEFAULT_LOCATION_ID);
  const { locations, isLoading: locationsLoading } = useLocations();
  
  // Get current location for station info display
  const currentLocation = locations.find(loc => loc.id === locationId);
  
  return (
    <div className="dashboard">
      <div className="dashboard__main">
        <div className="dashboard__map">
          <MapTile />
        </div>
        
        <div className="dashboard__center">
          <ActivityScoresTile />
          <WildlifeIntelTile />
          <LiveCamTile />
          <DriveTimesTile />
        </div>
        
        <div className="dashboard__right">
          <div className="dashboard__location-selector">
            <select 
              className="location-selector__dropdown"
              value={locationId}
              onChange={(e) => setLocationId(Number(e.target.value))}
              disabled={locationsLoading}
            >
              {locations.map(loc => (
                <option key={loc.id} value={loc.id}>{loc.name}</option>
              ))}
            </select>
            {currentLocation?.station_info && (
              <div className="location-selector__station-info">
                Tides: {currentLocation.station_info.name}
                {currentLocation.station_info.distance_miles > 0 && (
                  <span className="station-info__distance">
                    {' '}({currentLocation.station_info.distance_miles} mi {currentLocation.station_info.direction})
                  </span>
                )}
              </div>
            )}
          </div>
          <SunTile locationId={locationId} />
          <WaterTempsTile locationId={locationId} />
          <TidesTile locationId={locationId} />
        </div>
      </div>
      
      <div className="dashboard__timeline">
        <SeasonalTimelineTile />
      </div>
    </div>
  );
}
