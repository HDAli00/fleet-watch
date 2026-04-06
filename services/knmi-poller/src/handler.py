"""Lambda handler: EventBridge → KNMI API → Kinesis weather-stream."""
from __future__ import annotations

import os
from typing import Any

import structlog
from aws_lambda_powertools import Logger, Tracer

from .client import fetch_latest_observations
from .parser import parse_knmi_response
from .publisher import publish_readings

logger = Logger(service=os.environ.get("POWERTOOLS_SERVICE_NAME", "knmi-poller"))
tracer = Tracer(service=os.environ.get("POWERTOOLS_SERVICE_NAME", "knmi-poller"))
log = structlog.get_logger()


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    """Poll KNMI API and publish observations to Kinesis weather-stream."""
    log.info("knmi.poller.start")

    raw = fetch_latest_observations()
    readings = parse_knmi_response(raw)

    if not readings:
        log.warning("knmi.poller.no_readings")
        return {"published": 0, "stations": []}

    published = publish_readings(readings)

    station_codes = [r.station_code for r in readings]
    log.info("knmi.poller.complete", published=published, stations=station_codes)

    return {"published": published, "stations": station_codes}
