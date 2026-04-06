"""Unit tests for Pearson R² — no I/O, full branch coverage."""
from __future__ import annotations

import pytest

from app.services.correlation import pearson_r2


class TestPearsonR2:
    def test_perfect_positive_correlation(self) -> None:
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [2.0, 4.0, 6.0, 8.0, 10.0]
        assert pearson_r2(xs, ys) == pytest.approx(1.0)

    def test_perfect_negative_correlation(self) -> None:
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [10.0, 8.0, 6.0, 4.0, 2.0]
        # Negative correlation → r = -1 → r² = 1
        assert pearson_r2(xs, ys) == pytest.approx(1.0)

    def test_no_correlation(self) -> None:
        xs = [1.0, 2.0, 3.0, 4.0]
        ys = [1.0, 3.0, 2.0, 4.0]
        result = pearson_r2(xs, ys)
        assert 0.0 <= result <= 1.0

    def test_empty_lists(self) -> None:
        assert pearson_r2([], []) == 0.0

    def test_single_point(self) -> None:
        assert pearson_r2([1.0], [2.0]) == 0.0

    def test_constant_x_series(self) -> None:
        """Zero variance in x — no correlation possible."""
        xs = [5.0, 5.0, 5.0, 5.0]
        ys = [1.0, 2.0, 3.0, 4.0]
        assert pearson_r2(xs, ys) == 0.0

    def test_constant_y_series(self) -> None:
        """Zero variance in y — no correlation possible."""
        xs = [1.0, 2.0, 3.0, 4.0]
        ys = [7.0, 7.0, 7.0, 7.0]
        assert pearson_r2(xs, ys) == 0.0

    def test_both_constant_series(self) -> None:
        xs = [3.0, 3.0, 3.0]
        ys = [7.0, 7.0, 7.0]
        assert pearson_r2(xs, ys) == 0.0

    def test_unequal_lengths_raises(self) -> None:
        with pytest.raises(ValueError, match="equal length"):
            pearson_r2([1.0, 2.0], [1.0])

    def test_r2_bounded_0_to_1(self) -> None:
        """R² must always be in [0, 1]."""
        import random
        rng = random.Random(42)  # noqa: S311
        for _ in range(20):
            n = rng.randint(2, 50)
            xs = [rng.uniform(0, 1000) for _ in range(n)]
            ys = [rng.uniform(0, 500) for _ in range(n)]
            r2 = pearson_r2(xs, ys)
            # R² must be in [0, 1] (tiny float tolerance)
            assert 0.0 <= r2 <= 1.0 + 1e-10

    def test_solar_irradiance_scenario(self) -> None:
        """Realistic irradiance (W/m²) vs AC power (W) — should be high R²."""
        irradiance = [0.0, 100.0, 300.0, 600.0, 900.0, 1000.0, 850.0, 500.0, 200.0, 50.0]  # noqa: E501
        ac_power = [0.0, 44.0, 132.0, 264.0, 396.0, 440.0, 374.0, 220.0, 88.0, 22.0]
        r2 = pearson_r2(irradiance, ac_power)
        assert r2 > 0.99, f"Expected high R² for linear solar data, got {r2}"
