"""Unit tests for pure transform functions — no mocks, no I/O."""
from __future__ import annotations

import pytest

from src.transform import (
    ANOMALY_THRESHOLD,
    STC_IRRADIANCE_WM2,
    compute_dc_power,
    compute_efficiency,
    compute_expected_ac_power,
    is_anomaly,
)


class TestComputeDcPower:
    def test_normal_values(self) -> None:
        assert compute_dc_power(38.4, 8.2) == pytest.approx(314.88)

    def test_zero_voltage(self) -> None:
        assert compute_dc_power(0.0, 8.2) == 0.0

    def test_zero_current(self) -> None:
        assert compute_dc_power(38.4, 0.0) == 0.0


class TestComputeEfficiency:
    @pytest.mark.parametrize(
        "ac_power, irradiance, area, expected",
        [
            (300.0, 800.0, 1.72, pytest.approx(21.8, rel=1e-2)),
            (440.0, 1000.0, 1.72, pytest.approx(25.58, rel=1e-2)),
            (0.0, 800.0, 1.72, pytest.approx(0.0)),
        ],
    )
    def test_normal(
        self, ac_power: float, irradiance: float, area: float, expected: object
    ) -> None:
        assert compute_efficiency(ac_power, irradiance, area) == expected

    def test_zero_irradiance_returns_zero(self) -> None:
        """Guard against division by zero when irradiance is 0."""
        assert compute_efficiency(300.0, 0.0, 1.72) == 0.0

    def test_negative_irradiance_returns_zero(self) -> None:
        assert compute_efficiency(300.0, -1.0, 1.72) == 0.0


class TestComputeExpectedAcPower:
    def test_full_irradiance(self) -> None:
        # At STC (1000 W/m²), expected = rated_power_w
        assert compute_expected_ac_power(1000.0, 440.0) == pytest.approx(440.0)

    def test_half_irradiance(self) -> None:
        assert compute_expected_ac_power(500.0, 440.0) == pytest.approx(220.0)

    def test_zero_irradiance(self) -> None:
        assert compute_expected_ac_power(0.0, 440.0) == pytest.approx(0.0)

    def test_custom_stc(self) -> None:
        assert compute_expected_ac_power(800.0, 400.0, stc_irradiance=800.0) == pytest.approx(400.0)


class TestProcessReading:
    def test_normal_reading_no_anomaly(self) -> None:
        from src.models import PanelReading, PanelStatus
        from src.transform import process_reading
        from datetime import datetime, timezone

        reading = PanelReading(
            panel_id="panel-NL-001",
            site_id="site-test-01",
            timestamp=datetime(2026, 4, 5, 10, 0, tzinfo=timezone.utc),
            dc_voltage_v=38.4,
            dc_current_a=8.2,
            ac_power_w=312.5,
            temperature_c=44.1,
            irradiance_wm2=680.0,
            efficiency_pct=18.7,
            status=PanelStatus.OK,
        )
        result = process_reading(reading, panel_area_m2=1.72, rated_power_w=440.0)

        assert result.dc_power_w == pytest.approx(38.4 * 8.2)
        assert result.expected_ac_power_w == pytest.approx(680.0 / 1000.0 * 440.0)
        assert result.anomaly_flag is False
        assert result.panel_id == "panel-NL-001"

    def test_anomaly_reading(self) -> None:
        from src.models import PanelReading, PanelStatus
        from src.transform import process_reading
        from datetime import datetime, timezone

        reading = PanelReading(
            panel_id="panel-NL-001",
            site_id="site-test-01",
            timestamp=datetime(2026, 4, 5, 11, 0, tzinfo=timezone.utc),
            dc_voltage_v=38.4,
            dc_current_a=8.2,
            ac_power_w=50.0,  # very low → anomaly
            temperature_c=44.1,
            irradiance_wm2=680.0,
            efficiency_pct=5.0,
            status=PanelStatus.WARNING,
        )
        result = process_reading(reading, panel_area_m2=1.72, rated_power_w=440.0)
        assert result.anomaly_flag is True


class TestIsAnomaly:
    @pytest.mark.parametrize(
        "ac_power, expected_power, should_flag",
        [
            # Below 60% threshold — anomaly
            (200.0, 400.0, True),   # 50% → anomaly
            (239.9, 400.0, True),   # 59.975% → anomaly
            # Exactly at boundary — NOT anomaly (strict <, not <=)
            (240.0, 400.0, False),  # exactly 60% → not anomaly
            # Above threshold — not anomaly
            (260.0, 400.0, False),  # 65% → ok
            (400.0, 400.0, False),  # 100% → ok
            # Zero expected — no irradiance, cannot judge
            (0.0, 0.0, False),
            (100.0, 0.0, False),
            # Negative expected guard (should not happen but defensive)
            (100.0, -1.0, False),
        ],
    )
    def test_threshold_cases(
        self, ac_power: float, expected_power: float, should_flag: bool
    ) -> None:
        assert is_anomaly(ac_power, expected_power) == should_flag

    def test_threshold_constant_is_sixty_percent(self) -> None:
        """Verify the threshold constant has not been accidentally changed."""
        assert ANOMALY_THRESHOLD == 0.60

    def test_stc_irradiance_constant(self) -> None:
        assert STC_IRRADIANCE_WM2 == 1000.0
