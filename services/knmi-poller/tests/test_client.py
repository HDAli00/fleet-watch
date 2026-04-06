"""KNMI client tests — respx HTTP mock at boundary only."""
from __future__ import annotations

import httpx
import pytest
import respx

from src.client import fetch_latest_observations

MOCK_FILES_RESPONSE = {
    "files": [
        {"filename": "KNMI_20260405T1000.json"},
        {"filename": "KNMI_20260405T0950.json"},
    ]
}

MOCK_URL_RESPONSE = {
    "temporaryDownloadUrl": "https://download.example.com/KNMI_20260405T1000.json"
}

MOCK_OBS_DATA = {
    "stations": [
        {
            "stationid": "344",
            "timestamp": "2026-04-05T10:00:00+00:00",
            "T": 13.2,
            "FF": 5.8,
            "Q": 380.0,
            "N": 5,
            "RH": 0.2,
        }
    ]
}


@respx.mock
def test_fetch_latest_observations_returns_json() -> None:
    """Full fetch flow returns the observation JSON."""
    respx.get(
        "https://api.dataplatform.knmi.nl/open-data/v1/datasets/Actuele10mindataKNMIstations/versions/2/files"
    ).mock(return_value=httpx.Response(200, json=MOCK_FILES_RESPONSE))

    respx.get(
        "https://api.dataplatform.knmi.nl/open-data/v1/datasets/Actuele10mindataKNMIstations/versions/2/files/KNMI_20260405T1000.json/url"
    ).mock(return_value=httpx.Response(200, json=MOCK_URL_RESPONSE))

    respx.get("https://download.example.com/KNMI_20260405T1000.json").mock(
        return_value=httpx.Response(200, json=MOCK_OBS_DATA)
    )

    result = fetch_latest_observations(api_key="test-key")
    assert result == MOCK_OBS_DATA


@respx.mock
def test_fetch_raises_on_empty_files_list() -> None:
    """Raises ValueError when no files are available."""
    respx.get(
        "https://api.dataplatform.knmi.nl/open-data/v1/datasets/Actuele10mindataKNMIstations/versions/2/files"
    ).mock(return_value=httpx.Response(200, json={"files": []}))

    with pytest.raises(ValueError, match="No KNMI observation files available"):
        fetch_latest_observations(api_key="test-key")


@respx.mock
def test_fetch_raises_on_api_error() -> None:
    """HTTP 401 propagates as httpx.HTTPStatusError."""
    respx.get(
        "https://api.dataplatform.knmi.nl/open-data/v1/datasets/Actuele10mindataKNMIstations/versions/2/files"
    ).mock(return_value=httpx.Response(401, json={"detail": "Unauthorized"}))

    with pytest.raises(httpx.HTTPStatusError):
        fetch_latest_observations(api_key="bad-key")
