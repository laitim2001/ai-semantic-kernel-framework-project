"""
File: backend/src/api/v1/health.py
Purpose: /health endpoint — minimal liveness probe for Sprint 49.1 acceptance.
Category: api/v1
Scope: Phase 49 / Sprint 49.1

Description:
    Lightweight liveness check. Returns version + ok status.
    Sprint 49.3 onwards extends with readiness probe (DB / Redis /
    RabbitMQ ping). For Sprint 49.1 we only need to prove the FastAPI
    app boots and routing works.

Created: 2026-04-29 (Sprint 49.1 Day 3)
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str


@router.get("", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe; Sprint 49.3 will add readiness with DB/Redis/MQ checks."""
    return HealthResponse(status="ok", version="2.0.0-alpha")
