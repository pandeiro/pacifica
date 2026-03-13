import './MapTile.css';

const locations = [
  { name: 'Dana Point', top: '15%', left: '75%' },
  { name: 'Laguna', top: '35%', left: '65%' },
  { name: 'Crystal Cove', top: '45%', left: '55%' },
  { name: 'Newport', top: '55%', left: '45%' },
  { name: 'Huntington', top: '65%', left: '35%' },
  { name: 'PV', top: '75%', left: '25%' },
  { name: 'Santa Monica', top: '85%', left: '15%' },
];

export function MapTile() {
  return (
    <div className="tile map-tile">
      <div className="tile__header">
        <div className="tile__title">
          <span className="tile__title-icon">🗺️</span>
          Coastal Map
        </div>
        <div className="status-dot status-dot--live" />
      </div>
      
      <div className="map-tile__container">
        <div className="map-tile__placeholder">
          <div className="map-tile__grid" />
          <div className="map-tile__coastline" />
          
          <div className="map-tile__locations">
            {locations.map((loc) => (
              <div
                key={loc.name}
                className="map-location"
                style={{ top: loc.top, left: loc.left }}
              >
                <div className="map-location__dot" />
                <span className="map-location__label">{loc.name}</span>
              </div>
            ))}
          </div>
          
          <span className="map-tile__label">Interactive Map Placeholder</span>
        </div>
      </div>
    </div>
  );
}
