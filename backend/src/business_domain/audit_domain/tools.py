"""
File: backend/src/business_domain/audit_domain/tools.py
Purpose: 3 ToolSpec stubs + register_audit_tools() entry.
Category: Business domain / audit_domain / tool layer adaptation
Scope: Phase 51 / Sprint 51.0 Day 3.2 (per 08b-business-tools-spec.md §Domain 4)

Description:
    Three mock_audit_* tools — query_logs (read-only) / generate_report
    (read-only + open_world) / flag_anomaly (destructive + ask_once).

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

from .mock_executor import DEFAULT_BASE_URL, AuditMockExecutor

ToolHandler = Callable[[ToolCall], Awaitable[str | dict[str, Any]]]


SPEC_QUERY_LOGS = ToolSpec(
    name="mock_audit_query_logs",
    description=("Query audit logs by optional time_range / action_filter / user_id_filter."),
    input_schema={
        "type": "object",
        "properties": {
            "time_range_start": {"type": "string", "format": "date-time"},
            "time_range_end": {"type": "string", "format": "date-time"},
            "action_filter": {"type": "string"},
            "user_id_filter": {"type": "string"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 20},
        },
    },
    annotations=ToolAnnotations(read_only=True),
    concurrency_policy=ConcurrencyPolicy.READ_ONLY_PARALLEL,
    hitl_policy=ToolHITLPolicy.AUTO,
    risk_level=RiskLevel.LOW,
    tags=("domain:audit",),
)

SPEC_GENERATE_REPORT = ToolSpec(
    name="mock_audit_generate_report",
    description=("Generate an audit report from a template (e.g., compliance_quarterly)."),
    input_schema={
        "type": "object",
        "properties": {
            "template": {"type": "string"},
            "params": {"type": "object", "additionalProperties": True},
        },
        "required": ["template"],
    },
    annotations=ToolAnnotations(read_only=True, open_world=True),
    concurrency_policy=ConcurrencyPolicy.SEQUENTIAL,
    hitl_policy=ToolHITLPolicy.AUTO,
    risk_level=RiskLevel.MEDIUM,
    tags=("domain:audit",),
)

SPEC_FLAG_ANOMALY = ToolSpec(
    name="mock_audit_flag_anomaly",
    description=("Flag an audit record as anomalous; records reason for human review."),
    input_schema={
        "type": "object",
        "properties": {
            "record_id": {"type": "string"},
            "reason": {"type": "string", "minLength": 1, "maxLength": 500},
        },
        "required": ["record_id", "reason"],
    },
    annotations=ToolAnnotations(destructive=True),
    concurrency_policy=ConcurrencyPolicy.SEQUENTIAL,
    hitl_policy=ToolHITLPolicy.ASK_ONCE,
    risk_level=RiskLevel.MEDIUM,
    tags=("domain:audit",),
)

AUDIT_SPECS: tuple[ToolSpec, ...] = (
    SPEC_QUERY_LOGS,
    SPEC_GENERATE_REPORT,
    SPEC_FLAG_ANOMALY,
)


def _build_handlers(executor: AuditMockExecutor) -> dict[str, ToolHandler]:
    async def h_query(call: ToolCall) -> str:
        result = await executor.query_logs(
            time_range_start=call.arguments.get("time_range_start"),
            time_range_end=call.arguments.get("time_range_end"),
            action_filter=call.arguments.get("action_filter"),
            user_id_filter=call.arguments.get("user_id_filter"),
            limit=call.arguments.get("limit", 20),
        )
        return json.dumps(result)

    async def h_report(call: ToolCall) -> str:
        result = await executor.generate_report(
            template=call.arguments["template"],
            params=call.arguments.get("params", {}),
        )
        return json.dumps(result)

    async def h_flag(call: ToolCall) -> str:
        result = await executor.flag_anomaly(
            record_id=call.arguments["record_id"],
            reason=call.arguments["reason"],
        )
        return json.dumps(result)

    return {
        "mock_audit_query_logs": h_query,
        "mock_audit_generate_report": h_report,
        "mock_audit_flag_anomaly": h_flag,
    }


def register_audit_tools(
    registry: ToolRegistry,
    handlers: dict[str, ToolHandler],
    *,
    mock_url: str = DEFAULT_BASE_URL,
) -> None:
    """Register 3 mock_audit_* ToolSpecs + handlers."""
    executor = AuditMockExecutor(base_url=mock_url)
    for spec in AUDIT_SPECS:
        registry.register(spec)
    handlers.update(_build_handlers(executor))
