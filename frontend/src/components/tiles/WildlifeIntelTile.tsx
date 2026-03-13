import './WildlifeIntelTile.css';
import type { Sighting } from '../../types';

const sightings: Sighting[] = [
  { id: '1', species: 'Gray Whale', emoji: '🐋', location: 'Pt Vicente', time: '2h ago', source: 'Harbor Breeze', count: 3, isHot: true },
  { id: '2', species: 'Dolphins', emoji: '🐬', location: 'Dana Point', time: '3h ago', source: 'Dana Wharf', count: 25 },
  { id: '3', species: 'Sea Lion', emoji: '🦭', location: 'Laguna Beach', time: '4h ago', source: 'iNaturalist' },
  { id: '4', species: 'Garibaldi', emoji: '🐠', location: 'Shaw\'s Cove', time: '5h ago', source: 'South Coast Divers', isHot: true },
  { id: '5', species: 'Brown Pelican', emoji: '🦅', location: 'Crystal Cove', time: '6h ago', source: 'iNaturalist' },
];

export function WildlifeIntelTile() {
  return (
    <div className="tile wildlife-intel">
      <div className="tile__header">
        <div className="tile__title">
          <span className="tile__title-icon">🔍</span>
          Wildlife Intel
        </div>
      </div>
      
      <div className="tile__content">
        <div className="sightings-list">
          {sightings.map((sighting) => (
            <div 
              key={sighting.id} 
              className={`sighting-item ${sighting.isHot ? 'sighting-item--hot' : ''}`}
            >
              <span className="sighting-item__emoji">{sighting.emoji}</span>
              <div className="sighting-item__info">
                <div className="sighting-item__species">
                  {sighting.species}
                  {sighting.isHot && (
                    <span className="sighting-item__hot-badge">HOT</span>
                  )}
                </div>
                <div className="sighting-item__meta">
                  <span>{sighting.location}</span>
                  <span className="sighting-item__dot" />
                  <span className="sighting-item__time">{sighting.time}</span>
                  <span className="sighting-item__dot" />
                  <span>{sighting.source}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
