from __future__ import annotations

from fastapi import APIRouter, Request

from ..db import ping as db_ping
from ..models import HealthReport
from ..redis_bus import LeaderElector, RedisBus

router = APIRouter()


@router.get("/health", response_model=HealthReport)
async def health(request: Request) -> HealthReport:
    bus: RedisBus = request.app.state.bus
    elector: LeaderElector = request.app.state.elector

    db_ok = await db_ping()
    redis_ok = await bus.ping()

    return HealthReport(
        db="ok" if db_ok else "down",
        redis="ok" if redis_ok else "down",
        leader=elector.is_leader,
        instance=elector.instance_id,
    )
