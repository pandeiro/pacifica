# Technical Reference: Wildlife Species Spotlight View

## 1. Overview

The Species Spotlight is an alternative view mode for the Wildlife tile that shifts from a
chronological feed to a curated, species-centric layout. It groups ~27 charismatic marine species
into 6 visual "charisma groups," ranked by rarity tier and recency. Rarer species surface to the
top, giving divers and wildlife enthusiasts a quick read on what's been seen and what's overdue.

**Design philosophy**: the classic feed view answers "what's been reported lately?" The Spotlight
view answers "has anyone seen an Orca recently?" — a fundamentally different question.

---

## 2. Architecture

### 2.1 View Toggle

The Wildlife tile header contains a `[ Feed | Spotlight ]` pill toggle, persisted to
`localStorage` under key `wildlife-view-mode` (defaults to `'feed'`).

Both views share the same filter panel (search, source pills, taxon pills). However:
- **Feed view**: respects all filters (taxon, source, search)
- **Spotlight view**: respects source and search filters only; ignores taxon filter (the curated
  species list already defines what to show)

### 2.2 Data Flow

```
useWildlife() → raw SightingRecord[]
  ├─ useWildlifeAggregation() → feed view (existing)
  └─ useSpeciesSpotlight()    → spotlight view (new)
```

The spotlight hook receives the same raw `SightingRecord[]` array, filtered by source/search only.
It matches each sighting against the species registry via case-insensitive substring matching,
then aggregates, groups, and sorts.

### 2.3 File Map

| File | Purpose |
|---|---|
| `frontend/src/utils/speciesRegistry.ts` | Curated species catalog: groups, tiers, match patterns |
| `frontend/src/hooks/useSpeciesSpotlight.ts` | Aggregation hook: raw sightings → ranked groups |
| `frontend/src/components/tiles/SpeciesSpotlightView.tsx` | Render component |
| `frontend/src/components/tiles/SpeciesSpotlightView.css` | Styles for groups, cards, tier accents |
| `frontend/src/components/tiles/WildlifeTile.tsx` | Toggle integration + conditional rendering |
| `frontend/src/components/tiles/WildlifeTile.css` | Toggle button styles |
| `frontend/src/__tests__/useSpeciesSpotlight.test.ts` | 18 unit tests |
| `api/routes/sightings.py` | Added `octopus`, `sea otter` canonical mappings |

---

## 3. Species Registry

### 3.1 Charisma Groups

Six groups define the visual layout. Each has a key, display label, and emoji prefix.

| Key | Label | Emoji | Species Count |
|---|---|---|---|
| `giants` | The Giants | 🐋 | 7 |
| `frequent-flyers` | The Frequent Flyers | 🐬 | 5 |
| `predators` | The Predators | 🦈 | 4 |
| `bucket-list` | The Bucket List | 🌟 | 6 |
| `haul-out` | The Haul-Out Crew | 🦭 | 3 |
| `sea-birds` | The Sea Birds | 🦅 | 4 |

Total: **29 curated species**.

### 3.2 Rarity Tiers

Each species is assigned one of four tiers that determine sort priority within its group.

| Tier | Weight | Description | Example Species |
|---|---|---|---|
| `once` | 0 | Seen <5×/year. Unicorn sightings. | Orca, Blue Whale, Octopus, Sea Otter |
| `thrill` | 1 | Exciting every time but not unicorn-rare. | Humpback Whale, Mako Shark, Elephant Seal |
| `notable` | 2 | Worth stopping for. Regular but interesting. | Gray Whale, Risso's Dolphin, Garibaldi |
| `regulars` | 3 | Commonly seen. Daily occurrence. | California Sea Lion, Brown Pelican, Common Dolphin |

### 3.3 Species Assignments

#### The Giants 🐋
| Tier | Species | Match Patterns |
|---|---|---|
| `once` | Blue Whale | `blue whale` |
| `once` | Orca | `orca`, `killer whale` |
| `thrill` | Fin Whale | `fin whale` |
| `thrill` | Humpback Whale | `humpback whale` |
| `thrill` | Sperm Whale | `sperm whale` |
| `notable` | Gray Whale | `gray whale`, `grey whale` |
| `notable` | Minke Whale | `minke whale` |

#### The Frequent Flyers 🐬
| Tier | Species | Match Patterns |
|---|---|---|
| `thrill` | Dall's Porpoise | `dall's porpoise`, `dalls porpoise` |
| `notable` | Pacific White-Sided Dolphin | `pacific white-sided dolphin` |
| `notable` | Risso's Dolphin | `risso's dolphin`, `rissos dolphin` |
| `regulars` | Common Dolphin | `common dolphin` |
| `regulars` | Bottlenose Dolphin | `bottlenose dolphin` |

#### The Predators 🦈
| Tier | Species | Match Patterns |
|---|---|---|
| `once` | White Shark | `white shark`, `great white shark` |
| `thrill` | Mako Shark | `mako shark` |
| `thrill` | Thresher Shark | `thresher shark` |
| `notable` | Blue Shark | `blue shark` |

#### The Bucket List 🌟
| Tier | Species | Match Patterns |
|---|---|---|
| `once` | Octopus | `octopus`, `lilliput` |
| `once` | Sea Otter | `sea otter`, `otter` |
| `once` | Mola Mola | `mola mola`, `sunfish` |
| `once` | Sea Turtle | `sea turtle`, `turtle` |
| `thrill` | Moray Eel | `moray eel`, `moray` |
| `notable` | Garibaldi | `garibaldi` |

#### The Haul-Out Crew 🦭
| Tier | Species | Match Patterns |
|---|---|---|
| `thrill` | Elephant Seal | `elephant seal` |
| `regulars` | California Sea Lion | `california sea lion` |
| `regulars` | Harbor Seal | `harbor seal` |

#### The Sea Birds 🦅
| Tier | Species | Match Patterns |
|---|---|---|
| `thrill` | Albatross | `albatross` |
| `notable` | Black-vented Shearwater | `shearwater` |
| `regulars` | Brown Pelican | `brown pelican`, `pelican` |
| `regulars` | Double-crested Cormorant | `double-crested cormorant`, `cormorant` |

---

## 4. Matching Algorithm

Each `SightingRecord` is matched against the registry using case-insensitive substring matching.
The first group+species that matches wins; a sighting can only match one spotlight species.

```
for each sighting:
  for each group in SPOTLIGHT_GROUPS:
    for each species in group:
      for each pattern in species.matchPatterns:
        if sighting.species.toLowerCase().contains(pattern.toLowerCase()):
          → matched, break all loops
```

Unmatched species (e.g., "Sea Cucumber", "Shark" without specific type) are silently excluded
from the spotlight view.

---

## 5. Ranking & Aggregation

### 5.1 Per-Species Aggregation

All sightings for a matched species are aggregated into a single `SpotlightSpeciesData`:
- **Count**: sum of all non-null counts, formatted as `"N+"` (e.g., `"250+"`)
- **Locations**: deduplicated set of location names
- **Sources**: deduplicated set of source keys
- **Latest date**: most recent `sighting_date` across all sightings
- **Days ago**: calendar days from today to latest date

### 5.2 Sorting Within Group

Species within each group are sorted by:
1. **Tier weight** ascending (0 = `once` first, 3 = `regulars` last)
2. **Days since last sighting** ascending (most recently seen first)

### 5.3 Stale Threshold

Species not seen in **30+ days** are moved to a `stale` array and rendered at the bottom of their
group behind a dashed separator, with reduced opacity (40%, rising to 60% on hover). Species
never seen at all also appear as stale.

This creates a visual "have you seen one?" section — the rarer species that haven't been spotted
recently are visible but de-emphasized.

---

## 6. Visual Design

### 6.1 Species Card

Each species renders as a compact card:

```
🐋  Blue Whale               24+
    3 days ago — Palos Verdes · ACS-LA
    [ACS-LA] [Davey's]
```

- Left border accent color by tier: gold (`once`), teal (`thrill`), subtle white (`notable`),
  transparent (`regulars`)
- Stale cards get a dashed top border separator within their group

### 6.2 Tier Border Colors

```css
.spotlight-card--once    { border-left-color: rgba(255, 215, 0, 0.6); }  /* gold */
.spotlight-card--thrill  { border-left-color: rgba(65, 184, 220, 0.5); } /* teal */
.spotlight-card--notable { border-left-color: rgba(255, 255, 255, 0.12); }
.spotlight-card--regulars { border-left-color: transparent; }
```

---

## 7. API Changes

Added canonical species mappings to `api/routes/sightings.py` for Octopus and Sea Otter:

```python
# Invertebrates
"octopus": "Octopus",
"california lilliput octopus": "Octopus",
"two-spot octopus": "Octopus",
# Marine Mammals
"sea otter": "Sea Otter",
"otter": "Sea Otter",
```

No schema changes. No new API endpoints. The Spotlight view consumes the existing
`GET /api/sightings` endpoint and does all grouping client-side.

---

## 8. Data Notes

- **Giant Sea Bass**: queried the production DB — 0 sightings. Not included in registry.
- **Octopus**: 1 sighting in DB (`California Lilliput Octopus`, 2026-03-21, from iNaturalist).
  Classified as `once` tier.
- **Sea Otter**: 0 sightings in DB. Included as `once` tier — bucket list species that could
  appear via iNaturalist.
- **Garibaldi**: 1 sighting in DB. User reports it's common in SoCal waters. Moved from
  Bucket List to `notable` tier in The Predators group.

---

## 9. Future Considerations

- **Seasonal weighting**: certain species could get a recency boost during their known migration
  windows (e.g., Gray Whale southbound Dec-Feb)
- **Sparkline thumbnails**: add a mini 30-day frequency chart per species card
- **Location filtering**: let users pick a location and see only sightings from that spot
- **Push notifications**: alert when a bucket-list species is sighted nearby
- **Historical trending**: show whether a species is trending more/less frequently vs last year
