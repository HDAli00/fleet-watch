"""Database operations for panel telemetry using psycopg3.

Lightweight: no ORM — direct SQL for hot-path Lambda performance.
"""

from __future__ import annotations

import json
import os

import boto3
import psycopg
import structlog

from .models import ProcessedReading, WeatherReading

log = structlog.get_logger()

# Cached at module level so warm Lambda invocations skip Secrets Manager round-trips.
_cached_dsn: str | None = None


def _get_connection_string() -> str:
    global _cached_dsn
    if _cached_dsn is not None:
        return _cached_dsn
    secret_arn = os.environ["DB_SECRET_ARN"]
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_arn)
    secret = json.loads(response["SecretString"])
    _cached_dsn = (
        f"host={secret['host']} "
        f"port={secret.get('port', 5432)} "
        f"dbname={secret.get('dbname', 'solar')} "
        f"user={secret['username']} "
        f"password={secret['password']}"
    )
    return _cached_dsn


def get_panel_specs_batch(
    conn: psycopg.Connection[psycopg.rows.TupleRow],
    panel_ids: list[str],
) -> dict[str, tuple[float, float]]:
    """Fetch (rated_power_w, area_m2) for multiple panels in one query."""
    if not panel_ids:
        return {}
    with conn.cursor() as cur:
        cur.execute(
            "SELECT panel_id, rated_power_w, area_m2"
            " FROM panels WHERE panel_id = ANY(%s)",
            (panel_ids,),
        )
        rows = cur.fetchall()
    return {row[0]: (float(row[1]), float(row[2])) for row in rows}


def upsert_telemetry(
    conn: psycopg.Connection[psycopg.rows.TupleRow],
    reading: ProcessedReading,
) -> None:
    """Upsert a processed reading into the telemetry table."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO telemetry (
                panel_id, site_id, ts,
                dc_voltage_v, dc_current_a, dc_power_w,
                ac_power_w, temperature_c, irradiance_wm2,
                efficiency_pct, expected_ac_power_w,
                anomaly_flag, status
            ) VALUES (
                %(panel_id)s, %(site_id)s, %(ts)s,
                %(dc_voltage_v)s, %(dc_current_a)s, %(dc_power_w)s,
                %(ac_power_w)s, %(temperature_c)s, %(irradiance_wm2)s,
                %(efficiency_pct)s, %(expected_ac_power_w)s,
                %(anomaly_flag)s, %(status)s
            )
            ON CONFLICT DO NOTHING
            """,
            {
                "panel_id": reading.panel_id,
                "site_id": reading.site_id,
                "ts": reading.timestamp,
                "dc_voltage_v": reading.dc_voltage_v,
                "dc_current_a": reading.dc_current_a,
                "dc_power_w": reading.dc_power_w,
                "ac_power_w": reading.ac_power_w,
                "temperature_c": reading.temperature_c,
                "irradiance_wm2": reading.irradiance_wm2,
                "efficiency_pct": reading.efficiency_pct,
                "expected_ac_power_w": reading.expected_ac_power_w,
                "anomaly_flag": reading.anomaly_flag,
                "status": reading.status.value,
            },
        )
    conn.commit()


def upsert_weather_obs(
    conn: psycopg.Connection[psycopg.rows.TupleRow],
    reading: WeatherReading,
) -> None:
    """Upsert a KNMI weather observation into the weather_obs table."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO weather_obs (
                station_code, ts, temperature_c, wind_speed_ms,
                solar_rad_wm2, cloud_cover_oktas, precipitation_mm
            ) VALUES (
                %(station_code)s, %(ts)s, %(temperature_c)s, %(wind_speed_ms)s,
                %(solar_rad_wm2)s, %(cloud_cover_oktas)s, %(precipitation_mm)s
            )
            ON CONFLICT DO NOTHING
            """,
            {
                "station_code": reading.station_code,
                "ts": reading.ts,
                "temperature_c": reading.temperature_c,
                "wind_speed_ms": reading.wind_speed_ms,
                "solar_rad_wm2": reading.solar_rad_wm2,
                "cloud_cover_oktas": reading.cloud_cover_oktas,
                "precipitation_mm": reading.precipitation_mm,
            },
        )
    conn.commit()


def open_connection() -> psycopg.Connection[psycopg.rows.TupleRow]:
    """Open a new psycopg3 connection using Secrets Manager credentials."""
    return psycopg.connect(_get_connection_string())
