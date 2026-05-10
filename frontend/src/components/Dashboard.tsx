import { useState, useEffect } from 'react';
import './Dashboard.css';
import { MapTile } from './tiles/MapTile';
import { LiveCamTile } from './tiles/LiveCamTile';
import { WildlifeTile } from './tiles/WildlifeTile';
import { ConditionsSlideshowTile } from './tiles/ConditionsSlideshowTile';
import { SeasonalTimelineTile } from './tiles/SeasonalTimelineTile';
import { useWildlife } from '../hooks/useWildlife';

const DEFAULT_LOCATION_ID = 3;

export function Dashboard() {
  const [locationId, setLocationId] = useState(DEFAULT_LOCATION_ID);
  const { sightings } = useWildlife();
  const [bgLoaded, setBgLoaded] = useState(false);

  useEffect(() => {
    const img = new Image();
    img.onload = () => setBgLoaded(true);
    img.src = '/coastal-bg.jpg';
    if (img.complete) setBgLoaded(true);
  }, []);

  return (
    <div className={`dashboard${bgLoaded ? ' dashboard--loaded' : ''}`}>
      <MapTile
        locationId={locationId}
        onLocationChange={setLocationId}
        sightings={sightings?.sightings ?? []}
      />

      <LiveCamTile onLocationChange={setLocationId} />

      <WildlifeTile />

      <ConditionsSlideshowTile locationId={locationId} />

      <div className="dashboard__timeline">
        <SeasonalTimelineTile />
      </div>
    </div>
  );
}
