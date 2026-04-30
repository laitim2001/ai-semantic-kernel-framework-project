"""
File: backend/src/mock_services/routers/incident.py
Purpose: Mock incident management — create / update / close / get / list incidents.
Category: Mock services / routers (mocks 08b §Domain 5)
Scope: Phase 51 / Sprint 51.0 Day 3.3

Description:
    Five endpoints supporting the 5 mock_incident_* tools:
    - POST   /mock/incident/create           — create new incident
    - POST   /mock/incident/update_status    — update incident.status
    - POST   /mock/incident/close            — close incident (HIGH risk)
    - GET    /mock/incident/{id}             — fetch single incident
    - POST   /mock/incident/list             — filtered list (severity / status)

    `create` mutates an in-memory _live_incidents dict alongside seed data
    (seed acts as historical record; live ones added at runtime).

Created: 2026-04-30 (Sprint 51.0 Day 3)
Last Modified: 2026-04-30
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from mock_services.data.loader import SeedDB, get_db
from mock_services.schemas import Incident

router = APIRouter(prefix="/mock/incident", tags=["mock-incident"])

# Live incidents created at runtime (process-restart resets)
_live_incidents: dict[str, dict[str, Any]] = {}


class CreateIncidentRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    severity: Literal["low", "medium", "high", "critical"] = "high"
    alert_ids: list[str] = Field(default_factory=list)


class UpdateStatusRequest(BaseModel):
    incident_id: str
    status: Literal["open", "investigating", "resolved", "closed"]


class CloseIncidentRequest(BaseModel):
    incident_id: str
    resolution: str = Field(..., min_length=1, max_length=1000)


class CloseIncidentResponse(BaseModel):
    incident_id: str
    status: str
    resolution: str
    closed_at: datetime
    message: str


class ListIncidentsRequest(BaseModel):
    severity: Literal["low", "medium", "high", "critical"] | None = None
    status: Literal["open", "investigating", "resolved", "closed"] | None = None
    limit: int = Field(default=20, ge=1, le=100)


def _all_incidents(db: SeedDB) -> dict[str, dict[str, Any]]:
    merged = dict(db.incidents)
    merged.update(_live_incidents)
    return merged


@router.post("/create", response_model=Incident)
async def create_incident(request: CreateIncidentRequest) -> Incident:
    incident_id = f"inc_live_{uuid.uuid4().hex[:8]}"
    record: dict[str, Any] = {
        "id": incident_id,
        "title": request.title,
        "severity": request.severity,
        "status": "open",
        "alert_ids": request.alert_ids,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _live_incidents[incident_id] = record
    return Incident(**record)


@router.post("/update_status", response_model=Incident)
async def update_status(request: UpdateStatusRequest, db: SeedDB = Depends(get_db)) -> Incident:
    incidents = _all_incidents(db)
    incident = incidents.get(request.incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail=f"incident {request.incident_id} not found")
    if request.incident_id in _live_incidents:
        _live_incidents[request.incident_id]["status"] = request.status
        return Incident(**_live_incidents[request.incident_id])
    # Seed records: simulate update by returning a mutated copy (seed is read-only)
    mutated = dict(incident)
    mutated["status"] = request.status
    return Incident(**mutated)


@router.post("/close", response_model=CloseIncidentResponse)
async def close_incident(
    request: CloseIncidentRequest, db: SeedDB = Depends(get_db)
) -> CloseIncidentResponse:
    incidents = _all_incidents(db)
    if request.incident_id not in incidents:
        raise HTTPException(status_code=404, detail=f"incident {request.incident_id} not found")
    if request.incident_id in _live_incidents:
        _live_incidents[request.incident_id]["status"] = "closed"
    return CloseIncidentResponse(
        incident_id=request.incident_id,
        status="closed_pending_review",
        resolution=request.resolution,
        closed_at=datetime.now(timezone.utc),
        message="mock close recorded; real impl (Phase 55) requires multi-reviewer HITL",
    )


@router.get("/{incident_id}", response_model=Incident)
async def get_incident(incident_id: str, db: SeedDB = Depends(get_db)) -> Incident:
    incident = _all_incidents(db).get(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail=f"incident {incident_id} not found")
    return Incident(**incident)


@router.post("/list", response_model=list[Incident])
async def list_incidents(
    request: ListIncidentsRequest, db: SeedDB = Depends(get_db)
) -> list[Incident]:
    items = list(_all_incidents(db).values())
    if request.severity is not None:
        items = [i for i in items if i["severity"] == request.severity]
    if request.status is not None:
        items = [i for i in items if i["status"] == request.status]
    items.sort(key=lambda i: i["created_at"], reverse=True)
    return [Incident(**i) for i in items[: request.limit]]
