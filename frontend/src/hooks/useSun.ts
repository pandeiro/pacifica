import { useState, useEffect, useCallback } from 'react';
import type { SunEventsResponse } from '../types';
import { API_URL } from '../config';

interface UseSunReturn {
  sun: SunEventsResponse | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

export function useSun(locationId: number): UseSunReturn {
  const [sun, setSun] = useState<SunEventsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const sunRes = await fetch(`${API_URL}/api/sun-events?location_id=${locationId}&days=3`);
      
      if (sunRes.ok) {
        const sunData = await sunRes.json();
        // Transform new API format to match expected format
        if (sunData.events && sunData.events.length > 0) {
          const today = sunData.events[0];
          setSun({
            location_id: sunData.location_id,
            location_name: sunData.location_name,
            date: today.date,
            sunrise: today.sunrise,
            sunset: today.sunset,
            golden_hour_morning_start: today.golden_hour.morning.start,
            golden_hour_morning_end: today.golden_hour.morning.end,
            golden_hour_evening_start: today.golden_hour.evening.start,
            golden_hour_evening_end: today.golden_hour.evening.end,
          });
        } else {
          setSun(null);
        }
      } else {
        setSun(null);
      }
    } catch (e) {
      setError(e as Error);
    } finally {
      setIsLoading(false);
    }
  }, [locationId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { sun, isLoading, error, refetch: fetchData };
}
