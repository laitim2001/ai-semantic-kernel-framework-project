"""
core.config — Pydantic Settings.

Sprint 49.2 expands DB-related fields. Sprint 49.3 / 49.4 will further add
RLS / OTel / LLM provider fields.

Per project rules (.claude/rules/code-quality.md): always use Pydantic
Settings (not raw os.environ) so type-safe + validation + .env support.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """V2 backend settings. Loaded from env / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- Application ------------------------------------------------
    env: str = "development"
    log_level: str = "INFO"
    app_version: str = "2.0.0-alpha"

    # ---- PostgreSQL -------------------------------------------------
    # async URL format: postgresql+asyncpg://user:pwd@host:port/db
    database_url: str = "postgresql+asyncpg://ipa_v2:ipa_v2_dev@localhost:5432/ipa_v2"

    # Pool sizing (Sprint 49.2)
    db_pool_size: int = 10
    db_pool_max_overflow: int = 20
    db_pool_recycle_sec: int = 300
    db_echo: bool = False  # True only for local SQL debugging

    # ---- Redis (Sprint 49.4 wires) ----------------------------------
    redis_url: str = "redis://localhost:6379/0"

    # ---- JWT (Sprint 49.3 wires identity) ---------------------------
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60

    # ---- Business domain (Sprint 55.1) ------------------------------
    # mock   → 51.0 HTTP mock_executor pathway (PoC default; backwards-compat)
    # service → 55.1+ DB-backed service classes (production)
    # Override via env: BUSINESS_DOMAIN_MODE=service
    business_domain_mode: Literal["mock", "service"] = "mock"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings singleton. FastAPI Depends(get_settings)."""
    return Settings()


__all__ = ["Settings", "get_settings"]
