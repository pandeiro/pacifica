import './SeasonalTimelineTile.css';
import type { SeasonalEvent } from '../../types';

const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const currentMonth = new Date().getMonth();

const seasonalEvents: SeasonalEvent[] = [
  { name: '🐋 Gray Whales S', emoji: '🐋', startMonth: 0, endMonth: 2, category: 'migration', isActive: currentMonth <= 2 },
  { name: '🐋 Gray Whales N', emoji: '🐋', startMonth: 2, endMonth: 4, category: 'migration', isActive: currentMonth >= 2 && currentMonth <= 4 },
  { name: '🐋 Blue Whales', emoji: '🐋', startMonth: 5, endMonth: 10, category: 'migration', isActive: currentMonth >= 5 && currentMonth <= 10 },
  { name: '🐟 Grunion', emoji: '🐟', startMonth: 3, endMonth: 8, category: 'spawning', isActive: currentMonth >= 3 && currentMonth <= 8 },
  { name: '🫞 Lobster Season', emoji: '🫞', startMonth: 9, endMonth: 11, category: 'season', isActive: currentMonth >= 9 || currentMonth <= 2 },
  { name: '✨ Bioluminescence', emoji: '✨', startMonth: 3, endMonth: 5, category: 'bloom', isActive: currentMonth >= 3 && currentMonth <= 5 },
];

export function SeasonalTimelineTile() {
  const getEventStyle = (event: SeasonalEvent) => {
    const left = (event.startMonth / 12) * 100;
    const width = ((event.endMonth - event.startMonth + 1) / 12) * 100;
    return {
      left: `${left}%`,
      width: `${width}%`,
    };
  };

  const currentMarkerPosition = ((currentMonth + 0.5) / 12) * 100;

  return (
    <div className="tile seasonal-timeline">
      <div className="tile__header">
        <div className="tile__title">
          <span className="tile__title-icon">📅</span>
          Seasonal Timeline
        </div>
      </div>
      
      <div className="tile__content">
        <div className="timeline-container">
          <div className="timeline-track">
            <div className="timeline-months">
              {months.map((month, i) => (
                <div 
                  key={month} 
                  className={`timeline-month ${i === currentMonth ? 'timeline-month--current' : ''}`}
                >
                  {month}
                </div>
              ))}
            </div>
            
            <div className="timeline-events">
              {seasonalEvents.map((event, index) => (
                <div
                  key={event.name}
                  className={`timeline-event timeline-event--${event.category}`}
                  style={{
                    ...getEventStyle(event),
                    top: `${6 + (index % 2) * 10}px`,
                  }}
                  title={event.name}
                >
                  {event.name}
                </div>
              ))}
            </div>
            
            <div 
              className="timeline-current-marker"
              style={{ left: `${currentMarkerPosition}%` }}
            />
          </div>
          
          <div className="timeline-legend">
            <div className="timeline-legend__item">
              <div className="timeline-legend__dot timeline-legend__dot--migration" />
              <span>Migration</span>
            </div>
            <div className="timeline-legend__item">
              <div className="timeline-legend__dot timeline-legend__dot--spawning" />
              <span>Spawning</span>
            </div>
            <div className="timeline-legend__item">
              <div className="timeline-legend__dot timeline-legend__dot--bloom" />
              <span>Bloom</span>
            </div>
            <div className="timeline-legend__item">
              <div className="timeline-legend__dot timeline-legend__dot--season" />
              <span>Season</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
