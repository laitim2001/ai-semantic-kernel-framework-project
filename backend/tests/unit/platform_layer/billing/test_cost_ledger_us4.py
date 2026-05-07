"""5 unit tests for US-4 Cost Ledger LLM/tool hooks (Sprint 56.3 Day 3)."""

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
async def test_record_llm_call_uses_cached_pricing_when_cached_input(
    db_session: AsyncSession,
    loader: PricingLoader,
) -> None:
    """Cached portion uses cached_input_per_million; remainder at input rate.

    Sprint 57.2: signature changed to input_tokens + output_tokens (split).
    For this cached-pricing test, all 1000 tokens are input (output=0).
      cached cost   = 500 * 1.25 / 1M = 0.000625
      billable input= 500 * 2.50 / 1M = 0.001250
      input total   = 0.001875
      output total  = 0 (output_tokens=0)
    """
    t = await seed_tenant(db_session, code="US4_CACHED")
    svc = CostLedgerService(db=db_session, pricing_loader=loader)
    entries = await svc.record_llm_call(
        tenant_id=t.id,
        provider="azure_openai",
        model="gpt-5.4",
        input_tokens=1_000,
        output_tokens=0,
        cached_input_tokens=500,
    )
    assert len(entries) == 2
    input_entry, output_entry = entries[0], entries[1]
    assert input_entry.sub_type == "azure_openai_gpt-5.4_input"
    assert output_entry.sub_type == "azure_openai_gpt-5.4_output"
    assert input_entry.total_cost_usd == Decimal("0.0018750000")
    assert output_entry.total_cost_usd == Decimal(
        "0E-10"
    ) or output_entry.total_cost_usd == Decimal("0")


@pytest.mark.asyncio
async def test_record_llm_call_unknown_provider_uses_zero_cost(
    db_session: AsyncSession,
    loader: PricingLoader,
) -> None:
    """Defensive — unknown provider/model → both entries persisted with cost=0.

    Sprint 57.2: split into input + output entries; both zero-cost when
    pricing missing. sub_type carries provider/model attribution for
    monthly anomaly surface.
    """
    t = await seed_tenant(db_session, code="US4_UNK")
    svc = CostLedgerService(db=db_session, pricing_loader=loader)
    entries = await svc.record_llm_call(
        tenant_id=t.id,
        provider="bogus_provider",
        model="bogus_model",
        input_tokens=600,
        output_tokens=400,
    )
    assert len(entries) == 2
    for e in entries:
        assert e.total_cost_usd == Decimal("0E-10") or e.total_cost_usd == Decimal("0")
    assert entries[0].sub_type == "bogus_provider_bogus_model_input"
    assert entries[1].sub_type == "bogus_provider_bogus_model_output"


@pytest.mark.asyncio
async def test_record_tool_call_uses_default_pricing_when_unknown(
    db_session: AsyncSession,
    loader: PricingLoader,
) -> None:
    """Unknown tool name falls back to default_per_call from yaml (0.0001)."""
    t = await seed_tenant(db_session, code="US4_TOOL_UNK")
    svc = CostLedgerService(db=db_session, pricing_loader=loader)
    entry = await svc.record_tool_call(tenant_id=t.id, tool_name="never_seen_tool")
    assert entry.unit_cost_usd == Decimal("0.0001")
    assert entry.total_cost_usd == Decimal("0.0001")
    assert entry.sub_type == "never_seen_tool"


@pytest.mark.asyncio
async def test_record_tool_call_uses_override_pricing_when_known(
    db_session: AsyncSession,
    loader: PricingLoader,
) -> None:
    """Known tool name uses yaml override (salesforce_query=0.001)."""
    t = await seed_tenant(db_session, code="US4_TOOL_KNOWN")
    svc = CostLedgerService(db=db_session, pricing_loader=loader)
    entry = await svc.record_tool_call(tenant_id=t.id, tool_name="salesforce_query")
    assert entry.unit_cost_usd == Decimal("0.001")


@pytest.mark.asyncio
async def test_record_llm_call_per_tenant_isolation(
    db_session: AsyncSession,
    loader: PricingLoader,
) -> None:
    """Multi-tenant 鐵律: ledger entries scope strictly to tenant_id.

    Sprint 57.2: each call writes 2 entries (input + output); tenant
    isolation invariant unchanged.
    """
    t_a = await seed_tenant(db_session, code="US4_ISO_A")
    t_b = await seed_tenant(db_session, code="US4_ISO_B")
    svc = CostLedgerService(db=db_session, pricing_loader=loader)

    await svc.record_llm_call(
        tenant_id=t_a.id,
        provider="azure_openai",
        model="gpt-5.4",
        input_tokens=80,
        output_tokens=20,
    )
    await svc.record_llm_call(
        tenant_id=t_b.id,
        provider="azure_openai",
        model="gpt-5.4",
        input_tokens=700,
        output_tokens=299,
    )

    rows_a = (
        (await db_session.execute(select(CostLedger).where(CostLedger.tenant_id == t_a.id)))
        .scalars()
        .all()
    )
    rows_b = (
        (await db_session.execute(select(CostLedger).where(CostLedger.tenant_id == t_b.id)))
        .scalars()
        .all()
    )
    assert len(rows_a) == 2  # input + output split
    assert {r.sub_type for r in rows_a} == {
        "azure_openai_gpt-5.4_input",
        "azure_openai_gpt-5.4_output",
    }
    assert {r.quantity for r in rows_a} == {Decimal("80"), Decimal("20")}
    assert len(rows_b) == 2
    assert {r.quantity for r in rows_b} == {Decimal("700"), Decimal("299")}
