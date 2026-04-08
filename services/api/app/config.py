"""Application settings — pydantic-settings, reads from env."""

from __future__ import annotations

from enum import StrEnum

from pydantic_settings import BaseSettings, SettingsConfigDict


class TelemetryWindow(StrEnum):
    """Valid time-range query windows for telemetry endpoint."""

    ONE_HOUR = "1h"
    SIX_HOURS = "6h"
    ONE_DAY = "24h"
    SEVEN_DAYS = "7d"


class PanelStatus(StrEnum):
    """Valid panel operational states."""

    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    OFFLINE = "offline"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    db_secret_arn: str = ""
    aws_region: str = "eu-west-1"
    log_level: str = "INFO"


settings = Settings()
