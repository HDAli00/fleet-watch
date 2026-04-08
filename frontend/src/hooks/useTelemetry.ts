import { api } from "../api/client";
import type { TelemetryReading, TelemetryWindow } from "../types";
import { usePolling } from "./usePolling";

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
  const { data, loading, error, refresh } = usePolling<TelemetryReading>(
    () =>
      panelId
        ? api.telemetry.getForPanel(panelId, window)
        : Promise.resolve([]),
    [panelId, window],
    refreshMs
  );
  return { readings: data, loading, error, refresh };
}
