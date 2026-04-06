"""Publish WeatherReading records to Kinesis weather-stream."""
from __future__ import annotations

import json
import os
from typing import Any

import boto3
import structlog

from .models import WeatherReading

log = structlog.get_logger()

KINESIS_MAX_BATCH = 500  # AWS Kinesis PutRecords limit


def _reading_to_record(reading: WeatherReading) -> dict[str, Any]:
    """Serialise a WeatherReading to a Kinesis PutRecords entry."""
    data = reading.model_dump(mode="json")
    return {
        "Data": json.dumps(data).encode("utf-8"),
        "PartitionKey": reading.station_code,  # string — preserves ordering per station
    }


def publish_readings(readings: list[WeatherReading], stream_name: str | None = None) -> int:
    """Publish readings to Kinesis in batches of up to 500.

    Returns the number of successfully published records.
    """
    if not readings:
        return 0

    target_stream = stream_name or os.environ["WEATHER_STREAM_NAME"]
    client = boto3.client("kinesis")
    published = 0

    # Batch into chunks of KINESIS_MAX_BATCH
    for i in range(0, len(readings), KINESIS_MAX_BATCH):
        batch = readings[i : i + KINESIS_MAX_BATCH]
        records = [_reading_to_record(r) for r in batch]

        response = client.put_records(StreamName=target_stream, Records=records)
        failed = response.get("FailedRecordCount", 0)
        batch_published = len(batch) - failed
        published += batch_published

        if failed:
            log.warning("kinesis.put.partial_failure", failed=failed, batch_size=len(batch))
        else:
            log.info("kinesis.put.success", count=batch_published, stream=target_stream)

    return published
