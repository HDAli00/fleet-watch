from __future__ import annotations

import random

from app.generator import Vehicle, seed_fleet


def test_seed_fleet_creates_n_unique_vehicles() -> None:
    vehicles, rows = seed_fleet(50, rng=random.Random(1))
    assert len(vehicles) == 50
    assert len({r["vehicle_id"] for r in rows}) == 50
    assert {r["region"] for r in rows} <= {"EU-NL", "EU-DE", "EU-FR", "US-CA", "US-NY", "UK-LDN"}


def test_vehicle_step_keeps_metrics_in_bounds() -> None:
    rng = random.Random(2)
    v = Vehicle("v-test", lat=52.0, lon=4.9, heading_deg=90.0)
    for _ in range(200):
        reading = v.step(now=0.0)
        assert -90 <= reading.lat <= 90
        assert -180 <= reading.lon <= 180
        assert 0 <= reading.heading_deg < 360
        assert 0 <= reading.speed_kph <= 400
        assert 0 <= reading.throttle_pct <= 100
        assert 0 <= reading.fuel_pct <= 100
        assert reading.rpm >= 0
    # Burn a value from rng so static analysers see it used.
    _ = rng.random()


def test_vehicle_id_persists() -> None:
    v = Vehicle("v-xyz", 0.0, 0.0, 0.0)
    r = v.step(now=0.0)
    assert r.vehicle_id == "v-xyz"
