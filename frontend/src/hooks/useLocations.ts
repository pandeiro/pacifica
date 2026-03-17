import { useState, useEffect, useCallback } from 'react';

export interface StationInfo {
  name: string;
  distance_miles: number;
  direction: string;
}

export interface Location {
  id: number;
  name: string;
  slug: string;
  lat: number;
  lng: number;
  location_type: string;
  region: string;
  noaa_station_id: string | null;
  coastline_bearing: number | null;
  description: string;
  station_info?: StationInfo;
}

interface UseLocationsReturn {
  locations: Location[];
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

import { API_URL } from '../config';

export function useLocations(): UseLocationsReturn {
  const [locations, setLocations] = useState<Location[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const res = await fetch(`${API_URL}/api/locations`);
      
      if (!res.ok) {
        throw new Error(`Locations API error: ${res.status}`);
      }
      
      const data = await res.json();
      setLocations(data);
    } catch (e) {
      setError(e as Error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { locations, isLoading, error, refetch: fetchData };
}
