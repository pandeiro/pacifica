import { useMemo } from 'react';
import type { SightingRecord } from '../types';
import {
  SPOTLIGHT_GROUPS,
  TIER_WEIGHT,
  type SpotlightGroup,
  type SpotlightSpecies,
} from '../utils/speciesRegistry';

// --- Types ---

export interface SpotlightSpeciesData {
  species: SpotlightSpecies;
  latestDate: string | null;
  daysAgo: number | null; // null = never seen in window
  totalCount: number;
  countLabel: string;
  locations: string[];
  sources: string[];
  sightingDates: string[];
  stale: boolean; // true if not seen in 30+ days
}

export interface SpotlightGroupData {
  group: SpotlightGroup;
  recent: SpotlightSpeciesData[];
  stale: SpotlightSpeciesData[];
}

// --- Helpers ---

const STALE_THRESHOLD_DAYS = 30;

function calcDaysAgo(dateStr: string | null): number | null {
  if (!dateStr) return null;
  const [y, m, d] = dateStr.split('-').map(Number);
  const date = new Date(y, m - 1, d);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.floor((today.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
}

function matchesSpecies(sighting: SightingRecord, sp: SpotlightSpecies): boolean {
  const speciesLower = sighting.species.toLowerCase();
  return sp.matchPatterns.some((pattern) => speciesLower.includes(pattern.toLowerCase()));
}

// --- Hook ---

export function useSpeciesSpotlight(
  rawSightings: SightingRecord[],
): SpotlightGroupData[] {
  return useMemo(() => {
    // Build a map: species name -> sighting records
    // Each sighting matches exactly one spotlight species (first match wins)
    const matched = new Map<string, SightingRecord[]>();

    for (const s of rawSightings) {
      // Already matched to another species? skip
      let matchedKey: string | null = null;
      for (const group of SPOTLIGHT_GROUPS) {
        for (const sp of group.species) {
          if (matchesSpecies(s, sp)) {
            matchedKey = sp.name;
            break;
          }
        }
        if (matchedKey) break;
      }
      if (!matchedKey) continue;

      if (!matched.has(matchedKey)) {
        matched.set(matchedKey, []);
      }
      matched.get(matchedKey)!.push(s);
    }

    // Build SpotlightGroupData for each group
    return SPOTLIGHT_GROUPS.map((group): SpotlightGroupData => {
      const recent: SpotlightSpeciesData[] = [];
      const stale: SpotlightSpeciesData[] = [];

      for (const sp of group.species) {
        const sightings = matched.get(sp.name) ?? [];

        if (sightings.length === 0) {
          // Never seen — show as stale
          stale.push({
            species: sp,
            latestDate: null,
            daysAgo: null,
            totalCount: 0,
            countLabel: '',
            locations: [],
            sources: [],
            sightingDates: [],
            stale: true,
          });
          continue;
        }

        // Aggregate
        const sightingDates = [...new Set(
          sightings.map((s) => s.sighting_date).filter(Boolean) as string[],
        )].sort((a, b) => b.localeCompare(a));

        const latestDate = sightingDates[0] ?? null;
        const daysAgo = calcDaysAgo(latestDate);
        const isStale = daysAgo !== null && daysAgo > STALE_THRESHOLD_DAYS;

        const sumCount = sightings
          .map((s) => s.count ?? 0)
          .filter((c) => c > 0)
          .reduce((a, b) => a + b, 0);
        const hasAnyCount = sightings.some((s) => s.count != null && s.count > 0);

        const locations = [...new Set(
          sightings.map((s) => s.location_name).filter(Boolean) as string[],
        )];
        const sources = [...new Set(sightings.map((s) => s.source))];

        const data: SpotlightSpeciesData = {
          species: sp,
          latestDate,
          daysAgo,
          totalCount: sumCount,
          countLabel: hasAnyCount ? `${sumCount}+` : '',
          locations,
          sources,
          sightingDates,
          stale: isStale,
        };

        if (isStale) {
          stale.push(data);
        } else {
          recent.push(data);
        }
      }

      // Sort: tier weight asc, then days since last sighting asc
      const sortByTierAndRecency = (a: SpotlightSpeciesData, b: SpotlightSpeciesData) => {
        const tierDiff = TIER_WEIGHT[a.species.tier] - TIER_WEIGHT[b.species.tier];
        if (tierDiff !== 0) return tierDiff;
        // Both seen: sort by recency. Both unseen: sort by name.
        if (a.daysAgo !== null && b.daysAgo !== null) return a.daysAgo - b.daysAgo;
        if (a.daysAgo !== null) return -1;
        if (b.daysAgo !== null) return 1;
        return a.species.name.localeCompare(b.species.name);
      };

      recent.sort(sortByTierAndRecency);
      stale.sort(sortByTierAndRecency);

      return { group, recent, stale };
    });
  }, [rawSightings]);
}
