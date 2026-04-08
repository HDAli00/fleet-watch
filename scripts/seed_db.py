#!/usr/bin/env python3
"""Seed the database with Dutch solar sites, panels, and sample weather stations.

Usage:
    DATABASE_URL=postgresql+asyncpg://... uv run python scripts/seed_db.py

The script is idempotent — re-running it will not duplicate data.
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import date

# Make sure we can import from services/api
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services", "api"))

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

import app.models  # noqa: F401
from app.models.panel import Panel
from app.models.site import Site

SITES = [
    Site(
        site_id="site-NL-001",
        name="Amsterdam Noord",
        location="Amsterdam, Noord-Holland",
        lat=52.4009,
        lon=4.9267,
        knmi_station="240",
        panel_count=30,
        capacity_kwp=13.2,
    ),
    Site(
        site_id="site-NL-002",
        name="Rotterdam Maasvlakte",
        location="Rotterdam, Zuid-Holland",
        lat=51.9225,
        lon=4.4792,
        knmi_station="344",
        panel_count=50,
        capacity_kwp=22.0,
    ),
    Site(
        site_id="site-NL-003",
        name="Eindhoven Woensel",
        location="Eindhoven, Noord-Brabant",
        lat=51.4416,
        lon=5.4697,
        knmi_station="370",
        panel_count=20,
        capacity_kwp=8.8,
    ),
]

PANELS: list[Panel] = []
for site in SITES:
    for i in range(1, site.panel_count + 1):
        PANELS.append(
            Panel(
                panel_id=f"{site.site_id}-panel-{i:03d}",
                site_id=site.site_id,
                model="Longi LR5-72HPH-440M",
                rated_power_w=440.0,
                area_m2=1.72,
                installed_at=date(2024, 6, 1),
            )
        )


async def main() -> None:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: Set DATABASE_URL environment variable first.", file=sys.stderr)
        sys.exit(1)

    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        for site in SITES:
            existing = await session.get(Site, site.site_id)
            if existing is None:
                session.add(site)
                print(f"  + Site {site.site_id} ({site.name})")
            else:
                print(f"  ~ Site {site.site_id} already exists, skipping")

        await session.flush()

        panel_count = 0
        for panel in PANELS:
            existing = await session.get(Panel, panel.panel_id)
            if existing is None:
                session.add(panel)
                panel_count += 1

        await session.commit()
        print(f"\n✓ Seeded {len(SITES)} sites, {panel_count} panels")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
