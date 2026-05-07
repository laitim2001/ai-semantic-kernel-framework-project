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
async def test_cost_ledger_service_record_llm_call_writes_two_entries(
    db_session: AsyncSession,
    loader: PricingLoader,
) -> None:
    """Sprint 57.2 — record_llm_call writes 2 ledger entries (input + output split).

    Replaces 56.3 single-entry combined test (closes AD-Cost-Ledger-Token-Split).
    Pricing now split: input * input_per_million / 1M + output * output_per_million / 1M.
    """
    t = await seed_tenant(db_session, code="CL_LLM_1")
    svc = CostLedgerService(db=db_session, pricing_loader=loader)

    entries = await svc.record_llm_call(
        tenant_id=t.id,
        provider="azure_openai",
        model="gpt-5.4",
        input_tokens=600,
        output_tokens=400,
    )
    assert len(entries) == 2
    input_entry, output_entry = entries[0], entries[1]
    # gpt-5.4: input=2.50/M, output=10.00/M
    assert input_entry.cost_type == "llm"
    assert input_entry.sub_type == "azure_openai_gpt-5.4_input"
    assert input_entry.quantity == Decimal("600")
    # 600 * 2.50 / 1_000_000 = 0.0015
    assert input_entry.total_cost_usd == Decimal("0.0015000000")
    assert output_entry.sub_type == "azure_openai_gpt-5.4_output"
    assert output_entry.quantity == Decimal("400")
    # 400 * 10.00 / 1_000_000 = 0.004
    assert output_entry.total_cost_usd == Decimal("0.0040000000")

    rows = (
        (await db_session.execute(select(CostLedger).where(CostLedger.tenant_id == t.id)))
        .scalars()
        .all()
    )
    assert len(rows) == 2


@pytest.mark.asyncio
async def test_cost_ledger_service_aggregate_groups_by_cost_type_and_sub_type(
    db_session: AsyncSession,
    loader: PricingLoader,
) -> None:
    """US-3 — aggregate(month) SUMs grouped by (cost_type, sub_type)."""
    t = await seed_tenant(db_session, code="CL_AGG_1")
    svc = CostLedgerService(db=db_session, pricing_loader=loader)

    # Sprint 57.2: each LLM call now writes 2 entries (input + output split).
    # 2 LLM calls × 2 entries = 4 LLM entries (2 input sub_type + 2 output sub_type)
    # + 2 tool entries (different tool names).
    await svc.record_llm_call(
        tenant_id=t.id,
        provider="azure_openai",
        model="gpt-5.4",
        input_tokens=500,
        output_tokens=200,
    )
    await svc.record_llm_call(
        tenant_id=t.id,
        provider="azure_openai",
        model="gpt-5.4",
        input_tokens=300,
        output_tokens=100,
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
    # Sprint 57.2: LLM split into 2 sub_types (_input + _output).
    # Each call contributes 1 entry per sub_type → entry_count=2 per sub_type.
    llm_input_slice = aggregated.by_type["llm"]["azure_openai_gpt-5.4_input"]
    llm_output_slice = aggregated.by_type["llm"]["azure_openai_gpt-5.4_output"]
    assert llm_input_slice.entry_count == 2
    assert llm_input_slice.quantity == Decimal("800")  # 500 + 300
    assert llm_output_slice.entry_count == 2
    assert llm_output_slice.quantity == Decimal("300")  # 200 + 100
    # Tool: 2 distinct sub_types, entry_count=1 each.
    assert aggregated.by_type["tool"]["salesforce_query"].entry_count == 1
    assert aggregated.by_type["tool"]["d365_create"].entry_count == 1
    # Total cost = sum across all slices > 0
    assert aggregated.total_cost_usd > Decimal("0")
