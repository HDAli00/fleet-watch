/**
 * Typed API client — all fetch calls go through here.
 * BASE_URL resolves to the Vite dev proxy (/api) or the real ALB URL
 * set via VITE_API_BASE_URL at build time.
 */
import type {
  CorrelationResult,
  Panel,
  Site,
  TelemetryReading,
  TelemetryWindow,
  WeatherObs,
} from "../types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function apiFetch<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${BASE_URL}${path}`, window.location.href);
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  }
  const res = await fetch(url.toString());
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text()}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  sites: {
    list: () => apiFetch<Site[]>("/sites"),
    get: (siteId: string) => apiFetch<Site>(`/sites/${siteId}`),
  },

  panels: {
    list: (siteId?: string) =>
      apiFetch<Panel[]>("/panels", siteId ? { site_id: siteId } : undefined),
    get: (panelId: string) => apiFetch<Panel>(`/panels/${panelId}`),
  },

  telemetry: {
    getForPanel: (panelId: string, window: TelemetryWindow) =>
      apiFetch<TelemetryReading[]>(`/telemetry/${panelId}`, { window }),
    recentAnomalies: (window: TelemetryWindow = "1h") =>
      apiFetch<TelemetryReading[]>("/telemetry/anomalies/recent", { window }),
    correlation: (siteId: string, window: TelemetryWindow = "24h") =>
      apiFetch<CorrelationResult>(`/telemetry/correlation/${siteId}`, { window }),
  },

  weather: {
    getStation: (stationCode: string, hours = 24) =>
      apiFetch<WeatherObs[]>(`/weather/${stationCode}`, { hours: String(hours) }),
  },
};
