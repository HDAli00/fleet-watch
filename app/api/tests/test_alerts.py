from __future__ import annotations

from datetime import UTC, datetime

from app.alerts import evaluate
from app.models import TelemetryIn


def _reading(**overrides: float | int | str) -> TelemetryIn:
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
    return TelemetryIn(**base)  # type: ignore[arg-type]


def test_no_alerts_for_normal_reading() -> None:
    assert evaluate(_reading()) == []


def test_coolant_critical_above_110() -> None:
    alerts = evaluate(_reading(coolant_c=112.0))
    assert any(a.kind == "coolant_overheat" and a.severity == "critical" for a in alerts)


def test_coolant_warn_between_100_and_110() -> None:
    alerts = evaluate(_reading(coolant_c=105.0))
    assert any(a.kind == "coolant_warm" and a.severity == "warn" for a in alerts)


def test_battery_low_critical() -> None:
    alerts = evaluate(_reading(battery_v=11.0))
    assert any(a.kind == "battery_low" and a.severity == "critical" for a in alerts)


def test_battery_weak_warn() -> None:
    alerts = evaluate(_reading(battery_v=11.8))
    assert any(a.kind == "battery_weak" and a.severity == "warn" for a in alerts)


def test_oil_pressure_low_critical() -> None:
    alerts = evaluate(_reading(oil_psi=10.0))
    assert any(a.kind == "oil_pressure_low" and a.severity == "critical" for a in alerts)


def test_rpm_redline_warn() -> None:
    alerts = evaluate(_reading(rpm=8000))
    assert any(a.kind == "rpm_redline" and a.severity == "warn" for a in alerts)


def test_multiple_simultaneous_alerts() -> None:
    alerts = evaluate(_reading(coolant_c=115.0, battery_v=11.0))
    kinds = {a.kind for a in alerts}
    assert {"coolant_overheat", "battery_low"}.issubset(kinds)
