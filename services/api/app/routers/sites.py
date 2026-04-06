"""GET /sites and GET /sites/{site_id} endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_db
from app.models.site import Site, SiteRead

router = APIRouter(prefix="/sites", tags=["sites"])


@router.get("", response_model=list[SiteRead])
async def list_sites(db: AsyncSession = Depends(get_db)) -> list[Site]:
    """Return all registered solar sites."""
    result = await db.execute(select(Site).order_by(Site.name))
    return list(result.scalars().all())


@router.get("/{site_id}", response_model=SiteRead)
async def get_site(site_id: str, db: AsyncSession = Depends(get_db)) -> Site:
    """Return a single site by ID."""
    site = await db.get(Site, site_id)
    if site is None:
        raise HTTPException(status_code=404, detail=f"Site '{site_id}' not found")
    return site
