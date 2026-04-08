"""Pydantic v2 models for KNMI weather observations."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# KNMI station codes are always strings — never compare as int
KNMI_STATIONS: dict[str, str] = {
    "240": "Amsterdam Schiphol",
    "260": "De Bilt",
    "344": "Rotterdam",
    "370": "Eindhoven",
    "380": "Maastricht",
}


class KNMIStation(BaseModel):
    """A KNMI weather station."""

    model_config = ConfigDict(frozen=True)

    code: str  # always string, e.g. "344" not 344
    name: str


class WeatherReading(BaseModel):
    """Parsed KNMI 10-minute weather observation."""

    model_config = ConfigDict(frozen=True)

    station_code: str  # always string
    ts: datetime  # timezone-aware
    temperature_c: float
    wind_speed_ms: float = Field(ge=0)
    solar_rad_wm2: float = Field(ge=0)
    cloud_cover_oktas: int = Field(ge=0, le=8)
    precipitation_mm: float = Field(ge=0)
