import { useState } from 'react';
import './WildlifeTile.css';
import type { TaxonGroup } from '../../types';
import { useWildlife } from '../../hooks/useWildlife';
import { useWildlifeAggregation } from '../../hooks/useWildlifeAggregation';
import type { AggregatedSpecies } from '../../hooks/useWildlifeAggregation';
import { getSpeciesEmoji } from '../../utils/speciesEmoji';

const SOURCE_BADGES: Record<string, { label: string; color: string }> = {
  inaturalist: { label: 'iNat', color: 'badge--green' },
  daveyslocker: { label: 'Davey\'s', color: 'badge--blue' },
  dana_wharf: { label: 'Dana Wharf', color: 'badge--blue' },
  acs_la: { label: 'ACS-LA', color: 'badge--teal' },
  harbor_breeze: { label: 'H. Breeze', color: 'badge--blue' },
  island_packers: { label: 'Is. Packers', color: 'badge--blue' },
  whale_alert: { label: 'Whale Alert', color: 'badge--orange' },
  twitter: { label: 'Twitter', color: 'badge--gray' },
};

const TAXON_GROUPS: TaxonGroup[] = ['whale', 'dolphin', 'shark', 'pinniped', 'bird', 'other'];

export function WildlifeTile() {
  const { sightings, isLoading, error } = useWildlife();
  const [searchQuery, setSearchQuery] = useState('');
  const [activeFilters, setActiveFilters] = useState<Set<TaxonGroup>>(
    new Set(TAXON_GROUPS)
  );
  const [selectedSources, setSelectedSources] = useState<Set<string>>(new Set());

  const rawSightings = sightings?.sightings ?? [];

  const aggregation = useWildlifeAggregation(rawSightings, {
    searchQuery,
    activeTaxonGroups: activeFilters,
    selectedSources,
  });

  const { timeBlocks } = aggregation;
  const hasResults = timeBlocks.length > 0;

  const toggleTaxonGroup = (group: TaxonGroup) => {
    const newFilters = new Set(activeFilters);
    if (newFilters.has(group)) {
      newFilters.delete(group);
    } else {
      newFilters.add(group);
    }
    setActiveFilters(newFilters);
  };

  const toggleSourceFilter = (source: string) => {
    const newSources = new Set(selectedSources);
    if (newSources.has(source)) {
      newSources.delete(source);
    } else {
      newSources.add(source);
    }
    setSelectedSources(newSources);
  };

  return (
    <div className="tile wildlife-tile">
        <div className="tile__header">
          <div className="tile__title">
            <span className="tile__title-icon">🔍</span>
            Wildlife
          </div>
        </div>

      <div className="tile__content">
        {/* Search bar */}
        <div className="wildlife-tile__search">
          <input
            type="text"
            className="wildlife-tile__search-input"
            placeholder="Search species, location, or source..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        {/* Taxon filter pills */}
        <div className="wildlife-tile__filters">
          {TAXON_GROUPS.map((group) => (
            <button
              key={group}
              className={`wildlife-tile__filter-pill ${
                activeFilters.has(group) ? 'wildlife-tile__filter-pill--active' : ''
              }`}
              onClick={() => toggleTaxonGroup(group)}
            >
              {group.charAt(0).toUpperCase() + group.slice(1)}
            </button>
          ))}
        </div>

        {/* Loading/Error states */}
        {isLoading && <div className="wildlife-tile__status">Loading sightings...</div>}
        {error && <div className="wildlife-tile__status wildlife-tile__status--error">Error: {error.message}</div>}

        {/* Empty state */}
        {!isLoading && !error && !hasResults && (
          <div className="wildlife-tile__status">No sightings reported in the last 7 days.</div>
        )}

        {/* Aggregated sightings, grouped by recency */}
        {!isLoading && !error && hasResults && (
          <div className="sightings-container">
            {timeBlocks.map((block) => (
              <div key={block.label} className="sightings-group">
                <div className="sightings-group__header">{block.label}</div>
                <div className="sightings-list">
                  {block.species.map((sp) => (
                    <SpeciesRow
                      key={`${block.label}-${sp.species}`}
                      species={sp}
                      onSourceClick={toggleSourceFilter}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function SpeciesRow({
  species: sp,
  onSourceClick,
}: {
  species: AggregatedSpecies;
  onSourceClick: (source: string) => void;
}) {
  return (
    <div className="species-row">
      <div className="species-row__main">
        <span className="species-row__emoji">
          {getSpeciesEmoji(sp.species)}
        </span>
        <div className="species-row__info">
          <div className="species-row__name">
            {sp.species}
            {sp.countLabel && (
              <span className="species-row__count">{sp.countLabel}</span>
            )}
          </div>
          {sp.locations.length > 0 && (
            <div className="species-row__locations">
              {sp.locations.join(' · ')}
            </div>
          )}
          {sp.sources.length > 0 && (
            <div className="species-row__sources">
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
