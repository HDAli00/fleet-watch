"""SQLModel WeatherObs: KNMI observation table + read variant."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlmodel import Field, SQLModel


class WeatherObsBase(SQLModel):
    station_code: str = Field(index=True)  # always string e.g. "344"
    ts: datetime  # timezone-aware
    temperature_c: float | None = None
    wind_speed_ms: float | None = None
    solar_rad_wm2: float | None = None
    cloud_cover_oktas: int | None = None
    precipitation_mm: float | None = None


class WeatherObs(WeatherObsBase, table=True):
    __tablename__ = "weather_obs"

    id: int | None = Field(default=None, primary_key=True)
    raw_payload: dict[str, Any] | None = Field(default=None, sa_type=None)  # type: ignore[call-overload]


class WeatherObsRead(WeatherObsBase):
    id: int
