"""Pure anomaly detection function — mirrors Lambda transform logic."""
from __future__ import annotations

ANOMALY_THRESHOLD: float = 0.60  # strict <: 60.0% is NOT anomalous; 59.9% IS


def is_anomaly(ac_power_w: float, expected_ac_power_w: float) -> bool:
    """True if ac_power_w is below ANOMALY_THRESHOLD of expected output.

    Uses strict < (not <=) per ADR-004:
    - 60.0% → False (not anomalous)
    - 59.9% → True  (anomalous)
    Returns False when expected_ac_power_w is zero (no irradiance → no expectation).
    """
    if expected_ac_power_w <= 0:
        return False
    return ac_power_w < (expected_ac_power_w * ANOMALY_THRESHOLD)
