import './SeasonalTimelineTile.css';
import { useSeasonalEvents } from '../../hooks/useSeasonalEvents';
import type { SeasonalEvent } from '../../types';

const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const currentMonth = new Date().getMonth();

const categoryEmoji: Record<string, string> = {
  migration: '🐋',
  spawning: '🐟',
  bloom: '✨',
  season: '🦞',
  breeding: '🐣',
  tidal: '🌊',
};

function isActiveInMonth(event: SeasonalEvent, month: number): boolean {
  // Events spanning year boundary (e.g., lobster: Oct 10 → Mar 15)
  if (event.typical_start_month > event.typical_end_month) {
    return month >= (event.typical_start_month - 1) || month <= (event.typical_end_month - 1);
  }
  return month >= (event.typical_start_month - 1) && month <= (event.typical_end_month - 1);
}

export function SeasonalTimelineTile() {
  const { events, isLoading, error } = useSeasonalEvents();

  const getEventStyle = (event: SeasonalEvent) => {
    const startMonth = event.typical_start_month - 1; // 0-indexed
    const endMonth = event.typical_end_month - 1;
    const left = (startMonth / 12) * 100;

    // Handle year-wrap events (e.g., lobster: month 10 → 3)
    const width = startMonth <= endMonth
      ? ((endMonth - startMonth + 1) / 12) * 100
      : ((12 - startMonth + endMonth + 1) / 12) * 100;

    return { left: `${left}%`, width: `${width}%` };
  };

  const currentMarkerPosition = ((currentMonth + 0.5) / 12) * 100;

  // Legend categories present in the data
  const categories = [...new Set(events.map(e => e.category))].sort();

  return (
    <div className="tile seasonal-timeline">
      <div className="tile__header">
        <div className="tile__title">
          <span className="tile__title-icon">📅</span>
          Seasonal
        </div>
      </div>

      <div className="tile__content">
        {isLoading && (
          <div className="timeline-loading">Loading events…</div>
        )}

        {error && !isLoading && (
          <div className="timeline-loading">Events unavailable</div>
        )}

        {!isLoading && !error && (
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
                {events.map((event) => (
                  <div
                    key={event.id}
                    className={`timeline-event timeline-event--${event.category} ${isActiveInMonth(event, currentMonth) ? 'timeline-event--active' : ''}`}
                    style={getEventStyle(event)}
                    title={event.description ?? event.name}
                  >
                    {categoryEmoji[event.category] ?? '📋'} {event.name}
                  </div>
                ))}
              </div>

              <div
                className="timeline-current-marker"
                style={{ left: `${currentMarkerPosition}%` }}
              />
            </div>

            <div className="timeline-legend">
              {categories.map(cat => (
                <div key={cat} className="timeline-legend__item">
                  <div className={`timeline-legend__dot timeline-legend__dot--${cat}`} />
                  <span>{cat.charAt(0).toUpperCase() + cat.slice(1)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
