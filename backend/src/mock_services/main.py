"""
File: backend/src/mock_services/main.py
Purpose: FastAPI app entry point for mock backend (port 8001).
Category: Mock services / app entry
Scope: Phase 51 / Sprint 51.0 Day 1.1

Description:
    Standalone FastAPI app loaded with seed.json on startup. Provides:
    - GET /health — liveness check (returns SeedDB row counts)
    - GET /         — service identification banner
    - /mock/crm/*   — CRM router (Day 1.5)
    - /mock/kb/*    — KB router (Day 1.6)
    - /mock/<5 domain>/* — added in Day 2-3

Run:
    uvicorn mock_services.main:app --port 8001
    or
    python scripts/mock_dev.py start

Created: 2026-04-30 (Sprint 51.0 Day 1)
Last Modified: 2026-04-30
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI

from mock_services.data.loader import load_seed
from mock_services.routers import crm as crm_router
from mock_services.routers import kb as kb_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    db = load_seed()
    app.state.db_stats = db.stats()
    yield


app = FastAPI(
    title="V2 Mock Services",
    version="51.0.0",
    description=(
        "Mock backend for Phase 51-54 demo material. NOT production. "
        "Phase 55 真實 enterprise integration 上線時整個目錄刪除。"
    ),
    lifespan=lifespan,
)

app.include_router(crm_router.router)
app.include_router(kb_router.router)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "v2-mock-services",
        "version": "51.0.0",
        "warning": "test-infra; not for production use",
    }


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "db_stats": app.state.db_stats}
