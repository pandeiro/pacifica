import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useSpeciesSpotlight } from '../hooks/useSpeciesSpotlight';
import type { SightingRecord } from '../types';

// --- Test helpers ---

function today(): Date {
  return new Date(2026, 2, 21); // March 21, 2026
}

function dateStr(offsetDays: number): string {
  const d = today();
  d.setDate(d.getDate() + offsetDays);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function sighting(overrides: Partial<SightingRecord> & { species: string; source: string }): SightingRecord {
  return {
    id: Math.random(),
    timestamp: new Date().toISOString(),
    sighting_date: dateStr(0),
    taxon_group: 'other',
    count: null,
    location_id: null,
    location_name: null,
    source_url: null,
    confidence: 'high',
    raw_text: null,
    metadata: {},
    ...overrides,
  };
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(today());
});

afterEach(() => {
  vi.useRealTimers();
});

// --- Tests ---

describe('useSpeciesSpotlight', () => {

  // ── Basic matching ──────────────────────────────────────────────────

  describe('species matching', () => {
    it('matches a canonical species name', () => {
      const { result } = renderHook(() =>
        useSpeciesSpotlight([
          sighting({ species: 'Gray Whale', source: 'acs_la', sighting_date: dateStr(-1) }),
        ]),
      );

      const giants = result.current.find((g) => g.group.key === 'giants')!;
      const grayWhale = giants.recent.find((sp) => sp.species.name === 'Gray Whale');
      expect(grayWhale).toBeDefined();
      expect(grayWhale!.daysAgo).toBe(1);
      expect(grayWhale!.sources).toEqual(['acs_la']);
    });

    it('matches variant species names (killer whale -> Orca)', () => {
      const { result } = renderHook(() =>
        useSpeciesSpotlight([
          sighting({ species: 'Killer Whale', source: 'daveyslocker', sighting_date: dateStr(0) }),
        ]),
      );

      const giants = result.current.find((g) => g.group.key === 'giants')!;
      const orca = giants.recent.find((sp) => sp.species.name === 'Orca');
      expect(orca).toBeDefined();
      expect(orca!.daysAgo).toBe(0);
    });

    it('matches mola mola via "sunfish"', () => {
      const { result } = renderHook(() =>
        useSpeciesSpotlight([
          sighting({ species: 'Sunfish', source: 'inaturalist', sighting_date: dateStr(-3) }),
        ]),
      );

      const bucket = result.current.find((g) => g.group.key === 'bucket-list')!;
      const mola = bucket.recent.find((sp) => sp.species.name === 'Mola Mola');
      expect(mola).toBeDefined();
      expect(mola!.daysAgo).toBe(3);
    });

    it('ignores species not in the registry', () => {
      const { result } = renderHook(() =>
        useSpeciesSpotlight([
          sighting({ species: 'Sea Cucumber', source: 'inaturalist', sighting_date: dateStr(0) }),
        ]),
      );

      // No group should have any recent species
      const allRecent = result.current.flatMap((g) => g.recent);
      expect(allRecent).toHaveLength(0);
    });

    it('matches case-insensitively', () => {
      const { result } = renderHook(() =>
        useSpeciesSpotlight([
          sighting({ species: 'gray whale', source: 'acs_la', sighting_date: dateStr(-1) }),
        ]),
      );

      const giants = result.current.find((g) => g.group.key === 'giants')!;
      const grayWhale = giants.recent.find((sp) => sp.species.name === 'Gray Whale');
      expect(grayWhale).toBeDefined();
    });
  });

  // ── Mixed recent + stale within a group ─────────────────────────────

  describe('mixed recent and stale', () => {
    it('splits species within the same group into recent and stale', () => {
      const { result } = renderHook(() =>
        useSpeciesSpotlight([
          sighting({ species: 'Blue Whale', source: 'acs_la', sighting_date: dateStr(-10) }),
          sighting({ species: 'Orca', source: 'daveyslocker', sighting_date: dateStr(-60) }),
        ]),
      );

      const giants = result.current.find((g) => g.group.key === 'giants')!;
      // Blue Whale (10 days ago) should be recent
      expect(giants.recent.find((sp) => sp.species.name === 'Blue Whale')).toBeDefined();
      // Orca (60 days ago) should be stale
      const orca = giants.stale.find((sp) => sp.species.name === 'Orca');
      expect(orca).toBeDefined();
      expect(orca!.stale).toBe(true);
    });
  });

  // ── Tier ordering ───────────────────────────────────────────────────

  describe('tier ordering', () => {
    it('places Once in a Lifetime above The Regulars in same group', () => {
      const { result } = renderHook(() =>
        useSpeciesSpotlight([
          sighting({ species: 'California Sea Lion', source: 'inaturalist', sighting_date: dateStr(0) }),
          sighting({ species: 'Elephant Seal', source: 'inaturalist', sighting_date: dateStr(-2) }),
        ]),
      );

      const haulOut = result.current.find((g) => g.group.key === 'haul-out')!;
      const names = haulOut.recent.map((sp) => sp.species.name);
      // Elephant Seal (thrill) should come before California Sea Lion (regulars)
      expect(names.indexOf('Elephant Seal')).toBeLessThan(names.indexOf('California Sea Lion'));
    });

    it('orders by recency within same tier', () => {
      const { result } = renderHook(() =>
        useSpeciesSpotlight([
          sighting({ species: 'Fin Whale', source: 'daveyslocker', sighting_date: dateStr(-5) }),
          sighting({ species: 'Humpback Whale', source: 'dana_wharf', sighting_date: dateStr(-1) }),
        ]),
      );

      const giants = result.current.find((g) => g.group.key === 'giants')!;
      const names = giants.recent.map((sp) => sp.species.name);
      // Both are "thrill" tier, but Humpback was seen 1 day ago vs Fin 5 days ago
      expect(names.indexOf('Humpback Whale')).toBeLessThan(names.indexOf('Fin Whale'));
    });
  });

  // ── Aggregation ─────────────────────────────────────────────────────

  describe('aggregation', () => {
    it('sums counts across multiple sightings of same species', () => {
      const { result } = renderHook(() =>
        useSpeciesSpotlight([
          sighting({ species: 'Common Dolphin', source: 'daveyslocker', count: 50, sighting_date: dateStr(-1) }),
          sighting({ species: 'Common Dolphin', source: 'dana_wharf', count: 200, sighting_date: dateStr(0) }),
        ]),
      );

      const flyers = result.current.find((g) => g.group.key === 'frequent-flyers')!;
      const dolphin = flyers.recent.find((sp) => sp.species.name === 'Common Dolphin');
      expect(dolphin).toBeDefined();
      expect(dolphin!.totalCount).toBe(250);
      expect(dolphin!.countLabel).toBe('250+');
    });

    it('deduplicates locations and sources', () => {
      const { result } = renderHook(() =>
        useSpeciesSpotlight([
          sighting({ species: 'Gray Whale', source: 'acs_la', location_name: 'Palos Verdes', sighting_date: dateStr(-1) }),
          sighting({ species: 'Gray Whale', source: 'acs_la', location_name: 'Palos Verdes', sighting_date: dateStr(0) }),
          sighting({ species: 'Gray Whale', source: 'daveyslocker', location_name: 'Newport Beach', sighting_date: dateStr(0) }),
        ]),
      );

      const giants = result.current.find((g) => g.group.key === 'giants')!;
      const grayWhale = giants.recent.find((sp) => sp.species.name === 'Gray Whale');
      expect(grayWhale!.locations).toHaveLength(2);
      expect(grayWhale!.sources).toHaveLength(2);
    });

    it('uses most recent sighting date', () => {
      const { result } = renderHook(() =>
        useSpeciesSpotlight([
          sighting({ species: 'Orca', source: 'island_packers', sighting_date: dateStr(-10) }),
          sighting({ species: 'Orca', source: 'daveyslocker', sighting_date: dateStr(-2) }),
        ]),
      );

      const giants = result.current.find((g) => g.group.key === 'giants')!;
      const orca = giants.recent.find((sp) => sp.species.name === 'Orca');
      expect(orca!.daysAgo).toBe(2);
    });
  });

  // ── Stale threshold ─────────────────────────────────────────────────

  describe('stale threshold', () => {
    it('places species not seen in 30+ days in stale section', () => {
      const { result } = renderHook(() =>
        useSpeciesSpotlight([
          sighting({ species: 'Blue Whale', source: 'acs_la', sighting_date: dateStr(-45) }),
        ]),
      );

      const giants = result.current.find((g) => g.group.key === 'giants')!;
      const blueWhale = giants.stale.find((sp) => sp.species.name === 'Blue Whale');
      expect(blueWhale).toBeDefined();
      expect(blueWhale!.stale).toBe(true);
    });

    it('places species never seen in stale section', () => {
      const { result } = renderHook(() =>
        useSpeciesSpotlight([]),
      );

      // All species should be stale
      for (const group of result.current) {
        expect(group.recent).toHaveLength(0);
        expect(group.stale.length).toBeGreaterThan(0);
      }
    });

    it('keeps species seen within 30 days in recent section', () => {
      const { result } = renderHook(() =>
        useSpeciesSpotlight([
          sighting({ species: 'Blue Whale', source: 'acs_la', sighting_date: dateStr(-25) }),
        ]),
      );

      const giants = result.current.find((g) => g.group.key === 'giants')!;
      const blueWhale = giants.recent.find((sp) => sp.species.name === 'Blue Whale');
      expect(blueWhale).toBeDefined();
      expect(blueWhale!.stale).toBe(false);
    });
  });

  // ── Days ago calculation ────────────────────────────────────────────

  describe('days ago', () => {
    it('returns 0 for today', () => {
      const { result } = renderHook(() =>
        useSpeciesSpotlight([
          sighting({ species: 'Orca', source: 'daveyslocker', sighting_date: dateStr(0) }),
        ]),
      );

      const giants = result.current.find((g) => g.group.key === 'giants')!;
      const orca = giants.recent.find((sp) => sp.species.name === 'Orca');
      expect(orca!.daysAgo).toBe(0);
    });

    it('returns null for species with no sightings', () => {
      const { result } = renderHook(() =>
        useSpeciesSpotlight([]),
      );

      const giants = result.current.find((g) => g.group.key === 'giants')!;
      const anySpecies = giants.stale[0];
      expect(anySpecies.daysAgo).toBeNull();
    });
  });

  // ── Group structure ─────────────────────────────────────────────────

  describe('group structure', () => {
    it('returns all 6 groups even with no sightings', () => {
      const { result } = renderHook(() =>
        useSpeciesSpotlight([]),
      );

      expect(result.current).toHaveLength(6);
      const keys = result.current.map((g) => g.group.key);
      expect(keys).toEqual(['giants', 'frequent-flyers', 'predators', 'bucket-list', 'haul-out', 'sea-birds']);
    });

    it('returns groups with recent and stale arrays', () => {
      const { result } = renderHook(() =>
        useSpeciesSpotlight([
          sighting({ species: 'Gray Whale', source: 'acs_la', sighting_date: dateStr(-1) }),
        ]),
      );

      for (const group of result.current) {
        expect(Array.isArray(group.recent)).toBe(true);
        expect(Array.isArray(group.stale)).toBe(true);
      }
    });
  });
});
