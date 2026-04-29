from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Severity = Literal["info", "warn", "critical"]


class TelemetryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vehicle_id: str = Field(min_length=1, max_length=64)
    ts: datetime
    rpm: int = Field(ge=0, le=20000)
    speed_kph: float = Field(ge=0, le=400)
    coolant_c: float = Field(ge=-40, le=200)
    oil_psi: float = Field(ge=0, le=200)
    battery_v: float = Field(ge=0, le=20)
    throttle_pct: float = Field(ge=0, le=100)
    fuel_pct: float = Field(ge=0, le=100)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    heading_deg: float = Field(ge=0, lt=360)


class VehicleSummary(BaseModel):
    vehicle_id: str
    make: str
    model: str
    year: int
    region: str
    status: Literal["ok", "warn", "critical", "offline"]
    last_seen: datetime | None
    last_lat: float | None
    last_lon: float | None
    last_speed_kph: float | None
    last_coolant_c: float | None
    last_battery_v: float | None


class HistoryPoint(BaseModel):
    ts: datetime
    rpm: int
    speed_kph: float
    coolant_c: float
    oil_psi: float
    battery_v: float
    throttle_pct: float
    fuel_pct: float


class VehicleHistory(BaseModel):
    vehicle_id: str
    window_minutes: int
    points: list[HistoryPoint]


class FleetEvent(BaseModel):
    id: int
    vehicle_id: str
    ts: datetime
    kind: str
    severity: Severity
    message: str


class FleetKpis(BaseModel):
    ts: datetime
    active_vehicles: int
    msgs_per_sec: float
    alerts_per_min: float
    p95_ingest_ms: float
    leader_instance: str | None


class FleetSnapshot(BaseModel):
    kpis: FleetKpis
    positions: list[VehiclePosition]


class VehiclePosition(BaseModel):
    vehicle_id: str
    lat: float
    lon: float
    heading_deg: float
    speed_kph: float
    status: Literal["ok", "warn", "critical", "offline"]


FleetSnapshot.model_rebuild()


class HealthReport(BaseModel):
    db: Literal["ok", "down"]
    redis: Literal["ok", "down"]
    leader: bool
    instance: str
