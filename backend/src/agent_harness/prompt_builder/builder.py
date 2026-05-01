"""
File: backend/src/agent_harness/prompt_builder/builder.py
Purpose: DefaultPromptBuilder — concrete impl of PromptBuilder ABC (Cat 5).
Category: 範疇 5 (Prompt Construction)
Scope: Phase 52 / Sprint 52.2 (Day 1.6 — skeleton; Day 2 wires memory/cache)

Description:
    DefaultPromptBuilder is the single entry point for LLM prompt assembly.
    It assembles 6 sections (system / tools / memory_layers / conversation /
    user_message), runs them through a PositionStrategy, builds cache
    breakpoints, estimates tokens, and returns a PromptArtifact.

    Day 1 scope (this commit):
      - Constructor accepts 7 DI (memory_retrieval / cache_manager /
        token_counter / tracer / default_strategy / default_cache_policy /
        templates_overrides)
      - build() entry emits tracer span + child TraceContext (W3-2 carryover)
      - 4 sections wired (system / tools passthrough / conversation / user)
      - Memory injection STUB (returns {}; Day 2.1 wires real call)
      - Cache breakpoint STUB (returns []; Day 2.3 wires real call)
      - Position strategy applied + token estimation real

    Day 2+ wires _inject_memory_layers + _build_cache_breakpoints to real
    51.2 MemoryRetrieval + 52.1 PromptCacheManager.

    Anti-pattern AP-8 (No Centralized PromptBuilder) — V1 violated by
    scattering prompt assembly. V2 forbids ad-hoc messages = [{...}]
    construction; CI lint rule enforces in 52.2 Day 4.

    W3-2 audit carryover (multi-tenant + observability cross-cutting):
      - tenant_id REQUIRED (per multi-tenant-data.md tri-rule)
      - tracer span emitted at build() entry
      - trace_context propagated to memory_retrieval / cache_manager
      - NO process-wide cache fallback (per plan §2.5)

Owner: 01-eleven-categories-spec.md §範疇 5

Created: 2026-05-01 (Sprint 52.2 Day 1.6)

Related:
    - sprint-52-2-plan.md §2.4 / §2.5 / §2.6
    - claudedocs/5-status/V2-AUDIT-WEEK3-SUMMARY.md §3 (W3-2 critical findings)
    - .claude/rules/observability-instrumentation.md
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable
from uuid import UUID, uuid4

from agent_harness._contracts import (
    CacheBreakpoint,
    CachePolicy,
    LoopState,
    MemoryHint,
    Message,
    PromptArtifact,
    ToolSpec,
    TraceContext,
)
from agent_harness.context_mgmt.cache_manager import PromptCacheManager
from agent_harness.context_mgmt.token_counter._abc import TokenCounter
from agent_harness.memory.retrieval import MemoryRetrieval
from agent_harness.prompt_builder._abc import PromptBuilder
from agent_harness.prompt_builder.strategies import (
    LostInMiddleStrategy,
    PositionStrategy,
    PromptSections,
)
from agent_harness.prompt_builder.templates import SYSTEM_ROLE_TEMPLATE


# ---------------------------------------------------------------------------
# Tracer protocol (Cat 12 Day 1 minimal stub; replaced by real OTel in 53.x)
# ---------------------------------------------------------------------------


@runtime_checkable
class _Span(Protocol):
    """Duck-typed span; real impl in Cat 12 module (Phase 53.x)."""

    span_id: str

    def end(self) -> None: ...


@runtime_checkable
class Tracer(Protocol):
    """Duck-typed tracer; real impl in Cat 12 module (Phase 53.x).

    Day 1.6 default = NoOpTracer (below). DefaultPromptBuilder.__init__
    accepts any object satisfying this Protocol — tests can inject
    MockTracer for span assertions, real OTel SDK arrives in 53.x.
    """

    def start_span(
        self,
        *,
        name: str,
        parent_span_id: str | None = None,
        attributes: dict[str, str] | None = None,
    ) -> _Span: ...


@dataclass
class _NoOpSpan:
    """No-op span used when builder constructed without tracer."""

    span_id: str = field(default_factory=lambda: uuid4().hex[:16])
    _start: float = field(default_factory=time.perf_counter)

    @property
    def duration_seconds(self) -> float:
        return time.perf_counter() - self._start

    def end(self) -> None:
        return None


class _NoOpTracer:
    """No-op tracer: produces _NoOpSpan; no metric emission."""

    def start_span(
        self,
        *,
        name: str,
        parent_span_id: str | None = None,
        attributes: dict[str, str] | None = None,
    ) -> _Span:
        return _NoOpSpan()


# ---------------------------------------------------------------------------
# DefaultPromptBuilder
# ---------------------------------------------------------------------------


class DefaultPromptBuilder(PromptBuilder):
    """6-section layered prompt assembly with strategy + cache + memory injection.

    Constructor DI (per plan §2.4 + W3-2 carryover Day 1.6 update):
      - memory_retrieval: 51.2 MemoryRetrieval (cross-layer search coordinator)
      - cache_manager: 52.1 PromptCacheManager (tenant-scoped breakpoint hints)
      - token_counter: 52.1 TokenCounter (per-provider exact / approx)
      - tracer: Cat 12 Tracer protocol (default = _NoOpTracer)
      - default_strategy: PositionStrategy (default = LostInMiddleStrategy)
      - default_cache_policy: CachePolicy (default = CachePolicy() with all flags)
      - system_role_text: override of SYSTEM_ROLE_TEMPLATE for tenant-specific role
    """

    def __init__(
        self,
        *,
        memory_retrieval: MemoryRetrieval,
        cache_manager: PromptCacheManager,
        token_counter: TokenCounter,
        tracer: Tracer | None = None,
        default_strategy: PositionStrategy | None = None,
        default_cache_policy: CachePolicy | None = None,
        system_role_text: str | None = None,
    ) -> None:
        self._memory_retrieval = memory_retrieval
        self._cache_manager = cache_manager
        self._token_counter = token_counter
        self._tracer: Tracer = tracer if tracer is not None else _NoOpTracer()
        self._default_strategy: PositionStrategy = (
            default_strategy if default_strategy is not None else LostInMiddleStrategy()
        )
        self._default_cache_policy: CachePolicy = (
            default_cache_policy if default_cache_policy is not None else CachePolicy()
        )
        self._system_role_text = system_role_text or SYSTEM_ROLE_TEMPLATE

    async def build(
        self,
        *,
        state: LoopState,
        tenant_id: UUID,
        user_id: UUID | None = None,
        tools: list[ToolSpec] | None = None,
        cache_policy: CachePolicy | None = None,
        position_strategy: PositionStrategy | None = None,
        trace_context: TraceContext | None = None,
    ) -> PromptArtifact:
        """Assemble PromptArtifact with span + propagation (W3-2 carryover)."""
        # --- Step 0: tracer span + child TraceContext (W3-2) ---
        span = self._tracer.start_span(
            name="prompt_builder.build",
            parent_span_id=trace_context.span_id if trace_context else None,
            attributes={
                "tenant_id": str(tenant_id),
                "agent": self.__class__.__name__,
            },
        )
        child_ctx = TraceContext(
            trace_id=trace_context.trace_id if trace_context else uuid4().hex,
            span_id=span.span_id,
            parent_span_id=trace_context.span_id if trace_context else None,
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=trace_context.session_id if trace_context else None,
        )

        try:
            # --- Step 1: build sections ---
            tools_list: list[ToolSpec] = tools if tools is not None else []
            user_msg = self._extract_last_user_message(state)
            query_text = self._message_to_query(user_msg) if user_msg else ""

            memory_layers = await self._inject_memory_layers(
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=state.durable.session_id,
                query=query_text,
                trace_context=child_ctx,
            )

            sections = PromptSections(
                system=self._build_system_section(),
                tools=tools_list,
                memory_layers=memory_layers,
                conversation=self._extract_conversation(state, user_msg),
                user_message=user_msg,
            )

            # --- Step 2: position strategy ---
            strategy = position_strategy if position_strategy is not None else self._default_strategy
            messages = strategy.arrange(sections)

            # --- Step 3: cache breakpoints ---
            cache_breakpoints = await self._build_cache_breakpoints(
                tenant_id=tenant_id,
                policy=cache_policy if cache_policy is not None else self._default_cache_policy,
                sections=sections,
                trace_context=child_ctx,
            )

            # --- Step 4: token estimation ---
            estimated_tokens = self._token_counter.count(messages=messages, tools=tools_list)

            return PromptArtifact(
                messages=messages,
                cache_breakpoints=cache_breakpoints,
                estimated_input_tokens=estimated_tokens,
                layer_metadata={
                    "memory_layers_used": list(memory_layers.keys()),
                    "position_strategy": strategy.__class__.__name__,
                    "cache_sections": [
                        bp.section_id for bp in cache_breakpoints if bp.section_id
                    ],
                    "trace_id": child_ctx.trace_id,
                },
            )
        finally:
            span.end()

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _build_system_section(self) -> Message:
        """Default system role; override via system_role_text constructor arg."""
        return Message(role="system", content=self._system_role_text)

    def _extract_last_user_message(self, state: LoopState) -> Message | None:
        """Return the last role='user' message from transient.messages, or None."""
        for msg in reversed(state.transient.messages):
            if msg.role == "user":
                return msg
        return None

    def _extract_conversation(
        self, state: LoopState, current_user_msg: Message | None
    ) -> list[Message]:
        """Conversation = transient messages minus the current user message (last user)."""
        if current_user_msg is None:
            return list(state.transient.messages)
        # Exclude the current user message by identity to avoid duplication
        return [m for m in state.transient.messages if m is not current_user_msg]

    def _message_to_query(self, msg: Message) -> str:
        """Extract plain text from Message.content for memory query."""
        if isinstance(msg.content, str):
            return msg.content
        parts: list[str] = []
        for block in msg.content:
            text = getattr(block, "text", None)
            if text:
                parts.append(str(text))
        return " ".join(parts)

    # ------------------------------------------------------------------
    # Memory injection (Day 1.6 STUB; Day 2.1 wires real)
    # ------------------------------------------------------------------

    async def _inject_memory_layers(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID | None,
        session_id: UUID | None,
        query: str,
        trace_context: TraceContext | None = None,
    ) -> dict[str, list[MemoryHint]]:
        """Day 1.6 STUB returning {}.

        Day 2.1 will call:
            await self._memory_retrieval.search(
                query=query, tenant_id=tenant_id, user_id=user_id,
                session_id=session_id, scopes=("system","tenant","role","user","session"),
                time_scales=("short_term","long_term","semantic"), top_k=10,
                trace_context=trace_context,  # W3-2 propagation
            )
        and group hints by layer + sort by time_scale priority.
        """
        return {}

    # ------------------------------------------------------------------
    # Cache breakpoint builder (Day 1.6 STUB; Day 2.3 wires real)
    # ------------------------------------------------------------------

    async def _build_cache_breakpoints(
        self,
        *,
        tenant_id: UUID,
        policy: CachePolicy,
        sections: PromptSections,
        trace_context: TraceContext | None = None,
    ) -> list[CacheBreakpoint]:
        """Day 1.6 STUB returning [].

        Day 2.3 will call:
            await self._cache_manager.get_cache_breakpoints(
                tenant_id=tenant_id, policy=policy,
                trace_context=trace_context,  # W3-2 propagation
            )
        and decorate each breakpoint with content_hash from sections.
        """
        return []
