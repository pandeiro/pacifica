import './ActivityScoresTile.css';
import type { ActivityScore } from '../../types';

const activities: ActivityScore[] = [
  { activity: 'Snorkeling', emoji: '🤿', score: 78, rating: 'Good', location: 'Shaw\'s Cove', details: 'Solid vis, calm conditions' },
  { activity: 'Whale Watching', emoji: '🐋', score: 92, rating: 'Great', location: 'Pt Vicente', details: 'Gray whales active' },
  { activity: 'Body Surfing', emoji: '🏄', score: 65, rating: 'Fair', location: 'The Wedge', details: 'Small swell, onshore later' },
  { activity: 'Tidepooling', emoji: '🦀', score: 85, rating: 'Great', location: 'Crystal Cove', details: 'Low tide at 3:45pm' },
  { activity: 'Scenic Drive', emoji: '🚗', score: 95, rating: 'Epic', location: 'PCH North', details: 'Clear skies, golden hour' },
];

const getScoreColor = (score: number): string => {
  if (score >= 90) return 'score-epic';
  if (score >= 80) return 'score-great';
  if (score >= 70) return 'score-good';
  if (score >= 60) return 'score-fair';
  return 'score-poor';
};

const getBarColor = (score: number): string => {
  if (score >= 90) return 'var(--score-epic)';
  if (score >= 80) return 'var(--score-great)';
  if (score >= 70) return 'var(--score-good)';
  if (score >= 60) return 'var(--score-fair)';
  return 'var(--score-poor)';
};

export function ActivityScoresTile() {
  return (
    <div className="tile activity-scores">
      <div className="tile__header">
        <div className="tile__title">
          <span className="tile__title-icon">📊</span>
          Activity Scores
        </div>
      </div>
      
      <div className="tile__content">
        <div className="activity-list">
          {activities.map((activity) => (
            <div key={activity.activity} className="activity-item">
              <span className="activity-item__emoji">{activity.emoji}</span>
              <div className="activity-item__info">
                <span className="activity-item__name">{activity.activity}</span>
                <span className="activity-item__location">{activity.location}</span>
              </div>
              <div className="activity-item__score">
                <span className={`activity-item__rating ${getScoreColor(activity.score)}`}>
                  {activity.rating}
                </span>
                <div className="activity-item__bar">
                  <div 
                    className="activity-item__bar-fill"
                    style={{ 
                      width: `${activity.score}%`,
                      backgroundColor: getBarColor(activity.score)
                    }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
