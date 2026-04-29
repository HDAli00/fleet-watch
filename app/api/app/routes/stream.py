from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from ..db import (
    count_active_vehicles,
    fetch_recent_events,
    fetch_recent_positions,
    msgs_per_sec_last_minute,
)
from ..redis_bus import LeaderElector, RedisBus

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/stream/fleet")
async def stream_fleet(request: Request) -> EventSourceResponse:
    bus: RedisBus = request.app.state.bus
    elector: LeaderElector = request.app.state.elector

    async def gen() -> AsyncIterator[dict[str, str]]:
        pubsub_iter = bus.subscribe("fleet.positions", "fleet.events")
        msg_task: asyncio.Task[dict[str, Any] | None] | None = None
        kpi_task: asyncio.Task[dict[str, Any]] | None = None
        try:
            yield {"event": "snapshot", "data": json.dumps(await _snapshot(elector))}

            msg_task = asyncio.create_task(_anext(pubsub_iter))
            kpi_task = asyncio.create_task(_kpi_loop(elector))

            while True:
                if await request.is_disconnected():
                    break
                done, _ = await asyncio.wait(
                    {kpi_task, msg_task},
                    return_when=asyncio.FIRST_COMPLETED,
                    timeout=5.0,
                )

                if msg_task in done:
                    msg = msg_task.result()
                    msg_task = asyncio.create_task(_anext(pubsub_iter))
                    if msg is not None:
                        channel = str(msg["channel"])
                        event = "positions" if channel.endswith("positions") else "event"
                        yield {"event": event, "data": json.dumps(msg["data"])}

                if kpi_task in done:
                    payload = kpi_task.result()
                    kpi_task = asyncio.create_task(_kpi_loop(elector))
                    yield {"event": "kpis", "data": json.dumps(payload)}
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("fleet stream error")
        finally:
            for t in (msg_task, kpi_task):
                if t is not None:
                    t.cancel()
                    with contextlib.suppress(asyncio.CancelledError, Exception):
                        await t
            with contextlib.suppress(Exception):
                await pubsub_iter.aclose()  # type: ignore[attr-defined]

    return EventSourceResponse(gen())


@router.get("/stream/vehicles/{vehicle_id}")
async def stream_vehicle(vehicle_id: str, request: Request) -> EventSourceResponse:
    bus: RedisBus = request.app.state.bus

    async def gen() -> AsyncIterator[dict[str, str]]:
        pubsub_iter = bus.subscribe("fleet.positions", "fleet.events")
        msg_task: asyncio.Task[dict[str, Any] | None] | None = None
        try:
            msg_task = asyncio.create_task(_anext(pubsub_iter))
            while True:
                if await request.is_disconnected():
                    break
                done, _ = await asyncio.wait({msg_task}, timeout=5.0)
                if msg_task not in done:
                    continue
                msg = msg_task.result()
                msg_task = asyncio.create_task(_anext(pubsub_iter))
                if msg is None:
                    continue
                data = msg["data"]
                channel = str(msg["channel"])
                if channel.endswith("positions"):
                    positions = data.get("positions") or []
                    for pos in positions:
                        if pos.get("vehicle_id") == vehicle_id:
                            yield {"event": "position", "data": json.dumps(pos)}
                elif channel.endswith("events"):
                    if data.get("vehicle_id") == vehicle_id:
                        yield {"event": "event", "data": json.dumps(data)}
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("vehicle stream error")
        finally:
            if msg_task is not None:
                msg_task.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await msg_task
            with contextlib.suppress(Exception):
                await pubsub_iter.aclose()  # type: ignore[attr-defined]

    return EventSourceResponse(gen())


async def _kpi_loop(elector: LeaderElector) -> dict[str, Any]:
    await asyncio.sleep(1.0)
    return await _snapshot(elector)


async def _snapshot(elector: LeaderElector) -> dict[str, Any]:
    active = await count_active_vehicles()
    rate = await msgs_per_sec_last_minute()
    events = await fetch_recent_events(limit=100)
    alert_count = sum(1 for e in events if e.get("severity") in ("warn", "critical"))
    positions = await fetch_recent_positions()
    return {
        "ts": datetime.now(tz=UTC).isoformat(),
        "kpis": {
            "active_vehicles": active,
            "msgs_per_sec": round(rate, 1),
            "alerts_per_min": float(alert_count),
            "p95_ingest_ms": 0.0,
            "leader_instance": elector.instance_id if elector.is_leader else None,
        },
        "positions": [p.model_dump() for p in positions],
    }


async def _anext(it: AsyncIterator[dict[str, Any]]) -> dict[str, Any] | None:
    try:
        return await it.__anext__()
    except StopAsyncIteration:
        return None
