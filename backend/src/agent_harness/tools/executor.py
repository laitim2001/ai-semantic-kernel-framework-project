"""
File: backend/src/agent_harness/tools/executor.py
Purpose: Production ToolExecutor — permission gate + JSONSchema validate + concurrency-aware batch.
Category: 範疇 2 (Tool Layer)
Scope: Phase 51 / Sprint 51.1 Day 2.2

Description:
    Concrete `ToolExecutor` that orchestrates the full tool-execution
    pipeline (replaces `_inmemory.InMemoryToolExecutor`, DEPRECATED-IN: 51.1):

      1. Registry lookup — unknown tool → ToolResult(success=False, error="unknown tool: <name>")
      2. Permission gate — calls `PermissionChecker.check()`:
         - DENY → ToolResult(success=False, error="permission denied: destructive without explicit approval")
         - REQUIRE_APPROVAL → ToolResult(success=False, error="approval required: <hitl_policy>/<risk_level>")
           (51.1 returns error semantically; Phase 53.3 wires ApprovalManager invocation)
         - ALLOW → continue
      3. JSONSchema runtime validation — call.arguments validated against
         spec.input_schema using cached `Draft202012Validator`. Bad input
         → ToolResult(success=False, error="schema mismatch: <field>: <reason>")
      4. Handler dispatch — async handler invocation inside tracer span
      5. Metric emission — `tool_execution_duration_seconds` per call
         (status=success / error / denied / approval_required / schema_invalid / unknown)
      6. Exception → ToolResult(success=False, error=str(exc))

    `execute_batch()` honors `ConcurrencyPolicy` per spec:
      - All calls SEQUENTIAL or any spec missing → sequential await loop
      - All calls READ_ONLY_PARALLEL or ALL_PARALLEL → asyncio.gather
      - Mixed (some sequential + some parallel) → sequential (conservative)

    Validators are cached per spec.name to avoid Draft202012Validator
    re-construction on every call.

Key Components:
    - ToolExecutorImpl: concrete `ToolExecutor` (ABC in `_abc.py`)
    - ToolHandler: type alias `Callable[[ToolCall], Awaitable[str | dict]]`

Owner: 01-eleven-categories-spec.md §範疇 2
Single-source: 17.md §2.1

Created: 2026-04-30 (Sprint 51.1 Day 2.2)
Last Modified: 2026-04-30

Modification History (newest-first):
    - 2026-04-30: Initial creation (Sprint 51.1 Day 2.2) — full pipeline:
      registry lookup + permission + JSONSchema validate + tracer span +
      metric emit + concurrency-aware batch.

Related:
    - ._abc (ToolExecutor ABC; 49.1)
    - .registry (Day 1.4 ToolRegistryImpl)
    - .permissions (Day 2.1 PermissionChecker)
    - ._inmemory (DEPRECATED-IN 51.1; tracer/metric pattern carried forward)
    - sprint-51-1-plan.md §決策 4 (permission) / §決策 5 (JSONSchema position)
    - .claude/rules/observability-instrumentation.md (Cat 2 emits
      tool_execution_duration_seconds per call with extended status labels)
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

from jsonschema import Draft202012Validator  # type: ignore[import-untyped]
from jsonschema.exceptions import ValidationError  # type: ignore[import-untyped]

from agent_harness._contracts import (
    ConcurrencyPolicy,
    ExecutionContext,
    SpanCategory,
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
from .permissions import PermissionChecker, PermissionDecision

ToolHandler = Callable[[ToolCall], Awaitable[str | dict[str, Any]]]


class ToolExecutorImpl(ToolExecutor):
    """Production tool executor: permission + schema + concurrency + metrics."""

    def __init__(
        self,
        *,
        registry: ToolRegistry,
        handlers: dict[str, ToolHandler],
        permission_checker: PermissionChecker | None = None,
        tracer: Tracer | None = None,
        metric_registry: MetricRegistry | None = None,
    ) -> None:
        self._registry = registry
        self._handlers = dict(handlers)
        self._permission = permission_checker or PermissionChecker()
        self._tracer = tracer or NoOpTracer()
        self._metrics = metric_registry or MetricRegistry()
        self._validator_cache: dict[str, Draft202012Validator] = {}

    async def execute(
        self,
        call: ToolCall,
        *,
        trace_context: TraceContext | None = None,
        context: ExecutionContext | None = None,
    ) -> ToolResult:
        ctx = context or ExecutionContext()
        spec = self._registry.get(call.name)
        if spec is None:
            return self._fail(call, "unknown", f"unknown tool: {call.name}", trace_context, t0=None)

        decision = self._permission.check(spec, call, ctx)
        if decision is PermissionDecision.DENY:
            return self._fail(
                call,
                "denied",
                f"permission denied: destructive tool '{call.name}' requires explicit approval",
                trace_context,
                t0=None,
            )
        if decision is PermissionDecision.REQUIRE_APPROVAL:
            return self._fail(
                call,
                "approval_required",
                (
                    f"approval required: tool '{call.name}' "
                    f"(hitl_policy={spec.hitl_policy.value}, risk_level={spec.risk_level.value})"
                ),
                trace_context,
                t0=None,
            )

        schema_error = self._validate_arguments(spec, call)
        if schema_error is not None:
            return self._fail(
                call, "schema_invalid", f"schema mismatch: {schema_error}", trace_context, t0=None
            )

        handler = self._handlers.get(call.name)
        if handler is None:
            return self._fail(
                call,
                "unknown",
                f"no handler registered for tool: {call.name}",
                trace_context,
                t0=None,
            )

        async with self._tracer.start_span(
            name=f"tool.{call.name}",
            category=SpanCategory.TOOLS,
            trace_context=trace_context,
        ):
            t0 = time.monotonic()
            try:
                raw = await handler(call)
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
        context: ExecutionContext | None = None,
    ) -> list[ToolResult]:
        if not calls:
            return []
        if self._batch_can_parallelize(calls):
            return list(
                await asyncio.gather(
                    *(self.execute(c, trace_context=trace_context, context=context) for c in calls)
                )
            )
        results: list[ToolResult] = []
        for c in calls:
            results.append(await self.execute(c, trace_context=trace_context, context=context))
        return results

    def _batch_can_parallelize(self, calls: list[ToolCall]) -> bool:
        for c in calls:
            spec = self._registry.get(c.name)
            if spec is None:
                return False
            if spec.concurrency_policy is ConcurrencyPolicy.SEQUENTIAL:
                return False
        return True

    def _validate_arguments(self, spec: ToolSpec, call: ToolCall) -> str | None:
        validator = self._validator_cache.get(spec.name)
        if validator is None:
            validator = Draft202012Validator(spec.input_schema)
            self._validator_cache[spec.name] = validator
        try:
            validator.validate(call.arguments)
        except ValidationError as exc:
            path = ".".join(str(p) for p in exc.absolute_path) or "<root>"
            return f"{path}: {exc.message}"
        return None

    def _fail(
        self,
        call: ToolCall,
        status: str,
        error: str,
        trace_context: TraceContext | None,
        *,
        t0: float | None,
    ) -> ToolResult:
        duration = (time.monotonic() - t0) if t0 is not None else 0.0
        self._safe_emit(
            "tool_execution_duration_seconds",
            duration,
            {"tool_name": call.name, "status": status},
            trace_context,
        )
        return ToolResult(
            tool_call_id=call.id,
            tool_name=call.name,
            success=False,
            content="",
            error=error,
        )

    def _safe_emit(
        self,
        metric_name: str,
        value: float,
        labels: dict[str, str],
        trace_context: TraceContext | None,
    ) -> None:
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
            pass
