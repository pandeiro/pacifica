import { useHealth } from '../hooks/useHealth';
import { useScraperHealth, type ScraperStatus } from '../hooks/useScraperHealth';
import './StatusPage.css';

const SCRAPER_LABELS: Record<string, string> = {
  noaa_tides: 'NOAA Tides',
  noaa_water_temp: 'NOAA Water Temp',
  south_coast_divers: 'South Coast Divers',
  acs_la: 'ACS-LA Gray Whale',
  inaturalist: 'iNaturalist',
  daveyslocker: "Davey's Locker",
  dana_wharf: 'Dana Wharf',
  harbor_breeze: 'Harbor Breeze',
  island_packers: 'Island Packers',
};

function formatDuration(ms: number | null): string {
  if (ms === null) return '--';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function formatRelativeTime(iso: string | null): string {
  if (!iso) return 'never';
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function StatusPill({ scraper }: { scraper: ScraperStatus }) {
  if (scraper.last_status === 'failure' && scraper.consecutive_failures >= 3) {
    return <span className="status-pill status-pill--error">failed</span>;
  }
  if (scraper.is_stale) {
    return <span className="status-pill status-pill--stale">stale</span>;
  }
  if (scraper.last_status === 'success') {
    return <span className="status-pill status-pill--ok">ok</span>;
  }
  return <span className="status-pill status-pill--unknown">unknown</span>;
}

function formatCount(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

export function StatusPage() {
  const { data: health, isLoading: healthLoading } = useHealth();
  const { data: scraperHealth, isLoading: scraperLoading } = useScraperHealth();

  const isLoading = healthLoading || scraperLoading;

  return (
    <div className="status-page">
      <header className="status-page__header">
        <div className="status-page__title-group">
          <h1 className="status-page__title">Status</h1>
          {scraperHealth && (
            <span className={`status-page__overall status-page__overall--${scraperHealth.status}`}>
              {scraperHealth.status}
            </span>
          )}
        </div>
        <a href="/" className="status-page__back">Dashboard</a>
      </header>

      <div className="status-page__summary">
        <div className="status-card">
          <div className="status-card__label">API</div>
          <div className={`status-card__value ${health?.status === 'healthy' ? 'status-card__value--ok' : 'status-card__value--error'}`}>
            {isLoading && !health ? '...' : health?.status === 'healthy' ? 'online' : 'offline'}
          </div>
        </div>
        <div className="status-card">
          <div className="status-card__label">Database</div>
          <div className={`status-card__value ${health?.database === 'connected' ? 'status-card__value--ok' : 'status-card__value--error'}`}>
            {isLoading && !health ? '...' : health?.database === 'connected' ? 'connected' : 'disconnected'}
          </div>
        </div>
        <div className="status-card">
          <div className="status-card__label">Scrapers</div>
          <div className={`status-card__value ${scraperHealth?.status === 'healthy' ? 'status-card__value--ok' : scraperHealth?.status === 'degraded' ? 'status-card__value--warn' : 'status-card__value--error'}`}>
            {isLoading && !scraperHealth ? '...' : `${scraperHealth?.healthy_count ?? 0}/${scraperHealth?.total_scrapers ?? 0}`}
          </div>
        </div>
        <div className="status-card">
          <div className="status-card__label">Version</div>
          <div className="status-card__value status-card__value--muted">
            {health?.version ?? '--'}
          </div>
        </div>
      </div>

      <div className="status-page__table-container">
        <table className="status-table">
          <thead>
            <tr>
              <th>Scraper</th>
              <th>Status</th>
              <th>Last Run</th>
              <th>Duration</th>
              <th>Records</th>
            </tr>
          </thead>
          <tbody>
            {!scraperHealth && scraperLoading && (
              <tr><td colSpan={5} className="status-table__loading">Loading...</td></tr>
            )}
            {scraperHealth?.scrapers.map((s) => (
              <tr key={s.name} className={s.is_stale ? 'status-table__row--stale' : s.last_status === 'failure' && s.consecutive_failures >= 3 ? 'status-table__row--error' : ''}>
                <td className="status-table__name">{SCRAPER_LABELS[s.name] ?? s.name}</td>
                <td><StatusPill scraper={s} /></td>
                <td className="status-table__mono">{formatRelativeTime(s.last_run_at)}</td>
                <td className="status-table__mono">{formatDuration(s.last_duration_ms)}</td>
                <td className="status-table__mono">{formatCount(s.last_records_created)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {scraperHealth?.scrapers.some(s => s.last_error) && (
        <div className="status-page__errors">
          <div className="status-page__errors-title">Recent Errors</div>
          {scraperHealth.scrapers.filter(s => s.last_error).map(s => (
            <div key={s.name} className="status-page__error-item">
              <span className="status-page__error-scraper">{SCRAPER_LABELS[s.name] ?? s.name}</span>
              <span className="status-page__error-text">{s.last_error}</span>
            </div>
          ))}
        </div>
      )}

      <footer className="status-page__footer">
        <span>Refreshing every 30s</span>
        {health?.version && <span>v{health.version}</span>}
      </footer>
    </div>
  );
}
