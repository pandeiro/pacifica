import { useMemo } from 'react';
import type { SightingRecord, TaxonGroup, InatObservation } from '../types';

// --- Types ---

export type SortMode = 'count' | 'alpha' | 'recent';

export interface AggregatedSpecies {
  species: string;
  taxonGroup: TaxonGroup;
  count: number;
  countLabel: string; // e.g. "12+" (sum across sources, with '+')
  locations: string[];
  sources: string[];
  sightingDates: string[]; // distinct dates this species appeared
  latestDate: string | null; // most recent sighting_date for this species
  inatLinks: InatObservation[]; // up to 5 most recent iNat observations
  inatPhotoUrl: string | null; // best available photo from iNat observations
}

export interface TimeBlock {
  label: string;      // "Last Day" | "Last Week" | "Older"
  species: AggregatedSpecies[];
}

export interface WildlifeAggregation {
  timeBlocks: TimeBlock[];
  totalRaw: number;    // pre-filter count
  totalFiltered: number; // post-filter count
  totalAggregated: number; // post-aggregation count
}

export interface WildlifeFilters {
  searchQuery: string;
  activeTaxonGroups: Set<TaxonGroup>;
  selectedSources: Set<string>;
  sortBy: SortMode;
}

// --- Helpers ---

const TIME_BLOCK_ORDER = ['Last Day', 'Last Week', 'Older'] as const;

function getTimeGroup(sightingDate: string | null): string | null {
  if (!sightingDate) return null;

  const [year, month, day] = sightingDate.split('-').map(Number);
  const date = new Date(year, month - 1, day);
  const now = new Date();
  const currentDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const diffDays = Math.floor((currentDate.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

  if (diffDays < 0) return null;
  if (diffDays <= 1) return 'Last Day';
  if (diffDays <= 7) return 'Last Week';
  if (diffDays <= 50) return 'Older';
  return null;
}

// --- Hook ---

export function useWildlifeAggregation(
  rawSightings: SightingRecord[],
  filters: WildlifeFilters,
): WildlifeAggregation {
  const { searchQuery, activeTaxonGroups, selectedSources, sortBy } = filters;

  return useMemo(() => {
    // Step 1: Apply filters
    const filtered = rawSightings.filter((s) => {
      if (!activeTaxonGroups.has(s.taxon_group)) return false;
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

    // Step 2: Group by time block, then aggregate by species within each block
    const blockMap = new Map<string, Map<string, SightingRecord[]>>();

    for (const s of filtered) {
      const timeLabel = getTimeGroup(s.sighting_date);
      if (!timeLabel) continue;

      if (!blockMap.has(timeLabel)) {
        blockMap.set(timeLabel, new Map());
      }
      const speciesMap = blockMap.get(timeLabel)!;
      const key = s.species.toLowerCase();
      if (!speciesMap.has(key)) {
        speciesMap.set(key, []);
      }
      speciesMap.get(key)!.push(s);
    }

    // Step 3: Build aggregated time blocks
    const timeBlocks: TimeBlock[] = TIME_BLOCK_ORDER.map((label) => {
      const speciesMap = blockMap.get(label);
      if (!speciesMap) return { label, species: [] };

      const species: AggregatedSpecies[] = Array.from(speciesMap.entries())
        .map(([, sightings]) => {
          const representative = sightings[0];
          const sumCount = sightings
            .map((s) => s.count ?? 0)
            .filter((c) => c > 0)
            .reduce((a, b) => a + b, 0);
          const hasAnyCount = sightings.some((s) => s.count != null && s.count > 0);

          const locations = [...new Set(
            sightings.map((s) => s.location_name).filter(Boolean) as string[],
          )];
          const sources = [...new Set(sightings.map((s) => s.source))];
          const sightingDates = [...new Set(
            sightings.map((s) => s.sighting_date).filter(Boolean) as string[],
          )];
          const latestDate = sightingDates.length > 0
            ? sightingDates.sort((a, b) => b.localeCompare(a))[0]
            : null;

          // Extract iNat observation links from metadata
          let inatLinks: InatObservation[] = [];
          let inatPhotoUrl: string | null = null;
          const inatSighting = sightings.find((s) => s.source === 'inaturalist');
          if (inatSighting) {
            const meta = inatSighting.metadata;
            const rawObs = meta.observations;
            if (Array.isArray(rawObs)) {
              inatLinks = rawObs.filter(
                (o): o is InatObservation =>
                  typeof o === 'object' && o !== null && 'obs_id' in o && 'url' in o,
              );
            }
            if (typeof meta.photo_url === 'string') {
              inatPhotoUrl = meta.photo_url;
            }
          }

          return {
            species: representative.species,
            taxonGroup: representative.taxon_group,
            count: sumCount,
            countLabel: hasAnyCount ? `${sumCount}+` : '',
            locations,
            sources,
            sightingDates,
            latestDate,
            inatLinks,
            inatPhotoUrl,
          };
        })
        .sort((a, b) => {
          switch (sortBy) {
            case 'alpha':
              return a.species.localeCompare(b.species);
            case 'recent':
              return (b.latestDate ?? '').localeCompare(a.latestDate ?? '') || a.species.localeCompare(b.species);
            case 'count':
            default:
              if (b.count !== a.count) return b.count - a.count;
              return a.species.localeCompare(b.species);
          }
        });

      return { label, species };
    }).filter((block) => block.species.length > 0);

    // Count totals for debugging / summary
    const totalRaw = rawSightings.length;
    const totalFiltered = filtered.length;
    const totalAggregated = timeBlocks.reduce(
      (sum, block) => sum + block.species.length,
      0,
    );

    return { timeBlocks, totalRaw, totalFiltered, totalAggregated };
  }, [rawSightings, searchQuery, activeTaxonGroups, selectedSources, sortBy]);
}
