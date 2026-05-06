"""
File: backend/tests/integration/api/test_phase56_3_e2e.py
Purpose: Cross-AD e2e — Phase 56.3 SLA Monitor + Cost Ledger combined chat flow.
Category: Tests / Integration / API (Phase 56 SaaS Stage 1)
Scope: Sprint 56.3 / Day 4 / US-5 closeout cross-AD e2e

Description:
    Single integrated chat flow that exercises:
    - US-1 SLAMetricRecorder: record_loop_completion called via chat router
      observer; classify_loop_complexity bucket recorded in Redis sliding
      window; get_loop_p99 returns the recorded latency.
    - US-3 + US-4 CostLedgerService: LoopCompleted observer writes 1 LLM
      ledger entry; ToolCallExecuted observer writes 1 tool ledger entry;
      aggregate(month) returns by_type breakdown with total_cost_usd > 0.
    - US-2 + US-3 quota carryover from 56.2 (still in chat router):
      pre-call estimate + post-call reconcile via record_usage.
    - All 4 hooks coexist in single _stream_loop_events run without
      breaking SSE event stream (best-effort failure pattern).

    Uses fakeredis + real db_session fixture (Postgres testcontainer per
    conftest.py). Stub loop yields ToolCallExecuted + LoopCompleted with
    known total_tokens to exercise both Cost Ledger code paths.

Created: 2026-05-06 (Sprint 56.3 Day 4 / US-5 closeout)
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fakeredis import FakeAsyncRedis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_harness._contracts import LoopCompleted, TraceContext
from agent_harness._contracts.events import ToolCallExecuted
from api.v1.chat.router import _stream_loop_events
from api.v1.chat.session_registry import SessionRegistry
from infrastructure.db.models.cost_ledger import CostLedger
from platform_layer.billing.cost_ledger import CostLedgerService
from platform_layer.billing.pricing import PricingLoader
from platform_layer.observability.sla_monitor import SLAMetricRecorder
from platform_layer.tenant.plans import PlanLoader
from platform_layer.tenant.quota import QuotaEnforcer
from tests.conftest import seed_tenant

pytestmark = pytest.mark.asyncio

_PRICING_YAML = Path(__file__).resolve().parents[3] / "config" / "llm_pricing.yml"


class _StubLoopWithToolAndCompletion:
    """Stub agent loop emitting ToolCallExecuted + LoopCompleted in one run."""

    def __init__(self, *, total_tokens: int, tool_name: str) -> None:
        self._total_tokens = total_tokens
        self._tool_name = tool_name

    async def run(
        self,
        *,
        session_id: UUID,
        user_input: str,
        trace_context: TraceContext,
    ) -> AsyncIterator[object]:
        yield ToolCallExecuted(
            tool_call_id="tc-e2e-1",
            tool_name=self._tool_name,
            duration_ms=15.0,
            result_content="ok",
            trace_context=trace_context,
        )
        yield LoopCompleted(
            stop_reason="end_turn",
            total_turns=1,
            total_tokens=self._total_tokens,
            trace_context=trace_context,
        )


async def _consume(stream: AsyncIterator[bytes]) -> None:
    async for _ in stream:
        pass


async def test_phase56_3_cross_ad_full_flow(db_session: AsyncSession) -> None:
    """Single chat flow exercises US-1 (SLA) + US-3+4 (Cost Ledger) + 56.2 carryover (quota)."""
    # Setup: real tenant + fakeredis SLA recorder + fakeredis QuotaEnforcer +
    # PricingLoader-backed CostLedgerService.
    t = await seed_tenant(db_session, code="P563_E2E")
    tenant_id = t.id
    session_id = uuid4()

    redis = FakeAsyncRedis()
    sla_recorder = SLAMetricRecorder(redis_client=redis)
    quota_enforcer = QuotaEnforcer(client=redis, plan_loader=PlanLoader())
    pricing = PricingLoader()
    pricing.load_from_yaml(_PRICING_YAML)
    cost_ledger = CostLedgerService(db=db_session, pricing_loader=pricing)

    registry = SessionRegistry()
    await registry.register(tenant_id, session_id)

    # 56.2 carryover (US-2 + US-3): pre-call estimate + reserve.
    msg = "x" * 800
    estimated_tokens = quota_enforcer.estimate_pre_call_tokens(msg, fallback=1000)
    assert estimated_tokens == 200, f"56.2 estimate wrong: {estimated_tokens}"
    await quota_enforcer.check_and_reserve(
        tenant_id=tenant_id, plan_name="enterprise", estimated_tokens=estimated_tokens
    )
    assert await quota_enforcer.get_usage(tenant_id) == 200

    # Stub loop emits 1 ToolCallExecuted + 1 LoopCompleted.
    stub_loop = _StubLoopWithToolAndCompletion(total_tokens=120, tool_name="salesforce_query")
    trace_ctx = TraceContext(tenant_id=tenant_id, session_id=session_id)
    chat_start_time = time.monotonic()

    await _consume(
        _stream_loop_events(
            stub_loop,
            tenant_id,
            session_id,
            registry,
            user_input=msg,
            trace_context=trace_ctx,
            quota_enforcer=quota_enforcer,
            estimated_tokens=estimated_tokens,
            sla_recorder=sla_recorder,
            chat_start_time=chat_start_time,
            cost_ledger=cost_ledger,
        )
    )

    # === US-1 (SLA) assertion ===
    # complexity = simple (turns=1, tokens=120 < 1500); recorded in 5-min window.
    p99 = await sla_recorder.get_loop_p99(tenant_id, complexity_category="simple")
    assert p99 is not None, "US-1: SLA loop_completion not recorded"
    # Latency may be 0 ms in test (sub-millisecond stub-loop run); presence of
    # a record is what US-1 closeout asserts (recorder wired into chat router).
    assert p99 >= 0, f"US-1: SLA latency must be >= 0, got {p99}"

    # === US-3 + US-4 (Cost Ledger) assertions ===
    rows = (
        (
            await db_session.execute(
                select(CostLedger)
                .where(CostLedger.tenant_id == tenant_id)
                .order_by(CostLedger.recorded_at)
            )
        )
        .scalars()
        .all()
    )
    cost_types = {r.cost_type for r in rows}
    assert "llm" in cost_types, "US-4: LLM ledger entry missing"
    assert "tool" in cost_types, "US-4: Tool ledger entry missing"
    assert len(rows) == 2, f"US-4: expected 2 entries (1 LLM + 1 tool), got {len(rows)}"

    llm_row = next(r for r in rows if r.cost_type == "llm")
    assert llm_row.sub_type == "azure_openai_gpt-5.4_total"
    assert llm_row.session_id == session_id

    tool_row = next(r for r in rows if r.cost_type == "tool")
    assert tool_row.sub_type == "salesforce_query"
    assert tool_row.session_id == session_id

    # US-3 aggregate API works end-to-end.
    month = llm_row.recorded_at.strftime("%Y-%m")
    aggregate = await cost_ledger.aggregate(tenant_id=tenant_id, month=month)
    assert aggregate.total_cost_usd > 0, "US-3: aggregate total_cost_usd must be > 0"
    assert "llm" in aggregate.by_type
    assert "tool" in aggregate.by_type

    # === 56.2 carryover (quota US-3) assertion ===
    # Reserved 200 → actual 120 → counter reconciled to 120.
    final_usage = await quota_enforcer.get_usage(tenant_id)
    assert final_usage == 120, f"56.2 reconciliation wrong: {final_usage}"
