"""Integration tests for Lambda handler using real Postgres and moto."""
from __future__ import annotations

import base64
import json
import os
from typing import Any
from unittest.mock import patch

import psycopg
import pytest

SAMPLE_READING: dict[str, Any] = {
    "panel_id": "panel-NL-001",
    "site_id": "site-test-01",
    "timestamp": "2026-04-05T10:00:00+00:00",
    "dc_voltage_v": 38.4,
    "dc_current_a": 8.2,
    "ac_power_w": 312.5,
    "temperature_c": 44.1,
    "irradiance_wm2": 680.0,
    "efficiency_pct": 18.7,
    "status": "ok",
}

ANOMALY_READING: dict[str, Any] = {
    **SAMPLE_READING,
    "ac_power_w": 100.0,  # far below 60% of expected ~299W → anomaly
    "timestamp": "2026-04-05T11:00:00+00:00",
}


def _make_kinesis_event(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "Records": [
            {
                "kinesis": {
                    "data": base64.b64encode(
                        json.dumps(r).encode()
                    ).decode(),
                    "sequenceNumber": f"seq-{i}",
                    "partitionKey": r["panel_id"],
                    "approximateArrivalTimestamp": 1000.0,
                    "kinesisSchemaVersion": "1.0",
                },
                "eventSource": "aws:kinesis",
                "eventID": f"shardId-000000000000:seq-{i}",
                "invokeIdentityArn": "arn:aws:iam::123:role/test",
                "eventVersion": "1.0",
                "eventName": "aws:kinesis:record",
                "eventSourceARN": "arn:aws:kinesis:eu-west-1:123:stream/solar-panels-stream",
                "awsRegion": "eu-west-1",
            }
            for i, r in enumerate(records)
        ]
    }


@pytest.mark.usefixtures("secrets_client")
def test_handler_processes_valid_record(pg_dsn: str) -> None:
    """A valid panel reading is written to the telemetry table."""
    event = _make_kinesis_event([SAMPLE_READING])

    with (
        patch.dict(os.environ, {
            "DB_SECRET_ARN": "test-db-secret",
            "RAW_BUCKET_NAME": "",
            "AWS_DEFAULT_REGION": "eu-west-1",
        }),
        patch("src.db._get_connection_string", return_value=pg_dsn),
    ):
        from src.handler import handler
        result = handler(event, object())

    assert result["processed"] == 1
    assert result["failed"] == 0

    with psycopg.connect(pg_dsn) as conn:
        row = conn.execute(
            "SELECT ac_power_w, anomaly_flag FROM telemetry WHERE panel_id = %s",
            ("panel-NL-001",),
        ).fetchone()
    assert row is not None
    assert float(row[0]) == pytest.approx(312.5)
    assert row[1] is False  # normal output, not anomalous


@pytest.mark.usefixtures("secrets_client")
def test_handler_sets_anomaly_flag(pg_dsn: str) -> None:
    """A reading with very low output sets anomaly_flag = True."""
    event = _make_kinesis_event([ANOMALY_READING])

    with (
        patch.dict(os.environ, {
            "DB_SECRET_ARN": "test-db-secret",
            "RAW_BUCKET_NAME": "",
            "AWS_DEFAULT_REGION": "eu-west-1",
        }),
        patch("src.db._get_connection_string", return_value=pg_dsn),
    ):
        from src.handler import handler
        result = handler(event, object())

    assert result["processed"] == 1

    with psycopg.connect(pg_dsn) as conn:
        row = conn.execute(
            "SELECT anomaly_flag FROM telemetry WHERE panel_id = %s AND ac_power_w < 200",
            ("panel-NL-001",),
        ).fetchone()
    assert row is not None
    assert row[0] is True


@pytest.mark.usefixtures("secrets_client")
def test_handler_skips_invalid_record(pg_dsn: str) -> None:
    """An invalid record increments failed count without crashing the batch."""
    bad_record: dict[str, Any] = {"invalid": "payload"}
    event = _make_kinesis_event([bad_record, SAMPLE_READING])

    with (
        patch.dict(os.environ, {
            "DB_SECRET_ARN": "test-db-secret",
            "RAW_BUCKET_NAME": "",
            "AWS_DEFAULT_REGION": "eu-west-1",
        }),
        patch("src.db._get_connection_string", return_value=pg_dsn),
    ):
        from src.handler import handler
        result = handler(event, object())

    assert result["failed"] == 1
    assert result["processed"] == 1
