import { useState, useEffect, useCallback } from 'react';
import { API_URL } from '../config';
import type { LiveCam } from '../types';

interface UseLiveCamsReturn {
  cams: LiveCam[];
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

export function useLiveCams(): UseLiveCamsReturn {
  const [cams, setCams] = useState<LiveCam[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_URL}/api/live-cams`);

      if (!res.ok) {
        throw new Error(`Live cams API error: ${res.status}`);
      }

      const data: LiveCam[] = await res.json();
      setCams(data);
    } catch (e) {
      setError(e as Error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { cams, isLoading, error, refetch: fetchData };
}
