import { useState, useMemo, useEffect, useCallback, useRef } from 'react';
import { useSun } from '../../hooks/useSun';
import { useWaterTemp } from '../../hooks/useWaterTemp';
import { useVisibility } from '../../hooks/useVisibility';
import { useTides } from '../../hooks/useTides';
import './ConditionsSlideshowTile.css';

interface ConditionsSlideshowTileProps {
  locationId: number;
}

function formatTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleTimeString('en-US', { 
    hour: 'numeric', 
    minute: '2-digit',
    hour12: true,
    timeZone: 'America/Los_Angeles'
  }).toLowerCase();
}

function interpolateTideHeight(
  time: number,
  event1: { timestamp: string; height: number; type: string },
  event2: { timestamp: string; height: number; type: string }
): number {
  const t1 = new Date(event1.timestamp).getTime();
  const t2 = new Date(event2.timestamp).getTime();
  if (time <= t1) return event1.height;
  if (time >= t2) return event2.height;
  const t = (time - t1) / (t2 - t1);
  return event1.height + (event2.height - event1.height) * (1 - Math.cos(Math.PI * t)) / 2;
}

function SunPage({ locationId }: { locationId: number }) {
  const { sun, isLoading, error } = useSun(locationId);

  if (isLoading) return <div className="conditions__loading">Loading...</div>;
  if (error || !sun) return <div className="conditions__error">Sun data unavailable</div>;

  return (
    <div className="conditions__sun">
      <div className="conditions__sun-row">
        <div className="conditions__sun-block">
          <span className="conditions__sun-time conditions__sun-time--rise">
            {formatTime(sun.sunrise).replace(/\s*[ap]m/i, '')}
          </span>
          <span className="conditions__sun-label">Sunrise</span>
        </div>
        <div className="conditions__sun-arrow">&rarr;</div>
        <div className="conditions__sun-block">
          <span className="conditions__sun-time conditions__sun-time--set">
            {formatTime(sun.sunset).replace(/\s*[ap]m/i, '')}
          </span>
          <span className="conditions__sun-label">Sunset</span>
        </div>
      </div>
    </div>
  );
}

function WaterTempPage({ locationId }: { locationId: number }) {
  const { data, isLoading, error } = useWaterTemp(locationId);

  if (isLoading) return <div className="conditions__loading">Loading...</div>;
  if (error || !data) return <div className="conditions__error">Water temp unavailable</div>;

  const sparklineData = data.history.slice(0, 48).reverse();
  const maxTemp = Math.max(...sparklineData.map(d => d.temperature_f));
  const minTemp = Math.min(...sparklineData.map(d => d.temperature_f));
  const tempRange = maxTemp - minTemp || 1;

  return (
    <div className="conditions__water-temp">
      <div className="conditions__temp-display">
        {data.current_temp_f ? (
          <>
            <span className="conditions__temp-value">{Math.round(data.current_temp_f)}</span>
            <span className="conditions__temp-unit">&deg;F</span>
          </>
        ) : (
          <span className="conditions__temp-na">--</span>
        )}
      </div>

      {sparklineData.length > 0 && (
        <div className="conditions__sparkline">
          {sparklineData.map((reading, i) => {
            const h = ((reading.temperature_f - minTemp) / tempRange) * 100;
            const isCurrent = i === sparklineData.length - 1;
            return (
              <div
                key={i}
                className={`conditions__sparkline-bar${isCurrent ? ' conditions__sparkline-bar--current' : ''}`}
                style={{ height: `${Math.max(h, 10)}%` }}
                title={`${reading.temperature_f.toFixed(1)}°F`}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

function TidesPage({ locationId }: { locationId: number }) {
  const { tides, isLoading, error } = useTides(locationId);
  const [hoverPos, setHoverPos] = useState<{ x: number; time: number; height: number } | null>(null);
  const curveRef = useRef<HTMLDivElement>(null);
  const [curveDims, setCurveDims] = useState({ w: 300, h: 70 });

  // Measure the actual rendered dimensions of the curve container
  useEffect(() => {
    const el = curveRef.current;
    if (!el) return;
    const obs = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect;
      if (width > 0 && height > 0) {
        setCurveDims({ w: Math.round(width), h: Math.round(height) });
      }
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  const { w: width, h: height } = curveDims;
  const padY = Math.round(height * 0.1);

  const graphData = useMemo(() => {
    if (!tides?.events) return [];
    return tides.events
      .map(e => ({ timestamp: e.timestamp, height: e.height_ft, type: e.type }))
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
  }, [tides]);

  const { nextHigh, nextLow } = useMemo(() => {
    if (!tides?.events) return { nextHigh: null, nextLow: null };
    const now = new Date().getTime();
    const future = tides.events
      .filter(e => new Date(e.timestamp).getTime() > now)
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
    return {
      nextHigh: future.find(e => e.type === 'high') || null,
      nextLow: future.find(e => e.type === 'low') || null,
    };
  }, [tides]);

  const { minHeight, startTime, timeRange, heightRange } = useMemo(() => {
    if (graphData.length === 0) {
      return { minHeight: 0, startTime: 0, endTime: 1, timeRange: 1, heightRange: 1 };
    }
    const heights = graphData.map(e => e.height);
    const minH = Math.min(...heights);
    const maxH = Math.max(...heights);
    const start = new Date(graphData[0].timestamp).getTime();
    const end = new Date(graphData[graphData.length - 1].timestamp).getTime();
    return {
      minHeight: minH,
      startTime: start,
      endTime: end,
      timeRange: end - start || 1,
      heightRange: maxH - minH || 1
    };
  }, [graphData]);

  const curvePath = useMemo(() => {
    if (graphData.length < 2 || width < 10 || height < 10) return '';
    const numPoints = 200;
    let path = '';
    const drawHeight = height - padY * 2;
    for (let i = 0; i <= numPoints; i++) {
      const t = i / numPoints;
      const time = startTime + t * timeRange;
      let interpolatedHeight: number | undefined;
      for (let j = 0; j < graphData.length - 1; j++) {
        const t1 = new Date(graphData[j].timestamp).getTime();
        const t2 = new Date(graphData[j + 1].timestamp).getTime();
        if (time >= t1 && time <= t2) {
          interpolatedHeight = interpolateTideHeight(time, graphData[j], graphData[j + 1]);
          break;
        }
      }
      interpolatedHeight ??= graphData[0].height;
      const x = t * width;
      const normalizedHeight = (interpolatedHeight - minHeight) / heightRange;
      const y = height - padY - (normalizedHeight * drawHeight);
      if (i === 0) path = `M ${x.toFixed(1)},${y.toFixed(1)}`;
      else path += ` L ${x.toFixed(1)},${y.toFixed(1)}`;
    }
    return path;
  }, [graphData, startTime, timeRange, minHeight, heightRange, width, height, padY]);

  const currentPos = useMemo(() => {
    if (!tides?.current_height_ft || graphData.length === 0) return null;
    const now = Date.now();
    if (now < startTime || now > timeRange + startTime) return null;
    const drawHeight = height - padY * 2;
    const x = ((now - startTime) / timeRange) * width;
    const normalizedHeight = (tides.current_height_ft - minHeight) / heightRange;
    const y = height - padY - (normalizedHeight * drawHeight);
    return { x, y };
  }, [tides, graphData, startTime, timeRange, minHeight, heightRange, width, height, padY]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (graphData.length < 2) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const pixelX = e.clientX - rect.left;
    const t = pixelX / rect.width;
    const time = startTime + t * timeRange;

    let interpolatedHeight = graphData[0].height;
    for (let j = 0; j < graphData.length - 1; j++) {
      const t1 = new Date(graphData[j].timestamp).getTime();
      const t2 = new Date(graphData[j + 1].timestamp).getTime();
      if (time >= t1 && time <= t2) {
        interpolatedHeight = interpolateTideHeight(time, graphData[j], graphData[j + 1]);
        break;
      }
    }
    const drawHeight = height - padY * 2;
    const x = t * width;
    setHoverPos({ x, time, height: interpolatedHeight });
  }, [graphData, startTime, timeRange, width, height, padY]);

  const handleMouseLeave = useCallback(() => {
    setHoverPos(null);
  }, []);

  if (isLoading) return <div className="conditions__loading">Loading...</div>;
  if (error) return <div className="conditions__error">Tide data unavailable</div>;

  return (
    <div className="conditions__tides">
      <div className="conditions__tides-row">
        <div className="conditions__tides-info">
          {tides?.next_tide && (
            <div className="conditions__tides-time" data-testid="conditions-next-tide">
              {formatTime(tides.next_tide.timestamp)}
            </div>
          )}
          {nextHigh && (
            <div className="conditions__tides-event conditions__tides-event--high">
              <span className="conditions__tides-event-label">High</span>
              <span className="conditions__tides-event-value">+{nextHigh.height_ft.toFixed(1)} ft</span>
            </div>
          )}
          {nextLow && (
            <div className="conditions__tides-event conditions__tides-event--low">
              <span className="conditions__tides-event-label">Low</span>
              <span className="conditions__tides-event-value">{nextLow.height_ft.toFixed(1)} ft</span>
            </div>
          )}
        </div>

        {graphData.length > 0 && curvePath && (
          <div className="conditions__tides-curve">
            <div
              className="conditions__tides-curve-wrap"
              ref={curveRef}
              onMouseMove={handleMouseMove}
              onMouseLeave={handleMouseLeave}
            >
              <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
                <path className="conditions__tides-curve-path" d={curvePath} fill="none" />
                {currentPos && (
                  <line
                    className="conditions__tides-curve-now"
                    x1={currentPos.x} y1="0"
                    x2={currentPos.x} y2={height}
                  />
                )}
                {hoverPos && (
                  <>
                    <line
                      className="conditions__tides-hover-line"
                      x1={hoverPos.x} y1="0"
                      x2={hoverPos.x} y2={height}
                    />
                    <circle
                      className="conditions__tides-hover-point"
                      cx={hoverPos.x}
                      cy={height - padY - ((hoverPos.height - minHeight) / heightRange * (height - padY * 2))}
                      r="3"
                    />
                  </>
                )}
              </svg>
            </div>
            {hoverPos ? (
              <div className="conditions__tides-hover-info">
                {formatTime(new Date(hoverPos.time).toISOString())} &mdash; {hoverPos.height.toFixed(1)}ft
              </div>
            ) : (
              <div className="conditions__tides-hover-info">&nbsp;</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function VisibilityPage({ locationId }: { locationId: number }) {
  const { data, isLoading, error } = useVisibility(locationId);

  if (isLoading) return <div className="conditions__loading">Loading...</div>;
  if (error || !data) return <div className="conditions__error">Visibility unavailable</div>;

  const formatRange = (min: number | null, max: number | null): string => {
    if (min === null || max === null) return '--';
    if (min === max) return `${min}`;
    return `${min}-${max}`;
  };

  const hasViz = data.visibility_min !== null && data.visibility_max !== null;
  const hasSwell = data.swell_min !== null && data.swell_max !== null;

  return (
    <div className="conditions__visibility">
      <div className="conditions__viz-row">
        <div className="conditions__viz-section">
          <div className="conditions__viz-label">Viz</div>
          <div className="conditions__viz-value">
            {hasViz ? formatRange(data.visibility_min, data.visibility_max) : '--'}
            {hasViz && <span className="conditions__viz-unit">ft</span>}
          </div>
        </div>
        <div className="conditions__viz-divider" />
        <div className="conditions__viz-section">
          <div className="conditions__viz-label">Swell</div>
          <div className="conditions__viz-value">
            {hasSwell ? formatRange(data.swell_min, data.swell_max) : '--'}
            {hasSwell && <span className="conditions__viz-unit">ft</span>}
          </div>
        </div>
      </div>
    </div>
  );
}

const SLIDE_INTERVAL = 5000;

export function ConditionsSlideshowTile({ locationId }: ConditionsSlideshowTileProps) {
  const [activePage, setActivePage] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const pages = ['Sun', 'Water', 'Tides', 'Viz'];

  const advance = useCallback(() => {
    setActivePage(p => (p + 1) % pages.length);
  }, [pages.length]);

  useEffect(() => {
    if (isPaused) return;
    intervalRef.current = setInterval(advance, SLIDE_INTERVAL);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [advance, isPaused]);

  return (
    <div
      className="tile conditions-tile"
      data-testid="conditions-tile"
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      <div className="tile__header">
        <div className="tile__title">Conditions</div>
        <div className="conditions__nav">
          {pages.map((label, i) => (
            <button
              key={label}
              className={`conditions__dot${i === activePage ? ' conditions__dot--active' : ''}`}
              onClick={() => setActivePage(i)}
              title={label}
            />
          ))}
        </div>
      </div>

      <div className="tile__content conditions__content">
        <div className={`conditions__slide${activePage === 0 ? ' conditions__slide--active' : ''}`}>
          <SunPage locationId={locationId} />
        </div>
        <div className={`conditions__slide${activePage === 1 ? ' conditions__slide--active' : ''}`}>
          <WaterTempPage locationId={locationId} />
        </div>
        <div className={`conditions__slide${activePage === 2 ? ' conditions__slide--active' : ''}`}>
          <TidesPage locationId={locationId} />
        </div>
        <div className={`conditions__slide${activePage === 3 ? ' conditions__slide--active' : ''}`}>
          <VisibilityPage locationId={locationId} />
        </div>
      </div>
    </div>
  );
}
