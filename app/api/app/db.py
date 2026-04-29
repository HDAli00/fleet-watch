from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any

import asyncpg

from .models import HistoryPoint, TelemetryIn, VehicleHistory, VehiclePosition, VehicleSummary

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None


async def init_pool(database_url: str, *, min_size: int = 2, max_size: int = 10) -> asyncpg.Pool:
    global _pool
    dsn = database_url.replace("postgresql+asyncpg://", "postgresql://")
    _pool = await asyncpg.create_pool(dsn, min_size=min_size, max_size=max_size)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("DB pool not initialised")
    return _pool


@asynccontextmanager
async def acquire() -> AsyncIterator[asyncpg.Connection]:
    async with get_pool().acquire() as conn:
        yield conn


async def ping() -> bool:
    try:
        async with acquire() as conn:
            await conn.fetchval("SELECT 1")
        return True
    except Exception:
        logger.exception("db ping failed")
        return False


class BatchedWriter:
    """Buffer telemetry rows and flush to Postgres on a fixed cadence.

    Bounded in-memory queue: when full, oldest rows are dropped (telemetry is best-effort).
    """

    def __init__(self, *, flush_ms: int, max_rows: int) -> None:
        self._flush_ms = flush_ms
        self._max_rows = max_rows
        self._buf: list[TelemetryIn] = []
        self._lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None
        self._stopping = asyncio.Event()
        self.dropped = 0
        self.written = 0

    async def submit(self, row: TelemetryIn) -> None:
        async with self._lock:
            if len(self._buf) >= self._max_rows:
                self._buf.pop(0)
                self.dropped += 1
            self._buf.append(row)

    async def submit_many(self, rows: Iterable[TelemetryIn]) -> None:
        async with self._lock:
            for row in rows:
                if len(self._buf) >= self._max_rows:
                    self._buf.pop(0)
                    self.dropped += 1
                self._buf.append(row)

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name="batched-writer")

    async def stop(self) -> None:
        self._stopping.set()
        if self._task is not None:
            await self._task
            self._task = None
        await self._flush_now()

    async def _run(self) -> None:
        interval = self._flush_ms / 1000.0
        while not self._stopping.is_set():
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._stopping.wait(), timeout=interval)
            try:
                await self._flush_now()
            except Exception:
                logger.exception("batched writer flush failed")

    async def _flush_now(self) -> None:
        async with self._lock:
            if not self._buf:
                return
            rows = self._buf
            self._buf = []

        records = [
            (
                r.ts,
                r.vehicle_id,
                r.rpm,
                r.speed_kph,
                r.coolant_c,
                r.oil_psi,
                r.battery_v,
                r.throttle_pct,
                r.fuel_pct,
                r.lat,
                r.lon,
                r.heading_deg,
            )
            for r in rows
        ]
        async with acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO telemetry
                  (ts, vehicle_id, rpm, speed_kph, coolant_c, oil_psi,
                   battery_v, throttle_pct, fuel_pct, lat, lon, heading_deg)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
                """,
                records,
            )
        self.written += len(records)


# ── read paths ──────────────────────────────────────────────────────────────


async def upsert_vehicles(rows: Iterable[dict[str, Any]]) -> None:
    items = list(rows)
    if not items:
        return
    records = [
        (r["vehicle_id"], r["vin"], r["make"], r["model"], r["year"], r["region"]) for r in items
    ]
    async with acquire() as conn:
        await conn.executemany(
            """
            INSERT INTO vehicles (vehicle_id, vin, make, model, year, region)
            VALUES ($1,$2,$3,$4,$5,$6)
            ON CONFLICT (vehicle_id) DO NOTHING
            """,
            records,
        )


async def fetch_fleet_summary(*, limit: int | None = None) -> list[VehicleSummary]:
    sql = """
        SELECT v.vehicle_id, v.make, v.model, v.year, v.region,
               t.ts AS last_seen,
               t.lat AS last_lat, t.lon AS last_lon,
               t.speed_kph AS last_speed,
               t.coolant_c AS last_coolant,
               t.battery_v AS last_battery
        FROM vehicles v
        LEFT JOIN LATERAL (
            SELECT ts, lat, lon, speed_kph, coolant_c, battery_v
            FROM telemetry
            WHERE vehicle_id = v.vehicle_id
            ORDER BY ts DESC
            LIMIT 1
        ) t ON true
        ORDER BY v.vehicle_id
    """
    if limit is not None:
        sql += f" LIMIT {int(limit)}"

    out: list[VehicleSummary] = []
    now = datetime.now(tz=__import__("datetime").timezone.utc)
    async with acquire() as conn:
        rows = await conn.fetch(sql)
    for r in rows:
        last_seen = r["last_seen"]
        status = _classify_status(
            last_seen=last_seen,
            now=now,
            coolant=r["last_coolant"],
            battery=r["last_battery"],
        )
        out.append(
            VehicleSummary(
                vehicle_id=r["vehicle_id"],
                make=r["make"],
                model=r["model"],
                year=r["year"],
                region=r["region"],
                status=status,
                last_seen=last_seen,
                last_lat=r["last_lat"],
                last_lon=r["last_lon"],
                last_speed_kph=r["last_speed"],
                last_coolant_c=r["last_coolant"],
                last_battery_v=r["last_battery"],
            )
        )
    return out


def _classify_status(
    *,
    last_seen: datetime | None,
    now: datetime,
    coolant: float | None,
    battery: float | None,
) -> str:
    if last_seen is None:
        return "offline"
    age = now - last_seen
    if age > timedelta(seconds=30):
        return "offline"
    if coolant is not None and coolant >= 110:
        return "critical"
    if battery is not None and battery < 11.5:
        return "critical"
    if (coolant is not None and coolant >= 100) or (battery is not None and battery < 12.0):
        return "warn"
    return "ok"


async def fetch_vehicle(vehicle_id: str) -> VehicleSummary | None:
    rows = await fetch_fleet_summary()
    for r in rows:
        if r.vehicle_id == vehicle_id:
            return r
    return None


async def fetch_history(vehicle_id: str, window_minutes: int) -> VehicleHistory:
    async with acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT ts, rpm, speed_kph, coolant_c, oil_psi, battery_v, throttle_pct, fuel_pct
            FROM telemetry
            WHERE vehicle_id = $1
              AND ts >= NOW() - ($2::int || ' minutes')::interval
            ORDER BY ts ASC
            """,
            vehicle_id,
            window_minutes,
        )
    return VehicleHistory(
        vehicle_id=vehicle_id,
        window_minutes=window_minutes,
        points=[
            HistoryPoint(
                ts=r["ts"],
                rpm=r["rpm"],
                speed_kph=r["speed_kph"],
                coolant_c=r["coolant_c"],
                oil_psi=r["oil_psi"],
                battery_v=r["battery_v"],
                throttle_pct=r["throttle_pct"],
                fuel_pct=r["fuel_pct"],
            )
            for r in rows
        ],
    )


async def fetch_recent_positions(*, limit: int = 1000) -> list[VehiclePosition]:
    """Latest position per vehicle across the fleet for the live map."""
    async with acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT DISTINCT ON (vehicle_id)
                vehicle_id, lat, lon, heading_deg, speed_kph, coolant_c, battery_v, ts
            FROM telemetry
            WHERE ts >= NOW() - INTERVAL '60 seconds'
            ORDER BY vehicle_id, ts DESC
            LIMIT $1
            """,
            limit,
        )
    now = datetime.now(tz=__import__("datetime").timezone.utc)
    out: list[VehiclePosition] = []
    for r in rows:
        status = _classify_status(
            last_seen=r["ts"],
            now=now,
            coolant=r["coolant_c"],
            battery=r["battery_v"],
        )
        out.append(
            VehiclePosition(
                vehicle_id=r["vehicle_id"],
                lat=r["lat"],
                lon=r["lon"],
                heading_deg=r["heading_deg"],
                speed_kph=r["speed_kph"],
                status=status,
            )
        )
    return out


async def insert_event(
    *, vehicle_id: str, kind: str, severity: str, message: str, ts: datetime | None = None
) -> int:
    async with acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO events (vehicle_id, ts, kind, severity, message)
            VALUES ($1, COALESCE($2, NOW()), $3, $4, $5)
            RETURNING id
            """,
            vehicle_id,
            ts,
            kind,
            severity,
            message,
        )
    return int(row["id"])


async def fetch_recent_events(*, limit: int = 100, severity: str | None = None) -> list[dict[str, Any]]:
    async with acquire() as conn:
        if severity:
            rows = await conn.fetch(
                """
                SELECT id, vehicle_id, ts, kind, severity, message
                FROM events WHERE severity = $1
                ORDER BY ts DESC LIMIT $2
                """,
                severity,
                limit,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT id, vehicle_id, ts, kind, severity, message
                FROM events ORDER BY ts DESC LIMIT $1
                """,
                limit,
            )
    return [dict(r) for r in rows]


async def count_active_vehicles() -> int:
    async with acquire() as conn:
        v = await conn.fetchval(
            """
            SELECT COUNT(DISTINCT vehicle_id) FROM telemetry
            WHERE ts >= NOW() - INTERVAL '30 seconds'
            """
        )
    return int(v or 0)


async def msgs_per_sec_last_minute() -> float:
    async with acquire() as conn:
        v = await conn.fetchval(
            """
            SELECT COUNT(*)::float / 60.0 FROM telemetry
            WHERE ts >= NOW() - INTERVAL '60 seconds'
            """
        )
    return float(v or 0.0)
