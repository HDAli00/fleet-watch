"""SQLModel Panel: table + read variants."""

from __future__ import annotations

from datetime import date

from sqlmodel import Field, SQLModel


class PanelBase(SQLModel):
    site_id: str = Field(foreign_key="sites.site_id", index=True)
    model: str | None = None
    rated_power_w: float = Field(gt=0)
    area_m2: float = Field(gt=0)
    installed_at: date | None = None


class Panel(PanelBase, table=True):
    __tablename__ = "panels"

    panel_id: str = Field(primary_key=True)


class PanelRead(PanelBase):
    panel_id: str
