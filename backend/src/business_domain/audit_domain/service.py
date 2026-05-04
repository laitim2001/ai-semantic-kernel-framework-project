"""
File: backend/src/business_domain/audit_domain/service.py
Purpose: AuditService — query audit_log table (08b §Domain 4).
Category: Business Domain / audit_domain — service layer
Scope: Sprint 55.1 US-3 / Day 3.1d

Description:
    query_logs() reads the existing `audit_log` table (Sprint 49.3 Day 1
    schema; append-only + hash chained). Tenant-filtered with optional
    time range (timestamp_ms BIGINT) + operation filter.

    Sprint 55.1 keeps this domain READ-ONLY at production layer. The
    higher-risk audit_flag_anomaly tool stays mock-backed for now and may
    move to a separate sprint when its destructive semantics are designed.

Created: 2026-05-04 (Sprint 55.1 Day 3)
Last Modified: 2026-05-04

Modification History:
    - 2026-05-04: Initial creation (Sprint 55.1 Day 3.1d)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from business_domain._base import BusinessServiceBase
from business_domain._obs import business_service_span
from infrastructure.db.models import AuditLog


class AuditService(BusinessServiceBase):
    """Read-only audit query service; tenant-filtered audit_log walk."""

    SERVICE_NAME = "audit"

    async def query_logs(
        self,
        *,
        start_ms: int | None = None,
        end_ms: int | None = None,
        operation: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Query audit_log entries in tenant scope.

        Args:
            start_ms: inclusive lower bound on timestamp_ms (None → no lower bound).
            end_ms:   exclusive upper bound (None → no upper bound).
            operation: optional exact-match filter on AuditLog.operation.
            limit: max rows (default 50; service-level cap, not DB limit).

        Returns:
            List of dicts with the audit log fields the caller needs (no ORM
            row leakage; serializable JSON-friendly shape).
        """
        async with business_service_span(
            self.tracer, service_name=self.SERVICE_NAME, method="query_logs"
        ):
            stmt = select(AuditLog).where(AuditLog.tenant_id == self.tenant_id)
            if start_ms is not None:
                stmt = stmt.where(AuditLog.timestamp_ms >= start_ms)
            if end_ms is not None:
                stmt = stmt.where(AuditLog.timestamp_ms < end_ms)
            if operation is not None:
                stmt = stmt.where(AuditLog.operation == operation)
            stmt = stmt.order_by(AuditLog.timestamp_ms.desc()).limit(limit)

            rows = (await self.db.execute(stmt)).scalars().all()
            return [
                {
                    "id": r.id,
                    "tenant_id": str(self.tenant_id),
                    "operation": r.operation,
                    "resource_type": r.resource_type,
                    "resource_id": r.resource_id,
                    "operation_data": r.operation_data,
                    "timestamp_ms": r.timestamp_ms,
                    "timestamp_iso": datetime.fromtimestamp(
                        r.timestamp_ms / 1000, tz=timezone.utc
                    ).isoformat(),
                }
                for r in rows
            ]


__all__ = ["AuditService"]
