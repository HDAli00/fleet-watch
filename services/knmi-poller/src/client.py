"""KNMI Open Data API client — HTTPS only, typed responses."""

from __future__ import annotations

import os

import boto3
import httpx
import structlog

log = structlog.get_logger()

KNMI_BASE_URL = "https://api.dataplatform.knmi.nl/open-data/v1"
DATASET_NAME = "Actuele10mindataKNMIstations"
DATASET_VERSION = "2"


def _get_api_key() -> str:
    """Retrieve KNMI API key from Secrets Manager at runtime."""
    secret_arn = os.environ["KNMI_SECRET_ARN"]
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_arn)
    return response["SecretString"]


def fetch_latest_observations(api_key: str | None = None) -> dict[object, object]:
    """Fetch the latest KNMI 10-min observation file and return parsed JSON.

    If *api_key* is omitted, it is retrieved from Secrets Manager via
    the ``KNMI_SECRET_ARN`` environment variable.
    """
    resolved_key = api_key if api_key is not None else _get_api_key()
    return _fetch(resolved_key)


def _fetch(api_key: str) -> dict[object, object]:
    headers = {"Authorization": api_key}
    files_url = (
        f"{KNMI_BASE_URL}/datasets/{DATASET_NAME}/versions/{DATASET_VERSION}/files"
    )

    with httpx.Client(timeout=30.0) as http:
        resp = http.get(
            files_url,
            headers=headers,
            params={"orderBy": "lastModified", "sorting": "desc"},
        )
        resp.raise_for_status()
        files_payload = resp.json()

        files = files_payload.get("files", [])
        if not files:
            raise ValueError("No KNMI observation files available")

        latest_filename: str = files[0]["filename"]
        log.info("knmi.file.selected", filename=latest_filename)

        url_resp = http.get(
            f"{files_url}/{latest_filename}/url",
            headers=headers,
        )
        url_resp.raise_for_status()
        # Presigned download URL — no auth header needed
        download_url: str = url_resp.json()["temporaryDownloadUrl"]

        data_resp = http.get(download_url)
        data_resp.raise_for_status()

    log.info(
        "knmi.file.downloaded", filename=latest_filename, bytes=len(data_resp.content)
    )
    return data_resp.json()  # type: ignore[no-any-return]
