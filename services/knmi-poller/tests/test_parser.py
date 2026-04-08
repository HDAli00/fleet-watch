"""Parser tests — real fixture files, no mocks, 100% branch coverage."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.models import WeatherReading
from src.parser import parse_knmi_response

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    ("fixture_file", "expected_station", "expected_temp_range"),
    [
        ("knmi_de_bilt.json", "260", (-5.0, 35.0)),
        ("knmi_rotterdam.json", "344", (-5.0, 35.0)),
        ("knmi_eindhoven.json", "370", (-5.0, 35.0)),
    ],
)
def test_parse_known_stations(
    fixture_file: str,
    expected_station: str,
    expected_temp_range: tuple[float, float],
) -> None:
    raw = json.loads((FIXTURES / fixture_file).read_text())
    readings = parse_knmi_response(raw)

    assert len(readings) > 0
    assert all(isinstance(r, WeatherReading) for r in readings)

    station_reading = next(r for r in readings if r.station_code == expected_station)

    # station_code must be a string, never an int
    assert isinstance(station_reading.station_code, str)
    assert station_reading.station_code == expected_station

    lo, hi = expected_temp_range
    assert lo <= station_reading.temperature_c <= hi
    assert station_reading.solar_rad_wm2 >= 0
    assert 0 <= station_reading.cloud_cover_oktas <= 8
    assert station_reading.wind_speed_ms >= 0
    assert station_reading.precipitation_mm >= 0
    assert station_reading.ts.tzinfo is not None  # timezone-aware


def test_unknown_stations_filtered_out() -> None:
    """Station codes not in KNMI_STATIONS are silently skipped."""
    raw = json.loads((FIXTURES / "knmi_de_bilt.json").read_text())
    readings = parse_knmi_response(raw)
    codes = [r.station_code for r in readings]
    assert "999" not in codes  # fixture has station 999 which is not in our list


def test_multiple_stations_in_one_file() -> None:
    """Eindhoven fixture has 2 stations — both should be parsed."""
    raw = json.loads((FIXTURES / "knmi_eindhoven.json").read_text())
    readings = parse_knmi_response(raw)
    codes = {r.station_code for r in readings}
    assert "370" in codes
    assert "260" in codes


def test_empty_stations_list() -> None:
    assert parse_knmi_response({"stations": []}) == []


def test_missing_stations_key() -> None:
    assert parse_knmi_response({}) == []


def test_invalid_stations_type() -> None:
    assert parse_knmi_response({"stations": "not_a_list"}) == []


def test_station_with_missing_timestamp_skipped() -> None:
    raw = {
        "stations": [
            {"stationid": "344", "T": 12.0, "FF": 3.0, "Q": 300.0, "N": 4, "RH": 0.0}
        ]
    }
    readings = parse_knmi_response(raw)
    assert readings == []


def test_cloud_cover_clamped_to_8() -> None:
    """cloud_cover_oktas > 8 should be clamped to 8."""
    raw = {
        "stations": [
            {
                "stationid": "344",
                "timestamp": "2026-04-05T10:00:00+00:00",
                "T": 12.0,
                "FF": 3.0,
                "Q": 300.0,
                "N": 9,  # invalid KNMI value
                "RH": 0.0,
            }
        ]
    }
    readings = parse_knmi_response(raw)
    assert len(readings) == 1
    assert readings[0].cloud_cover_oktas == 8


def test_none_fields_use_defaults() -> None:
    """None field values should fall back to 0.0 without crashing."""
    raw = {
        "stations": [
            {
                "stationid": "344",
                "timestamp": "2026-04-05T10:00:00+00:00",
                "T": None,
                "FF": None,
                "Q": None,
                "N": None,
                "RH": None,
            }
        ]
    }
    readings = parse_knmi_response(raw)
    assert len(readings) == 1
    r = readings[0]
    assert r.temperature_c == 0.0
    assert r.wind_speed_ms == 0.0
    assert r.solar_rad_wm2 == 0.0
    assert r.cloud_cover_oktas == 0
    assert r.precipitation_mm == 0.0
