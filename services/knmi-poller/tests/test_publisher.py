"""Publisher tests — moto Kinesis."""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from unittest.mock import patch

from src.models import WeatherReading
from src.publisher import publish_readings

SAMPLE_READINGS = [
    WeatherReading(
        station_code="344",
        ts=datetime(2026, 4, 5, 10, 0, tzinfo=UTC),
        temperature_c=13.2,
        wind_speed_ms=5.8,
        solar_rad_wm2=380.0,
        cloud_cover_oktas=5,
        precipitation_mm=0.2,
    ),
    WeatherReading(
        station_code="260",
        ts=datetime(2026, 4, 5, 10, 0, tzinfo=UTC),
        temperature_c=11.8,
        wind_speed_ms=3.2,
        solar_rad_wm2=420.0,
        cloud_cover_oktas=3,
        precipitation_mm=0.0,
    ),
]


def test_publish_readings_success(kinesis_client: object) -> None:
    """Published record count matches input."""
    with patch.dict(
        os.environ,
        {"WEATHER_STREAM_NAME": "solar-weather-stream", "AWS_DEFAULT_REGION": "eu-west-1"},  # noqa: E501
    ):
        published = publish_readings(
            SAMPLE_READINGS, stream_name="solar-weather-stream"
        )

    assert published == 2


def test_publish_empty_list(kinesis_client: object) -> None:
    assert publish_readings([]) == 0


def test_published_records_have_correct_partition_key(kinesis_client: object) -> None:
    """Partition key must equal station_code (string)."""
    import boto3
    with patch.dict(
        os.environ,
        {"WEATHER_STREAM_NAME": "solar-weather-stream", "AWS_DEFAULT_REGION": "eu-west-1"},  # noqa: E501
    ):
        publish_readings(SAMPLE_READINGS, stream_name="solar-weather-stream")

    client = boto3.client("kinesis", region_name="eu-west-1")
    shard_id = client.describe_stream(StreamName="solar-weather-stream")[
        "StreamDescription"
    ]["Shards"][0]["ShardId"]
    shard_iterator = client.get_shard_iterator(
        StreamName="solar-weather-stream",
        ShardId=shard_id,
        ShardIteratorType="TRIM_HORIZON",
    )["ShardIterator"]
    records = client.get_records(ShardIterator=shard_iterator)["Records"]

    assert len(records) == 2
    partition_keys = {r["PartitionKey"] for r in records}
    assert "344" in partition_keys
    assert "260" in partition_keys

    # Verify station_code is string in payload
    for record in records:
        payload = json.loads(record["Data"])
        assert isinstance(payload["station_code"], str)
