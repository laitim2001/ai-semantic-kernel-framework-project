"""Observability module — OpenTelemetry + Azure Monitor integration.

Sprint 122, Story 122-2: Provides distributed tracing, metrics, and
log correlation for the IPA Platform backend.

Exports:
    setup_observability: Initialize OTel SDK with Azure Monitor exporters.
    create_span: Create a custom span for business operations.
    record_agent_execution: Record agent execution span + metrics.
    record_llm_call: Record LLM API call span + metrics.
    record_mcp_tool_call: Record MCP tool call span + metrics.
    get_tracer: Get the IPA Platform tracer instance.
    get_meter: Get the IPA Platform meter instance.
    IPA_METRICS: Pre-configured business metrics collection.
"""

from src.core.observability.metrics import IPA_METRICS, get_meter
from src.core.observability.setup import get_tracer, setup_observability
from src.core.observability.spans import (
    create_span,
    record_agent_execution,
    record_llm_call,
    record_mcp_tool_call,
)

__all__ = [
    "setup_observability",
    "create_span",
    "record_agent_execution",
    "record_llm_call",
    "record_mcp_tool_call",
    "get_tracer",
    "get_meter",
    "IPA_METRICS",
]
