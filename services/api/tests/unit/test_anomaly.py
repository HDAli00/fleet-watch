"""Unit tests for anomaly detection — mirrors Lambda transform tests."""
from __future__ import annotations

import pytest

from app.services.anomaly import ANOMALY_THRESHOLD, is_anomaly


@pytest.mark.parametrize(
    ("ac_power", "expected_power", "should_flag"),
    [
        (200.0, 400.0, True),    # 50% → anomaly
        (239.9, 400.0, True),    # 59.975% → anomaly (strict <)
        (240.0, 400.0, False),   # exactly 60% → NOT anomaly
        (260.0, 400.0, False),   # 65% → ok
        (400.0, 400.0, False),   # 100% → ok
        (0.0, 0.0, False),       # zero expected → no judgement
        (100.0, 0.0, False),     # zero expected → no judgement
        (100.0, -1.0, False),    # negative expected → no judgement
    ],
)
def test_is_anomaly(ac_power: float, expected_power: float, should_flag: bool) -> None:
    assert is_anomaly(ac_power, expected_power) == should_flag


def test_threshold_constant_unchanged() -> None:
    """Guard against accidental threshold changes — affects anomaly detection SLA."""
    assert ANOMALY_THRESHOLD == 0.60
