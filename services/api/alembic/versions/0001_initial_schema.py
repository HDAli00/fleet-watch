"""Initial schema: sites, panels, telemetry (partitioned), weather_obs

Revision ID: 0001
Revises:
Create Date: 2026-04-05 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── sites ────────────────────────────────────────────────────────────────
    op.create_table(
        "sites",
        sa.Column("site_id", sa.Text, primary_key=True),
        sa.Column("name", sa.Text, nullable=False, index=True),
        sa.Column("location", sa.Text, nullable=True),
        sa.Column("lat", sa.Float, nullable=False),
        sa.Column("lon", sa.Float, nullable=False),
        sa.Column("knmi_station", sa.Text, nullable=False),
        sa.Column("panel_count", sa.Integer, nullable=False),
        sa.Column("capacity_kwp", sa.Float, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )

    # ── panels ───────────────────────────────────────────────────────────────
    op.create_table(
        "panels",
        sa.Column("panel_id", sa.Text, primary_key=True),
        sa.Column("site_id", sa.Text, sa.ForeignKey("sites.site_id"), nullable=False, index=True),
        sa.Column("model", sa.Text, nullable=True),
        sa.Column("rated_power_w", sa.Float, nullable=False),
        sa.Column("area_m2", sa.Float, nullable=False),
        sa.Column("installed_at", sa.Date, nullable=True),
    )

    # ── telemetry (declarative partitioned — range on ts) ────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS telemetry (
            id              BIGSERIAL,
            panel_id        TEXT        NOT NULL,
            site_id         TEXT        NOT NULL,
            ts              TIMESTAMPTZ NOT NULL,
            dc_voltage_v    DOUBLE PRECISION,
            dc_current_a    DOUBLE PRECISION,
            dc_power_w      DOUBLE PRECISION,
            ac_power_w      DOUBLE PRECISION NOT NULL,
            temperature_c   DOUBLE PRECISION,
            irradiance_wm2  DOUBLE PRECISION,
            efficiency_pct  DOUBLE PRECISION,
            expected_ac_power_w DOUBLE PRECISION,
            anomaly_flag    BOOLEAN NOT NULL DEFAULT FALSE,
            status          TEXT    NOT NULL
        ) PARTITION BY RANGE (ts)
    """)
    # Default partition catches anything outside monthly partitions
    op.execute("""
        CREATE TABLE IF NOT EXISTS telemetry_default
        PARTITION OF telemetry DEFAULT
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_telemetry_panel_ts ON telemetry (panel_id, ts)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_telemetry_anomaly ON telemetry (anomaly_flag) WHERE anomaly_flag = TRUE")

    # ── weather_obs ──────────────────────────────────────────────────────────
    op.create_table(
        "weather_obs",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("station_code", sa.Text, nullable=False, index=True),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("temperature_c", sa.Float, nullable=True),
        sa.Column("wind_speed_ms", sa.Float, nullable=True),
        sa.Column("solar_rad_wm2", sa.Float, nullable=True),
        sa.Column("cloud_cover_oktas", sa.Integer, nullable=True),
        sa.Column("precipitation_mm", sa.Float, nullable=True),
        sa.Column("raw_payload", sa.JSON, nullable=True),
    )
    op.create_index("ix_weather_obs_station_ts", "weather_obs", ["station_code", "ts"])


def downgrade() -> None:
    op.drop_table("weather_obs")
    op.execute("DROP TABLE IF EXISTS telemetry_default")
    op.execute("DROP TABLE IF EXISTS telemetry")
    op.drop_table("panels")
    op.drop_table("sites")
