import { api } from "../api/client";
import type { TelemetryReading, TelemetryWindow } from "../types";
import { usePolling } from "./usePolling";

interface UseAnomaliesResult {
  anomalies: TelemetryReading[];
  loading: boolean;
  error: string | null;
}

export function useAnomalies(
  window: TelemetryWindow = "1h",
  refreshMs = 30_000
): UseAnomaliesResult {
  const { data, loading, error } = usePolling<TelemetryReading>(
    () => api.telemetry.recentAnomalies(window),
    [window],
    refreshMs
  );
  return { anomalies: data, loading, error };
}
