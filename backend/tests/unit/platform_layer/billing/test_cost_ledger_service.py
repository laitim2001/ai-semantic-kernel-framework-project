"""CostLedgerService tests (Sprint 56.3 Day 3 / US-3 + US-4)."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models.cost_ledger import CostLedger
from platform_layer.billing.cost_ledger import CostLedgerService
from platform_layer.billing.pricing import PricingLoader
from tests.conftest import seed_tenant

_PRICING_YAML = Path(__file__).resolve().parents[4] / "config" / "llm_pricing.yml"


@pytest.fixture
def loader() -> PricingLoader:
    pl = PricingLoader()
    pl.load_from_yaml(_PRICING_YAML)
    return pl


@pytest.mark.asyncio
async def test_cost_ledger_service_record_llm_call_writes_one_entry(
    db_session: AsyncSession,
    loader: PricingLoader,
) -> None:
    """US-3 — record_llm_call writes 1 ledger entry with computed cost."""
    t = await seed_tenant(db_session, code="CL_LLM_1")
    svc = CostLedgerService(db=db_session, pricing_loader=loader)

    entry = await svc.record_llm_call(
        tenant_id=t.id,
        provider="azure_openai",
        model="gpt-5.4",
        total_tokens=1_000,
    )
    assert entry.cost_type == "llm"
    assert entry.sub_type == "azure_openai_gpt-5.4_total"
    assert entry.quantity == Decimal("1000")
    # avg_per_million = (2.50 + 10.00) / 2 = 6.25 USD/M; cost for 1000 tokens
    # = 1000 * 6.25 / 1_000_000 = 0.00625
    assert entry.total_cost_usd == Decimal("0.0062500000")

    rows = (
        (await db_session.execute(select(CostLedger).where(CostLedger.tenant_id == t.id)))
        .scalars()
        .all()
    )
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_cost_ledger_service_aggregate_groups_by_cost_type_and_sub_type(
    db_session: AsyncSession,
    loader: PricingLoader,
) -> None:
    """US-3 — aggregate(month) SUMs grouped by (cost_type, sub_type)."""
    t = await seed_tenant(db_session, code="CL_AGG_1")
    svc = CostLedgerService(db=db_session, pricing_loader=loader)

    # 2 LLM entries (same sub_type) + 2 tool entries (different tool names).
    await svc.record_llm_call(
        tenant_id=t.id, provider="azure_openai", model="gpt-5.4", total_tokens=500
    )
    await svc.record_llm_call(
        tenant_id=t.id, provider="azure_openai", model="gpt-5.4", total_tokens=300
    )
    await svc.record_tool_call(tenant_id=t.id, tool_name="salesforce_query")
    await svc.record_tool_call(tenant_id=t.id, tool_name="d365_create")

    # Pull the year-month from the most recent entry to avoid month boundary edge.
    most_recent = (
        await db_session.execute(
            select(CostLedger.recorded_at)
            .where(CostLedger.tenant_id == t.id)
            .order_by(CostLedger.recorded_at.desc())
            .limit(1)
        )
    ).scalar_one()
    month = most_recent.strftime("%Y-%m")

    aggregated = await svc.aggregate(tenant_id=t.id, month=month)
    assert "llm" in aggregated.by_type
    assert "tool" in aggregated.by_type
    # LLM grouped under one sub_type — entry_count = 2.
    llm_slice = aggregated.by_type["llm"]["azure_openai_gpt-5.4_total"]
    assert llm_slice.entry_count == 2
    assert llm_slice.quantity == Decimal("800")  # 500 + 300
    # Tool: 2 distinct sub_types, entry_count=1 each.
    assert aggregated.by_type["tool"]["salesforce_query"].entry_count == 1
    assert aggregated.by_type["tool"]["d365_create"].entry_count == 1
    # Total cost = sum across all slices > 0
    assert aggregated.total_cost_usd > Decimal("0")
