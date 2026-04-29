from __future__ import annotations

from dataclasses import dataclass

from .models import Severity, TelemetryIn


@dataclass(frozen=True)
class Alert:
    kind: str
    severity: Severity
    message: str


def evaluate(reading: TelemetryIn) -> list[Alert]:
    alerts: list[Alert] = []

    if reading.coolant_c >= 110:
        alerts.append(
            Alert(
                kind="coolant_overheat",
                severity="critical",
                message=f"coolant {reading.coolant_c:.1f}°C exceeds 110°C",
            )
        )
    elif reading.coolant_c >= 100:
        alerts.append(
            Alert(
                kind="coolant_warm",
                severity="warn",
                message=f"coolant {reading.coolant_c:.1f}°C above 100°C",
            )
        )

    if reading.battery_v < 11.5:
        alerts.append(
            Alert(
                kind="battery_low",
                severity="critical",
                message=f"battery {reading.battery_v:.2f}V under 11.5V",
            )
        )
    elif reading.battery_v < 12.0:
        alerts.append(
            Alert(
                kind="battery_weak",
                severity="warn",
                message=f"battery {reading.battery_v:.2f}V under 12.0V",
            )
        )

    if reading.oil_psi < 15:
        alerts.append(
            Alert(
                kind="oil_pressure_low",
                severity="critical",
                message=f"oil pressure {reading.oil_psi:.1f}psi under 15psi",
            )
        )

    if reading.rpm > 7500:
        alerts.append(
            Alert(
                kind="rpm_redline",
                severity="warn",
                message=f"rpm {reading.rpm} above 7500",
            )
        )

    return alerts
