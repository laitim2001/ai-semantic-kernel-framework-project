"""
core.config — Pydantic Settings.

Sprint 49.1 stub: minimal Settings; Sprint 49.2 expands with full DB /
Redis / RabbitMQ / OTel / LLM provider config.

Per project rules (.claude/rules/code-quality.md): always use Pydantic
Settings (not raw os.environ) so type-safe + validation + .env support.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """V2 backend settings. Loaded from env / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application
    env: str = "development"
    log_level: str = "INFO"
    app_version: str = "2.0.0-alpha"

    # PostgreSQL (Sprint 49.2 will use)
    database_url: str = "postgresql+asyncpg://ipa_v2:ipa_v2_dev@localhost:5432/ipa_v2"

    # Redis (Sprint 49.2 will use)
    redis_url: str = "redis://localhost:6379/0"

    # JWT (Sprint 49.3 will use)
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings singleton. FastAPI Depends(get_settings)."""
    return Settings()


__all__ = ["Settings", "get_settings"]
