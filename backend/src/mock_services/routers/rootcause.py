"""
File: backend/src/mock_services/routers/rootcause.py
Purpose: Mock root cause analysis — diagnose incident, suggest fix, apply fix.
Category: Mock services / routers (mocks 08b §Domain 3)
Scope: Phase 51 / Sprint 51.0 Day 2.6

Description:
    Three endpoints supporting the 3 mock_rootcause_* tools:
    - POST /mock/rootcause/diagnose         — incident_id -> top RCA finding
    - POST /mock/rootcause/suggest_fix      — incident_id -> mock fix proposal
    - POST /mock/rootcause/apply_fix        — apply_fix(fix_id, dry_run); HIGH risk

    apply_fix is the most destructive mock operation. Default dry_run=true; with
    dry_run=false it merely records action and returns "closed_pending_review".
    Real implementation (Phase 55) would actually mutate infrastructure and
    requires multi-reviewer HITL approval.

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

router = APIRouter(prefix="/mock/rootcause", tags=["mock-rootcause"])

# In-memory ledger of fix actions (process-restart resets)
_applied_fixes: list[dict[str, Any]] = []


class DiagnoseRequest(BaseModel):
    incident_id: str


class DiagnoseResponse(BaseModel):
    finding_id: str
    incident_id: str
    hypothesis: str
    confidence: float
    evidence: list[str]


class SuggestFixRequest(BaseModel):
    incident_id: str


class FixSuggestion(BaseModel):
    fix_id: str
    incident_id: str
    description: str
    risk_level: str = Field(..., examples=["low", "medium", "high"])
    estimated_minutes: int


class ApplyFixRequest(BaseModel):
    fix_id: str
    dry_run: bool = Field(default=True)


class ApplyFixResponse(BaseModel):
    fix_id: str
    status: str
    dry_run: bool
    applied_at: datetime
    message: str


@router.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose(request: DiagnoseRequest, db: SeedDB = Depends(get_db)) -> DiagnoseResponse:
    if request.incident_id not in db.incidents:
        raise HTTPException(status_code=404, detail=f"incident {request.incident_id} not found")
    candidates = [f for f in db.rca_findings.values() if f["incident_id"] == request.incident_id]
    if not candidates:
        raise HTTPException(
            status_code=404,
            detail=f"no RCA findings for incident {request.incident_id}",
        )
    top = max(candidates, key=lambda f: f["confidence"])
    return DiagnoseResponse(
        finding_id=top["id"],
        incident_id=top["incident_id"],
        hypothesis=top["hypothesis"],
        confidence=top["confidence"],
        evidence=top.get("evidence", []),
    )


@router.post("/suggest_fix", response_model=FixSuggestion)
async def suggest_fix(request: SuggestFixRequest, db: SeedDB = Depends(get_db)) -> FixSuggestion:
    incident = db.incidents.get(request.incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail=f"incident {request.incident_id} not found")
    fix_id = f"fix_{uuid.uuid4().hex[:8]}"
    severity_to_risk = {"low": "low", "medium": "medium", "high": "high", "critical": "high"}
    return FixSuggestion(
        fix_id=fix_id,
        incident_id=request.incident_id,
        description=f"Mock fix proposal for incident '{incident['title']}'.",
        risk_level=severity_to_risk.get(incident["severity"], "medium"),
        estimated_minutes=15,
    )


@router.post("/apply_fix", response_model=ApplyFixResponse)
async def apply_fix(request: ApplyFixRequest) -> ApplyFixResponse:
    record = {
        "fix_id": request.fix_id,
        "dry_run": request.dry_run,
        "applied_at": datetime.now(timezone.utc).isoformat(),
    }
    _applied_fixes.append(record)
    if request.dry_run:
        return ApplyFixResponse(
            fix_id=request.fix_id,
            status="dry_run_ok",
            dry_run=True,
            applied_at=datetime.now(timezone.utc),
            message="dry-run only; no real mutation performed",
        )
    return ApplyFixResponse(
        fix_id=request.fix_id,
        status="closed_pending_review",
        dry_run=False,
        applied_at=datetime.now(timezone.utc),
        message="mock apply recorded; real impl (Phase 55) requires multi-reviewer HITL",
    )
