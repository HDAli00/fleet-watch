"""SQLModel Site: table + read + create variants."""
from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel


class SiteBase(SQLModel):
    name: str = Field(index=True)
    location: str | None = None
    lat: float
    lon: float
    knmi_station: str  # KNMI station code, always string e.g. "344"
    panel_count: int = Field(gt=0)
    capacity_kwp: float = Field(gt=0)


class Site(SiteBase, table=True):
    __tablename__ = "sites"

    site_id: str = Field(primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SiteRead(SiteBase):
    site_id: str
    created_at: datetime


class SiteCreate(SiteBase):
    site_id: str
