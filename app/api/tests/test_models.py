from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models import TelemetryIn


def _kwargs(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "vehicle_id": "v-0001",
        "ts": datetime(2026, 4, 28, 0, 0, 0, tzinfo=UTC),
        "rpm": 2000,
        "speed_kph": 60.0,
        "coolant_c": 90.0,
        "oil_psi": 40.0,
        "battery_v": 13.6,
        "throttle_pct": 30.0,
        "fuel_pct": 70.0,
        "lat": 52.0,
        "lon": 4.9,
        "heading_deg": 90.0,
    }
    base.update(overrides)
    return base


def test_telemetry_accepts_valid_reading() -> None:
    TelemetryIn(**_kwargs())  # type: ignore[arg-type]


def test_telemetry_rejects_lat_out_of_range() -> None:
    with pytest.raises(ValidationError):
        TelemetryIn(**_kwargs(lat=120.0))  # type: ignore[arg-type]


def test_telemetry_rejects_negative_speed() -> None:
    with pytest.raises(ValidationError):
        TelemetryIn(**_kwargs(speed_kph=-1.0))  # type: ignore[arg-type]


def test_telemetry_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        TelemetryIn(**_kwargs(extra_field="x"))  # type: ignore[arg-type]


def test_telemetry_rejects_heading_360() -> None:
    with pytest.raises(ValidationError):
        TelemetryIn(**_kwargs(heading_deg=360.0))  # type: ignore[arg-type]
