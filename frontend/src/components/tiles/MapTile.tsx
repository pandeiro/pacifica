import { useRef, useEffect, useCallback } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import './MapTile.css';
import { useLocations } from '../../hooks/useLocations';
import type { Location } from '../../hooks/useLocations';

interface MapTileProps {
  locationId?: number;
  onLocationChange?: (locationId: number) => void;
}

const STYLE_URL = 'https://basemaps.cartocdn.com/gl/dark-matter-nolabels-gl-style/style.json';
const PUBLIC_LANDS_URL = '/data/socal-public-lands.geojson';

// Rotate map so NW-SE coastline runs vertically
const COASTLINE_BEARING = -45;

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

export function MapTile({ locationId, onLocationChange }: MapTileProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const styleLoadedRef = useRef(false);
  const mountedRef = useRef(true);
  const { locations } = useLocations();

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
      data: { type: 'FeatureCollection', features: [] },
    });

    map.addLayer({
      id: 'location-dots',
      type: 'circle',
      source: 'locations',
      paint: {
        'circle-radius': 6,
        'circle-color': ['get', 'color'],
        'circle-stroke-width': 2,
        'circle-stroke-color': 'rgba(255,255,255,0.8)',
        'circle-opacity': 0.9,
      },
      filter: ['!=', ['get', 'id'], -1],
    });

    map.addLayer({
      id: 'location-selected',
      type: 'circle',
      source: 'locations',
      paint: {
        'circle-radius': 10,
        'circle-color': '#00d4aa',
        'circle-stroke-width': 3,
        'circle-stroke-color': '#ffffff',
        'circle-blur': 0.15,
        'circle-opacity': 1,
      },
      filter: ['==', ['get', 'id'], -1],
    });

    map.addLayer({
      id: 'location-labels',
      type: 'symbol',
      source: 'locations',
      layout: {
        'text-field': ['get', 'name'],
        'text-size': 10,
        'text-offset': [0, 1.4],
        'text-anchor': 'top',
        'text-font': ['Noto Sans Regular'],
      },
      paint: {
        'text-color': '#e8f4f8',
        'text-halo-color': '#050a14',
        'text-halo-width': 1.5,
      },
    });

    map.on('click', 'location-dots', handleMapClick);
    map.on('click', 'location-selected', handleMapClick);
    map.on('mousemove', 'location-dots', handleMapHover);
    map.on('mousemove', 'location-selected', handleMapHover);
    map.on('mouseleave', 'location-dots', () => {
      map.getCanvas().style.cursor = '';
      if (popupRef.current) popupRef.current.remove();
    });
    map.on('mouseleave', 'location-selected', () => {
      map.getCanvas().style.cursor = '';
      if (popupRef.current) popupRef.current.remove();
    });

    styleLoadedRef.current = true;

    // Load and add public lands overlay
    fetch(PUBLIC_LANDS_URL)
      .then((res) => res.json())
      .then((geojson: GeoJSON.FeatureCollection) => {
        if (!mountedRef.current) return;
        map.addSource('public-lands', { type: 'geojson', data: geojson });

        map.addLayer({
          id: 'public-lands-fill',
          type: 'fill',
          source: 'public-lands',
          paint: {
            'fill-color': ['match', ['get', 'type'],
              'National Forest', '#1a4d2e',
              'National Park', '#0d3b2a',
              'National Recreation Area', '#1a4d2e',
              'State Park', '#2d6b3f',
              'State Beach', '#3a7d52',
              '#2d5f3d'
            ],
            'fill-opacity': 0.45,
          },
        }, 'location-dots');

        map.addLayer({
          id: 'public-lands-outline',
          type: 'line',
          source: 'public-lands',
          paint: {
            'line-color': ['match', ['get', 'type'],
              'National Forest', '#3d8b4f',
              'National Park', '#2d7a3f',
              'State Park', '#4a9960',
              'State Beach', '#5aab70',
              '#4a8b5a'
            ],
            'line-width': 1.5,
            'line-opacity': 0.6,
          },
        }, 'location-dots');
      })
      .catch(() => {
        // Public lands data not available — continue without overlay
      });
  }, [handleMapClick, handleMapHover]);

  // Initialize map
  useEffect(() => {
    mountedRef.current = true;

    if (!mapContainer.current) return;

    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: STYLE_URL,
      center: [-118.5, 34.0],
      zoom: 6,
      bearing: COASTLINE_BEARING,
      attributionControl: false,
      maxZoom: 14,
      minZoom: 5,
    });

    mapRef.current = map;

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
  }, [addLocationLayers]);

  // Update location data when locations load
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !styleLoadedRef.current || locations.length === 0) return;

    const source = map.getSource('locations') as maplibregl.GeoJSONSource;
    if (source) {
      source.setData(locationsToGeoJSON(locations));
      fitMapToLocations(map, locations);
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

  return (
    <div className="tile map-tile">
      <div className="tile__header">
        <div className="tile__title">
          <span className="tile__title-icon">🗺️</span>
          Coastal Map
        </div>
      </div>
      <div className="map-tile__container" ref={mapContainer} />
    </div>
  );
}
