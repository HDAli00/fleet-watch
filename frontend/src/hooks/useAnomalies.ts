/**
 * useAnomalies — polls recent anomaly readings on an interval.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { TelemetryReading, TelemetryWindow } from "../types";

interface UseAnomaliesResult {
  anomalies: TelemetryReading[];
  loading: boolean;
  error: string | null;
}

export function useAnomalies(
  window: TelemetryWindow = "1h",
  refreshMs = 30_000
): UseAnomaliesResult {
  const [anomalies, setAnomalies] = useState<TelemetryReading[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const fetch = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = new AbortController();
    setLoading(true);

    api.telemetry
      .recentAnomalies(window)
      .then((data) => {
        setAnomalies(data);
        setError(null);
      })
      .catch((err: unknown) => {
        if (err instanceof Error && err.name !== "AbortError") {
          setError(err.message);
        }
      })
      .finally(() => setLoading(false));
  }, [window]);

  useEffect(() => {
    fetch();
    const interval = setInterval(fetch, refreshMs);
    return () => {
      clearInterval(interval);
      abortRef.current?.abort();
    };
  }, [fetch, refreshMs]);

  return { anomalies, loading, error };
}
