"""
File: backend/src/business_domain/patrol/tools.py
Purpose: 4 ToolSpec stubs + register_patrol_tools() entry for the patrol domain.
Category: Business domain / patrol / tool layer adaptation
Scope: Phase 51 / Sprint 51.0 Day 2.3 (per 08b-business-tools-spec.md §Domain 1)

Description:
    Defines 4 mock_patrol_* ToolSpecs and the register entry that wires both:
    1. ToolSpec into a ToolRegistry (specs)
    2. ToolHandler closures into a handlers dict (callable adapters that
       translate ToolCall -> typed PatrolMockExecutor method args)

    HITL policy + risk_level encoded in ToolSpec.tags as Sprint 51.0 workaround;
    Sprint 51.1 will extend ToolSpec with first-class fields (per retro CARRY-021).

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

from .mock_executor import DEFAULT_BASE_URL, PatrolMockExecutor

ToolHandler = Callable[[ToolCall], Awaitable[str | dict[str, Any]]]


# === ToolSpec definitions =================================================

SPEC_CHECK_SERVERS = ToolSpec(
    name="mock_patrol_check_servers",
    description=(
        "Run health check on a list of server ids. Returns per-server "
        "PatrolResult (health + metrics)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "scope": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "description": "Server ids to check (e.g., ['web-01', 'db-01']).",
            },
        },
        "required": ["scope"],
    },
    annotations=ToolAnnotations(read_only=True, idempotent=True),
    concurrency_policy=ConcurrencyPolicy.READ_ONLY_PARALLEL,
    tags=("domain:patrol", "hitl_policy:auto", "risk:low"),
)

SPEC_GET_RESULTS = ToolSpec(
    name="mock_patrol_get_results",
    description="Fetch a stored PatrolResult by patrol_id.",
    input_schema={
        "type": "object",
        "properties": {
            "patrol_id": {"type": "string"},
        },
        "required": ["patrol_id"],
    },
    annotations=ToolAnnotations(read_only=True, idempotent=True),
    concurrency_policy=ConcurrencyPolicy.READ_ONLY_PARALLEL,
    tags=("domain:patrol", "hitl_policy:auto", "risk:low"),
)

SPEC_SCHEDULE = ToolSpec(
    name="mock_patrol_schedule",
    description=("Schedule a recurring patrol via cron expression. Returns schedule_id."),
    input_schema={
        "type": "object",
        "properties": {
            "cron": {"type": "string", "description": "Cron expression."},
            "scope": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
            },
        },
        "required": ["cron", "scope"],
    },
    annotations=ToolAnnotations(destructive=True),
    concurrency_policy=ConcurrencyPolicy.SEQUENTIAL,
    tags=("domain:patrol", "hitl_policy:ask_once", "risk:medium"),
)

SPEC_CANCEL = ToolSpec(
    name="mock_patrol_cancel",
    description="Cancel a scheduled patrol by schedule_id.",
    input_schema={
        "type": "object",
        "properties": {
            "schedule_id": {"type": "string"},
        },
        "required": ["schedule_id"],
    },
    annotations=ToolAnnotations(destructive=True),
    concurrency_policy=ConcurrencyPolicy.SEQUENTIAL,
    tags=("domain:patrol", "hitl_policy:ask_once", "risk:medium"),
)

PATROL_SPECS: tuple[ToolSpec, ...] = (
    SPEC_CHECK_SERVERS,
    SPEC_GET_RESULTS,
    SPEC_SCHEDULE,
    SPEC_CANCEL,
)


# === Handler factory + register entry =====================================


def _build_handlers(executor: PatrolMockExecutor) -> dict[str, ToolHandler]:
    async def h_check(call: ToolCall) -> str:
        result = await executor.check_servers(scope=call.arguments["scope"])
        return json.dumps(result)

    async def h_get(call: ToolCall) -> str:
        result = await executor.get_results(patrol_id=call.arguments["patrol_id"])
        return json.dumps(result)

    async def h_schedule(call: ToolCall) -> str:
        result = await executor.schedule(cron=call.arguments["cron"], scope=call.arguments["scope"])
        return json.dumps(result)

    async def h_cancel(call: ToolCall) -> str:
        result = await executor.cancel(schedule_id=call.arguments["schedule_id"])
        return json.dumps(result)

    return {
        "mock_patrol_check_servers": h_check,
        "mock_patrol_get_results": h_get,
        "mock_patrol_schedule": h_schedule,
        "mock_patrol_cancel": h_cancel,
    }


def register_patrol_tools(
    registry: InMemoryToolRegistry,
    handlers: dict[str, ToolHandler],
    *,
    mock_url: str = DEFAULT_BASE_URL,
) -> None:
    """Register 4 mock_patrol_* ToolSpecs + handlers wired to PatrolMockExecutor."""
    executor = PatrolMockExecutor(base_url=mock_url)
    for spec in PATROL_SPECS:
        registry.register(spec)
    handlers.update(_build_handlers(executor))
