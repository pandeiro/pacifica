import { useState } from 'react';
import './LiveCamTile.css';
import type { LiveCam } from '../../types';

const cams: LiveCam[] = [
  { id: '1', name: 'Anacapa Underwater', location: 'Channel Islands', embedUrl: '', isLive: true },
  { id: '2', name: 'Laguna Beach', location: 'Laguna', embedUrl: '', isLive: true },
  { id: '3', name: 'Santa Monica', location: 'Santa Monica', embedUrl: '', isLive: true },
  { id: '4', name: 'Morro Bay', location: 'Morro Bay', embedUrl: '', isLive: false },
];

export function LiveCamTile() {
  const [activeCam, setActiveCam] = useState(cams[0]);

  return (
    <div className="tile live-cam">
      <div className="tile__header">
        <div className="tile__title">
          <span className="tile__title-icon">📹</span>
          Live Cam
        </div>
      </div>
      
      <div className="live-cam__viewport">
        <div className="live-cam__placeholder">
          <div className="live-cam__icon">📷</div>
          <span className="live-cam__label">Camera Feed Placeholder</span>
        </div>
        
        <div className="live-cam__overlay">
          <span className="live-cam__live-badge">
            <span className="live-cam__live-dot" />
            LIVE
          </span>
          <span className="live-cam__cam-name">{activeCam.name}</span>
        </div>
      </div>
      
      <div className="live-cam__selector">
        {cams.map((cam) => (
          <button
            key={cam.id}
            className={`live-cam__option ${cam.id === activeCam.id ? 'live-cam__option--active' : ''}`}
            onClick={() => setActiveCam(cam)}
          >
            {cam.location}
          </button>
        ))}
      </div>
    </div>
  );
}
