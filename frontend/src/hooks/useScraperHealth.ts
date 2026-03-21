import { useState, useEffect, useCallback } from 'react';
import { API_URL } from '../config';

export interface ScraperStatus {
  name: string;
  last_run_at: string | null;
  last_status: string | null;
  last_duration_ms: number | null;
  last_records_created: number;
  last_records_updated: number;
  last_error: string | null;
  is_stale: boolean;
  minutes_since_last_success: number | null;
  consecutive_failures: number;
}

interface ScraperHealthData {
  status: string;
  scrapers: ScraperStatus[];
  total_scrapers: number;
  healthy_count: number;
  stale_count: number;
  failed_count: number;
}

interface UseScraperHealthReturn {
  data: ScraperHealthData | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

const POLL_INTERVAL = 30 * 1000;

export function useScraperHealth(): UseScraperHealthReturn {
  const [data, setData] = useState<ScraperHealthData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/health/scrapers`);
      if (!res.ok) throw new Error(`Scraper health API error: ${res.status}`);
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
