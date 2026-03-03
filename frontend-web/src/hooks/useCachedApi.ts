/**
 * API caching hook with SWR for optimal performance.
 * 
 * Features:
 * - Automatic revalidation
 * - Stale-while-revalidate
 * - Request deduplication
 * - Cache invalidation
 */

import useSWR, { SWRConfiguration } from 'swr';
import { useCallback } from 'react';

const fetcher = async (url: string) => {
  const res = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('token')}`,
    },
  });
  
  if (!res.ok) throw new Error('API request failed');
  return res.json();
};

/**
 * Cached API hook with optimized defaults
 */
export function useCachedApi<T>(
  url: string | null,
  options?: SWRConfiguration
) {
  const config: SWRConfiguration = {
    revalidateOnFocus: false,
    revalidateOnReconnect: true,
    dedupingInterval: 2000,
    focusThrottleInterval: 5000,
    ...options,
  };

  const { data, error, mutate, isLoading } = useSWR<T>(
    url,
    fetcher,
    config
  );

  const refresh = useCallback(() => {
    mutate();
  }, [mutate]);

  return {
    data,
    error,
    isLoading,
    refresh,
  };
}

/**
 * Prefetch API data
 */
export function prefetchApi(url: string) {
  return fetcher(url);
}

/**
 * Cache configuration presets
 */
export const cachePresets = {
  // Static data (rarely changes)
  static: {
    revalidateOnFocus: false,
    revalidateOnReconnect: false,
    dedupingInterval: 60000, // 1 minute
  },
  // Dynamic data (changes frequently)
  dynamic: {
    revalidateOnFocus: true,
    revalidateOnReconnect: true,
    refreshInterval: 30000, // 30 seconds
  },
  // User-specific data
  user: {
    revalidateOnFocus: true,
    revalidateOnReconnect: true,
    dedupingInterval: 5000,
  },
};
