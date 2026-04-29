from __future__ import annotations

from fastapi import APIRouter, Request, status

from ..alerts import evaluate
from ..db import BatchedWriter, insert_event
from ..models import TelemetryIn
from ..redis_bus import RedisBus

router = APIRouter()


@router.post("/telemetry", status_code=status.HTTP_202_ACCEPTED)
async def post_telemetry(reading: TelemetryIn, request: Request) -> dict[str, str]:
    writer: BatchedWriter = request.app.state.writer
    bus: RedisBus = request.app.state.bus

    await writer.submit(reading)

    await bus.publish(
        "fleet.positions",
        {
            "positions": [
                {
                    "vehicle_id": reading.vehicle_id,
                    "lat": round(reading.lat, 5),
                    "lon": round(reading.lon, 5),
                    "heading_deg": round(reading.heading_deg, 1),
                    "speed_kph": round(reading.speed_kph, 1),
                    "coolant_c": round(reading.coolant_c, 1),
                    "battery_v": round(reading.battery_v, 2),
                }
            ]
        },
    )

    for alert in evaluate(reading):
        try:
            await insert_event(
                vehicle_id=reading.vehicle_id,
                kind=alert.kind,
                severity=alert.severity,
                message=alert.message,
                ts=reading.ts,
            )
            await bus.publish(
                "fleet.events",
                {
                    "vehicle_id": reading.vehicle_id,
                    "ts": reading.ts.isoformat(),
                    "kind": alert.kind,
                    "severity": alert.severity,
                    "message": alert.message,
                },
            )
        except Exception:
            # Telemetry ingest must remain best-effort; an alert insert failure
            # should not propagate.
            pass

    return {"status": "accepted"}
