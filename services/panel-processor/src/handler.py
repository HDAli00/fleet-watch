"""Lambda handler: Kinesis panels/weather stream consumer.

Dispatches on STREAM_TYPE env var:
  "panels"  → validate PanelReading → transform → DB upsert → S3 archive
  "weather" → validate WeatherReading → DB upsert
"""
from __future__ import annotations

import base64
import json
import os
from typing import Any

import boto3
import structlog
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.data_classes import KinesisStreamEvent
from pydantic import ValidationError

from .db import get_panel_specs_batch, open_connection, upsert_telemetry, upsert_weather_obs
from .models import PanelReading, WeatherReading
from .transform import process_reading

logger = Logger(service=os.environ.get("POWERTOOLS_SERVICE_NAME", "panel-processor"))
tracer = Tracer(service=os.environ.get("POWERTOOLS_SERVICE_NAME", "panel-processor"))
log = structlog.get_logger()

_s3 = boto3.client("s3")
RAW_BUCKET = os.environ.get("RAW_BUCKET_NAME", "")
STREAM_TYPE = os.environ.get("STREAM_TYPE", "panels")  # "panels" | "weather"


def _archive_to_s3(raw_payload: dict[str, Any], key_prefix: str, ts: str) -> None:
    if not RAW_BUCKET:
        return
    date_prefix = ts[:10].replace("-", "/")
    key = f"raw/{key_prefix}/{date_prefix}.json"
    _s3.put_object(
        Bucket=RAW_BUCKET,
        Key=key,
        Body=json.dumps(raw_payload),
        ContentType="application/json",
    )


def _process_panels_batch(
    conn: Any,
    records: list[tuple[dict[str, Any], str]],
) -> tuple[int, int]:
    """Process a decoded batch of panel records. Returns (processed, failed)."""
    # Batch-prefetch all panel specs in one query to avoid N+1
    payloads = [p for p, _ in records]
    panel_ids = list({p["panel_id"] for p in payloads if "panel_id" in p})
    specs_map = get_panel_specs_batch(conn, panel_ids)

    processed = failed = 0
    for payload, raw_data in records:
        try:
            reading = PanelReading.model_validate(payload)
            specs = specs_map.get(reading.panel_id)
            if specs is None:
                log.warning("panel.specs.missing", panel_id=reading.panel_id)
                failed += 1
                continue
            rated_power_w, area_m2 = specs
            processed_reading = process_reading(reading, area_m2, rated_power_w)
            upsert_telemetry(conn, processed_reading)
            _archive_to_s3(payload, f"panels/{reading.panel_id}", str(reading.timestamp))
            log.info(
                "panel.processed",
                panel_id=reading.panel_id,
                anomaly=processed_reading.anomaly_flag,
                ac_power_w=processed_reading.ac_power_w,
            )
            processed += 1
        except ValidationError as exc:
            log.warning("record.invalid", error=exc.errors())
            failed += 1
        except Exception as exc:  # noqa: BLE001
            log.error("record.failed", error=str(exc))
            failed += 1
    return processed, failed


def _process_weather_batch(
    conn: Any,
    records: list[tuple[dict[str, Any], str]],
) -> tuple[int, int]:
    """Process a decoded batch of weather records. Returns (processed, failed)."""
    processed = failed = 0
    for payload, _ in records:
        try:
            reading = WeatherReading.model_validate(payload)
            upsert_weather_obs(conn, reading)
            log.info("weather.processed", station=reading.station_code)
            processed += 1
        except ValidationError as exc:
            log.warning("record.invalid", error=exc.errors())
            failed += 1
        except Exception as exc:  # noqa: BLE001
            log.error("record.failed", error=str(exc))
            failed += 1
    return processed, failed


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: dict[str, Any], context: object) -> dict[str, int]:
    """Process a Kinesis batch — dispatches on STREAM_TYPE."""
    kinesis_event = KinesisStreamEvent(event)

    decoded: list[tuple[dict[str, Any], str]] = []
    for record in kinesis_event.records:
        raw_data = base64.b64decode(record.kinesis.data).decode("utf-8")
        decoded.append((json.loads(raw_data), raw_data))

    conn = open_connection()
    try:
        if STREAM_TYPE == "weather":
            processed, failed = _process_weather_batch(conn, decoded)
        else:
            processed, failed = _process_panels_batch(conn, decoded)
    finally:
        conn.close()

    log.info("batch.complete", processed=processed, failed=failed, stream_type=STREAM_TYPE)
    return {"processed": processed, "failed": failed}
