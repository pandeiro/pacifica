import { useRef, useEffect, useCallback, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import './MapTile.css';
import { useLocations } from '../../hooks/useLocations';
import type { Location } from '../../hooks/useLocations';
import type { SightingRecord } from '../../types';

interface MapTileProps {
  locationId?: number;
  onLocationChange?: (locationId: number) => void;
  sightings?: SightingRecord[];
}

const MAP_STYLES: Record<string, { url: string; label: string }> = {
  dark: {
    url: 'https://basemaps.cartocdn.com/gl/dark-matter-nolabels-gl-style/style.json',
    label: 'Dark',
  },
  fiord: {
    url: 'https://tiles.openfreemap.org/styles/fiord',
    label: 'Fiord',
  },
  dark2: {
    url: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
    label: 'Dark+',
  },
  positron: {
    url: 'https://basemaps.cartocdn.com/gl/positron-nolabels-gl-style/style.json',
    label: 'Positron',
  },
};

// CPAD ArcGIS REST — SoCal bbox query
const CPAD_REST_URL =
  'https://gis.cnra.ca.gov/arcgis/rest/services/Boundaries/CPAD_AgencyLevel/MapServer/1/query';

// Rotate map so NW-SE coastline runs vertically
const COASTLINE_BEARING = -45;

const SOCAL_BBOX = [-121.0, 32.5, -117.0, 35.5];

const TYPE_COLORS: Record<string, string> = {
  harbor: '#2d8b96',
  beach: '#00d4aa',
  island: '#ffd93d',
  tidepool: '#c084fc',
  viewpoint: '#ff9f43',
};

function getTypeColor(type: string): string {
  return TYPE_COLORS[type] || '#00d4aa';
}

function formatPopupTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString('en-US', {
      timeZone: 'America/Los_Angeles',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  } catch {
    return iso;
  }
}

function inatSightingsToGeoJSON(
  sightings: SightingRecord[],
  locations: Location[],
): GeoJSON.FeatureCollection {
  const locMap = new Map(locations.map((l) => [l.id, l]));
  const inat = sightings.filter((s) => s.source === 'inaturalist');

  // Group by location_id, collect species and metadata
  const byLocation = new Map<number, { species: string[]; photoUrl: string | null; obsCount: number; obsLinks: { url: string; photo_url: string | null; observed_at: string }[] }>();

  for (const s of inat) {
    if (!s.location_id) continue;
    const loc = locMap.get(s.location_id);
    if (!loc) continue;

    if (!byLocation.has(s.location_id)) {
      byLocation.set(s.location_id, { species: [], photoUrl: null, obsCount: 0, obsLinks: [] });
    }
    const entry = byLocation.get(s.location_id)!;
    if (!entry.species.includes(s.species)) {
      entry.species.push(s.species);
    }

    const meta = s.metadata;
    if (!entry.photoUrl && typeof meta.photo_url === 'string') {
      entry.photoUrl = meta.photo_url;
    }
    if (typeof meta.obs_count === 'number') {
      entry.obsCount += meta.obs_count;
    }
    const rawObs = meta.observations;
    if (Array.isArray(rawObs)) {
      for (const o of rawObs) {
        if (typeof o === 'object' && o !== null && 'url' in o) {
          entry.obsLinks.push({
            url: String(o.url),
            photo_url: typeof o.photo_url === 'string' ? o.photo_url : null,
            observed_at: String(o.observed_at ?? ''),
          });
        }
      }
    }
  }

  return {
    type: 'FeatureCollection',
    features: Array.from(byLocation.entries()).map(([locId, data]) => {
      const loc = locMap.get(locId)!;
      return {
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [loc.lng, loc.lat] },
        properties: {
          location_id: locId,
          location_name: loc.name,
          species_list: data.species.join(', '),
          photo_url: data.photoUrl,
          obs_count: data.obsCount,
          obs_links_json: JSON.stringify(data.obsLinks.slice(0, 5)),
        },
      };
    }),
  };
}

function locationsToGeoJSON(locations: Location[]): GeoJSON.FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: locations.map((loc) => ({
      type: 'Feature',
      geometry: {
        type: 'Point',
        coordinates: [loc.lng, loc.lat],
      },
      properties: {
        id: loc.id,
        name: loc.name,
        type: loc.location_type,
        color: getTypeColor(loc.location_type),
      },
    })),
  };
}

function fitMapToLocations(map: maplibregl.Map, locations: Location[]) {
  if (locations.length === 0) return;
  const bounds = new maplibregl.LngLatBounds();
  for (const loc of locations) {
    bounds.extend([loc.lng, loc.lat]);
  }
  map.fitBounds(bounds, { padding: 30, maxZoom: 10, bearing: COASTLINE_BEARING });
}

async function fetchPublicLands(bbox: number[]): Promise<GeoJSON.FeatureCollection | null> {
  const params = new URLSearchParams({
    where: '1=1',
    outFields: 'UNIT_NAME,ACCESS_TYP,AGNCY_LEV,AGNCY_NAME,AGNCY_TYP,LAYER',
    f: 'geojson',
    returnGeometry: 'true',
    geometry: JSON.stringify({
      xmin: bbox[0],
      ymin: bbox[1],
      xmax: bbox[2],
      ymax: bbox[3],
    }),
    geometryType: 'esriGeometryEnvelope',
    inSR: '4326',
    spatialRel: 'esriSpatialRelIntersects',
    outSR: '4326',
    resultRecordCount: '2000',
  });

  try {
    const res = await fetch(`${CPAD_REST_URL}?${params}`);
    if (!res.ok) return null;
    const data = await res.json();
    if (!data.features?.length) return null;

    // Transform CPAD properties to match our layer expectations
    data.features = data.features.map((f: GeoJSON.Feature) => ({
      ...f,
      properties: {
        name: f.properties?.UNIT_NAME || 'Unknown',
        access: f.properties?.ACCESS_TYP || 'Unknown',
        agency_level: f.properties?.AGNCY_LEV || 'Unknown',
        agency: f.properties?.AGNCY_NAME || '',
        type: f.properties?.LAYER || f.properties?.AGNCY_LEV || 'Unknown',
      },
    }));

    return data;
  } catch {
    return null;
  }
}

export function MapTile({ locationId, onLocationChange, sightings = [] }: MapTileProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const styleLoadedRef = useRef(false);
  const mountedRef = useRef(true);
  const locationsRef = useRef<Location[]>([]);
  const userMarkerRef = useRef<maplibregl.Marker | null>(null);
  const sightingsRef = useRef<SightingRecord[]>([]);
  const { locations } = useLocations();
  const [currentStyle, setCurrentStyle] = useState('dark');
  const [showInat, setShowInat] = useState(false);

  // Keep ref in sync so callbacks always see current data
  locationsRef.current = locations;
  sightingsRef.current = sightings;

  const handleMapClick = useCallback(
    (e: maplibregl.MapMouseEvent & { features?: GeoJSON.Feature[] }) => {
      if (!e.features?.length || !onLocationChange) return;
      const id = e.features[0].properties?.id;
      if (typeof id === 'number') {
        onLocationChange(id);
      }
    },
    [onLocationChange],
  );

  const handleMapHover = useCallback(
    (e: maplibregl.MapMouseEvent & { features?: GeoJSON.Feature[] }) => {
      if (!mapRef.current) return;
      const map = mapRef.current;
      map.getCanvas().style.cursor = e.features?.length ? 'pointer' : '';

      if (e.features?.length) {
        const props = e.features[0].properties;
        if (popupRef.current) popupRef.current.remove();
        popupRef.current = new maplibregl.Popup({
          closeButton: false,
          closeOnClick: false,
          offset: 12,
          className: 'map-location-popup',
        })
          .setLngLat(e.lngLat)
          .setHTML(
            `<div class="map-location-popup__name">${props?.name}</div>
             <div class="map-location-popup__type">${props?.type}</div>`,
          )
          .addTo(map);
      } else if (popupRef.current) {
        popupRef.current.remove();
        popupRef.current = null;
      }
    },
    [],
  );

  const addLocationLayers = useCallback((map: maplibregl.Map) => {
    if (!mountedRef.current) return;

    map.addSource('locations', {
      type: 'geojson',
      data: locationsToGeoJSON(locationsRef.current),
    });

    map.addLayer({
      id: 'location-dots',
      type: 'circle',
      source: 'locations',
      paint: {
        'circle-radius': 3,
        'circle-color': ['get', 'color'],
        'circle-stroke-width': 1,
        'circle-stroke-color': 'rgba(255,255,255,0.5)',
        'circle-opacity': 0.85,
      },
      filter: ['!=', ['get', 'id'], -1],
    });

    // Hovered dot — hidden by default, shown via filter on mousemove
    map.addLayer({
      id: 'location-hover',
      type: 'circle',
      source: 'locations',
      paint: {
        'circle-radius': 6,
        'circle-color': ['get', 'color'],
        'circle-stroke-width': 2,
        'circle-stroke-color': 'rgba(255,255,255,0.9)',
        'circle-opacity': 1,
      },
      filter: ['==', ['get', 'id'], -1],
    });

    map.addLayer({
      id: 'location-selected',
      type: 'circle',
      source: 'locations',
      paint: {
        'circle-radius': 8,
        'circle-color': '#00d4aa',
        'circle-stroke-width': 2.5,
        'circle-stroke-color': '#ffffff',
        'circle-blur': 0.15,
        'circle-opacity': 1,
      },
      filter: ['==', ['get', 'id'], -1],
    });

    // Labels — only shown on hover
    map.addLayer({
      id: 'location-labels',
      type: 'symbol',
      source: 'locations',
      layout: {
        'text-field': ['get', 'name'],
        'text-size': 10,
        'text-offset': [0, 1.2],
        'text-anchor': 'top',
        'text-font': ['Noto Sans Regular'],
        'text-allow-overlap': false,
      },
      paint: {
        'text-color': '#e8f4f8',
        'text-halo-color': '#050a14',
        'text-halo-width': 1.5,
      },
      filter: ['==', ['get', 'id'], -1],
    });

    function handleDotHover(e: maplibregl.MapMouseEvent & { features?: GeoJSON.Feature[] }) {
      if (!e.features?.length) return;
      map.getCanvas().style.cursor = 'pointer';
      const id = e.features[0].properties?.id;
      if (typeof id !== 'number') return;
      map.setFilter('location-hover', ['==', ['get', 'id'], id]);
      map.setFilter('location-labels', ['==', ['get', 'id'], id]);
    }

    function handleDotLeave() {
      map.getCanvas().style.cursor = '';
      map.setFilter('location-hover', ['==', ['get', 'id'], -1]);
      map.setFilter('location-labels', ['==', ['get', 'id'], -1]);
      if (popupRef.current) popupRef.current.remove();
    }

    map.on('click', 'location-dots', handleMapClick);
    map.on('click', 'location-selected', handleMapClick);
    map.on('mousemove', 'location-dots', handleDotHover);
    map.on('mouseleave', 'location-dots', handleDotLeave);
    map.on('mousemove', 'location-selected', handleMapHover);
    map.on('mouseleave', 'location-selected', () => {
      map.getCanvas().style.cursor = '';
      if (popupRef.current) popupRef.current.remove();
    });

    styleLoadedRef.current = true;

    // Load public lands from CPAD ArcGIS REST API
    fetchPublicLands(SOCAL_BBOX).then((geojson) => {
      if (!mountedRef.current || !geojson) return;
      map.addSource('public-lands', { type: 'geojson', data: geojson });

      map.addLayer(
        {
          id: 'public-lands-fill',
          type: 'fill',
          source: 'public-lands',
          paint: {
            'fill-color': [
              'match',
              ['get', 'type'],
              'Federal', '#1a4d2e',
              'State', '#2d6b3f',
              'Special District', '#2a5f45',
              'County', '#3a7d52',
              'City', '#357a50',
              'Non Profit', '#1f5c38',
              '#2d5f3d',
            ],
            'fill-opacity': 0.35,
          },
        },
        'location-dots',
      );

      map.addLayer(
        {
          id: 'public-lands-outline',
          type: 'line',
          source: 'public-lands',
          paint: {
            'line-color': [
              'match',
              ['get', 'type'],
              'Federal', '#3d8b4f',
              'State', '#4a9960',
              'Special District', '#4a8b5a',
              'County', '#5aab70',
              'City', '#55a06a',
              'Non Profit', '#3f8b50',
              '#4a8b5a',
            ],
            'line-width': 1,
            'line-opacity': 0.5,
          },
        },
        'location-dots',
      );

      // Hover popup for public lands
      map.on('mousemove', 'public-lands-fill', (e) => {
        if (!e.features?.length) return;
        map.getCanvas().style.cursor = 'default';
        const props = e.features[0].properties;
        if (popupRef.current) popupRef.current.remove();
        popupRef.current = new maplibregl.Popup({
          closeButton: false,
          closeOnClick: false,
          offset: 8,
          className: 'map-location-popup',
        })
          .setLngLat(e.lngLat)
          .setHTML(
            `<div class="map-location-popup__name">${props?.name || 'Protected Area'}</div>
             <div class="map-location-popup__type">${props?.agency_level || ''} · ${props?.access || ''}</div>`,
          )
          .addTo(map);
      });

      map.on('mouseleave', 'public-lands-fill', () => {
        if (popupRef.current) popupRef.current.remove();
      });
    });

    // iNaturalist observations layer
    const inatGeoJSON = inatSightingsToGeoJSON(sightingsRef.current, locationsRef.current);
    map.addSource('inat-observations', { type: 'geojson', data: inatGeoJSON });

    map.addLayer({
      id: 'inat-dots',
      type: 'circle',
      source: 'inat-observations',
      layout: {
        visibility: 'none',
      },
      paint: {
        'circle-radius': 5,
        'circle-color': '#7bc67e',
        'circle-stroke-width': 1.5,
        'circle-stroke-color': 'rgba(255,255,255,0.7)',
        'circle-opacity': 0.9,
      },
    });

    // Click popup for iNat observations
    map.on('click', 'inat-dots', (e) => {
      if (!e.features?.length) return;
      const props = e.features[0].properties;
      if (!props) return;

      let linksHtml = '';
      try {
        const links = JSON.parse(props.obs_links_json || '[]') as { url: string; photo_url: string | null; observed_at: string }[];
        linksHtml = links.map((l) => {
          const time = formatPopupTime(l.observed_at);
          return `<a href="${l.url}" target="_blank" rel="noopener" class="inat-popup__link">Observation · ${time} →</a>`;
        }).join('');
      } catch { /* ignore parse errors */ }

      const photoHtml = props.photo_url
        ? `<img src="${props.photo_url}" class="inat-popup__photo" alt="${props.species_list}" />`
        : '';

      if (popupRef.current) popupRef.current.remove();
      popupRef.current = new maplibregl.Popup({ offset: 12, maxWidth: '280px', className: 'inat-popup' })
        .setLngLat(e.lngLat)
        .setHTML(
          `<div class="inat-popup__inner">
            ${photoHtml}
            <div class="inat-popup__species">${props.species_list}</div>
            <div class="inat-popup__count">${props.obs_count} observation${props.obs_count !== '1' ? 's' : ''} at ${props.location_name}</div>
            <div class="inat-popup__links">${linksHtml}</div>
          </div>`,
        )
        .addTo(map);
    });

    // Hover cursor change for iNat dots
    map.on('mousemove', 'inat-dots', () => {
      map.getCanvas().style.cursor = 'pointer';
    });
    map.on('mouseleave', 'inat-dots', () => {
      map.getCanvas().style.cursor = '';
    });
  }, [handleMapClick, handleMapHover]);

  // Initialize map
  useEffect(() => {
    mountedRef.current = true;

    if (!mapContainer.current) return;

    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: MAP_STYLES[currentStyle].url,
      center: [-118.5, 34.0],
      zoom: 6,
      bearing: COASTLINE_BEARING,
      attributionControl: false,
      maxZoom: 14,
      minZoom: 5,
    });

    mapRef.current = map;

    // Compass-only navigation control (no zoom buttons)
    const nav = new maplibregl.NavigationControl({
      showCompass: true,
      showZoom: false,
      visualizePitch: false,
    });
    map.addControl(nav, 'top-right');

    map.on('load', () => {
      if (mountedRef.current) {
        addLocationLayers(map);
      }
    });

    return () => {
      mountedRef.current = false;
      if (popupRef.current) popupRef.current.remove();
      mapRef.current = null;
      styleLoadedRef.current = false;
      // Defer removal to avoid AbortError during style loading in Strict Mode
      const m = map;
      setTimeout(() => {
        try {
          m.remove();
        } catch {
          // Ignore cleanup errors
        }
      }, 0);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [addLocationLayers]);

  // Request user's geolocation and show pulsating marker
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    if (!navigator.geolocation) return;

    navigator.geolocation.getCurrentPosition(
      (position) => {
        if (!mountedRef.current || !mapRef.current) return;
        const { longitude, latitude } = position.coords;

        // Create pulsating dot marker
        const el = document.createElement('div');
        el.className = 'user-location-marker';
        el.innerHTML = '<div class="user-location-dot"></div><div class="user-location-pulse"></div>';

        const marker = new maplibregl.Marker({ element: el })
          .setLngLat([longitude, latitude])
          .addTo(mapRef.current);

        userMarkerRef.current = marker;
      },
      () => {
        // User denied or error — silently skip
      },
      { enableHighAccuracy: false, timeout: 10000 },
    );

    return () => {
      if (userMarkerRef.current) {
        userMarkerRef.current.remove();
        userMarkerRef.current = null;
      }
    };
  }, []);

  // Switch map style without full re-initialization
  const handleStyleSwitch = useCallback((styleKey: string) => {
    const map = mapRef.current;
    if (!map || styleKey === currentStyle) return;
    styleLoadedRef.current = false;
    setCurrentStyle(styleKey);
    map.setStyle(MAP_STYLES[styleKey].url);
    map.once('style.load', () => {
      if (mountedRef.current) {
        addLocationLayers(map);
        // Re-apply location data
        if (locationsRef.current.length > 0) {
          const source = map.getSource('locations') as maplibregl.GeoJSONSource;
          if (source) source.setData(locationsToGeoJSON(locationsRef.current));
        }
      }
    });
  }, [currentStyle, addLocationLayers]);

  // Update location data when locations load
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !styleLoadedRef.current || locations.length === 0) return;

    try {
      const source = map.getSource('locations') as maplibregl.GeoJSONSource;
      if (source) {
        source.setData(locationsToGeoJSON(locations));
        fitMapToLocations(map, locations);
      }
    } catch {
      // Source may not exist yet if style is still loading
    }
  }, [locations]);

  // Update selected marker filter when locationId changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !styleLoadedRef.current) return;

    const selectedId = locationId ?? -1;
    map.setFilter('location-selected', ['==', ['get', 'id'], selectedId]);
    map.setFilter('location-dots', ['!=', ['get', 'id'], selectedId]);

    // Fly to selected location
    if (locationId) {
      const loc = locations.find((l) => l.id === locationId);
      if (loc) {
        map.flyTo({ center: [loc.lng, loc.lat], zoom: Math.max(map.getZoom(), 9), bearing: COASTLINE_BEARING, duration: 600 });
      }
    }
  }, [locationId, locations]);

  // Toggle iNat layer visibility
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !styleLoadedRef.current) return;
    try {
      map.setLayoutProperty('inat-dots', 'visibility', showInat ? 'visible' : 'none');
    } catch {
      // Layer may not exist yet
    }
  }, [showInat]);

  // Update iNat data when sightings change
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !styleLoadedRef.current) return;
    try {
      const source = map.getSource('inat-observations') as maplibregl.GeoJSONSource;
      if (source) {
        source.setData(inatSightingsToGeoJSON(sightings, locations));
      }
    } catch {
      // Source may not exist yet
    }
  }, [sightings, locations]);

  return (
    <div className="tile map-tile">
      <div className="tile__header">
        <div className="tile__title">
          <span className="tile__title-icon">🗺️</span>
          Coastal Map
        </div>
        <div className="map-tile__header-right">
          <button
            className={`map-tile__layer-btn${showInat ? ' map-tile__layer-btn--active' : ''}`}
            onClick={() => setShowInat((v) => !v)}
            title="Toggle iNaturalist observations"
          >
            iNat
          </button>
          <div className="map-tile__styles">
            {Object.entries(MAP_STYLES).map(([key, { label }]) => (
              <button
                key={key}
                className={`map-tile__style-btn${key === currentStyle ? ' map-tile__style-btn--active' : ''}`}
                onClick={() => handleStyleSwitch(key)}
                title={`Switch to ${label} style`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>
      <div className="map-tile__container" ref={mapContainer} />
    </div>
  );
}
