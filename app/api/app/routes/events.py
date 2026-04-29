from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from ..db import fetch_recent_events

router = APIRouter()


@router.get("/events")
async def list_events(
    limit: int = Query(default=100, ge=1, le=500),
    severity: str | None = Query(default=None, pattern="^(info|warn|critical)$"),
) -> list[dict[str, Any]]:
    return await fetch_recent_events(limit=limit, severity=severity)
