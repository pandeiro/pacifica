import { useState, useMemo } from 'react';
import './WildlifeTile.css';
import type { SightingRecord, TaxonGroup } from '../../types';
import { useWildlife } from '../../hooks/useWildlife';
import { getSpeciesEmoji } from '../../utils/speciesEmoji';

interface GroupedSightings {
  [timeLabel: string]: SightingRecord[];
}

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

function formatRecency(sightingDate: string | null): string {
  if (!sightingDate) return '';
  
  const date = new Date(sightingDate);
  
  const formatter = new Intl.DateTimeFormat('en-US', {
    month: 'numeric',
    day: 'numeric',
  });
  return formatter.format(date);
}

function getTimeGroup(sightingDate: string | null): string {
  if (!sightingDate) return 'Older';
  
  const date = new Date(sightingDate);
  const now = new Date();
  const currentDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const sightingDateOnly = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const diffDays = Math.floor((currentDate.getTime() - sightingDateOnly.getTime()) / (1000 * 60 * 60 * 24));

  if (diffDays <= 1) {
    return 'Last Day';
  }
  if (diffDays <= 7) {
    return 'Last Week';
  }
  if (diffDays <= 50) {
    return 'Older';
  }
  return 'Older';
}

export function WildlifeTile() {
  const { sightings, isLoading, error } = useWildlife();
  const [searchQuery, setSearchQuery] = useState('');
  const [activeFilters, setActiveFilters] = useState<Set<TaxonGroup>>(
    new Set(TAXON_GROUPS)
  );
  const [selectedSources, setSelectedSources] = useState<Set<string>>(new Set());

  // Filter by search and taxon groups
  const filteredSightings = useMemo(() => {
    if (!sightings) return [];

    return sightings.sightings.filter((s) => {
      // Taxon group filter
      if (!activeFilters.has(s.taxon_group)) {
        return false;
      }

      // Source filter
      if (selectedSources.size > 0 && !selectedSources.has(s.source)) {
        return false;
      }

      // Search query
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        return (
          s.species.toLowerCase().includes(query) ||
          (s.location_name?.toLowerCase().includes(query) || false) ||
          s.source.toLowerCase().includes(query)
        );
      }

      return true;
    });
  }, [sightings, activeFilters, selectedSources, searchQuery]);

  // Group by recency
  const groupedSightings = useMemo(() => {
    const groups: GroupedSightings = {
      'Last Day': [],
      'Last Week': [],
      'Older': [],
    };

    filteredSightings.forEach((s) => {
      const group = getTimeGroup(s.sighting_date);
      if (group in groups) {
        groups[group].push(s);
      }
    });

    return groups;
  }, [filteredSightings]);

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

  const hasResults = filteredSightings.length > 0;

  return (
    <div className="tile wildlife-tile">
        <div className="tile__header">
          <div className="tile__title">
            <span className="tile__title-icon">🔍</span>
            Wildlife Tile
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

        {/* Sightings list, grouped by recency */}
        {!isLoading && !error && hasResults && (
          <div className="sightings-container">
            {['Last Day', 'Last Week', 'Older'].map((timeLabel) => {
              const group = groupedSightings[timeLabel];
              if (group.length === 0) return null;

              return (
                <div key={timeLabel} className="sightings-group">
                  <div className="sightings-group__header">{timeLabel}</div>
                  <div className="sightings-list">
                    {group.map((sighting) => (
                      <div key={sighting.id} className="sighting-item">
                        <span className="sighting-item__emoji">
                          {getSpeciesEmoji(sighting.species)}
                        </span>
                        <div className="sighting-item__info">
                          <div className="sighting-item__species">
                            {sighting.species}
                            {sighting.count && sighting.count > 1 && (
                              <span className="sighting-item__count">
                                ×{sighting.count}
                              </span>
                            )}
                          </div>
                          <div className="sighting-item__meta">
                            {sighting.location_name && (
                              <>
                                <span>{sighting.location_name}</span>
                                <span className="sighting-item__dot">·</span>
                              </>
                            )}
                            <span className="sighting-item__time">
                              {formatRecency(sighting.sighting_date)}
                            </span>
                            <span className="sighting-item__dot">·</span>
                            <button
                              className={`source-badge ${
                                SOURCE_BADGES[sighting.source]?.color || 'badge--gray'
                              }`}
                              onClick={() => toggleSourceFilter(sighting.source)}
                              title={`Filter by ${sighting.source}`}
                            >
                              {SOURCE_BADGES[sighting.source]?.label || sighting.source}
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
