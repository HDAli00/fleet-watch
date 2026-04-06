"""GET /panels endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_db
from app.models.panel import Panel, PanelRead

router = APIRouter(prefix="/panels", tags=["panels"])


@router.get("", response_model=list[PanelRead])
async def list_panels(
    site_id: str | None = None,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[Panel]:
    """Return all panels, optionally filtered by site_id."""
    query = select(Panel)
    if site_id is not None:
        query = query.where(Panel.site_id == site_id)
    result = await db.execute(query.order_by(Panel.panel_id))
    return list(result.scalars().all())


@router.get("/{panel_id}", response_model=PanelRead)
async def get_panel(panel_id: str, db: AsyncSession = Depends(get_db)) -> Panel:  # noqa: B008
    """Return a single panel by ID."""
    panel = await db.get(Panel, panel_id)
    if panel is None:
        raise HTTPException(status_code=404, detail=f"Panel '{panel_id}' not found")
    return panel
