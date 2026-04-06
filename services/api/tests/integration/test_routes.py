"""Integration tests: FastAPI routes against real Postgres via testcontainers."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.panel import Panel
from app.models.site import Site
from app.models.telemetry import Telemetry
from app.models.weather import WeatherObs

# ── Seed helpers ─────────────────────────────────────────────────────────────

async def _seed_site(db: AsyncSession) -> Site:
    site = Site(
        site_id="site-NL-001",
        name="Amsterdam Solar",
        lat=52.37,
        lon=4.90,
        knmi_station="240",
        panel_count=10,
        capacity_kwp=4.4,
    )
    db.add(site)
    await db.flush()
    return site


async def _seed_panel(db: AsyncSession, site_id: str) -> Panel:
    panel = Panel(
        panel_id="panel-NL-001",
        site_id=site_id,
        model="TestPanel 440W",
        rated_power_w=440.0,
        area_m2=1.72,
    )
    db.add(panel)
    await db.flush()
    return panel


async def _seed_telemetry(db: AsyncSession, panel_id: str, site_id: str) -> Telemetry:
    t = Telemetry(
        panel_id=panel_id,
        site_id=site_id,
        ts=datetime.now(tz=UTC),
        ac_power_w=312.5,
        irradiance_wm2=680.0,
        anomaly_flag=False,
        status="ok",
    )
    db.add(t)
    await db.flush()
    return t


# ── Tests ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(api_client: AsyncClient) -> None:
    resp = await api_client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_list_sites_empty(api_client: AsyncClient) -> None:
    resp = await api_client.get("/sites")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_site_not_found(api_client: AsyncClient) -> None:
    resp = await api_client.get("/sites/does-not-exist")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_and_get_site(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _seed_site(db_session)
    await db_session.commit()

    resp = await api_client.get("/sites")
    assert resp.status_code == 200
    sites = resp.json()
    assert any(s["site_id"] == "site-NL-001" for s in sites)

    resp2 = await api_client.get("/sites/site-NL-001")
    assert resp2.status_code == 200
    assert resp2.json()["name"] == "Amsterdam Solar"
    # knmi_station must always be a string
    assert isinstance(resp2.json()["knmi_station"], str)


@pytest.mark.asyncio
async def test_list_panels(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _seed_panel(db_session, "site-NL-001")
    await db_session.commit()

    resp = await api_client.get("/panels")
    assert resp.status_code == 200
    assert any(p["panel_id"] == "panel-NL-001" for p in resp.json())

    # Filter by site_id
    resp2 = await api_client.get("/panels", params={"site_id": "site-NL-001"})
    assert resp2.status_code == 200
    assert len(resp2.json()) >= 1


@pytest.mark.asyncio
async def test_get_panel_not_found(api_client: AsyncClient) -> None:
    resp = await api_client.get("/panels/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_telemetry_not_found(api_client: AsyncClient) -> None:
    resp = await api_client.get("/telemetry/no-such-panel")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_telemetry_returns_data(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _seed_telemetry(db_session, "panel-NL-001", "site-NL-001")
    await db_session.commit()

    resp = await api_client.get("/telemetry/panel-NL-001")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["ac_power_w"] == pytest.approx(312.5)
    assert data[0]["anomaly_flag"] is False


@pytest.mark.asyncio
async def test_telemetry_window_query_param(
    api_client: AsyncClient,
) -> None:
    """Invalid window value returns 422."""
    resp = await api_client.get("/telemetry/panel-NL-001", params={"window": "99d"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_recent_anomalies(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    anomaly = Telemetry(
        panel_id="panel-NL-001",
        site_id="site-NL-001",
        ts=datetime.now(tz=UTC),
        ac_power_w=50.0,
        irradiance_wm2=680.0,
        anomaly_flag=True,
        status="warning",
    )
    db_session.add(anomaly)
    await db_session.commit()

    resp = await api_client.get("/telemetry/anomalies/recent")
    assert resp.status_code == 200
    flags = [r["anomaly_flag"] for r in resp.json()]
    assert all(flags)


@pytest.mark.asyncio
async def test_weather_endpoint(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    obs = WeatherObs(
        station_code="240",
        ts=datetime.now(tz=UTC),
        temperature_c=14.2,
        solar_rad_wm2=420.0,
        wind_speed_ms=3.5,
        cloud_cover_oktas=3,
        precipitation_mm=0.0,
    )
    db_session.add(obs)
    await db_session.commit()

    resp = await api_client.get("/weather/240")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    # station_code is always a string
    assert isinstance(data[0]["station_code"], str)
    assert data[0]["station_code"] == "240"
