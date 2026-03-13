import './DriveTimesTile.css';
import type { DriveTime } from '../../types';

const driveTimes: DriveTime[] = [
  { location: 'Point Vicente', minutes: 22, distance: '18 mi' },
  { location: 'Leo Carrillo', minutes: 35, distance: '28 mi' },
  { location: 'Laguna Beach', minutes: 48, distance: '42 mi' },
  { location: 'Dana Point', minutes: 52, distance: '46 mi' },
];

export function DriveTimesTile() {
  return (
    <div className="tile drive-times">
      <div className="tile__header">
        <div className="tile__title">
          <span className="tile__title-icon">🚗</span>
          Drive Times
        </div>
      </div>
      
      <div className="tile__content">
        <div className="drive-list">
          {driveTimes.map((drive) => (
            <div key={drive.location} className="drive-item">
              <div className="drive-item__info">
                <span className="drive-item__icon">📍</span>
                <span className="drive-item__name">{drive.location}</span>
              </div>
              <div className="drive-item__time">
                <span className="drive-item__minutes">{drive.minutes}</span>
                <span className="drive-item__unit">min</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
