"""Database operations for panel telemetry using psycopg3.

Lightweight: no ORM — direct SQL for hot-path Lambda performance.
"""
from __future__ import annotations

import json
import os

import boto3
import psycopg
import structlog

from .models import ProcessedReading

log = structlog.get_logger()


def _get_connection_string() -> str:
    """Resolve DB credentials from Secrets Manager at runtime."""
    secret_arn = os.environ["DB_SECRET_ARN"]
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_arn)
    secret = json.loads(response["SecretString"])
    return (
        f"host={secret['host']} "
        f"port={secret.get('port', 5432)} "
        f"dbname={secret.get('dbname', 'solar')} "
        f"user={secret['username']} "
        f"password={secret['password']}"
    )


def get_panel_specs(
    conn: psycopg.Connection[psycopg.rows.TupleRow],
    panel_id: str,
) -> tuple[float, float] | None:
    """Fetch (rated_power_w, area_m2) for a panel. Returns None if not found."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT rated_power_w, area_m2 FROM panels WHERE panel_id = %s",
            (panel_id,),
        )
        row = cur.fetchone()
    if row is None:
        log.warning("panel.not_found", panel_id=panel_id)
        return None
    return float(row[0]), float(row[1])


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


def open_connection() -> psycopg.Connection[psycopg.rows.TupleRow]:
    """Open a new psycopg3 connection using Secrets Manager credentials."""
    return psycopg.connect(_get_connection_string())
