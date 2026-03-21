import { useState, useEffect } from 'react';
import './LiveCamTile.css';
import { useLiveCams } from '../../hooks/useLiveCams';
import type { LiveCam } from '../../types';

interface LiveCamTileProps {
  onLocationChange?: (locationId: number) => void;
}

function getEmbedSrc(cam: LiveCam): string {
  if (cam.embed_type === 'youtube') {
    return `https://www.youtube.com/embed/${cam.embed_url}?autoplay=1&mute=1&controls=1&rel=0&modestbranding=1`;
  }
  return cam.embed_url;
}

export function LiveCamTile({ onLocationChange }: LiveCamTileProps) {
  const { cams, isLoading, error } = useLiveCams();
  const [activeCamId, setActiveCamId] = useState<number | null>(null);

  // Use first cam (sort_order 0) as default once loaded
  const activeCam = activeCamId !== null
    ? cams.find(c => c.id === activeCamId) ?? cams[0]
    : cams[0];

  // Sync location selector when active cam changes
  useEffect(() => {
    if (activeCam?.location_id && onLocationChange) {
      onLocationChange(activeCam.location_id);
    }
  }, [activeCam?.location_id, onLocationChange]);

  return (
    <div className="tile live-cam">
      <div className="tile__header">
        <div className="tile__title">
          <span className="tile__title-icon">📹</span>
          Live Cam
        </div>
        {activeCam && (
          <span className="live-cam__source">{activeCam.source_name}</span>
        )}
      </div>

      <div className="live-cam__viewport">
        {isLoading && (
          <div className="live-cam__placeholder">
            <div className="live-cam__spinner" />
            <span className="live-cam__label">Loading feed…</span>
          </div>
        )}

        {error && !isLoading && (
          <div className="live-cam__placeholder">
            <div className="live-cam__icon">⚠️</div>
            <span className="live-cam__label">Feed unavailable</span>
          </div>
        )}

        {!isLoading && !error && activeCam && (
          <iframe
            key={activeCam.id}
            className="live-cam__iframe"
            src={getEmbedSrc(activeCam)}
            title={activeCam.name}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        )}

        {!isLoading && !error && activeCam && (
          <div className="live-cam__overlay">
            <span className="live-cam__live-badge">
              <span className="live-cam__live-dot" />
              LIVE
            </span>
            <span className="live-cam__cam-name">{activeCam.name}</span>
            {activeCam.location_name && (
              <span className="live-cam__location-badge">{activeCam.location_name}</span>
            )}
          </div>
        )}
      </div>

      {cams.length > 0 && (
        <div className="live-cam__selector">
          {cams.map((cam) => (
            <button
              key={cam.id}
              className={`live-cam__option ${cam.id === (activeCam?.id ?? cams[0]?.id) ? 'live-cam__option--active' : ''}`}
              onClick={() => setActiveCamId(cam.id)}
            >
              {cam.name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
