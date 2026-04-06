"""GET /telemetry endpoints — time-series panel readings."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import TelemetryWindow
from app.database import get_db
from app.models.telemetry import Telemetry, TelemetryRead
from app.models.weather import WeatherObs
from app.services.correlation import pearson_r2

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

_WINDOW_DELTAS: dict[TelemetryWindow, timedelta] = {
    TelemetryWindow.ONE_HOUR: timedelta(hours=1),
    TelemetryWindow.SIX_HOURS: timedelta(hours=6),
    TelemetryWindow.ONE_DAY: timedelta(hours=24),
    TelemetryWindow.SEVEN_DAYS: timedelta(days=7),
}


class CorrelationResult(BaseModel):
    site_id: str
    station_code: str
    window: str
    r2: float
    sample_count: int


@router.get("/{panel_id}", response_model=list[TelemetryRead])
async def get_panel_telemetry(
    panel_id: str,
    window: Annotated[TelemetryWindow, Query()] = TelemetryWindow.ONE_HOUR,
    db: AsyncSession = Depends(get_db),
) -> list[Telemetry]:
    """Return time-series readings for a panel over the specified window."""
    since = datetime.now(tz=timezone.utc) - _WINDOW_DELTAS[window]
    result = await db.execute(
        select(Telemetry)
        .where(Telemetry.panel_id == panel_id, Telemetry.ts >= since)
        .order_by(Telemetry.ts)
    )
    rows = list(result.scalars().all())
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No telemetry for panel '{panel_id}' in window '{window}'",
        )
    return rows


@router.get("/anomalies/recent", response_model=list[TelemetryRead])
async def get_recent_anomalies(
    window: Annotated[TelemetryWindow, Query()] = TelemetryWindow.ONE_HOUR,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    db: AsyncSession = Depends(get_db),
) -> list[Telemetry]:
    """Return recent anomalous panel readings across all panels."""
    since = datetime.now(tz=timezone.utc) - _WINDOW_DELTAS[window]
    result = await db.execute(
        select(Telemetry)
        .where(Telemetry.anomaly_flag.is_(True), Telemetry.ts >= since)  # type: ignore[union-attr]
        .order_by(Telemetry.ts.desc())  # type: ignore[union-attr]
        .limit(limit)
    )
    return list(result.scalars().all())


@router.get("/correlation/{site_id}", response_model=CorrelationResult)
async def get_irradiance_correlation(
    site_id: str,
    window: Annotated[TelemetryWindow, Query()] = TelemetryWindow.ONE_DAY,
    db: AsyncSession = Depends(get_db),
) -> CorrelationResult:
    """Return Pearson R² between irradiance (KNMI) and AC output for a site."""
    since = datetime.now(tz=timezone.utc) - _WINDOW_DELTAS[window]

    tel_result, obs_result = await asyncio.gather(
        db.execute(
            select(Telemetry.ts, Telemetry.ac_power_w, Telemetry.irradiance_wm2)
            .where(Telemetry.site_id == site_id, Telemetry.ts >= since)
            .order_by(Telemetry.ts)
        ),
        db.execute(
            select(WeatherObs.station_code)
            .where(WeatherObs.ts >= since)
            .order_by(WeatherObs.ts.desc())  # type: ignore[union-attr]
            .limit(1)
        ),
    )

    tel_rows = tel_result.all()
    if len(tel_rows) < 2:
        raise HTTPException(
            status_code=422,
            detail=f"Not enough telemetry data for site '{site_id}' (need ≥ 2 points)",
        )

    irradiance_vals = [float(r.irradiance_wm2 or 0) for r in tel_rows]
    power_vals = [float(r.ac_power_w) for r in tel_rows]
    r2 = pearson_r2(irradiance_vals, power_vals)

    row = obs_result.first()
    station_code = row[0] if row else "unknown"

    return CorrelationResult(
        site_id=site_id,
        station_code=station_code,
        window=window,
        r2=round(r2, 4),
        sample_count=len(tel_rows),
    )
