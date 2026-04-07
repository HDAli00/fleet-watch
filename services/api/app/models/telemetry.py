"""SQLModel Telemetry: partitioned time-series table + read variant."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import DateTime as SADateTime
from sqlmodel import Field, SQLModel


class TelemetryBase(SQLModel):
    panel_id: str = Field(index=True)
    site_id: str
    ts: datetime  # timezone-aware TIMESTAMPTZ
    dc_voltage_v: float | None = None
    dc_current_a: float | None = None
    dc_power_w: float | None = None
    ac_power_w: float
    temperature_c: float | None = None
    irradiance_wm2: float | None = None
    efficiency_pct: float | None = None
    expected_ac_power_w: float | None = None
    anomaly_flag: bool = False
    # Literal unsupported by SQLModel table models
    status: str  # "ok" | "warning" | "error" | "offline"


class Telemetry(TelemetryBase, table=True):
    __tablename__ = "telemetry"
    # No postgresql_partition_by here — partitioning is handled by Alembic
    # raw DDL in production; SQLModel.metadata.create_all (used in tests)
    # creates a plain table which avoids the "PK must include partition key" error.

    ts: datetime = Field(
        sa_column=Column("ts", SADateTime(timezone=True), nullable=False)
    )
    id: int | None = Field(default=None, primary_key=True)


class TelemetryRead(TelemetryBase):
    id: int
