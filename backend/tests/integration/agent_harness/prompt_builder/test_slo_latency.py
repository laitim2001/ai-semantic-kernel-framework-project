"""Sprint 52.2 Day 4.4 — SLO + tracer span integration (W3-2 carryover).

Verifies:
  - PromptBuilder.build() p50 / p95 / p99 over 100 runs (mocked deps).
  - LostInMiddle position-strategy accuracy over 50 prompts.
  - Tracer span emit count + name + attributes (tenant_id propagation).

W3-2 scope deviation (recorded in retrospective.md Audit Debt):
    Plan §4.4 expected child spans (memory_retrieval / cache_manager) AND a
    `prompt_builder_build_duration_seconds` metric emit count assertion.
    Day 1-2 design only emits ONE span per build() and no metrics — child
    span + metric instrumentation deferred to Phase 53.x (real OTel Tracer
    integration).
"""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from agent_harness._contracts import (
    DurableState,
    LoopState,
    Message,
    StateVersion,
    TransientState,
)
from agent_harness.context_mgmt.cache_manager import InMemoryCacheManager
from agent_harness.context_mgmt.token_counter.tiktoken_counter import (
    TiktokenCounter,
)
from agent_harness.memory.retrieval import MemoryRetrieval
from agent_harness.prompt_builder.builder import DefaultPromptBuilder


@dataclass
class _RecordedSpan:
    name: str
    parent_span_id: str | None
    attributes: dict[str, str]
    span_id: str = field(default_factory=lambda: uuid4().hex[:16])

    def end(self) -> None:
        return None


class _CaptureTracer:
    """Records every start_span call for assertions."""

    def __init__(self) -> None:
        self.spans: list[_RecordedSpan] = []

    def start_span(
        self,
        *,
        name: str,
        parent_span_id: str | None = None,
        attributes: dict[str, str] | None = None,
    ) -> _RecordedSpan:
        sp = _RecordedSpan(
            name=name,
            parent_span_id=parent_span_id,
            attributes=dict(attributes or {}),
        )
        self.spans.append(sp)
        return sp


def _state(tenant_id: UUID, msg_text: str = "ping") -> LoopState:
    return LoopState(
        transient=TransientState(messages=[Message(role="user", content=msg_text)]),
        durable=DurableState(session_id=uuid4(), tenant_id=tenant_id),
        version=StateVersion(
            version=1,
            parent_version=None,
            created_at=datetime.now(timezone.utc),
            created_by_category="orchestrator_loop",
        ),
    )


def _make_builder(tracer: _CaptureTracer) -> DefaultPromptBuilder:
    retrieval = MemoryRetrieval(layers={})

    async def _empty_search(*args: object, **kwargs: object) -> list[object]:
        return []

    retrieval.search = _empty_search  # type: ignore[method-assign]
    return DefaultPromptBuilder(
        memory_retrieval=retrieval,
        cache_manager=InMemoryCacheManager(),
        token_counter=TiktokenCounter(model="gpt-4o"),
        tracer=tracer,
    )


@pytest.mark.asyncio
async def test_build_p95_under_50ms_over_100_runs() -> None:
    """SLO: PromptBuilder.build() p95 < 50ms with mocked deps over 100 calls."""
    tracer = _CaptureTracer()
    builder = _make_builder(tracer)
    tenant_id = uuid4()

    durations_ms: list[float] = []
    for _ in range(100):
        state = _state(tenant_id)
        t0 = time.perf_counter()
        await builder.build(state=state, tenant_id=tenant_id)
        durations_ms.append((time.perf_counter() - t0) * 1000.0)

    p50 = statistics.median(durations_ms)
    sorted_d = sorted(durations_ms)
    p95 = sorted_d[int(len(sorted_d) * 0.95) - 1]
    p99 = sorted_d[int(len(sorted_d) * 0.99) - 1]

    print(
        f"\nbuild() latency over 100 runs: "
        f"p50={p50:.2f}ms p95={p95:.2f}ms p99={p99:.2f}ms"
    )
    assert p95 < 50.0, f"SLO violation: p95={p95:.2f}ms exceeds 50ms threshold"


@pytest.mark.asyncio
async def test_lost_in_middle_position_accuracy_over_50_runs() -> None:
    """LostInMiddle places system at index 0 and the latest user message last."""
    tracer = _CaptureTracer()
    builder = _make_builder(tracer)
    tenant_id = uuid4()

    correct = 0
    for i in range(50):
        state = _state(tenant_id, msg_text=f"query-{i}")
        artifact = await builder.build(state=state, tenant_id=tenant_id)

        msgs = artifact.messages
        if not msgs:
            continue
        first_is_system = msgs[0].role == "system"
        user_msgs = [m for m in msgs if m.role == "user"]
        last_user_correct = bool(user_msgs) and f"query-{i}" in str(
            user_msgs[-1].content
        )
        if first_is_system and last_user_correct:
            correct += 1

    print(f"\nLostInMiddle position accuracy: {correct}/50")
    assert correct == 50, f"Position accuracy below SLO: {correct}/50"


@pytest.mark.asyncio
async def test_tracer_emits_one_span_per_build() -> None:
    """100 build() -> 100 prompt_builder.build spans (Day 1-2 single-span design)."""
    tracer = _CaptureTracer()
    builder = _make_builder(tracer)
    tenant_id = uuid4()

    for _ in range(100):
        state = _state(tenant_id)
        await builder.build(state=state, tenant_id=tenant_id)

    assert len(tracer.spans) == 100
    assert all(sp.name == "prompt_builder.build" for sp in tracer.spans)


@pytest.mark.asyncio
async def test_tracer_attributes_propagate_tenant_id() -> None:
    """Span attributes include tenant_id for trace observability."""
    tracer = _CaptureTracer()
    builder = _make_builder(tracer)
    tenant_id = uuid4()

    state = _state(tenant_id)
    await builder.build(state=state, tenant_id=tenant_id)

    assert len(tracer.spans) == 1
    assert tracer.spans[0].attributes.get("tenant_id") == str(tenant_id)
