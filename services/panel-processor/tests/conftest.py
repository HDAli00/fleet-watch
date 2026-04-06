"""Shared fixtures: testcontainers Postgres + moto AWS mocks."""
from __future__ import annotations

import json
from collections.abc import Generator

import boto3
import psycopg
import pytest
from moto import mock_aws
from testcontainers.postgres import PostgresContainer

# Minimal schema needed for Lambda integration tests
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sites (
    site_id     TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    knmi_station TEXT
);

CREATE TABLE IF NOT EXISTS panels (
    panel_id     TEXT PRIMARY KEY,
    site_id      TEXT REFERENCES sites(site_id),
    model        TEXT,
    rated_power_w FLOAT NOT NULL,
    area_m2      FLOAT NOT NULL
);

CREATE TABLE IF NOT EXISTS telemetry (
    id              BIGSERIAL,
    panel_id        TEXT,
    site_id         TEXT,
    ts              TIMESTAMPTZ NOT NULL,
    dc_voltage_v    FLOAT,
    dc_current_a    FLOAT,
    dc_power_w      FLOAT,
    ac_power_w      FLOAT,
    temperature_c   FLOAT,
    irradiance_wm2  FLOAT,
    efficiency_pct  FLOAT,
    expected_ac_power_w FLOAT,
    anomaly_flag    BOOLEAN DEFAULT FALSE,
    status          TEXT
) PARTITION BY RANGE (ts);

-- Create initial partition for testing
CREATE TABLE telemetry_default PARTITION OF telemetry DEFAULT;
"""


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    with PostgresContainer("postgres:15-alpine") as pg:
        yield pg


@pytest.fixture(scope="session")
def pg_dsn(postgres_container: PostgresContainer) -> str:
    dsn = postgres_container.get_connection_url().replace("postgresql+psycopg2://", "")
    with psycopg.connect(f"postgresql://{dsn}") as conn:
        conn.execute(SCHEMA_SQL)
        # Seed test data
        conn.execute(
            "INSERT INTO sites (site_id, name, knmi_station) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
            ("site-test-01", "Test Site", "344"),
        )
        conn.execute(
            """INSERT INTO panels (panel_id, site_id, model, rated_power_w, area_m2)
               VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
            ("panel-NL-001", "site-test-01", "Test Panel", 440.0, 1.72),
        )
        conn.commit()
    return f"postgresql://{dsn}"


@pytest.fixture
def kinesis_client() -> Generator[boto3.client, None, None]:  # type: ignore[type-arg]
    with mock_aws():
        client = boto3.client("kinesis", region_name="eu-west-1")
        client.create_stream(StreamName="solar-panels-stream", ShardCount=1)
        yield client


@pytest.fixture
def secrets_client(pg_dsn: str) -> Generator[boto3.client, None, None]:  # type: ignore[type-arg]
    """Mocked Secrets Manager with DB credentials."""
    with mock_aws():
        client = boto3.client("secretsmanager", region_name="eu-west-1")
        # Parse DSN to construct secret JSON
        # postgresql://user:pass@host:port/dbname
        import re
        match = re.match(r"postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", pg_dsn)
        if match:
            user, password, host, port, dbname = match.groups()
        else:
            user, password, host, port, dbname = "test", "test", "localhost", "5432", "test"

        client.create_secret(
            Name="test-db-secret",
            SecretString=json.dumps({
                "username": user,
                "password": password,
                "host": host,
                "port": int(port),
                "dbname": dbname,
            }),
        )
        yield client
