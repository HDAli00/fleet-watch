#!/usr/bin/env python3
"""Verify KNMI API connectivity and print the latest observation for each tracked station.

Usage:
    KNMI_API_KEY=<your_key> python scripts/check_knmi.py

Exits 0 on success, 1 if the API is unreachable or returns no stations.
"""
from __future__ import annotations

import json
import os
import sys

import httpx

KNMI_BASE_URL = "https://api.dataplatform.knmi.nl/open-data/v1"
DATASET_NAME = "Actuele10mindataKNMIstations"
DATASET_VERSION = "2"

TARGET_STATIONS = {"240", "260", "344", "370", "380"}


def main() -> None:
    api_key = os.environ.get("KNMI_API_KEY", "")
    if not api_key:
        print("ERROR: Set KNMI_API_KEY environment variable.", file=sys.stderr)
        sys.exit(1)

    headers = {"Authorization": api_key}
    files_url = f"{KNMI_BASE_URL}/datasets/{DATASET_NAME}/versions/{DATASET_VERSION}/files"

    print(f"Connecting to KNMI Open Data API ({DATASET_NAME} v{DATASET_VERSION})…")

    with httpx.Client(timeout=30.0) as http:
        resp = http.get(files_url, headers=headers, params={"orderBy": "lastModified", "sorting": "desc"})
        resp.raise_for_status()
        files = resp.json().get("files", [])

        if not files:
            print("ERROR: No files available from KNMI API.", file=sys.stderr)
            sys.exit(1)

        latest = files[0]["filename"]
        print(f"Latest file: {latest}")

        url_resp = http.get(f"{files_url}/{latest}/url", headers=headers)
        url_resp.raise_for_status()
        download_url = url_resp.json()["temporaryDownloadUrl"]

        data_resp = http.get(download_url)
        data_resp.raise_for_status()
        raw = data_resp.json()

    stations = raw.get("stations", [])
    found: list[dict[str, object]] = []

    for station in stations:
        code = str(station.get("stationid", ""))
        if code in TARGET_STATIONS:
            found.append({
                "code": code,
                "temp_c": station.get("T"),
                "wind_ms": station.get("FF"),
                "irradiance_wm2": station.get("Q"),
                "timestamp": station.get("timestamp"),
            })

    if not found:
        print("WARNING: None of the target stations found in response.", file=sys.stderr)
        print(f"Available station IDs: {[str(s.get('stationid')) for s in stations[:10]]}")
        sys.exit(1)

    print(f"\nFound {len(found)}/{len(TARGET_STATIONS)} target stations:\n")
    for s in sorted(found, key=lambda x: str(x["code"])):
        print(
            f"  [{s['code']}]  {s['timestamp']}  "
            f"T={s['temp_c']}°C  FF={s['wind_ms']}m/s  Q={s['irradiance_wm2']}W/m²"
        )

    print(f"\n✓ KNMI API check passed ({len(found)} stations OK)")


if __name__ == "__main__":
    main()
