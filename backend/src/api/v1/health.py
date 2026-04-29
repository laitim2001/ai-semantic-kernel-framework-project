"""
File: backend/src/api/v1/health.py
Purpose: /health (liveness) + /health/ready (readiness) endpoints.
Category: api/v1
Scope: Phase 49 / Sprint 49.1 (liveness) → Sprint 49.4 Day 5 (readiness)

Description:
    Two endpoints:
    - GET /api/v1/health         — liveness; returns status+version, no I/O
    - GET /api/v1/health/ready   — readiness; pings DB; reports degradation

    Liveness asks "is the process alive?" — used by k8s livenessProbe to
    decide whether to restart the container.

    Readiness asks "can this process serve traffic right now?" — used by
    k8s readinessProbe + load balancer to remove the pod from rotation
    when DB/Redis/MQ become unreachable. Returning 503 is the correct
    behavior for a transient dependency outage.

Created: 2026-04-29 (Sprint 49.1 Day 3)
Last Modified: 2026-04-29 (Sprint 49.4 Day 5 — added /ready with DB ping)

Modification History:
    - 2026-04-29: Add /health/ready with DB ping (Sprint 49.4 Day 5)
    - 2026-04-29: Initial /health liveness (Sprint 49.1 Day 3)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text

from infrastructure.db import get_session_factory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str


class ReadinessCheck(BaseModel):
    name: str
    ok: bool
    detail: str | None = None


class ReadinessResponse(BaseModel):
    status: str
    checks: list[ReadinessCheck]


@router.get("", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe — process is up. Does not hit dependencies."""
    return HealthResponse(status="ok", version="2.0.0-alpha")


@router.get("/ready")
async def readiness() -> JSONResponse:
    """Readiness probe — process can serve traffic. Pings dependencies.

    Returns 200 with status='ready' when all checks pass, 503 with
    status='degraded' when any required check fails. Detail field
    carries the underlying error so log aggregation can group failures.
    """
    checks: list[ReadinessCheck] = []
    all_ok = True

    # DB ping — required for any tenant query path.
    try:
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        checks.append(ReadinessCheck(name="postgres", ok=True))
    except Exception as exc:  # noqa: BLE001
        all_ok = False
        checks.append(ReadinessCheck(name="postgres", ok=False, detail=str(exc)))
        logger.warning("readiness: postgres failed", exc_info=True)

    body = ReadinessResponse(status="ready" if all_ok else "degraded", checks=checks).model_dump()
    code = status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(content=body, status_code=code)
