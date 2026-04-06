"""Lambda handler: Kinesis panels/weather stream consumer.

Processes batches of IoT telemetry records:
  base64-decode → validate (Pydantic) → transform → DB upsert → S3 archive
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

from .db import get_panel_specs, open_connection, upsert_telemetry
from .models import PanelReading
from .transform import process_reading

logger = Logger(service=os.environ.get("POWERTOOLS_SERVICE_NAME", "panel-processor"))
tracer = Tracer(service=os.environ.get("POWERTOOLS_SERVICE_NAME", "panel-processor"))
log = structlog.get_logger()

_s3 = boto3.client("s3")
RAW_BUCKET = os.environ.get("RAW_BUCKET_NAME", "")


def _archive_to_s3(raw_payload: dict[str, Any], panel_id: str, ts: str) -> None:
    """Archive raw IoT JSON to S3 raw/panels/YYYY/MM/DD/{panel_id}.json."""
    if not RAW_BUCKET:
        return
    date_prefix = ts[:10].replace("-", "/")
    key = f"raw/panels/{date_prefix}/{panel_id}.json"
    _s3.put_object(
        Bucket=RAW_BUCKET,
        Key=key,
        Body=json.dumps(raw_payload),
        ContentType="application/json",
    )


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: dict[str, Any], context: object) -> dict[str, int]:
    """Process a Kinesis batch of panel telemetry records."""
    kinesis_event = KinesisStreamEvent(event)
    processed = 0
    failed = 0

    conn = open_connection()
    try:
        for record in kinesis_event.records:
            try:
                raw_data = base64.b64decode(record.kinesis.data).decode("utf-8")
                payload: dict[str, Any] = json.loads(raw_data)
                reading = PanelReading.model_validate(payload)

                specs = get_panel_specs(conn, reading.panel_id)
                if specs is None:
                    log.warning("panel.specs.missing", panel_id=reading.panel_id)
                    failed += 1
                    continue

                rated_power_w, area_m2 = specs
                processed_reading = process_reading(reading, area_m2, rated_power_w)

                upsert_telemetry(conn, processed_reading)
                _archive_to_s3(payload, reading.panel_id, str(reading.timestamp))

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
    finally:
        conn.close()

    log.info("batch.complete", processed=processed, failed=failed)
    return {"processed": processed, "failed": failed}
