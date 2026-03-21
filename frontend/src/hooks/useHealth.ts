import { useState, useEffect, useCallback } from 'react';
import { API_URL } from '../config';

interface HealthData {
  status: string;
  service: string;
  version: string;
  database: string;
}

interface UseHealthReturn {
  data: HealthData | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

const POLL_INTERVAL = 30 * 1000;

export function useHealth(): UseHealthReturn {
  const [data, setData] = useState<HealthData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/health`);
      if (!res.ok) throw new Error(`Health API error: ${res.status}`);
      const result = await res.json();
      setData(result);
      setError(null);
    } catch (e) {
      setError(e as Error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchData]);

  return { data, isLoading, error, refetch: fetchData };
}
