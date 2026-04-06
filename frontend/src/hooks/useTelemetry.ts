/**
 * useTelemetry — polls panel telemetry on an interval.
 * Auto-refreshes every `refreshMs` milliseconds (default 60s).
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { TelemetryReading, TelemetryWindow } from "../types";

interface UseTelemetryResult {
  readings: TelemetryReading[];
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useTelemetry(
  panelId: string | null,
  window: TelemetryWindow = "1h",
  refreshMs = 60_000
): UseTelemetryResult {
  const [readings, setReadings] = useState<TelemetryReading[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const fetch = useCallback(() => {
    if (!panelId) return;
    abortRef.current?.abort();
    abortRef.current = new AbortController();

    setLoading(true);
    setError(null);

    api.telemetry
      .getForPanel(panelId, window)
      .then((data) => {
        setReadings(data);
        setError(null);
      })
      .catch((err: unknown) => {
        if (err instanceof Error && err.name !== "AbortError") {
          setError(err.message);
        }
      })
      .finally(() => setLoading(false));
  }, [panelId, window]);

  useEffect(() => {
    fetch();
    const interval = setInterval(fetch, refreshMs);
    return () => {
      clearInterval(interval);
      abortRef.current?.abort();
    };
  }, [fetch, refreshMs]);

  return { readings, loading, error, refresh: fetch };
}
