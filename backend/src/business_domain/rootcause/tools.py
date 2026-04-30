"""
File: backend/src/business_domain/rootcause/tools.py
Purpose: 3 ToolSpec stubs + register_rootcause_tools() entry. apply_fix is HIGH risk + ALWAYS_ASK.
Category: Business domain / rootcause / tool layer adaptation
Scope: Phase 51 / Sprint 51.0 Day 2.7 (per 08b-business-tools-spec.md §Domain 3)

Description:
    `mock_rootcause_apply_fix` is the single highest-risk mock tool. Per 08b spec
    §Domain 3, hitl_policy MUST be ALWAYS_ASK and risk_level MUST be HIGH. Encoded
    in tags for Sprint 51.0 (CARRY-021 ToolSpec extension lands in 51.1).

Created: 2026-04-30 (Sprint 51.0 Day 2)
Last Modified: 2026-04-30
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

from agent_harness._contracts import (
    ConcurrencyPolicy,
    RiskLevel,
    ToolAnnotations,
    ToolCall,
    ToolHITLPolicy,
    ToolSpec,
)
from agent_harness.tools import ToolRegistry

from .mock_executor import DEFAULT_BASE_URL, RootcauseMockExecutor

ToolHandler = Callable[[ToolCall], Awaitable[str | dict[str, Any]]]


SPEC_DIAGNOSE = ToolSpec(
    name="mock_rootcause_diagnose",
    description="Return top RCA finding for an incident (highest-confidence hypothesis).",
    input_schema={
        "type": "object",
        "properties": {
            "incident_id": {"type": "string"},
        },
        "required": ["incident_id"],
    },
    annotations=ToolAnnotations(read_only=True),
    concurrency_policy=ConcurrencyPolicy.SEQUENTIAL,
    hitl_policy=ToolHITLPolicy.AUTO,
    risk_level=RiskLevel.LOW,
    tags=("domain:rootcause",),
)

SPEC_SUGGEST_FIX = ToolSpec(
    name="mock_rootcause_suggest_fix",
    description="Generate a mock fix proposal (fix_id + risk_level + ETA) for an incident.",
    input_schema={
        "type": "object",
        "properties": {
            "incident_id": {"type": "string"},
        },
        "required": ["incident_id"],
    },
    annotations=ToolAnnotations(read_only=True),
    concurrency_policy=ConcurrencyPolicy.SEQUENTIAL,
    hitl_policy=ToolHITLPolicy.AUTO,
    risk_level=RiskLevel.LOW,
    tags=("domain:rootcause",),
)

SPEC_APPLY_FIX = ToolSpec(
    name="mock_rootcause_apply_fix",
    description=(
        "HIGH-RISK: Apply a previously suggested fix to an incident. "
        "dry_run=true (default) records intent but performs no mutation. "
        "Live runs (dry_run=false) require ALWAYS_ASK HITL approval."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "fix_id": {"type": "string"},
            "dry_run": {"type": "boolean", "default": True},
        },
        "required": ["fix_id"],
    },
    annotations=ToolAnnotations(destructive=True, open_world=True),
    concurrency_policy=ConcurrencyPolicy.SEQUENTIAL,
    hitl_policy=ToolHITLPolicy.ALWAYS_ASK,
    risk_level=RiskLevel.HIGH,
    tags=("domain:rootcause",),
)

ROOTCAUSE_SPECS: tuple[ToolSpec, ...] = (
    SPEC_DIAGNOSE,
    SPEC_SUGGEST_FIX,
    SPEC_APPLY_FIX,
)


def _build_handlers(executor: RootcauseMockExecutor) -> dict[str, ToolHandler]:
    async def h_diagnose(call: ToolCall) -> str:
        result = await executor.diagnose(incident_id=call.arguments["incident_id"])
        return json.dumps(result)

    async def h_suggest(call: ToolCall) -> str:
        result = await executor.suggest_fix(incident_id=call.arguments["incident_id"])
        return json.dumps(result)

    async def h_apply(call: ToolCall) -> str:
        result = await executor.apply_fix(
            fix_id=call.arguments["fix_id"],
            dry_run=call.arguments.get("dry_run", True),
        )
        return json.dumps(result)

    return {
        "mock_rootcause_diagnose": h_diagnose,
        "mock_rootcause_suggest_fix": h_suggest,
        "mock_rootcause_apply_fix": h_apply,
    }


def register_rootcause_tools(
    registry: ToolRegistry,
    handlers: dict[str, ToolHandler],
    *,
    mock_url: str = DEFAULT_BASE_URL,
) -> None:
    """Register 3 mock_rootcause_* ToolSpecs + handlers."""
    executor = RootcauseMockExecutor(base_url=mock_url)
    for spec in ROOTCAUSE_SPECS:
        registry.register(spec)
    handlers.update(_build_handlers(executor))
