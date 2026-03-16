import { useState, useEffect, useCallback } from 'react';
import type { TidesResponse, SunEventsResponse } from '../types';
import { API_URL } from '../config';

interface UseTidesReturn {
  tides: TidesResponse | null;
  sun: SunEventsResponse | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

export function useTides(locationId: number, stationId: string): UseTidesReturn {
  const [tides, setTides] = useState<TidesResponse | null>(null);
  const [sun, setSun] = useState<SunEventsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const [tidesRes, sunRes] = await Promise.all([
        fetch(`${API_URL}/api/tides?station_id=${stationId}&hours=48`),
        fetch(`${API_URL}/api/sun?location_id=${locationId}`),
      ]);
      
      if (!tidesRes.ok) {
        throw new Error(`Tides API error: ${tidesRes.status}`);
      }
      
      // Sun endpoint might 404 if no data, that's ok
      const tidesData = await tidesRes.json();
      setTides(tidesData);
      
      if (sunRes.ok) {
        const sunData = await sunRes.json();
        setSun(sunData);
      } else {
        setSun(null);
      }
    } catch (e) {
      setError(e as Error);
    } finally {
      setIsLoading(false);
    }
  }, [locationId, stationId]);

  // Initial fetch
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { tides, sun, isLoading, error, refetch: fetchData };
}
