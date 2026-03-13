import './Dashboard.css';
import { MapTile } from './tiles/MapTile';
import { ActivityScoresTile } from './tiles/ActivityScoresTile';
import { LiveCamTile } from './tiles/LiveCamTile';
import { ConditionsTile } from './tiles/ConditionsTile';
import { WildlifeIntelTile } from './tiles/WildlifeIntelTile';
import { TidesSunTile } from './tiles/TidesSunTile';
import { DriveTimesTile } from './tiles/DriveTimesTile';
import { SeasonalTimelineTile } from './tiles/SeasonalTimelineTile';

export function Dashboard() {
  return (
    <div className="dashboard">
      <div className="dashboard__main">
        <div className="dashboard__map">
          <MapTile />
        </div>
        
        <div className="dashboard__center">
          <ActivityScoresTile />
          <ConditionsTile />
          <DriveTimesTile />
        </div>
        
        <div className="dashboard__right">
          <LiveCamTile />
          <WildlifeIntelTile />
          <TidesSunTile />
        </div>
      </div>
      
      <div className="dashboard__timeline">
        <SeasonalTimelineTile />
      </div>
    </div>
  );
}
