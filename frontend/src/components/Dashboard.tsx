import { useState } from 'react';
import './Dashboard.css';
import { MapTile } from './tiles/MapTile';
import { LiveCamTile } from './tiles/LiveCamTile';
import { WaterTempsTile } from './tiles/WaterTempsTile';
import { VisibilityTile } from './tiles/VisibilityTile';
import { WildlifeTile } from './tiles/WildlifeTile';
import { SunTile } from './tiles/SunTile';
import { TidesTile } from './tiles/TidesTile';
import { SeasonalTimelineTile } from './tiles/SeasonalTimelineTile';
import { useLocations } from '../hooks/useLocations';
import { useWildlife } from '../hooks/useWildlife';

// Default to Santa Monica (closest to us)
const DEFAULT_LOCATION_ID = 3;

export function Dashboard() {
  const [locationId, setLocationId] = useState(DEFAULT_LOCATION_ID);
  const { locations, isLoading: locationsLoading } = useLocations();
  const { sightings } = useWildlife();

  return (
    <div className="dashboard">
      <div className="dashboard__main">
        <div className="dashboard__left">
          <MapTile
            locationId={locationId}
            onLocationChange={setLocationId}
            sightings={sightings?.sightings ?? []}
          />
        </div>
        
        <div className="dashboard__center">
          <LiveCamTile onLocationChange={setLocationId} />
          <WildlifeTile />
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
            </div>
           <SunTile locationId={locationId} />
           <WaterTempsTile locationId={locationId} />
           <VisibilityTile locationId={locationId} />
           <TidesTile locationId={locationId} />
         </div>
      </div>
      
      <div className="dashboard__timeline">
        <SeasonalTimelineTile />
      </div>
    </div>
  );
}
