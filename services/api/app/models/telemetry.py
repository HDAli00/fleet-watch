"""SQLModel Telemetry: partitioned time-series table + read variant."""

from __future__ import annotations

from datetime import datetime

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
    __table_args__ = {"postgresql_partition_by": "RANGE (ts)"}

    id: int | None = Field(default=None, primary_key=True)


class TelemetryRead(TelemetryBase):
    id: int
