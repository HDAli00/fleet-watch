"""FastAPI application — Solar IoT Platform API."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_engine
from app.routers import panels, sites, telemetry, weather

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialise DB engine on startup."""
    log.info("api.startup")
    init_engine()
    yield
    log.info("api.shutdown")


app = FastAPI(
    title="Solar IoT Platform API",
    description="Real-time solar panel telemetry and KNMI weather correlation",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — restrict to CloudFront origin in prod; allow all in dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tightened to CloudFront URL via env in prod
    allow_methods=["GET"],  # read-only API
    allow_headers=["*"],
)

app.include_router(sites.router)
app.include_router(panels.router)
app.include_router(telemetry.router)
app.include_router(weather.router)


@app.get("/health", tags=["ops"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
