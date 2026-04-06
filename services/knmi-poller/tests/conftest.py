"""Shared fixtures: moto Kinesis + Secrets Manager."""
from __future__ import annotations

from collections.abc import Generator

import boto3
import pytest
from moto import mock_aws


@pytest.fixture
def aws_mocks() -> Generator[None, None, None]:
    with mock_aws():
        yield


@pytest.fixture
def kinesis_client(aws_mocks: None) -> boto3.client:  # type: ignore[type-arg]
    client = boto3.client("kinesis", region_name="eu-west-1")
    client.create_stream(StreamName="solar-weather-stream", ShardCount=1)
    return client


@pytest.fixture
def secrets_client(aws_mocks: None) -> boto3.client:  # type: ignore[type-arg]
    client = boto3.client("secretsmanager", region_name="eu-west-1")
    client.create_secret(
        Name="iot-platform/knmi-api-key",
        SecretString="test-knmi-api-key-12345",
    )
    return client
