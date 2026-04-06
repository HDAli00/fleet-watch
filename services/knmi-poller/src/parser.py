"""Parse KNMI observation JSON → list[WeatherReading].

Only extracts stations we care about (defined in KNMI_STATIONS).
100% branch coverage required — all KNMI field types parsed.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from pydantic import ValidationError

from .models import KNMI_STATIONS, WeatherReading

log = structlog.get_logger()


def _parse_ts(ts_str: str) -> datetime:
    """Parse ISO8601 timestamp and ensure timezone-aware."""
    dt = datetime.fromisoformat(ts_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _safe_float(value: object, default: float = 0.0) -> float:
    """Safely convert a value to float, returning default on failure."""
    if value is None:
        return default
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _safe_int(value: object, default: int = 0) -> int:
    """Safely convert a value to int, clamped to valid oktas range 0-8."""
    if value is None:
        return default
    try:
        result = int(float(value))  # type: ignore[arg-type]
        return max(0, min(8, result))  # clamp to valid KNMI oktas range
    except (TypeError, ValueError):
        return default


def parse_knmi_response(raw: dict[object, object]) -> list[WeatherReading]:
    """Extract WeatherReading records for our target stations.

    KNMI JSON structure:
    {
      "stations": [
        {
          "stationid": "344",
          "timestamp": "2026-04-05T10:00:00+00:00",
          "T": 12.3,           # temperature °C (× 0.1 in some formats)
          "FF": 5.2,            # wind speed m/s
          "Q": 320.0,           # global radiation W/m²
          "N": 4,               # cloud cover oktas
          "RH": 0.0             # precipitation mm
        },
        ...
      ]
    }
    """
    readings: list[WeatherReading] = []
    stations = raw.get("stations", [])

    if not isinstance(stations, list):
        log.warning("knmi.parse.no_stations")
        return readings

    for station in stations:
        if not isinstance(station, dict):
            continue

        station_code = str(station.get("stationid", ""))
        if station_code not in KNMI_STATIONS:
            continue  # skip stations we don't track

        ts_raw = station.get("timestamp", "")
        if not ts_raw:
            log.warning("knmi.parse.missing_timestamp", station=station_code)
            continue

        try:
            ts = _parse_ts(str(ts_raw))
            reading = WeatherReading(
                station_code=station_code,
                ts=ts,
                temperature_c=_safe_float(station.get("T")),
                wind_speed_ms=_safe_float(station.get("FF")),
                solar_rad_wm2=_safe_float(station.get("Q")),
                cloud_cover_oktas=_safe_int(station.get("N")),
                precipitation_mm=_safe_float(station.get("RH")),
            )
            readings.append(reading)
        except (ValidationError, ValueError) as exc:
            log.warning("knmi.parse.invalid", station=station_code, error=str(exc))

    log.info("knmi.parse.complete", count=len(readings))
    return readings
