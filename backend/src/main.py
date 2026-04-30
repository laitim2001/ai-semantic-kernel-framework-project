"""
File: backend/src/main.py
Purpose: V2 backend FastAPI app entry point.
Category: api / app entry
Scope: Phase 49 / Sprint 49.1 (minimal; later sprints register more routers)

Description:
    Sprint 49.1 minimum:
    - Mount /health endpoint (for Day 5.2 acceptance)
    - Wire Settings + basic logging
    - NO LLM, NO DB, NO auth, NO chat endpoints (those land Sprint 49.2+)

Run:
    uvicorn src.main:app --reload --port 8001

Created: 2026-04-29 (Sprint 49.1 Day 3)
"""

from __future__ import annotations

from fastapi import FastAPI

from api.v1 import health
from core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="IPA Platform V2",
    description="LLM-provider-neutral agent harness (server-side, multi-tenant)",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

# v1 routers
app.include_router(health.router, prefix="/api/v1")


@app.get("/")
async def root() -> dict[str, str]:
    """Top-level info endpoint."""
    return {
        "name": "IPA Platform V2",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/api/v1/health",
    }
