"""Pure correlation function: Pearson R² for irradiance vs output."""

from __future__ import annotations

import math


def pearson_r2(xs: list[float], ys: list[float]) -> float:
    """Compute Pearson R² between two equal-length lists.

    Returns 0.0 for edge cases:
    - empty lists
    - single data point
    - zero variance in either series (constant values)
    """
    n = len(xs)
    if n != len(ys):
        raise ValueError(f"xs and ys must have equal length, got {n} vs {len(ys)}")
    if n < 2:
        return 0.0

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=False))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)

    denom = math.sqrt(var_x * var_y)
    if denom == 0.0:
        return 0.0  # one or both series is constant — no correlation

    r = cov / denom
    return r * r  # R² = Pearson r squared
