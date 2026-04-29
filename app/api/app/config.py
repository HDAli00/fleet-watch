from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    database_url: str = Field(
        default="postgresql://fleet:fleet@postgres:5432/fleet",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")

    fleet_size: int = Field(default=500, alias="FLEET_SIZE")
    gen_rate_hz: float = Field(default=1.0, alias="GEN_RATE_HZ")
    gen_enabled: bool = Field(default=True, alias="GEN_ENABLED")

    batch_flush_ms: int = Field(default=500, alias="BATCH_FLUSH_MS")
    batch_max_rows: int = Field(default=2000, alias="BATCH_MAX_ROWS")

    leader_lock_ttl_s: int = Field(default=10, alias="LEADER_LOCK_TTL_S")
    leader_refresh_s: float = Field(default=3.0, alias="LEADER_REFRESH_S")

    instance_id: str = Field(default="local", alias="HOSTNAME")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
