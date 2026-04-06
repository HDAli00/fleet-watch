"""GET /weather endpoints — KNMI observations."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_db
from app.models.weather import WeatherObs, WeatherObsRead

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("/{station_code}", response_model=list[WeatherObsRead])
async def get_station_weather(
    station_code: str,  # always string — "344" not 344
    hours: Annotated[int, Query(ge=1, le=168)] = 24,
    db: AsyncSession = Depends(get_db),
) -> list[WeatherObs]:
    """Return weather observations for a KNMI station over the last N hours."""
    since = datetime.now(tz=timezone.utc) - timedelta(hours=hours)
    result = await db.execute(
        select(WeatherObs)
        .where(WeatherObs.station_code == station_code, WeatherObs.ts >= since)
        .order_by(WeatherObs.ts)
    )
    return list(result.scalars().all())
