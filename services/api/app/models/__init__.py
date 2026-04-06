"""SQLModel table models — import all to register SA metadata."""

from app.models.panel import Panel, PanelRead
from app.models.site import Site, SiteCreate, SiteRead
from app.models.telemetry import Telemetry, TelemetryRead
from app.models.weather import WeatherObs, WeatherObsRead

__all__ = [
    "Site",
    "SiteRead",
    "SiteCreate",
    "Panel",
    "PanelRead",
    "Telemetry",
    "TelemetryRead",
    "WeatherObs",
    "WeatherObsRead",
]
