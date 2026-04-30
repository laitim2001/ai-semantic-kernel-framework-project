"""
File: backend/src/mock_services/routers/correlation.py
Purpose: Mock correlation domain — analyze alert relationships, find root cause candidates.
Category: Mock services / routers (mocks 08b §Domain 2)
Scope: Phase 51 / Sprint 51.0 Day 2.4

Description:
    Three endpoints supporting the 3 mock_correlation_* tools:
    - POST /mock/correlation/analyze            — given alert_ids, return correlation chains
    - POST /mock/correlation/find_root_cause    — incident_id -> ranked rca candidates
    - GET  /mock/correlation/related/{alert_id} — alerts related to a given alert (within depth)

    Naive correlation: alerts within ±5 minutes of each other on same server_id.
    Phase 55 真實 integration 會接 Splunk / DataDog 真實 correlation engine.

Created: 2026-04-30 (Sprint 51.0 Day 2)
Last Modified: 2026-04-30
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from mock_services.data.loader import SeedDB, get_db

router = APIRouter(prefix="/mock/correlation", tags=["mock-correlation"])


class AnalyzeRequest(BaseModel):
    alert_ids: list[str] = Field(..., min_length=1)


class CorrelationChain(BaseModel):
    primary_alert_id: str
    related_alert_ids: list[str]
    likely_server_id: str | None = None
    confidence: float = Field(..., ge=0.0, le=1.0)


class RootCauseCandidate(BaseModel):
    finding_id: str
    incident_id: str
    hypothesis: str
    confidence: float
    evidence_count: int


class FindRootCauseRequest(BaseModel):
    incident_id: str


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@router.post("/analyze", response_model=list[CorrelationChain])
async def analyze(request: AnalyzeRequest, db: SeedDB = Depends(get_db)) -> list[CorrelationChain]:
    chains: list[CorrelationChain] = []
    for primary_id in request.alert_ids:
        primary = db.alerts.get(primary_id)
        if primary is None:
            continue
        primary_ts = _parse_ts(primary["timestamp"])
        related: list[str] = []
        for other_id, other in db.alerts.items():
            if other_id == primary_id:
                continue
            if other.get("server_id") and other["server_id"] != primary.get("server_id"):
                continue
            other_ts = _parse_ts(other["timestamp"])
            if abs((other_ts - primary_ts).total_seconds()) <= 5 * 60:
                related.append(other_id)
        chains.append(
            CorrelationChain(
                primary_alert_id=primary_id,
                related_alert_ids=related,
                likely_server_id=primary.get("server_id"),
                confidence=0.5 + min(0.4, 0.1 * len(related)),
            )
        )
    return chains


@router.post("/find_root_cause", response_model=list[RootCauseCandidate])
async def find_root_cause(
    request: FindRootCauseRequest, db: SeedDB = Depends(get_db)
) -> list[RootCauseCandidate]:
    if request.incident_id not in db.incidents:
        raise HTTPException(status_code=404, detail=f"incident {request.incident_id} not found")
    candidates: list[RootCauseCandidate] = []
    for finding in db.rca_findings.values():
        if finding["incident_id"] != request.incident_id:
            continue
        candidates.append(
            RootCauseCandidate(
                finding_id=finding["id"],
                incident_id=finding["incident_id"],
                hypothesis=finding["hypothesis"],
                confidence=finding["confidence"],
                evidence_count=len(finding.get("evidence", [])),
            )
        )
    candidates.sort(key=lambda c: c.confidence, reverse=True)
    return candidates


@router.get("/related/{alert_id}", response_model=list[dict[str, Any]])
async def related(
    alert_id: str,
    depth: int = Query(default=1, ge=1, le=3),
    db: SeedDB = Depends(get_db),
) -> list[dict[str, Any]]:
    primary = db.alerts.get(alert_id)
    if primary is None:
        raise HTTPException(status_code=404, detail=f"alert {alert_id} not found")
    primary_ts = _parse_ts(primary["timestamp"])
    window = timedelta(minutes=5 * depth)
    related = []
    for other_id, other in db.alerts.items():
        if other_id == alert_id:
            continue
        if (
            abs((_parse_ts(other["timestamp"]) - primary_ts).total_seconds())
            <= window.total_seconds()
        ):
            if (
                other.get("server_id") == primary.get("server_id")
                or primary.get("server_id") is None
            ):
                related.append(other)
    return related
