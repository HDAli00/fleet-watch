"""init schema: vehicles, telemetry, events

Revision ID: 0001
Revises:
Create Date: 2026-04-28
"""
from __future__ import annotations

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS vehicles (
            vehicle_id  TEXT PRIMARY KEY,
            vin         TEXT NOT NULL,
            make        TEXT NOT NULL,
            model       TEXT NOT NULL,
            year        INTEGER NOT NULL,
            region      TEXT NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS telemetry (
            ts            TIMESTAMPTZ NOT NULL,
            vehicle_id    TEXT NOT NULL,
            rpm           INTEGER NOT NULL,
            speed_kph     REAL NOT NULL,
            coolant_c     REAL NOT NULL,
            oil_psi       REAL NOT NULL,
            battery_v     REAL NOT NULL,
            throttle_pct  REAL NOT NULL,
            fuel_pct      REAL NOT NULL,
            lat           DOUBLE PRECISION NOT NULL,
            lon           DOUBLE PRECISION NOT NULL,
            heading_deg   REAL NOT NULL
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS telemetry_vid_ts_desc "
        "ON telemetry (vehicle_id, ts DESC);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS telemetry_ts_desc ON telemetry (ts DESC);"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id          BIGSERIAL PRIMARY KEY,
            vehicle_id  TEXT NOT NULL,
            ts          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            kind        TEXT NOT NULL,
            severity    TEXT NOT NULL,
            message     TEXT NOT NULL
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS events_ts_desc ON events (ts DESC);")
    op.execute(
        "CREATE INDEX IF NOT EXISTS events_vid_ts_desc ON events (vehicle_id, ts DESC);"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS events;")
    op.execute("DROP TABLE IF EXISTS telemetry;")
    op.execute("DROP TABLE IF EXISTS vehicles;")
