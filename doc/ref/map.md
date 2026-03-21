# Map Tile — Technical Reference

## Overview

The Coastal Map tile is the visual anchor of the Pacifica dashboard. It renders all 23 coastal locations on an interactive MapLibre GL JS map with a rotated view that aligns the SoCal coastline along the vertical axis.

## Architecture

### Dependencies
- **maplibre-gl** `4.5.0` — WebGL vector map renderer
- **CartoDB dark-matter-nolabels** — Base map style (no built-in labels)
- Custom GeoJSON overlay for public lands

### Data Flow
```
useLocations() hook
  → /api/locations
    → 23 locations with lat/lng, type, region
      → MapTile converts to GeoJSON FeatureCollection
        → MapLibre circle layer renders dots
```

### Bidirectional Location Sync
```
Dashboard (locationId state)
  ├→ MapTile: highlights selected marker, flies to location
  ├→ MapTile click: onLocationChange(id) → Dashboard updates
  └→ Right dropdown: setLocationId → MapTile re-highlights
```

## Map Configuration

### Style
- **URL**: `https://basemaps.cartocdn.com/gl/dark-matter-nolabels-gl-style/style.json`
- **Why**: Dark theme matching dashboard palette, zero built-in labels — only our custom location labels appear on the map
- **Alternative considered**: OpenFreeMap liberty/positron (had MapLibre 5.x projection compatibility issues)

### Viewport
| Parameter | Value | Notes |
|-----------|-------|-------|
| `center` | `[-118.5, 34.0]` | Roughly central SoCal |
| `zoom` | `6` | Covers SD to San Simeon |
| `bearing` | `-45` | Rotates NW-SE coastline to vertical |
| `maxZoom` | `14` | |
| `minZoom` | `5` | |

### Rotation
The bearing of `-45°` rotates the map so the SoCal coastline (which runs ~315° from true north) appears to run vertically. This maximizes use of the 350px-wide left column.

## Layers

### Location Markers (GeoJSON circle layer)

Source: `locations` — dynamically generated from `/api/locations` response.

| Layer ID | Type | Purpose |
|----------|------|---------|
| `location-dots` | circle | Unselected locations |
| `location-selected` | circle | Currently selected location (larger, glowing) |
| `location-labels` | symbol | Location name text |

**Color coding by `location_type`:**
| Type | Color |
|------|-------|
| harbor | `#2d8b96` (teal) |
| beach | `#00d4aa` (cyan) |
| island | `#ffd93d` (amber) |
| tidepool | `#c084fc` (purple) |
| viewpoint | `#ff9f43` (orange) |

### Public Lands Overlay

Source: `/data/socal-public-lands.geojson` — static GeoJSON file.

| Layer ID | Type | Purpose |
|----------|------|---------|
| `public-lands-fill` | fill | Semi-transparent green overlay |
| `public-lands-outline` | line | Boundary outline |

**Color coding by `type` property:**
| Type | Fill | Outline |
|------|------|---------|
| National Forest | `#1a4d2e` | `#3d8b4f` |
| National Park | `#0d3b2a` | `#2d7a3f` |
| State Park | `#2d6b3f` | `#4a9960` |
| State Beach | `#3a7d52` | `#5aab70` |

### Layer Order
1. Base map tiles (CartoDB)
2. `public-lands-fill` (below location markers)
3. `public-lands-outline`
4. `location-dots`
5. `location-selected`
6. `location-labels`

## Public Lands Data

### Current Data
`frontend/public/data/socal-public-lands.geojson` — hand-crafted simplified polygons for the major SoCal public lands:

- Angeles National Forest (USFS)
- Los Padres National Forest (USFS)
- Cleveland National Forest (USFS)
- Channel Islands National Park (NPS)
- Santa Monica Mountains NRA (NPS)
- Crystal Cove State Park
- Torrey Pines State Natural Reserve
- Point Mugu State Park
- Morro Bay State Park
- San Onofre State Beach

### Better Data Sources (TODO)
For accurate boundaries, replace with processed data from:

| Source | Coverage | Format | Notes |
|--------|----------|--------|-------|
| **USGS PAD-US 4.1** | Federal lands (USFS, NPS, BLM) | GDB → GeoJSON | [Download CA clip](https://www.sciencebase.gov/catalog/item/6759abcfd34edfeb8710a004) |
| **CPAD 2025a** | State/local/NGO lands | SHP → GeoJSON | [Download](https://data.cnra.ca.gov/dataset/cpad) |
| **30x30 Conserved Areas** | Subset of above | GeoJSON | [Download](https://data.ca.gov/dataset/30x30-conserved-areas-terrestrial-2024) |

**Processing workflow:**
```bash
# Install tools
brew install gdal
npm install -g mapshaper

# Convert PAD-US GDB to GeoJSON, clip to SoCal
ogr2ogr -f GeoJSON -spat -121.5 32.5 -117 35.6 \
  socal_protected.geojson PADUS4_1_CA.gdb PADUS4_1Combined

# Simplify for web
mapshaper socal_protected.geojson -simplify 10% -o public/data/

# Merge with CPAD data if needed
mapshaper -merge-layers cpad_socal.geojson padus_socal.geojson \
  -o public/data/socal-public-lands.geojson
```

## Component Interface

```typescript
interface MapTileProps {
  locationId?: number;           // Currently selected location (highlights on map)
  onLocationChange?: (id: number) => void;  // Fires when user clicks a location dot
}
```

## Files

| File | Purpose |
|------|---------|
| `frontend/src/components/tiles/MapTile.tsx` | Map component |
| `frontend/src/components/tiles/MapTile.css` | Tile container & popup styles |
| `frontend/public/data/socal-public-lands.geojson` | Public lands overlay data |
| `frontend/src/hooks/useLocations.ts` | Location data hook |

## Known Issues

- **React Strict Mode AbortError**: In dev mode, a benign `AbortError: signal is aborted without reason` appears in the console during the double-mount cycle. This is a MapLibre cleanup race condition and does not occur in production.
- **MapLibre 5.x incompatibility**: MapLibre 5.x had a `migrateProjection` error with all tested styles. Pinned to 4.5.0.

## Future Enhancements

- [ ] Swap hand-crafted GeoJSON for PAD-US/CPAD processed data
- [ ] Add wildlife sighting density heatmap layer
- [ ] Click popup with location summary + drive time
- [ ] Drill-down zoom on location click
- [ ] Layer toggle controls (show/hide public lands, labels, etc.)
