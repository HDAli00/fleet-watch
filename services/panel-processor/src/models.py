"""Pydantic v2 models for panel telemetry processing."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class PanelStatus(StrEnum):
    """Valid panel operational states."""

    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    OFFLINE = "offline"


class PanelReading(BaseModel):
    """Raw IoT telemetry payload received from Kinesis."""

    # no strict=True — JSON data always arrives as strings from Kinesis
    model_config = ConfigDict(frozen=True)

    panel_id: str
    site_id: str
    timestamp: datetime
    dc_voltage_v: float = Field(ge=0)
    dc_current_a: float = Field(ge=0)
    ac_power_w: float = Field(ge=0)
    temperature_c: float
    irradiance_wm2: float = Field(ge=0)
    efficiency_pct: float = Field(ge=0)
    status: PanelStatus


class WeatherReading(BaseModel):
    """KNMI weather observation received from the weather Kinesis stream."""

    model_config = ConfigDict(frozen=True)

    station_code: str  # always string e.g. "344"
    ts: datetime
    temperature_c: float
    wind_speed_ms: float = Field(ge=0)
    solar_rad_wm2: float = Field(ge=0)
    cloud_cover_oktas: int = Field(ge=0, le=8)
    precipitation_mm: float = Field(ge=0)


class ProcessedReading(BaseModel):
    """Enriched reading after transform — written to telemetry table."""

    model_config = ConfigDict(frozen=True)

    panel_id: str
    site_id: str
    timestamp: datetime
    dc_voltage_v: float
    dc_current_a: float
    dc_power_w: float
    ac_power_w: float
    temperature_c: float
    irradiance_wm2: float
    efficiency_pct: float
    expected_ac_power_w: float
    anomaly_flag: bool
    status: PanelStatus
