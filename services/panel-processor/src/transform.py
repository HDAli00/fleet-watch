"""Pure transformation functions for panel telemetry.

No I/O — all functions are deterministic and fully testable in isolation.
"""
from __future__ import annotations

from .models import PanelReading, ProcessedReading

# Named constants — never magic numbers
ANOMALY_THRESHOLD: float = 0.60  # ac_power < 60% of expected → anomaly (strict <)
STC_IRRADIANCE_WM2: float = 1000.0  # Standard Test Conditions reference irradiance


def compute_dc_power(voltage: float, current: float) -> float:
    """DC power in watts: V × A."""
    return voltage * current


def compute_efficiency(
    ac_power_w: float,
    irradiance_wm2: float,
    area_m2: float,
) -> float:
    """Panel efficiency as percentage.

    Returns 0.0 when irradiance is zero or negative to prevent division by zero.
    """
    if irradiance_wm2 <= 0:
        return 0.0
    incident_power = irradiance_wm2 * area_m2
    return (ac_power_w / incident_power) * 100.0


def compute_expected_ac_power(
    irradiance_wm2: float,
    rated_power_w: float,
    stc_irradiance: float = STC_IRRADIANCE_WM2,
) -> float:
    """Expected AC output based on irradiance vs STC rated power."""
    return (irradiance_wm2 / stc_irradiance) * rated_power_w


def is_anomaly(ac_power_w: float, expected_ac_power_w: float) -> bool:
    """True if output is below ANOMALY_THRESHOLD of irradiance-adjusted expectation.

    Uses strict < (not <=): 60.0% is not anomalous; 59.9% is.
    Returns False when expected_ac_power_w is zero (no irradiance → no expectation).
    """
    if expected_ac_power_w <= 0:
        return False
    return ac_power_w < (expected_ac_power_w * ANOMALY_THRESHOLD)


def process_reading(
    reading: PanelReading,
    panel_area_m2: float,
    rated_power_w: float,
) -> ProcessedReading:
    """Transform raw IoT reading into enriched ProcessedReading."""
    dc_power = compute_dc_power(reading.dc_voltage_v, reading.dc_current_a)
    efficiency = compute_efficiency(
        reading.ac_power_w, reading.irradiance_wm2, panel_area_m2
    )
    expected = compute_expected_ac_power(reading.irradiance_wm2, rated_power_w)
    anomaly = is_anomaly(reading.ac_power_w, expected)

    return ProcessedReading(
        panel_id=reading.panel_id,
        site_id=reading.site_id,
        timestamp=reading.timestamp,
        dc_voltage_v=reading.dc_voltage_v,
        dc_current_a=reading.dc_current_a,
        dc_power_w=dc_power,
        ac_power_w=reading.ac_power_w,
        temperature_c=reading.temperature_c,
        irradiance_wm2=reading.irradiance_wm2,
        efficiency_pct=efficiency,
        expected_ac_power_w=expected,
        anomaly_flag=anomaly,
        status=reading.status,
    )
