export type VehicleStatus = "ok" | "warn" | "critical" | "offline";

export interface VehicleSummary {
  vehicle_id: string;
  make: string;
  model: string;
  year: number;
  region: string;
  status: VehicleStatus;
  last_seen: string | null;
  last_lat: number | null;
  last_lon: number | null;
  last_speed_kph: number | null;
  last_coolant_c: number | null;
  last_battery_v: number | null;
}

export interface HistoryPoint {
  ts: string;
  rpm: number;
  speed_kph: number;
  coolant_c: number;
  oil_psi: number;
  battery_v: number;
  throttle_pct: number;
  fuel_pct: number;
}

export interface VehicleHistory {
  vehicle_id: string;
  window_minutes: number;
  points: HistoryPoint[];
}

export interface VehiclePosition {
  vehicle_id: string;
  lat: number;
  lon: number;
  heading_deg: number;
  speed_kph: number;
  coolant_c?: number;
  battery_v?: number;
  status?: VehicleStatus;
}

export interface FleetEvent {
  id: number;
  vehicle_id: string;
  ts: string;
  kind: string;
  severity: "info" | "warn" | "critical";
  message: string;
}

const BASE = "/api";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} -> ${res.status}`);
  return (await res.json()) as T;
}

export const api = {
  vehicles: (limit?: number): Promise<VehicleSummary[]> =>
    get(`/vehicles${limit ? `?limit=${limit}` : ""}`),
  vehicle: (id: string): Promise<VehicleSummary> => get(`/vehicles/${id}`),
  history: (id: string, windowMinutes = 60): Promise<VehicleHistory> =>
    get(`/vehicles/${id}/history?window_minutes=${windowMinutes}`),
  events: (limit = 100, severity?: string): Promise<FleetEvent[]> =>
    get(`/events?limit=${limit}${severity ? `&severity=${severity}` : ""}`),
};
