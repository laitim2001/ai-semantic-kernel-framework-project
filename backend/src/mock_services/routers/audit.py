"""
File: backend/src/mock_services/routers/audit.py
Purpose: Mock audit domain — query logs, generate reports, flag anomalies.
Category: Mock services / routers (mocks 08b §Domain 4)
Scope: Phase 51 / Sprint 51.0 Day 3.1

Description:
    Three endpoints supporting the 3 mock_audit_* tools:
    - POST /mock/audit/query_logs       — time_range + filters -> matching audit logs
    - POST /mock/audit/generate_report  — template + params -> placeholder report URL
    - POST /mock/audit/flag_anomaly     — record_id + reason -> records anomaly flag

    Real Phase 55 integration: ServiceNow audit / Splunk SIEM / GRC tooling.

Created: 2026-04-30 (Sprint 51.0 Day 3)
Last Modified: 2026-04-30
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from mock_services.data.loader import SeedDB, get_db
from mock_services.schemas import AuditLogEntry

router = APIRouter(prefix="/mock/audit", tags=["mock-audit"])

# In-memory anomaly flags ledger (process-restart resets)
_flagged_records: list[dict[str, Any]] = []


class QueryLogsRequest(BaseModel):
    time_range_start: datetime | None = None
    time_range_end: datetime | None = None
    action_filter: str | None = Field(default=None, examples=["incident.close"])
    user_id_filter: str | None = None
    limit: int = Field(default=20, ge=1, le=200)


class GenerateReportRequest(BaseModel):
    template: str = Field(..., examples=["compliance_quarterly", "incident_summary"])
    params: dict[str, Any] = Field(default_factory=dict)


class GenerateReportResponse(BaseModel):
    report_id: str
    template: str
    params: dict[str, Any]
    url: str
    generated_at: datetime


class FlagAnomalyRequest(BaseModel):
    record_id: str
    reason: str = Field(..., min_length=1, max_length=500)


class FlagAnomalyResponse(BaseModel):
    flag_id: str
    record_id: str
    reason: str
    flagged_at: datetime


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@router.post("/query_logs", response_model=list[AuditLogEntry])
async def query_logs(
    request: QueryLogsRequest, db: SeedDB = Depends(get_db)
) -> list[AuditLogEntry]:
    items = list(db.audit_logs.values())
    if request.action_filter is not None:
        items = [it for it in items if request.action_filter in it["action"]]
    if request.user_id_filter is not None:
        items = [it for it in items if it["user_id"] == request.user_id_filter]
    if request.time_range_start is not None:
        items = [it for it in items if _parse_ts(it["timestamp"]) >= request.time_range_start]
    if request.time_range_end is not None:
        items = [it for it in items if _parse_ts(it["timestamp"]) <= request.time_range_end]
    items.sort(key=lambda it: it["timestamp"], reverse=True)
    return [AuditLogEntry(**it) for it in items[: request.limit]]


@router.post("/generate_report", response_model=GenerateReportResponse)
async def generate_report(request: GenerateReportRequest) -> GenerateReportResponse:
    report_id = f"rpt_{uuid.uuid4().hex[:8]}"
    return GenerateReportResponse(
        report_id=report_id,
        template=request.template,
        params=request.params,
        url=f"https://mock-reports.example/{report_id}.pdf",
        generated_at=datetime.now(timezone.utc),
    )


@router.post("/flag_anomaly", response_model=FlagAnomalyResponse)
async def flag_anomaly(request: FlagAnomalyRequest) -> FlagAnomalyResponse:
    flag_id = f"flag_{uuid.uuid4().hex[:8]}"
    record = {
        "flag_id": flag_id,
        "record_id": request.record_id,
        "reason": request.reason,
        "flagged_at": datetime.now(timezone.utc).isoformat(),
    }
    _flagged_records.append(record)
    return FlagAnomalyResponse(
        flag_id=flag_id,
        record_id=request.record_id,
        reason=request.reason,
        flagged_at=datetime.now(timezone.utc),
    )
