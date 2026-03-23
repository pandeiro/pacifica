import { useState, useEffect, useCallback } from 'react';
import { API_URL } from '../config';
import type { SeasonalEvent } from '../types';

interface UseSeasonalEventsReturn {
  events: SeasonalEvent[];
  isLoading: boolean;
  error: Error | null;
}

export function useSeasonalEvents(): UseSeasonalEventsReturn {
  const [events, setEvents] = useState<SeasonalEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_URL}/api/seasonal-events`);

      if (!res.ok) {
        throw new Error(`Seasonal events API error: ${res.status}`);
      }

      const data: SeasonalEvent[] = await res.json();
      setEvents(data);
    } catch (e) {
      setError(e as Error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { events, isLoading, error };
}
