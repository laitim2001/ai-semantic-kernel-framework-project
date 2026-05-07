"""
File: backend/tests/integration/api/test_chat_cost_ledger.py
Purpose: Integration — chat router LoopCompleted + ToolCallExecuted → CostLedger entries.
Category: Tests / Integration / API (Phase 56 SaaS Stage 1)
Scope: Sprint 56.3 / Day 3 / 1 integration US-4.

Description:
    Drives _stream_loop_events with a stub loop yielding both
    ToolCallExecuted (1) + LoopCompleted (1). Asserts both ledger
    entries land in cost_ledger table with proper tenant_id + cost_type.

Created: 2026-05-06 (Sprint 56.3 Day 3)
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_harness._contracts import LoopCompleted, TraceContext
from agent_harness._contracts.events import ToolCallExecuted
from api.v1.chat.router import _stream_loop_events
from api.v1.chat.session_registry import SessionRegistry
from infrastructure.db.models.cost_ledger import CostLedger
from platform_layer.billing.cost_ledger import CostLedgerService
from platform_layer.billing.pricing import PricingLoader
from tests.conftest import seed_tenant

pytestmark = pytest.mark.asyncio

_PRICING_YAML = Path(__file__).resolve().parents[3] / "config" / "llm_pricing.yml"


class _StubLoop:
    """Yields ToolCallExecuted + LoopCompleted (1 of each) for chat router observer."""

    def __init__(
        self,
        input_tokens: int = 0,
        output_tokens: int = 0,
        tool_name: str = "salesforce_query",
        provider: str = "azure_openai",
        model: str = "gpt-5.4",
    ) -> None:
        self._input_tokens = input_tokens
        self._output_tokens = output_tokens
        self._tool_name = tool_name
        self._provider = provider
        self._model = model

    async def run(
        self,
        *,
        session_id: UUID,
        user_input: str,
        trace_context: TraceContext,
    ) -> AsyncIterator[object]:
        yield ToolCallExecuted(
            tool_call_id="tc-1",
            tool_name=self._tool_name,
            duration_ms=12.0,
            result_content="ok",
            trace_context=trace_context,
        )
        # Sprint 57.2: LoopCompleted carries split + provider/model
        # (closes AD-Cost-Ledger-Token-Split + Provider-Attribution).
        yield LoopCompleted(
            stop_reason="end_turn",
            total_turns=1,
            total_tokens=self._input_tokens + self._output_tokens,
            input_tokens=self._input_tokens,
            output_tokens=self._output_tokens,
            provider=self._provider,
            model=self._model,
            trace_context=trace_context,
        )


async def _consume(stream: AsyncIterator[bytes]) -> None:
    async for _ in stream:
        pass


async def test_chat_request_writes_cost_ledger_end_to_end(
    db_session: AsyncSession,
) -> None:
    """US-4 — full chat run yields LLM + tool ledger entries in cost_ledger table."""
    t = await seed_tenant(db_session, code="CL_E2E_1")
    session_id = uuid4()
    registry = SessionRegistry()
    await registry.register(t.id, session_id)

    pricing = PricingLoader()
    pricing.load_from_yaml(_PRICING_YAML)
    cost_ledger = CostLedgerService(db=db_session, pricing_loader=pricing)

    stub_loop = _StubLoop(
        input_tokens=1_200,
        output_tokens=800,
        tool_name="salesforce_query",
    )
    trace_ctx = TraceContext(tenant_id=t.id, session_id=session_id)

    await _consume(
        _stream_loop_events(
            stub_loop,
            t.id,
            session_id,
            registry,
            user_input="hello",
            trace_context=trace_ctx,
            cost_ledger=cost_ledger,
        )
    )

    rows = (
        (
            await db_session.execute(
                select(CostLedger)
                .where(CostLedger.tenant_id == t.id)
                .order_by(CostLedger.recorded_at)
            )
        )
        .scalars()
        .all()
    )

    cost_types = {r.cost_type for r in rows}
    assert "llm" in cost_types
    assert "tool" in cost_types
    # Sprint 57.2: 2 LLM entries (input + output split) + 1 tool entry = 3 total.
    assert len(rows) == 3

    # Both LLM entries have provider/model attribution + session_id.
    llm_rows = [r for r in rows if r.cost_type == "llm"]
    assert len(llm_rows) == 2
    sub_types = {r.sub_type for r in llm_rows}
    assert sub_types == {
        "azure_openai_gpt-5.4_input",
        "azure_openai_gpt-5.4_output",
    }
    assert all(r.session_id == session_id for r in llm_rows)

    # Tool entry sub_type = the tool name.
    tool_row = next(r for r in rows if r.cost_type == "tool")
    assert tool_row.sub_type == "salesforce_query"
    assert tool_row.session_id == session_id
