import { useState, useCallback } from 'react';
import { mockHomeData } from '../mocks/athlete-home-stub';
import type { HomeData } from '../types/home';

interface UseHomeDataResult {
  data: HomeData;
  loading: boolean;
  refresh: () => Promise<void>;
  lastRefreshedAt: Date;
}

/**
 * Placeholder hook for FE-MOBILE-2.
 * Returns mock data from `athlete-home-stub.ts`.
 *
 * To test different scenarios during development, change the import below:
 *   - mockHomeDataGreen  → readiness: 82 (green, one running session)
 *   - mockHomeDataYellow → readiness: 61 (yellow, one lifting session)
 *   - mockHomeDataRestDay → readiness: 72 (green, no session — rest day)
 *
 * REPLACED with real API call in Session FE-MOBILE-BACKEND-WIRING.
 * Drop-in contract: same return shape, same loading/refresh interface.
 */
export function useHomeData(): UseHomeDataResult {
  const [lastRefreshedAt, setLastRefreshedAt] = useState<Date>(new Date());
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async (): Promise<void> => {
    setLoading(true);
    // Simulate async fetch — real API call goes here in FE-MOBILE-BACKEND-WIRING
    await new Promise<void>((resolve) => setTimeout(resolve, 500));
    setLastRefreshedAt(new Date());
    setLoading(false);
  }, []);

  return {
    data: mockHomeData,
    loading,
    refresh,
    lastRefreshedAt,
  };
}
