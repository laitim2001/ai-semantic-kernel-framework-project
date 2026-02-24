"""Custom span helpers for IPA Platform business operations.

Sprint 122, Story 122-2: Provides decorator-style and context-manager
helpers for creating spans around agent execution, LLM calls, MCP tool
calls, and orchestration routing decisions.

Usage:
    from src.core.observability.spans import record_agent_execution

    async with record_agent_execution(
        agent_id="agent-123",
        agent_type="ChatCompletionAgent",
        session_id="sess-456",
    ) as span:
        result = await agent.execute(input)
        span.set_attribute("agent.result_tokens", result.tokens_used)
"""

import logging
import time
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncIterator, Dict, Iterator, Optional

from opentelemetry import trace
from opentelemetry.trace import Span, StatusCode

from src.core.observability.setup import get_tracer

logger = logging.getLogger(__name__)


@contextmanager
def create_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
) -> Iterator[Span]:
    """Create a custom span for a synchronous operation.

    Args:
        name: Span name (e.g., "agent.execute", "llm.call").
        attributes: Optional span attributes.
        kind: Span kind (INTERNAL, CLIENT, SERVER, PRODUCER, CONSUMER).

    Yields:
        The active Span instance.
    """
    tracer = get_tracer()
    with tracer.start_as_current_span(
        name,
        kind=kind,
        attributes=attributes or {},
    ) as span:
        try:
            yield span
        except Exception as exc:
            span.set_status(StatusCode.ERROR, str(exc))
            span.record_exception(exc)
            raise


@asynccontextmanager
async def record_agent_execution(
    agent_id: str,
    agent_type: str = "",
    session_id: str = "",
    extra_attributes: Optional[Dict[str, Any]] = None,
) -> AsyncIterator[Span]:
    """Record an agent execution span with standard attributes.

    Creates a span named "agent.execute" with agent metadata attributes.
    Also records the duration via the agent.execution.duration metric.

    Args:
        agent_id: Unique agent identifier.
        agent_type: Agent class name (e.g., "ChatCompletionAgent").
        session_id: Session context for the execution.
        extra_attributes: Additional span attributes.

    Yields:
        The active Span instance. Callers can add more attributes.
    """
    from src.core.observability.metrics import IPA_METRICS

    tracer = get_tracer()
    attributes: Dict[str, Any] = {
        "agent.id": agent_id,
        "agent.type": agent_type,
        "session.id": session_id,
    }
    if extra_attributes:
        attributes.update(extra_attributes)

    start_time = time.monotonic()

    with tracer.start_as_current_span(
        "agent.execute",
        kind=trace.SpanKind.INTERNAL,
        attributes=attributes,
    ) as span:
        try:
            yield span
            span.set_status(StatusCode.OK)
        except Exception as exc:
            span.set_status(StatusCode.ERROR, str(exc))
            span.record_exception(exc)
            raise
        finally:
            duration_s = time.monotonic() - start_time
            IPA_METRICS.agent_execution_duration.record(
                duration_s,
                {"agent.type": agent_type},
            )
            IPA_METRICS.agent_execution_count.add(
                1,
                {"agent.type": agent_type, "status": "ok" if span.status.status_code == StatusCode.OK else "error"},
            )


@asynccontextmanager
async def record_llm_call(
    model: str = "",
    provider: str = "azure",
    extra_attributes: Optional[Dict[str, Any]] = None,
) -> AsyncIterator[Span]:
    """Record an LLM API call span with standard attributes.

    Creates a span named "llm.call" with model/provider attributes.
    Records duration and token usage metrics.

    Args:
        model: Model deployment name (e.g., "gpt-5.2").
        provider: LLM provider name (e.g., "azure", "anthropic").
        extra_attributes: Additional span attributes.

    Yields:
        The active Span. Callers should set "llm.tokens.prompt" and
        "llm.tokens.completion" attributes after the call completes.
    """
    from src.core.observability.metrics import IPA_METRICS

    tracer = get_tracer()
    attributes: Dict[str, Any] = {
        "llm.model": model,
        "llm.provider": provider,
    }
    if extra_attributes:
        attributes.update(extra_attributes)

    start_time = time.monotonic()

    with tracer.start_as_current_span(
        "llm.call",
        kind=trace.SpanKind.CLIENT,
        attributes=attributes,
    ) as span:
        try:
            yield span
            span.set_status(StatusCode.OK)
        except Exception as exc:
            span.set_status(StatusCode.ERROR, str(exc))
            span.record_exception(exc)
            raise
        finally:
            duration_s = time.monotonic() - start_time
            labels = {"llm.model": model, "llm.provider": provider}
            IPA_METRICS.llm_call_duration.record(duration_s, labels)

            # Record token usage if set on span
            prompt_tokens = span.attributes.get("llm.tokens.prompt", 0) if hasattr(span, 'attributes') else 0
            completion_tokens = span.attributes.get("llm.tokens.completion", 0) if hasattr(span, 'attributes') else 0
            total_tokens = int(prompt_tokens) + int(completion_tokens)
            if total_tokens > 0:
                IPA_METRICS.llm_tokens_used.add(total_tokens, labels)


@asynccontextmanager
async def record_mcp_tool_call(
    tool_name: str,
    server_name: str = "",
    extra_attributes: Optional[Dict[str, Any]] = None,
) -> AsyncIterator[Span]:
    """Record an MCP tool call span with standard attributes.

    Creates a span named "mcp.tool.call" with tool metadata.

    Args:
        tool_name: MCP tool name (e.g., "execute_shell", "query_ldap").
        server_name: MCP server name (e.g., "azure_mcp", "filesystem_mcp").
        extra_attributes: Additional span attributes.

    Yields:
        The active Span instance.
    """
    from src.core.observability.metrics import IPA_METRICS

    tracer = get_tracer()
    attributes: Dict[str, Any] = {
        "mcp.tool.name": tool_name,
        "mcp.server.name": server_name,
    }
    if extra_attributes:
        attributes.update(extra_attributes)

    start_time = time.monotonic()

    with tracer.start_as_current_span(
        "mcp.tool.call",
        kind=trace.SpanKind.CLIENT,
        attributes=attributes,
    ) as span:
        try:
            yield span
            span.set_status(StatusCode.OK)
        except Exception as exc:
            span.set_status(StatusCode.ERROR, str(exc))
            span.record_exception(exc)
            raise
        finally:
            duration_s = time.monotonic() - start_time
            IPA_METRICS.mcp_tool_call_duration.record(
                duration_s,
                {"mcp.tool.name": tool_name, "mcp.server.name": server_name},
            )


@contextmanager
def record_orchestration_routing(
    intent: str = "",
    routing_layer: str = "",
    confidence: float = 0.0,
    extra_attributes: Optional[Dict[str, Any]] = None,
) -> Iterator[Span]:
    """Record an orchestration routing decision span.

    Creates a span named "orchestration.route" with routing metadata.

    Args:
        intent: Detected intent category.
        routing_layer: Layer that made the decision (pattern/semantic/llm).
        confidence: Routing confidence score (0.0-1.0).
        extra_attributes: Additional span attributes.

    Yields:
        The active Span instance.
    """
    tracer = get_tracer()
    attributes: Dict[str, Any] = {
        "orchestration.intent": intent,
        "orchestration.routing_layer": routing_layer,
        "orchestration.confidence": confidence,
    }
    if extra_attributes:
        attributes.update(extra_attributes)

    with tracer.start_as_current_span(
        "orchestration.route",
        kind=trace.SpanKind.INTERNAL,
        attributes=attributes,
    ) as span:
        try:
            yield span
            span.set_status(StatusCode.OK)
        except Exception as exc:
            span.set_status(StatusCode.ERROR, str(exc))
            span.record_exception(exc)
            raise
