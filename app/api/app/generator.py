from __future__ import annotations

import asyncio
import contextlib
import logging
import math
import random
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from .alerts import evaluate
from .config import Settings
from .db import BatchedWriter, insert_event, upsert_vehicles
from .models import TelemetryIn
from .redis_bus import LeaderElector, RedisBus

logger = logging.getLogger(__name__)


MAKES_MODELS = [
    ("Toyota", "Corolla"),
    ("Tesla", "Model 3"),
    ("Ford", "F-150"),
    ("Volkswagen", "Golf"),
    ("Honda", "Civic"),
    ("BMW", "3 Series"),
    ("Renault", "Clio"),
    ("Volvo", "XC60"),
]
REGIONS = ["EU-NL", "EU-DE", "EU-FR", "US-CA", "US-NY", "UK-LDN"]


class Vehicle:
    """One simulated car with realistic metric drift + random faults."""

    def __init__(self, vehicle_id: str, lat: float, lon: float, heading_deg: float) -> None:
        self.vehicle_id = vehicle_id
        self.lat = lat
        self.lon = lon
        self.heading_deg = heading_deg
        self.speed_kph = random.uniform(40, 120)
        self.rpm = int(self.speed_kph * 30 + random.uniform(-300, 300))
        self.coolant_c = random.uniform(85, 95)
        self.oil_psi = random.uniform(35, 55)
        self.battery_v = random.uniform(13.4, 14.2)
        self.throttle_pct = random.uniform(20, 60)
        self.fuel_pct = random.uniform(20, 100)
        self._fault_until: float = 0.0
        self._fault_kind: str | None = None

    def step(self, now: float) -> TelemetryIn:
        # Speed drift, bounded.
        self.speed_kph = _clamp(self.speed_kph + random.uniform(-3, 3), 0, 180)
        self.rpm = int(_clamp(self.speed_kph * 30 + random.uniform(-200, 200), 700, 7800))
        self.throttle_pct = _clamp(self.throttle_pct + random.uniform(-5, 5), 0, 100)
        self.coolant_c = _clamp(self.coolant_c + random.uniform(-0.4, 0.4), 70, 105)
        self.oil_psi = _clamp(self.oil_psi + random.uniform(-0.5, 0.5), 25, 70)
        self.battery_v = _clamp(self.battery_v + random.uniform(-0.05, 0.05), 12.2, 14.5)
        self.fuel_pct = _clamp(self.fuel_pct - random.uniform(0, 0.005), 0, 100)

        # ~1% chance to start a fault, lasting ~20s
        if self._fault_until > now:
            self._apply_fault()
        elif random.random() < 0.0008:
            self._fault_kind = random.choice(
                ["coolant_overheat", "battery_low", "oil_pressure_low", "rpm_spike"]
            )
            self._fault_until = now + 20.0
            self._apply_fault()
        else:
            self._fault_kind = None

        # GPS step
        self.heading_deg = (self.heading_deg + random.uniform(-5, 5)) % 360
        meters = self.speed_kph * (1000.0 / 3600.0)  # per-second step
        d_lat = (meters * math.cos(math.radians(self.heading_deg))) / 111_320.0
        d_lon = (meters * math.sin(math.radians(self.heading_deg))) / (
            111_320.0 * max(math.cos(math.radians(self.lat)), 0.01)
        )
        self.lat = _clamp(self.lat + d_lat, -85, 85)
        self.lon = ((self.lon + d_lon + 180) % 360) - 180

        return TelemetryIn(
            vehicle_id=self.vehicle_id,
            ts=datetime.now(tz=UTC),
            rpm=self.rpm,
            speed_kph=self.speed_kph,
            coolant_c=self.coolant_c,
            oil_psi=self.oil_psi,
            battery_v=self.battery_v,
            throttle_pct=self.throttle_pct,
            fuel_pct=self.fuel_pct,
            lat=self.lat,
            lon=self.lon,
            heading_deg=self.heading_deg,
        )

    def _apply_fault(self) -> None:
        match self._fault_kind:
            case "coolant_overheat":
                self.coolant_c = _clamp(self.coolant_c + 8, 70, 130)
            case "battery_low":
                self.battery_v = _clamp(self.battery_v - 1.2, 10, 14.5)
            case "oil_pressure_low":
                self.oil_psi = _clamp(self.oil_psi - 25, 0, 70)
            case "rpm_spike":
                self.rpm = int(_clamp(self.rpm + 1500, 700, 12000))
            case _:
                pass


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def seed_fleet(size: int, *, rng: random.Random | None = None) -> tuple[list[Vehicle], list[dict[str, object]]]:
    rng = rng or random.Random(0xF1EE7)
    vehicles: list[Vehicle] = []
    rows: list[dict[str, object]] = []
    for i in range(size):
        vid = f"v-{i:04d}"
        make, model = rng.choice(MAKES_MODELS)
        year = rng.randint(2015, 2025)
        region = rng.choice(REGIONS)
        # Cluster around 6 region centroids.
        cx, cy = _region_centroid(region)
        lat = cx + rng.uniform(-0.4, 0.4)
        lon = cy + rng.uniform(-0.4, 0.4)
        vehicles.append(Vehicle(vid, lat, lon, rng.uniform(0, 359.9)))
        rows.append(
            {
                "vehicle_id": vid,
                "vin": f"VIN{i:013d}"[-17:],
                "make": make,
                "model": model,
                "year": year,
                "region": region,
            }
        )
    return vehicles, rows


def _region_centroid(region: str) -> tuple[float, float]:
    return {
        "EU-NL": (52.37, 4.90),
        "EU-DE": (52.52, 13.40),
        "EU-FR": (48.85, 2.35),
        "US-CA": (37.77, -122.42),
        "US-NY": (40.73, -74.00),
        "UK-LDN": (51.50, -0.12),
    }[region]


class Generator:
    """Leader-only loop emitting telemetry at fleet_size * gen_rate_hz events/sec."""

    def __init__(
        self,
        *,
        settings: Settings,
        bus: RedisBus,
        elector: LeaderElector,
        writer: BatchedWriter,
        on_alert: Callable[[str, str, str, str], Awaitable[None]] | None = None,
    ) -> None:
        self._settings = settings
        self._bus = bus
        self._elector = elector
        self._writer = writer
        self._on_alert = on_alert
        self._task: asyncio.Task[None] | None = None
        self._stopping = asyncio.Event()
        self._vehicles: list[Vehicle] = []

    async def seed(self) -> None:
        self._vehicles, vrows = seed_fleet(self._settings.fleet_size)
        await upsert_vehicles(vrows)

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name="generator")

    async def stop(self) -> None:
        self._stopping.set()
        if self._task is not None:
            await self._task
            self._task = None

    async def _run(self) -> None:
        if not self._settings.gen_enabled:
            return
        period = 1.0 / max(self._settings.gen_rate_hz, 0.01)
        next_tick = asyncio.get_event_loop().time()
        while not self._stopping.is_set():
            try:
                if self._elector.is_leader and self._vehicles:
                    await self._tick()
            except Exception:
                logger.exception("generator tick failed")
            next_tick += period
            now = asyncio.get_event_loop().time()
            sleep_for = max(0.0, next_tick - now)
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._stopping.wait(), timeout=sleep_for or 0.001)

    async def _tick(self) -> None:
        loop_now = asyncio.get_event_loop().time()
        readings = [v.step(loop_now) for v in self._vehicles]

        await self._writer.submit_many(readings)

        # Publish a position snapshot (compact) and KPI batch
        positions = [
            {
                "vehicle_id": r.vehicle_id,
                "lat": round(r.lat, 5),
                "lon": round(r.lon, 5),
                "heading_deg": round(r.heading_deg, 1),
                "speed_kph": round(r.speed_kph, 1),
                "coolant_c": round(r.coolant_c, 1),
                "battery_v": round(r.battery_v, 2),
            }
            for r in readings
        ]
        await self._bus.publish("fleet.positions", {"positions": positions})

        # Emit alerts (sample to avoid spam)
        for r in readings:
            for alert in evaluate(r):
                if alert.severity == "critical" or random.random() < 0.05:
                    try:
                        await insert_event(
                            vehicle_id=r.vehicle_id,
                            kind=alert.kind,
                            severity=alert.severity,
                            message=alert.message,
                        )
                        await self._bus.publish(
                            "fleet.events",
                            {
                                "vehicle_id": r.vehicle_id,
                                "ts": r.ts.isoformat(),
                                "kind": alert.kind,
                                "severity": alert.severity,
                                "message": alert.message,
                            },
                        )
                    except Exception:
                        logger.exception("failed to record alert")
