from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import BatchedWriter, close_pool, init_pool
from .generator import Generator
from .redis_bus import LeaderElector, RedisBus
from .routes import events, health, stream, telemetry, vehicles

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()

    await init_pool(settings.database_url)

    bus = RedisBus(settings.redis_url)
    await bus.connect()

    elector = LeaderElector(
        bus,
        instance_id=settings.instance_id,
        ttl_s=settings.leader_lock_ttl_s,
        refresh_s=settings.leader_refresh_s,
    )
    elector.start()

    writer = BatchedWriter(
        flush_ms=settings.batch_flush_ms,
        max_rows=settings.batch_max_rows * 4,
    )
    writer.start()

    generator = Generator(settings=settings, bus=bus, elector=elector, writer=writer)
    await generator.seed()
    generator.start()

    app.state.bus = bus
    app.state.elector = elector
    app.state.writer = writer
    app.state.generator = generator

    try:
        yield
    finally:
        await generator.stop()
        await writer.stop()
        await elector.stop()
        await bus.close()
        await close_pool()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Fleet Telemetry API", version="0.1.0", lifespan=lifespan)

    origins = [o.strip() for o in settings.cors_origins.split(",")] if settings.cors_origins else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(telemetry.router)
    app.include_router(vehicles.router)
    app.include_router(events.router)
    app.include_router(stream.router)
    return app


app = create_app()
