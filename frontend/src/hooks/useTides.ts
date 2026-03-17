import { useState, useEffect, useCallback } from 'react';
import type { TidesResponse } from '../types';
import { API_URL } from '../config';

interface UseTidesReturn {
  tides: TidesResponse | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

export function useTides(locationId: number): UseTidesReturn {
  const [tides, setTides] = useState<TidesResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const tidesRes = await fetch(`${API_URL}/api/tides?location_id=${locationId}&hours=48`);
      
      if (!tidesRes.ok) {
        throw new Error(`Tides API error: ${tidesRes.status}`);
      }
      
      const tidesData = await tidesRes.json();
      setTides(tidesData);
    } catch (e) {
      setError(e as Error);
    } finally {
      setIsLoading(false);
    }
  }, [locationId]);

  // Initial fetch
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { tides, isLoading, error, refetch: fetchData };
}
