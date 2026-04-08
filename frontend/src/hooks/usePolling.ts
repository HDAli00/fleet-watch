/**
 * usePolling — generic auto-refreshing data fetcher.
 * Manages abort controller, loading/error state, and interval cleanup.
 */
import { useCallback, useEffect, useRef, useState } from "react";

interface UsePollingResult<T> {
  data: T[];
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

export function usePolling<T>(
  fetchFn: () => Promise<T[]>,
  deps: readonly unknown[],
  refreshMs: number
): UsePollingResult<T> {
  const [data, setData] = useState<T[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const loadData = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = new AbortController();
    setLoading(true);
    setError(null);

    fetchFn()
      .then(setData)
      .catch((err: unknown) => {
        if (err instanceof Error && err.name !== "AbortError") {
          setError(err.message);
        }
      })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, refreshMs);
    return () => {
      clearInterval(interval);
      abortRef.current?.abort();
    };
  }, [loadData, refreshMs]);

  return { data, loading, error, refresh: loadData };
}
