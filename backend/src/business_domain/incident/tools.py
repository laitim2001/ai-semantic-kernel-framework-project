"""
File: backend/src/business_domain/incident/tools.py
Purpose: 5 ToolSpec stubs + register_incident_tools() entry. close is HIGH risk + ALWAYS_ASK.
Category: Business domain / incident / tool layer adaptation
Scope: Phase 51 / Sprint 51.0 Day 3.4 (per 08b-business-tools-spec.md §Domain 5)

Description:
    Five mock_incident_* tools spanning the full incident lifecycle:
      create / update_status / close / get / list

    `close` is the highest-risk operation in this domain — closes an incident
    record permanently. Per 08b spec §Domain 5: hitl_policy=ALWAYS_ASK,
    risk_level=HIGH. Encoded in tags (CARRY-021 first-class fields in 51.1).

Created: 2026-04-30 (Sprint 51.0 Day 3)
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

from .mock_executor import DEFAULT_BASE_URL, IncidentMockExecutor

ToolHandler = Callable[[ToolCall], Awaitable[str | dict[str, Any]]]


SPEC_CREATE = ToolSpec(
    name="mock_incident_create",
    description="Create a new incident record (title + severity + linked alert_ids).",
    input_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string", "minLength": 1, "maxLength": 512},
            "severity": {
                "type": "string",
                "enum": ["low", "medium", "high", "critical"],
                "default": "high",
            },
            "alert_ids": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["title"],
    },
    annotations=ToolAnnotations(destructive=True),
    concurrency_policy=ConcurrencyPolicy.SEQUENTIAL,
    hitl_policy=ToolHITLPolicy.ASK_ONCE,
    risk_level=RiskLevel.MEDIUM,
    tags=("domain:incident",),
)

SPEC_UPDATE_STATUS = ToolSpec(
    name="mock_incident_update_status",
    description="Update an incident's status (open / investigating / resolved / closed).",
    input_schema={
        "type": "object",
        "properties": {
            "incident_id": {"type": "string"},
            "status": {
                "type": "string",
                "enum": ["open", "investigating", "resolved", "closed"],
            },
        },
        "required": ["incident_id", "status"],
    },
    annotations=ToolAnnotations(destructive=True),
    concurrency_policy=ConcurrencyPolicy.SEQUENTIAL,
    hitl_policy=ToolHITLPolicy.ASK_ONCE,
    risk_level=RiskLevel.MEDIUM,
    tags=("domain:incident",),
)

SPEC_CLOSE = ToolSpec(
    name="mock_incident_close",
    description=(
        "HIGH-RISK: Close an incident permanently with a resolution note. "
        "Requires ALWAYS_ASK HITL approval; mock returns 'closed_pending_review'."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "incident_id": {"type": "string"},
            "resolution": {"type": "string", "minLength": 1, "maxLength": 1000},
        },
        "required": ["incident_id", "resolution"],
    },
    annotations=ToolAnnotations(destructive=True),
    concurrency_policy=ConcurrencyPolicy.SEQUENTIAL,
    hitl_policy=ToolHITLPolicy.ALWAYS_ASK,
    risk_level=RiskLevel.HIGH,
    tags=("domain:incident",),
)

SPEC_GET = ToolSpec(
    name="mock_incident_get",
    description="Fetch a single incident by id.",
    input_schema={
        "type": "object",
        "properties": {"incident_id": {"type": "string"}},
        "required": ["incident_id"],
    },
    annotations=ToolAnnotations(read_only=True, idempotent=True),
    concurrency_policy=ConcurrencyPolicy.READ_ONLY_PARALLEL,
    hitl_policy=ToolHITLPolicy.AUTO,
    risk_level=RiskLevel.LOW,
    tags=("domain:incident",),
)

SPEC_LIST = ToolSpec(
    name="mock_incident_list",
    description="List incidents with optional severity / status filter.",
    input_schema={
        "type": "object",
        "properties": {
            "severity": {
                "type": "string",
                "enum": ["low", "medium", "high", "critical"],
            },
            "status": {
                "type": "string",
                "enum": ["open", "investigating", "resolved", "closed"],
            },
            "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
        },
    },
    annotations=ToolAnnotations(read_only=True),
    concurrency_policy=ConcurrencyPolicy.READ_ONLY_PARALLEL,
    hitl_policy=ToolHITLPolicy.AUTO,
    risk_level=RiskLevel.LOW,
    tags=("domain:incident",),
)

INCIDENT_SPECS: tuple[ToolSpec, ...] = (
    SPEC_CREATE,
    SPEC_UPDATE_STATUS,
    SPEC_CLOSE,
    SPEC_GET,
    SPEC_LIST,
)


def _build_handlers(executor: IncidentMockExecutor) -> dict[str, ToolHandler]:
    async def h_create(call: ToolCall) -> str:
        result = await executor.create(
            title=call.arguments["title"],
            severity=call.arguments.get("severity", "high"),
            alert_ids=call.arguments.get("alert_ids", []),
        )
        return json.dumps(result)

    async def h_update(call: ToolCall) -> str:
        result = await executor.update_status(
            incident_id=call.arguments["incident_id"],
            status=call.arguments["status"],
        )
        return json.dumps(result)

    async def h_close(call: ToolCall) -> str:
        result = await executor.close(
            incident_id=call.arguments["incident_id"],
            resolution=call.arguments["resolution"],
        )
        return json.dumps(result)

    async def h_get(call: ToolCall) -> str:
        result = await executor.get(incident_id=call.arguments["incident_id"])
        return json.dumps(result)

    async def h_list(call: ToolCall) -> str:
        result = await executor.list(
            severity=call.arguments.get("severity"),
            status=call.arguments.get("status"),
            limit=call.arguments.get("limit", 20),
        )
        return json.dumps(result)

    return {
        "mock_incident_create": h_create,
        "mock_incident_update_status": h_update,
        "mock_incident_close": h_close,
        "mock_incident_get": h_get,
        "mock_incident_list": h_list,
    }


def register_incident_tools(
    registry: ToolRegistry,
    handlers: dict[str, ToolHandler],
    *,
    mock_url: str = DEFAULT_BASE_URL,
) -> None:
    """Register 5 mock_incident_* ToolSpecs + handlers."""
    executor = IncidentMockExecutor(base_url=mock_url)
    for spec in INCIDENT_SPECS:
        registry.register(spec)
    handlers.update(_build_handlers(executor))
