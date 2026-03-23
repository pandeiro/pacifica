import { useState, useRef, useEffect, useMemo } from 'react';
import './WildlifeTile.css';
import type { TaxonGroup } from '../../types';
import { useWildlife } from '../../hooks/useWildlife';
import { useWildlifeAggregation } from '../../hooks/useWildlifeAggregation';
import type { AggregatedSpecies, SortMode } from '../../hooks/useWildlifeAggregation';
import { useSpeciesSpotlight } from '../../hooks/useSpeciesSpotlight';
import { SpeciesSpotlightView } from './SpeciesSpotlightView';
import { getSpeciesEmoji } from '../../utils/speciesEmoji';

type ViewMode = 'feed' | 'spotlight';
const VIEW_MODE_KEY = 'wildlife-view-mode';

const SOURCE_BADGES: Record<string, { label: string; color: string }> = {
  inaturalist: { label: 'iNat', color: 'badge--green' },
  daveyslocker: { label: "Davey's", color: 'badge--blue' },
  dana_wharf: { label: 'Dana Wharf', color: 'badge--blue' },
  acs_la: { label: 'ACS-LA', color: 'badge--teal' },
  harbor_breeze: { label: 'H. Breeze', color: 'badge--blue' },
  island_packers: { label: 'Is. Packers', color: 'badge--blue' },
};

const ALL_TAXON: TaxonGroup[] = ['whale', 'dolphin', 'shark', 'pinniped', 'bird', 'other'];
const POPULAR_TAXON: TaxonGroup[] = ['whale', 'dolphin', 'shark', 'pinniped'];
const ALL_SOURCES = Object.keys(SOURCE_BADGES);

export function WildlifeTile() {
  const { sightings, isLoading, error } = useWildlife();
  const [searchQuery, setSearchQuery] = useState('');
  const [activeFilters, setActiveFilters] = useState<Set<TaxonGroup>>(
    new Set(ALL_TAXON)
  );
  const [selectedSources, setSelectedSources] = useState<Set<string>>(new Set());
  const [sortBy, setSortBy] = useState<SortMode>('count');
  const [filterOpen, setFilterOpen] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>(() => {
    try {
      const saved = localStorage.getItem(VIEW_MODE_KEY);
      return saved === 'spotlight' ? 'spotlight' : 'feed';
    } catch {
      return 'feed';
    }
  });
  const filterRef = useRef<HTMLDivElement>(null);

  const rawSightings = sightings?.sightings ?? [];

  const aggregation = useWildlifeAggregation(rawSightings, {
    searchQuery,
    activeTaxonGroups: activeFilters,
    selectedSources,
    sortBy,
  });

  // Spotlight view: filter by source + search only (ignores taxon filter)
  const spotlightSightings = useMemo(() => {
    return rawSightings.filter((s) => {
      if (selectedSources.size > 0 && !selectedSources.has(s.source)) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        return (
          s.species.toLowerCase().includes(q) ||
          (s.location_name?.toLowerCase().includes(q) ?? false) ||
          s.source.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [rawSightings, selectedSources, searchQuery]);

  const spotlightGroups = useSpeciesSpotlight(spotlightSightings);

  const { timeBlocks } = aggregation;
  const hasResults = timeBlocks.length > 0;

  // Close filter panel on outside click
  useEffect(() => {
    if (!filterOpen) return;
    function handleClick(e: MouseEvent) {
      if (filterRef.current && !filterRef.current.contains(e.target as Node)) {
        setFilterOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [filterOpen]);

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

  const clearFilters = () => {
    setSearchQuery('');
    setActiveFilters(new Set(ALL_TAXON));
    setSelectedSources(new Set());
  };

  const handleViewModeChange = (mode: ViewMode) => {
    setViewMode(mode);
    try {
      localStorage.setItem(VIEW_MODE_KEY, mode);
    } catch {
      // localStorage unavailable
    }
  };

  const activeFilterCount =
    (selectedSources.size > 0 ? 1 : 0) +
    (searchQuery ? 1 : 0) +
    (activeFilters.size < ALL_TAXON.length ? 1 : 0);

  return (
    <div className="tile wildlife-tile">
      <div className="tile__header">
        <div className="tile__title">
          <span className="tile__title-icon">🔍</span>
          Wildlife
        </div>
        <div className="wildlife-tile__header-right">
          <div className="wildlife-tile__view-toggle">
            <button
              className={`wildlife-tile__toggle-btn ${viewMode === 'feed' ? 'wildlife-tile__toggle-btn--active' : ''}`}
              onClick={() => handleViewModeChange('feed')}
            >
              Feed
            </button>
            <button
              className={`wildlife-tile__toggle-btn ${viewMode === 'spotlight' ? 'wildlife-tile__toggle-btn--active' : ''}`}
              onClick={() => handleViewModeChange('spotlight')}
            >
              Spotlight
            </button>
          </div>
        <button
          className={`wildlife-tile__gear ${filterOpen ? 'wildlife-tile__gear--active' : ''}`}
          onClick={() => setFilterOpen((v) => !v)}
          title="Filters"
          aria-label="Toggle filters"
          aria-expanded={filterOpen}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3"/>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
          </svg>
          {activeFilterCount > 0 && (
            <span className="wildlife-tile__gear-badge">{activeFilterCount}</span>
          )}
        </button>
        </div>
      </div>

      <div className="tile__content">
        {/* Filters inset panel */}
        {filterOpen && (
          <div className="wildlife-filters" ref={filterRef}>
            <div className="wildlife-filters__search">
              <input
                type="text"
                className="wildlife-tile__search-input"
                placeholder="Search species, location..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                autoFocus
              />
            </div>

            <div className="wildlife-filters__section">
              <div className="wildlife-filters__label">Popular</div>
              <div className="wildlife-filters__pills">
                {POPULAR_TAXON.map((group) => (
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
            </div>

            <div className="wildlife-filters__section">
              <div className="wildlife-filters__label">Also</div>
              <div className="wildlife-filters__pills">
                {ALL_TAXON.filter((t) => !POPULAR_TAXON.includes(t)).map((group) => (
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
            </div>

            <div className="wildlife-filters__section">
              <div className="wildlife-filters__label">Sources</div>
              <div className="wildlife-filters__pills">
                {ALL_SOURCES.map((src) => (
                  <button
                    key={src}
                    className={`source-badge ${
                      SOURCE_BADGES[src]?.color || 'badge--gray'
                    } ${selectedSources.has(src) ? 'source-badge--selected' : ''}`}
                    onClick={() => toggleSourceFilter(src)}
                  >
                    {SOURCE_BADGES[src]?.label || src}
                  </button>
                ))}
              </div>
            </div>

            <div className="wildlife-filters__section">
              <div className="wildlife-filters__label">Sort by</div>
              <div className="wildlife-filters__pills">
                {([
                  { key: 'count' as SortMode, label: 'Count' },
                  { key: 'alpha' as SortMode, label: 'A → Z' },
                  { key: 'recent' as SortMode, label: 'Recent' },
                ]).map((opt) => (
                  <button
                    key={opt.key}
                    className={`wildlife-tile__filter-pill ${
                      sortBy === opt.key ? 'wildlife-tile__filter-pill--active' : ''
                    }`}
                    onClick={() => setSortBy(opt.key)}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            {activeFilterCount > 0 && (
              <button className="wildlife-filters__clear" onClick={clearFilters}>
                Clear filters
              </button>
            )}
          </div>
        )}

        {/* Loading/Error states */}
        {isLoading && <div className="wildlife-tile__status">Loading sightings...</div>}
        {error && <div className="wildlife-tile__status wildlife-tile__status--error">Error: {error.message}</div>}

        {/* Empty state */}
        {!isLoading && !error && !hasResults && (
          <div className="wildlife-tile__status">No sightings reported in the last 7 days.</div>
        )}

        {/* Aggregated sightings, grouped by recency */}
        {!isLoading && !error && hasResults && viewMode === 'feed' && (
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

        {/* Species Spotlight view */}
        {!isLoading && !error && viewMode === 'spotlight' && (
          <SpeciesSpotlightView
            groups={spotlightGroups}
            onSourceClick={toggleSourceFilter}
          />
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
