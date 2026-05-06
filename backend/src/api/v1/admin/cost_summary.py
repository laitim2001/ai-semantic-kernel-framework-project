"""
File: backend/src/api/v1/admin/cost_summary.py
Purpose: GET /api/v1/admin/tenants/{tenant_id}/cost-summary?month=YYYY-MM endpoint.
Category: API / Admin (Phase 56 SaaS Stage 1)
Scope: Sprint 56.3 / Day 3 / US-3 Cost Ledger.

Description:
    Returns per-tenant per-month aggregated cost ledger (LLM + tool + storage)
    with breakdown by cost_type and sub_type. Reads from CostLedgerService
    (singleton wired at app startup or test fixture).

    Auth: `require_admin_platform_role` (consistent admin endpoint pattern).

Created: 2026-05-06 (Sprint 56.3 Day 3)

Modification History:
    - 2026-05-06: Initial creation (Sprint 56.3 Day 3 / US-3)

Related:
    - sprint-56-3-plan.md §US-3
    - platform_layer/billing/cost_ledger.py (CostLedgerService.aggregate)
    - api/v1/admin/sla_reports.py (sibling endpoint pattern)
"""

from __future__ import annotations

import re
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.session import get_db_session
from platform_layer.billing import CostLedgerService, get_pricing_loader
from platform_layer.identity.auth import require_admin_platform_role

router = APIRouter(prefix="/admin/tenants", tags=["admin", "cost"])

_MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class AggregatedSliceResponse(BaseModel):
    quantity: Decimal
    total_cost_usd: Decimal
    entry_count: int


class CostSummaryResponse(BaseModel):
    tenant_id: UUID
    month: str
    total_cost_usd: Decimal
    by_type: dict[str, dict[str, AggregatedSliceResponse]]


@router.get(
    "/{tenant_id}/cost-summary",
    response_model=CostSummaryResponse,
    dependencies=[Depends(require_admin_platform_role)],
)
async def get_cost_summary(
    tenant_id: UUID,
    month: str = Query(..., description="YYYY-MM format"),
    db: AsyncSession = Depends(get_db_session),
) -> CostSummaryResponse:
    """Return per-month aggregated cost ledger for tenant."""
    if not _MONTH_PATTERN.match(month):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="month must be YYYY-MM",
        )
    pricing = get_pricing_loader()
    service = CostLedgerService(db=db, pricing_loader=pricing)
    aggregated = await service.aggregate(tenant_id=tenant_id, month=month)

    by_type_payload: dict[str, dict[str, AggregatedSliceResponse]] = {
        cost_type: {
            sub_type: AggregatedSliceResponse(
                quantity=slice_data.quantity,
                total_cost_usd=slice_data.total_cost_usd,
                entry_count=slice_data.entry_count,
            )
            for sub_type, slice_data in sub_types.items()
        }
        for cost_type, sub_types in aggregated.by_type.items()
    }

    return CostSummaryResponse(
        tenant_id=aggregated.tenant_id,
        month=aggregated.month,
        total_cost_usd=aggregated.total_cost_usd,
        by_type=by_type_payload,
    )
