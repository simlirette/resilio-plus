import { useState, useCallback, useEffect } from 'react';
import { useAuth } from '../auth/AuthProvider';
import type { HomeData } from '../types/home';

interface UseHomeDataResult {
  data: HomeData | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  lastRefreshedAt: Date | null;
}

export function useHomeData(): UseHomeDataResult {
  const { apiRequest, status } = useAuth();
  const [data, setData] = useState<HomeData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<Date | null>(null);

  const refresh = useCallback(async (): Promise<void> => {
    if (status !== 'authenticated') {
      setData(null);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const nextData = await apiRequest<HomeData>('/mobile/home');
      setData(nextData);
      setLastRefreshedAt(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Accueil indisponible.');
    } finally {
      setLoading(false);
    }
  }, [apiRequest, status]);

  useEffect(() => {
    if (status === 'authenticated') {
      void refresh();
    } else if (status === 'unauthenticated') {
      setData(null);
      setError(null);
    }
  }, [refresh, status]);

  return {
    data,
    loading: loading || (status === 'authenticated' && data === null && error === null),
    error,
    refresh,
    lastRefreshedAt,
  };
}
