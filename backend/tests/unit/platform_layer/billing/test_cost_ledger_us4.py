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
    """Cached portion uses cached_input_per_million; remainder at average."""
    t = await seed_tenant(db_session, code="US4_CACHED")
    svc = CostLedgerService(db=db_session, pricing_loader=loader)
    # 1000 total tokens; 500 cached. azure_openai/gpt-5.4 cached=1.25, avg=6.25.
    # cached cost = 500 * 1.25 / 1M = 0.000625
    # billable cost = 500 * 6.25 / 1M = 0.003125
    # total = 0.00375
    entry = await svc.record_llm_call(
        tenant_id=t.id,
        provider="azure_openai",
        model="gpt-5.4",
        total_tokens=1_000,
        cached_input_tokens=500,
    )
    assert entry.total_cost_usd == Decimal("0.0037500000")


@pytest.mark.asyncio
async def test_record_llm_call_unknown_provider_uses_zero_cost(
    db_session: AsyncSession,
    loader: PricingLoader,
) -> None:
    """Defensive — unknown provider/model → entry persisted with cost=0."""
    t = await seed_tenant(db_session, code="US4_UNK")
    svc = CostLedgerService(db=db_session, pricing_loader=loader)
    entry = await svc.record_llm_call(
        tenant_id=t.id,
        provider="bogus_provider",
        model="bogus_model",
        total_tokens=1_000,
    )
    assert entry.total_cost_usd == Decimal("0E-10") or entry.total_cost_usd == Decimal("0")
    assert entry.sub_type == "bogus_provider_bogus_model_total"


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
    """Multi-tenant 鐵律: ledger entries scope strictly to tenant_id."""
    t_a = await seed_tenant(db_session, code="US4_ISO_A")
    t_b = await seed_tenant(db_session, code="US4_ISO_B")
    svc = CostLedgerService(db=db_session, pricing_loader=loader)

    await svc.record_llm_call(
        tenant_id=t_a.id, provider="azure_openai", model="gpt-5.4", total_tokens=100
    )
    await svc.record_llm_call(
        tenant_id=t_b.id, provider="azure_openai", model="gpt-5.4", total_tokens=999
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
    assert len(rows_a) == 1 and rows_a[0].quantity == Decimal("100")
    assert len(rows_b) == 1 and rows_b[0].quantity == Decimal("999")
