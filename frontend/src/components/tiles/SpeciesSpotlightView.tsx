import './SpeciesSpotlightView.css';
import type { SpotlightGroupData, SpotlightSpeciesData } from '../../hooks/useSpeciesSpotlight';
import { getSpeciesEmoji } from '../../utils/speciesEmoji';

const SOURCE_BADGES: Record<string, { label: string; color: string }> = {
  inaturalist: { label: 'iNat', color: 'badge--green' },
  daveyslocker: { label: "Davey's", color: 'badge--blue' },
  dana_wharf: { label: 'Dana Wharf', color: 'badge--blue' },
  acs_la: { label: 'ACS-LA', color: 'badge--teal' },
  harbor_breeze: { label: 'H. Breeze', color: 'badge--blue' },
  island_packers: { label: 'Is. Packers', color: 'badge--blue' },
};

function formatDaysAgo(days: number | null): string {
  if (days === null) return 'not seen recently';
  if (days === 0) return 'today';
  if (days === 1) return 'yesterday';
  return `${days} days ago`;
}

export function SpeciesSpotlightView({
  groups,
  onSourceClick,
}: {
  groups: SpotlightGroupData[];
  onSourceClick: (source: string) => void;
}) {
  return (
    <div className="spotlight-container">
      {groups.map((g) => (
        <SpotlightGroupSection
          key={g.group.key}
          data={g}
          onSourceClick={onSourceClick}
        />
      ))}
    </div>
  );
}

function SpotlightGroupSection({
  data,
  onSourceClick,
}: {
  data: SpotlightGroupData;
  onSourceClick: (source: string) => void;
}) {
  const hasContent = data.recent.length > 0 || data.stale.length > 0;
  if (!hasContent) return null;

  return (
    <div className="spotlight-group">
      <div className="spotlight-group__header">
        <span className="spotlight-group__emoji">{data.group.emoji}</span>
        <span className="spotlight-group__label">{data.group.label}</span>
      </div>
      <div className="spotlight-group__list">
        {data.recent.map((sp) => (
          <SpotlightCard
            key={sp.species.name}
            data={sp}
            onSourceClick={onSourceClick}
          />
        ))}
        {data.stale.length > 0 && (
          <div className="spotlight-group__stale">
            {data.stale.map((sp) => (
              <SpotlightCard
                key={sp.species.name}
                data={sp}
                onSourceClick={onSourceClick}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function SpotlightCard({
  data: sp,
  onSourceClick,
}: {
  data: SpotlightSpeciesData;
  onSourceClick: (source: string) => void;
}) {
  const emoji = getSpeciesEmoji(sp.species.name);
  const tierClass = `spotlight-card--${sp.species.tier}`;

  return (
    <div className={`spotlight-card ${tierClass} ${sp.stale ? 'spotlight-card--stale' : ''}`}>
      <div className="spotlight-card__row">
        <span className="spotlight-card__emoji">{emoji}</span>
        <div className="spotlight-card__info">
          <div className="spotlight-card__name">
            {sp.species.name}
            {sp.countLabel && (
              <span className="spotlight-card__count">{sp.countLabel}</span>
            )}
          </div>
          <div className="spotlight-card__meta">
            {sp.daysAgo !== null ? (
              <>
                <span className="spotlight-card__ago">
                  {formatDaysAgo(sp.daysAgo)}
                </span>
                {sp.locations.length > 0 && (
                  <span className="spotlight-card__loc">
                    {' — '}{sp.locations.slice(0, 2).join(' · ')}
                  </span>
                )}
              </>
            ) : (
              <span className="spotlight-card__ago">no recent sightings</span>
            )}
          </div>
          {sp.sources.length > 0 && (
            <div className="spotlight-card__sources">
              {sp.sources.map((src) => (
                <button
                  key={src}
                  className={`source-badge ${SOURCE_BADGES[src]?.color || 'badge--gray'}`}
                  onClick={() => onSourceClick(src)}
                  title={`Filter by ${src}`}
                >
                  {SOURCE_BADGES[src]?.label || src}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
