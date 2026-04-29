from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..db import fetch_fleet_summary, fetch_history, fetch_vehicle
from ..models import VehicleHistory, VehicleSummary

router = APIRouter()


@router.get("/vehicles", response_model=list[VehicleSummary])
async def list_vehicles(limit: int | None = Query(default=None, ge=1, le=2000)) -> list[VehicleSummary]:
    return await fetch_fleet_summary(limit=limit)


@router.get("/vehicles/{vehicle_id}", response_model=VehicleSummary)
async def get_vehicle(vehicle_id: str) -> VehicleSummary:
    v = await fetch_vehicle(vehicle_id)
    if v is None:
        raise HTTPException(status_code=404, detail="vehicle not found")
    return v


@router.get("/vehicles/{vehicle_id}/history", response_model=VehicleHistory)
async def get_vehicle_history(
    vehicle_id: str, window_minutes: int = Query(default=60, ge=1, le=720)
) -> VehicleHistory:
    return await fetch_history(vehicle_id, window_minutes)
