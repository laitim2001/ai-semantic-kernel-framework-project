"""
File: backend/src/mock_services/routers/patrol.py
Purpose: Mock patrol domain — server health checks + schedule/cancel of patrol jobs.
Category: Mock services / routers (mocks 08b §Domain 1)
Scope: Phase 51 / Sprint 51.0 Day 2.1

Description:
    Four endpoints supporting the 4 mock_patrol_* tools:
    - POST /mock/patrol/check_servers       — run health check on scope (returns list[PatrolResult])
    - GET  /mock/patrol/results/{patrol_id} — fetch a single PatrolResult
    - POST /mock/patrol/schedule            — schedule recurring patrol (cron + scope)
    - POST /mock/patrol/cancel              — cancel scheduled patrol by id

    `schedule` and `cancel` mutate an in-memory schedules dict (process-restart
    resets). Result generator deterministically derives mock metrics from server_id.

Created: 2026-04-30 (Sprint 51.0 Day 2)
Last Modified: 2026-04-30
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from mock_services.data.loader import SeedDB, get_db
from mock_services.schemas import PatrolResult

router = APIRouter(prefix="/mock/patrol", tags=["mock-patrol"])

# In-memory schedules: id -> {cron, scope, created_at}
_schedules: dict[str, dict[str, str | list[str]]] = {}


class CheckServersRequest(BaseModel):
    scope: list[str] = Field(..., min_length=1, examples=[["web-01", "web-02"]])


class ScheduleRequest(BaseModel):
    cron: str = Field(..., examples=["*/5 * * * *"])
    scope: list[str] = Field(..., min_length=1)


class ScheduleResponse(BaseModel):
    schedule_id: str
    cron: str
    scope: list[str]
    created_at: datetime


class CancelRequest(BaseModel):
    schedule_id: str


def _make_result(server_id: str) -> dict[str, Any]:
    seed_hash = abs(hash(server_id)) % 100
    return {
        "id": f"pat_live_{uuid.uuid4().hex[:8]}",
        "server_id": server_id,
        "health": "warning" if seed_hash > 70 else ("critical" if seed_hash > 90 else "ok"),
        "metrics": {
            "cpu_pct": 20.0 + seed_hash * 0.7,
            "mem_pct": 30.0 + seed_hash * 0.5,
            "disk_pct": 40.0 + seed_hash * 0.3,
        },
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/check_servers", response_model=list[PatrolResult])
async def check_servers(
    request: CheckServersRequest, db: SeedDB = Depends(get_db)
) -> list[PatrolResult]:
    out: list[PatrolResult] = []
    for sid in request.scope:
        # Prefer seeded result if available; otherwise synthesize
        seeded = next((p for p in db.patrols.values() if p["server_id"] == sid), None)
        out.append(PatrolResult(**(seeded or _make_result(sid))))
    return out


@router.get("/results/{patrol_id}", response_model=PatrolResult)
async def get_result(patrol_id: str, db: SeedDB = Depends(get_db)) -> PatrolResult:
    raw = db.patrols.get(patrol_id)
    if raw is None:
        raise HTTPException(status_code=404, detail=f"patrol {patrol_id} not found")
    return PatrolResult(**raw)


@router.post("/schedule", response_model=ScheduleResponse)
async def schedule(request: ScheduleRequest) -> ScheduleResponse:
    sid = f"sched_{uuid.uuid4().hex[:8]}"
    _schedules[sid] = {
        "cron": request.cron,
        "scope": request.scope,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return ScheduleResponse(
        schedule_id=sid,
        cron=request.cron,
        scope=request.scope,
        created_at=datetime.now(timezone.utc),
    )


@router.post("/cancel")
async def cancel(request: CancelRequest) -> dict[str, str]:
    if request.schedule_id not in _schedules:
        raise HTTPException(status_code=404, detail=f"schedule {request.schedule_id} not found")
    _schedules.pop(request.schedule_id)
    return {"status": "cancelled", "schedule_id": request.schedule_id}
