import './ConditionsTile.css';
import type { Condition } from '../../types';

const conditions: Condition[] = [
  { type: 'Water Temp', value: '65', unit: '°F', trend: 'stable' },
  { type: 'Visibility', value: '12-15', unit: 'ft', trend: 'up' },
  { type: 'Swell', value: '2-3', unit: 'ft @ 12s', trend: 'down' },
  { type: 'Wind', value: '5', unit: 'mph W', trend: 'stable' },
  { type: 'Air Temp', value: '72', unit: '°F', trend: 'up' },
  { type: 'Tide', value: '+2.3', unit: 'ft', trend: 'down' },
];

const getTrendIcon = (trend: string) => {
  switch (trend) {
    case 'up': return '↗';
    case 'down': return '↘';
    default: return '→';
  }
};

// Generate random sparkline data
const generateSparkline = () => {
  return Array.from({ length: 12 }, () => Math.random() * 100);
};

export function ConditionsTile() {
  return (
    <div className="tile conditions">
      <div className="tile__header">
        <div className="tile__title">
          <span className="tile__title-icon">🌊</span>
          Conditions
        </div>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.625rem', color: 'var(--text-muted)' }}>
          Shaw's Cove
        </span>
      </div>
      
      <div className="tile__content">
        <div className="conditions-grid">
          {conditions.map((condition) => (
            <div key={condition.type} className="condition-item">
              <span className="condition-item__label">{condition.type}</span>
              <div className="condition-item__value">
                {condition.value}
                <span className="condition-item__unit">{condition.unit}</span>
                <span className="condition-item__trend">
                  {getTrendIcon(condition.trend || 'stable')}
                </span>
              </div>
              <div className="condition-item__sparkline">
                {generateSparkline().map((height, i) => (
                  <div
                    key={i}
                    className="sparkline-bar"
                    style={{ height: `${height}%` }}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
