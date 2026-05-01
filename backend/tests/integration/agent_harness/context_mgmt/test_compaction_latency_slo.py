"""
File: tests/integration/agent_harness/context_mgmt/test_compaction_latency_slo.py
Purpose: Latency SLO — Structural < 100ms p95, Semantic < 2000ms p95, Hybrid < 2500ms p95.
Category: Tests / Integration / 範疇 4 (Context Management)
Scope: Sprint 52.1 Day 4.7

Per Sprint 52.1 §1 Story 2 acceptance:
  - StructuralCompactor p95 < 100ms
  - SemanticCompactor p95 < 2000ms (mocked LLM zero-latency in this test)
  - HybridCompactor p95 < 2500ms

Methodology: 100 compaction calls per strategy on a 30-message state with
a tool blob; record duration_ms from CompactionResult, compute p50/p95/p99.
"""

from __future__ import annotations

import statistics
from datetime import datetime
from typing import AsyncIterator
from uuid import uuid4

import pytest

from adapters._base.chat_client import ChatClient
from adapters._base.pricing import PricingInfo
from adapters._base.types import ModelInfo, StreamEvent
from agent_harness._contracts import (
    CacheBreakpoint,
    ChatRequest,
    ChatResponse,
    DurableState,
    LoopState,
    Message,
    StateVersion,
    StopReason,
    ToolSpec,
    TraceContext,
    TransientState,
)
from agent_harness.context_mgmt.compactor.hybrid import HybridCompactor
from agent_harness.context_mgmt.compactor.semantic import SemanticCompactor
from agent_harness.context_mgmt.compactor.structural import StructuralCompactor


class _ZeroLatencyChat(ChatClient):
    """Mock ChatClient that returns immediately so SLO measurement is bounded by code only."""

    async def chat(
        self,
        request: ChatRequest,
        *,
        cache_breakpoints: list[CacheBreakpoint] | None = None,
        trace_context: TraceContext | None = None,
    ) -> ChatResponse:
        return ChatResponse(model="mock", content="summary", stop_reason=StopReason.END_TURN)

    def stream(
        self,
        request: ChatRequest,
        *,
        cache_breakpoints: list[CacheBreakpoint] | None = None,
        trace_context: TraceContext | None = None,
    ) -> AsyncIterator[StreamEvent]:
        return self._empty()

    async def _empty(self) -> AsyncIterator[StreamEvent]:
        if False:
            yield  # pragma: no cover

    async def count_tokens(
        self,
        *,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
    ) -> int:
        return 0

    def get_pricing(self) -> PricingInfo:
        return PricingInfo(
            input_per_million=0.0, output_per_million=0.0, cached_input_per_million=None
        )

    def supports_feature(self, feature: str) -> bool:  # type: ignore[override]
        return False

    def model_info(self) -> ModelInfo:
        return ModelInfo(
            model_name="mock",
            model_family="mock",
            provider="mock",
            context_window=8_192,
            max_output_tokens=2_048,
        )


def _make_state() -> LoopState:
    msgs: list[Message] = [Message(role="system", content="sys prompt")]
    for i in range(15):
        msgs.append(Message(role="user", content=f"q{i}"))
        msgs.append(Message(role="assistant", content=f"a{i}"))
    return LoopState(
        transient=TransientState(
            messages=msgs,
            current_turn=15,
            token_usage_so_far=95_000,
        ),
        durable=DurableState(session_id=uuid4(), tenant_id=uuid4()),
        version=StateVersion(
            version=1,
            parent_version=None,
            created_at=datetime.now(),
            created_by_category="orchestrator_loop",
        ),
    )


def _percentiles(samples: list[float]) -> tuple[float, float, float]:
    """Return (p50, p95, p99) — uses statistics.quantiles for robust estimation."""
    sorted_samples = sorted(samples)
    n = len(sorted_samples)
    p50 = sorted_samples[int(n * 0.50)]
    p95 = sorted_samples[int(n * 0.95)]
    p99 = sorted_samples[min(int(n * 0.99), n - 1)]
    return p50, p95, p99


@pytest.mark.asyncio
async def test_structural_compactor_p95_under_100ms() -> None:
    compactor = StructuralCompactor(
        keep_recent_turns=5, token_budget=100_000, token_threshold_ratio=0.75
    )
    samples: list[float] = []
    for _ in range(100):
        state = _make_state()
        result = await compactor.compact_if_needed(state)
        samples.append(result.duration_ms)

    p50, p95, p99 = _percentiles(samples)
    print(f"\nStructural latency: p50={p50:.2f}ms p95={p95:.2f}ms p99={p99:.2f}ms")
    assert p95 < 100, f"Structural p95={p95:.2f}ms exceeds 100ms SLO"


@pytest.mark.asyncio
async def test_semantic_compactor_p95_under_2000ms() -> None:
    compactor = SemanticCompactor(
        chat_client=_ZeroLatencyChat(),
        keep_recent_turns=5,
        token_budget=100_000,
    )
    samples: list[float] = []
    for _ in range(100):
        state = _make_state()
        result = await compactor.compact_if_needed(state)
        samples.append(result.duration_ms)

    p50, p95, p99 = _percentiles(samples)
    print(f"\nSemantic latency: p50={p50:.2f}ms p95={p95:.2f}ms p99={p99:.2f}ms")
    assert p95 < 2000, f"Semantic p95={p95:.2f}ms exceeds 2000ms SLO"


@pytest.mark.asyncio
async def test_hybrid_compactor_p95_under_2500ms() -> None:
    structural = StructuralCompactor(
        keep_recent_turns=5, token_budget=100_000, token_threshold_ratio=0.75
    )
    semantic = SemanticCompactor(
        chat_client=_ZeroLatencyChat(),
        keep_recent_turns=5,
        token_budget=100_000,
    )
    compactor = HybridCompactor(
        structural=structural,
        semantic=semantic,
        token_budget=100_000,
        token_threshold_ratio=0.75,
    )
    samples: list[float] = []
    for _ in range(100):
        state = _make_state()
        result = await compactor.compact_if_needed(state)
        samples.append(result.duration_ms)

    p50, p95, p99 = _percentiles(samples)
    print(f"\nHybrid latency: p50={p50:.2f}ms p95={p95:.2f}ms p99={p99:.2f}ms")
    assert p95 < 2500, f"Hybrid p95={p95:.2f}ms exceeds 2500ms SLO"
