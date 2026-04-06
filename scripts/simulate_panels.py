#!/usr/bin/env python3
"""Simulate solar panel IoT telemetry → Kinesis panels-stream.

Generates realistic AC power values based on a sine-curve irradiance model
(solar day 06:00–20:00 CEST). Optionally injects anomalies.

Usage:
    AWS_PROFILE=dev python scripts/simulate_panels.py \
        --site-id site-NL-001 \
        --panel-count 5 \
        --interval 60 \
        --anomaly-rate 0.05

Press Ctrl+C to stop.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from datetime import datetime, timezone


def solar_irradiance(hour: float) -> float:
    """Irradiance model: zero outside 06:00-20:00, sine peak at 13:00."""
    if hour < 6.0 or hour > 20.0:
        return 0.0
    angle = math.pi * (hour - 6.0) / 14.0
    return max(0.0, math.sin(angle) * 980.0)


def generate_reading(
    panel_id: str,
    site_id: str,
    irradiance: float,
    rated_power_w: float = 440.0,
    anomaly: bool = False,
) -> dict[object, object]:
    """Generate a single telemetry reading with realistic noise."""
    noise = random.gauss(0, 0.02)  # ±2% Gaussian noise
    raw_power = (irradiance / 1000.0) * rated_power_w * (1 + noise)
    if anomaly:
        # Inject anomaly: output is 20–55% of expected
        raw_power *= random.uniform(0.20, 0.55)

    ac_power_w = max(0.0, raw_power)
    dc_voltage_v = random.gauss(38.4, 0.5)
    dc_current_a = ac_power_w / max(dc_voltage_v, 0.1) * 1.02  # ~2% conversion loss

    return {
        "panel_id": panel_id,
        "site_id": site_id,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "dc_voltage_v": round(max(0.0, dc_voltage_v), 2),
        "dc_current_a": round(max(0.0, dc_current_a), 2),
        "ac_power_w": round(ac_power_w, 2),
        "temperature_c": round(random.gauss(42.0, 5.0), 1),
        "irradiance_wm2": round(irradiance, 1),
        "efficiency_pct": round((ac_power_w / (irradiance * 1.72 + 1e-9)) * 100, 1),
        "status": "warning" if anomaly else "ok",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate solar panel telemetry")
    parser.add_argument("--site-id", default="site-NL-001")
    parser.add_argument("--panel-count", type=int, default=3)
    parser.add_argument("--interval", type=float, default=10.0, help="seconds between batches")
    parser.add_argument("--anomaly-rate", type=float, default=0.05, help="fraction of readings that are anomalous")
    parser.add_argument("--stream-name", default="solar-panels-stream")
    parser.add_argument("--dry-run", action="store_true", help="print JSON instead of sending to Kinesis")
    args = parser.parse_args()

    if not args.dry_run:
        import boto3
        kinesis = boto3.client("kinesis")
        print(f"Sending to Kinesis stream '{args.stream_name}' every {args.interval}s")
    else:
        print("Dry-run mode — printing JSON to stdout")

    panel_ids = [f"{args.site_id}-panel-{i:03d}" for i in range(1, args.panel_count + 1)]

    try:
        while True:
            now = datetime.now(tz=timezone.utc)
            # Use Amsterdam local time for irradiance (UTC+2 in summer, UTC+1 in winter)
            hour = (now.hour + 1) % 24  # rough CEST
            irradiance = solar_irradiance(float(hour) + now.minute / 60.0)

            records = []
            for panel_id in panel_ids:
                anomaly = random.random() < args.anomaly_rate
                reading = generate_reading(panel_id, args.site_id, irradiance, anomaly=anomaly)

                if args.dry_run:
                    print(json.dumps(reading, indent=2))
                else:
                    import base64
                    records.append({
                        "Data": json.dumps(reading).encode("utf-8"),
                        "PartitionKey": panel_id,
                    })

            if not args.dry_run and records:
                resp = kinesis.put_records(StreamName=args.stream_name, Records=records)
                failed = resp.get("FailedRecordCount", 0)
                print(
                    f"[{now.strftime('%H:%M:%S')}] Sent {len(records)} records "
                    f"(irr={irradiance:.0f} W/m²) — {failed} failed"
                )

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\nSimulation stopped.")
        sys.exit(0)


if __name__ == "__main__":
    main()
