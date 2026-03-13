import './TidesSunTile.css';

export function TidesSunTile() {
  // Generate tide curve path
  const width = 300;
  const height = 80;
  const points = [];
  for (let i = 0; i <= width; i += 5) {
    const y = height / 2 + Math.sin(i * 0.02) * 25 + Math.sin(i * 0.05) * 10;
    points.push(`${i},${y}`);
  }
  const pathD = `M 0,${height} L ${points.join(' L ')} L ${width},${height} Z`;
  const lineD = `M ${points.join(' L ')}`;
  
  // Current position (roughly middle)
  const currentX = width * 0.4;
  const currentY = height / 2 + Math.sin(currentX * 0.02) * 25 + Math.sin(currentX * 0.05) * 10;

  return (
    <div className="tile tides-sun">
      <div className="tile__header">
        <div className="tile__title">
          <span className="tile__title-icon">🌙</span>
          Tides & Sun
        </div>
      </div>
      
      <div className="tile__content">
        <div className="tides-sun__chart">
          <div className="tide-curve">
            <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
              <path className="tide-curve__fill" d={pathD} />
              <path className="tide-curve__path" d={lineD} />
              <circle 
                className="tide-curve__current" 
                cx={currentX} 
                cy={currentY} 
                r="4" 
              />
            </svg>
          </div>
        </div>
        
        <div className="tides-sun__info">
          <div className="tide-info">
            <span className="tide-info__label">Next Low</span>
            <span className="tide-info__value">5:23am</span>
            <span className="tide-info__sub">-0.2 ft</span>
          </div>
          <div className="tide-info">
            <span className="tide-info__label">Next High</span>
            <span className="tide-info__value">11:47am</span>
            <span className="tide-info__sub">+4.8 ft</span>
          </div>
        </div>
        
        <div className="sun-info">
          <div className="sun-info__item">
            <span className="sun-info__icon">🌅</span>
            <span className="sun-info__label">Sunrise</span>
            <span className="sun-info__time">6:42am</span>
          </div>
          <div className="sun-info__item">
            <span className="sun-info__icon">🌇</span>
            <span className="sun-info__label">Sunset</span>
            <span className="sun-info__time">5:58pm</span>
          </div>
          <div className="sun-info__item">
            <span className="sun-info__icon">✨</span>
            <span className="sun-info__label">Golden Hour</span>
            <span className="sun-info__time">5:12pm</span>
          </div>
        </div>
      </div>
    </div>
  );
}
