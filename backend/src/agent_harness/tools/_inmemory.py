"""
File: backend/src/agent_harness/tools/_inmemory.py
Purpose: In-memory ToolRegistry + ToolExecutor for Sprint 50.x bring-up.
Category: 範疇 2 (Tool Layer) — STUB only
Scope: Phase 50 / Sprint 50.1 (Day 3.3)

Description:
    Minimum-viable implementations of `ToolRegistry` and `ToolExecutor` ABCs
    so the Phase 50 main TAO loop can run end-to-end without depending on
    sandbox infrastructure (containers / network / sql) that arrives in
    Phase 51.1.

    Bundles a single built-in tool — `echo_tool` — used by the 50.1 first
    end-to-end test ("user asks echo X → loop replies X") and by the 50.2
    demo case.

Lifecycle:
    DEPRECATED-IN: Sprint 51.1 — when Cat 2 lands its production-grade
    sandbox / permission / RBAC executor, this module's exports should be
    deleted (NOT renamed; both `_inmemory.py` itself + the `make_echo_*`
    helpers go away). The leading underscore in the filename is the
    deprecation marker.

Key Components:
    - InMemoryToolRegistry: dict-backed ToolSpec storage.
    - InMemoryToolExecutor: dispatches to async handlers; emits `tool_execution_duration_seconds` metric per call.
    - ToolHandler: type alias for `Callable[[ToolCall], Awaitable[str | dict]]`.
    - ECHO_TOOL_SPEC + echo_handler: built-in echo tool for 50.x bring-up.
    - make_echo_executor(): factory returning a wired-up (registry, executor) pair.

Created: 2026-04-30 (Sprint 50.1 Day 3.3)
Last Modified: 2026-04-30

Modification History (newest-first):
    - 2026-04-30: Initial creation (Sprint 50.1 Day 3.3) — registry + executor +
        echo_tool + factory. Tracer span + metric emit integrated.

Related:
    - ._abc (ToolRegistry / ToolExecutor ABCs; 49.1)
    - 01-eleven-categories-spec.md §範疇 2 (Tool Layer; full impl Phase 51.1)
    - 17-cross-category-interfaces.md §3.1 (cross-cat tool registry)
    - .claude/rules/observability-instrumentation.md (Cat 2 emits
      tool_execution_duration_seconds per call)
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

from agent_harness._contracts import (
    ConcurrencyPolicy,
    ExecutionContext,
    SpanCategory,
    ToolAnnotations,
    ToolCall,
    ToolResult,
    ToolSpec,
    TraceContext,
)
from agent_harness.observability import (
    MetricRegistry,
    NoOpTracer,
    Tracer,
    emit,
)

from ._abc import ToolExecutor, ToolRegistry

# Tool handler: receives a ToolCall, returns text or dict (serialized to text).
ToolHandler = Callable[[ToolCall], Awaitable[str | dict[str, Any]]]


class InMemoryToolRegistry(ToolRegistry):
    """Dict-backed ToolSpec storage. DEPRECATED-IN: 51.1 (Cat 2 production)."""

    def __init__(self) -> None:
        self._specs: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._specs:
            raise ValueError(f"Tool '{spec.name}' already registered")
        self._specs[spec.name] = spec

    def get(self, name: str) -> ToolSpec | None:
        return self._specs.get(name)

    def list(self) -> list[ToolSpec]:
        return list(self._specs.values())


class InMemoryToolExecutor(ToolExecutor):
    """Async dispatcher to in-memory handlers. DEPRECATED-IN: 51.1.

    `execute_batch` is sequential in 50.1 (no real parallelism needed for
    echo_tool tests). Phase 51.1 honors `ConcurrencyPolicy` per spec.
    """

    def __init__(
        self,
        handlers: dict[str, ToolHandler],
        *,
        tracer: Tracer | None = None,
        metric_registry: MetricRegistry | None = None,
    ) -> None:
        self._handlers = dict(handlers)
        self._tracer = tracer or NoOpTracer()
        self._metrics = metric_registry or MetricRegistry()

    async def execute(
        self,
        call: ToolCall,
        *,
        trace_context: TraceContext | None = None,
        context: ExecutionContext | None = None,  # 51.1 ABC sync; not consumed in stub
    ) -> ToolResult:
        del context  # stub ignores context (DEPRECATED-IN: 51.1)
        if call.name not in self._handlers:
            return ToolResult(
                tool_call_id=call.id,
                tool_name=call.name,
                success=False,
                content="",
                error=f"unknown tool: {call.name}",
            )

        async with self._tracer.start_span(
            name=f"tool.{call.name}",
            category=SpanCategory.TOOLS,
            trace_context=trace_context,
        ):
            t0 = time.monotonic()
            try:
                raw = await self._handlers[call.name](call)
                duration = time.monotonic() - t0
                self._safe_emit(
                    "tool_execution_duration_seconds",
                    duration,
                    {"tool_name": call.name, "status": "success"},
                    trace_context,
                )
                return ToolResult(
                    tool_call_id=call.id,
                    tool_name=call.name,
                    success=True,
                    content=raw if isinstance(raw, str) else str(raw),
                )
            except Exception as exc:  # noqa: BLE001 — propagate via ToolResult.error
                duration = time.monotonic() - t0
                self._safe_emit(
                    "tool_execution_duration_seconds",
                    duration,
                    {"tool_name": call.name, "status": "error"},
                    trace_context,
                )
                return ToolResult(
                    tool_call_id=call.id,
                    tool_name=call.name,
                    success=False,
                    content="",
                    error=str(exc),
                )

    async def execute_batch(
        self,
        calls: list[ToolCall],
        *,
        trace_context: TraceContext | None = None,
        context: ExecutionContext | None = None,  # 51.1 ABC sync
    ) -> list[ToolResult]:
        results: list[ToolResult] = []
        for c in calls:
            results.append(await self.execute(c, trace_context=trace_context, context=context))
        return results

    def _safe_emit(
        self,
        metric_name: str,
        value: float,
        labels: dict[str, str],
        trace_context: TraceContext | None,
    ) -> None:
        """Emit a metric; swallow KeyError from unregistered metric (NoOp tracer)."""
        try:
            emit(
                self._tracer,
                metric_name=metric_name,
                value=value,
                registry=self._metrics,
                labels=labels,
                trace_context=trace_context,
            )
        except KeyError:
            # Metric not registered in this MetricRegistry (e.g. minimal
            # test setup). NoOp on the metric; do NOT fail tool execution.
            pass


# === echo_tool — built-in for 50.x bring-up =================================

ECHO_TOOL_SPEC: ToolSpec = ToolSpec(
    name="echo_tool",
    description="Echoes the 'text' argument back verbatim. Test-only built-in.",
    input_schema={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Text to echo back.",
            },
        },
        "required": ["text"],
    },
    annotations=ToolAnnotations(
        read_only=True,
        destructive=False,
        idempotent=True,
        open_world=False,
    ),
    concurrency_policy=ConcurrencyPolicy.READ_ONLY_PARALLEL,
)


async def echo_handler(call: ToolCall) -> str:
    """Return the 'text' argument verbatim."""
    return str(call.arguments.get("text", ""))


def make_echo_executor(
    *,
    tracer: Tracer | None = None,
) -> tuple[InMemoryToolRegistry, InMemoryToolExecutor]:
    """Factory: ready-to-use registry + executor with echo_tool registered."""
    registry = InMemoryToolRegistry()
    registry.register(ECHO_TOOL_SPEC)
    executor = InMemoryToolExecutor(
        handlers={"echo_tool": echo_handler},
        tracer=tracer,
    )
    return registry, executor
