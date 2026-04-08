/** Domain types — mirrored from FastAPI response schemas. */

export interface Site {
  site_id: string;
  name: string;
  location: string | null;
  lat: number;
  lon: number;
  knmi_station: string; // always string — e.g. "344", never 344
  panel_count: number;
  capacity_kwp: number;
  created_at: string; // ISO8601
}

export interface Panel {
  panel_id: string;
  site_id: string;
  model: string | null;
  rated_power_w: number;
  area_m2: number;
  installed_at: string | null; // ISO date
}

export interface TelemetryReading {
  id: number;
  panel_id: string;
  site_id: string;
  ts: string; // ISO8601 with timezone
  dc_voltage_v: number | null;
  dc_current_a: number | null;
  dc_power_w: number | null;
  ac_power_w: number;
  temperature_c: number | null;
  irradiance_wm2: number | null;
  efficiency_pct: number | null;
  expected_ac_power_w: number | null;
  anomaly_flag: boolean;
  status: "ok" | "warning" | "error" | "offline";
}

export interface WeatherObs {
  id: number;
  station_code: string; // always string — "344" not 344
  ts: string;
  temperature_c: number | null;
  wind_speed_ms: number | null;
  solar_rad_wm2: number | null;
  cloud_cover_oktas: number | null;
  precipitation_mm: number | null;
}

export interface CorrelationResult {
  site_id: string;
  station_code: string;
  window: string;
  r2: number;
  sample_count: number;
}

export type TelemetryWindow = "1h" | "6h" | "24h" | "7d";
