"""
File: backend/src/business_domain/correlation/tools.py
Purpose: 3 ToolSpec stubs + register_correlation_tools() entry.
Category: Business domain / correlation / tool layer adaptation
Scope: Phase 51 / Sprint 51.0 Day 2.5 (per 08b-business-tools-spec.md §Domain 2)

Created: 2026-04-30 (Sprint 51.0 Day 2)
Last Modified: 2026-04-30
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

from agent_harness._contracts import (
    ConcurrencyPolicy,
    ToolAnnotations,
    ToolCall,
    ToolSpec,
)
from agent_harness.tools._inmemory import InMemoryToolRegistry

from .mock_executor import DEFAULT_BASE_URL, CorrelationMockExecutor

ToolHandler = Callable[[ToolCall], Awaitable[str | dict[str, Any]]]


SPEC_ANALYZE = ToolSpec(
    name="mock_correlation_analyze",
    description=(
        "Analyze a set of alert ids and return correlation chains "
        "(primary + related alerts within 5-minute time window on same server)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "alert_ids": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
            },
        },
        "required": ["alert_ids"],
    },
    annotations=ToolAnnotations(read_only=True),
    concurrency_policy=ConcurrencyPolicy.READ_ONLY_PARALLEL,
    tags=("domain:correlation", "hitl_policy:auto", "risk:low"),
)

SPEC_FIND_ROOT_CAUSE = ToolSpec(
    name="mock_correlation_find_root_cause",
    description="Return root-cause candidates ranked by confidence for an incident.",
    input_schema={
        "type": "object",
        "properties": {
            "incident_id": {"type": "string"},
        },
        "required": ["incident_id"],
    },
    annotations=ToolAnnotations(read_only=True),
    concurrency_policy=ConcurrencyPolicy.SEQUENTIAL,
    tags=("domain:correlation", "hitl_policy:auto", "risk:low"),
)

SPEC_GET_RELATED = ToolSpec(
    name="mock_correlation_get_related",
    description="Return alerts related to a given alert within a depth (1-3).",
    input_schema={
        "type": "object",
        "properties": {
            "alert_id": {"type": "string"},
            "depth": {"type": "integer", "minimum": 1, "maximum": 3, "default": 1},
        },
        "required": ["alert_id"],
    },
    annotations=ToolAnnotations(read_only=True, idempotent=True),
    concurrency_policy=ConcurrencyPolicy.READ_ONLY_PARALLEL,
    tags=("domain:correlation", "hitl_policy:auto", "risk:low"),
)

CORRELATION_SPECS: tuple[ToolSpec, ...] = (
    SPEC_ANALYZE,
    SPEC_FIND_ROOT_CAUSE,
    SPEC_GET_RELATED,
)


def _build_handlers(executor: CorrelationMockExecutor) -> dict[str, ToolHandler]:
    async def h_analyze(call: ToolCall) -> str:
        result = await executor.analyze(alert_ids=call.arguments["alert_ids"])
        return json.dumps(result)

    async def h_find_rc(call: ToolCall) -> str:
        result = await executor.find_root_cause(incident_id=call.arguments["incident_id"])
        return json.dumps(result)

    async def h_get_related(call: ToolCall) -> str:
        result = await executor.get_related(
            alert_id=call.arguments["alert_id"],
            depth=call.arguments.get("depth", 1),
        )
        return json.dumps(result)

    return {
        "mock_correlation_analyze": h_analyze,
        "mock_correlation_find_root_cause": h_find_rc,
        "mock_correlation_get_related": h_get_related,
    }


def register_correlation_tools(
    registry: InMemoryToolRegistry,
    handlers: dict[str, ToolHandler],
    *,
    mock_url: str = DEFAULT_BASE_URL,
) -> None:
    """Register 3 mock_correlation_* ToolSpecs + handlers."""
    executor = CorrelationMockExecutor(base_url=mock_url)
    for spec in CORRELATION_SPECS:
        registry.register(spec)
    handlers.update(_build_handlers(executor))
