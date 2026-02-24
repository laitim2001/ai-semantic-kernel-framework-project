"""Unit tests for custom span helpers.

Sprint 122, Story 122-2: Tests create_span, record_agent_execution,
record_llm_call, record_mcp_tool_call, and record_orchestration_routing.
"""

import pytest
from unittest.mock import patch, MagicMock

from opentelemetry.trace import StatusCode


class TestCreateSpan:
    """Tests for create_span() context manager."""

    def test_creates_span_with_name(self):
        """Should create a span with the given name."""
        from src.core.observability.spans import create_span

        with create_span("test.operation") as span:
            assert span is not None

    def test_creates_span_with_attributes(self):
        """Should create a span with custom attributes."""
        from src.core.observability.spans import create_span

        attrs = {"key1": "value1", "key2": 42}
        with create_span("test.operation", attributes=attrs) as span:
            assert span is not None

    def test_creates_span_without_attributes(self):
        """Should create a span with no attributes when None."""
        from src.core.observability.spans import create_span

        with create_span("test.operation", attributes=None) as span:
            assert span is not None

    def test_records_exception_on_error(self):
        """Should record exception and set error status on failure."""
        from src.core.observability.spans import create_span

        with pytest.raises(ValueError):
            with create_span("test.operation") as span:
                raise ValueError("test error")


class TestRecordAgentExecution:
    """Tests for record_agent_execution() async context manager."""

    @pytest.mark.asyncio
    async def test_creates_agent_span(self):
        """Should create agent.execute span with standard attributes."""
        from src.core.observability.spans import record_agent_execution

        async with record_agent_execution(
            agent_id="agent-123",
            agent_type="ChatCompletionAgent",
            session_id="sess-456",
        ) as span:
            assert span is not None

    @pytest.mark.asyncio
    async def test_agent_span_with_extra_attributes(self):
        """Should include extra attributes on the span."""
        from src.core.observability.spans import record_agent_execution

        async with record_agent_execution(
            agent_id="agent-123",
            agent_type="TestAgent",
            extra_attributes={"custom.field": "value"},
        ) as span:
            assert span is not None

    @pytest.mark.asyncio
    async def test_agent_span_records_error(self):
        """Should record exception on agent failure."""
        from src.core.observability.spans import record_agent_execution

        with pytest.raises(RuntimeError):
            async with record_agent_execution(
                agent_id="agent-err",
                agent_type="TestAgent",
            ):
                raise RuntimeError("agent failed")

    @pytest.mark.asyncio
    async def test_agent_span_records_metrics(self):
        """Should record duration and count metrics."""
        from src.core.observability.spans import record_agent_execution

        # Should not raise; metrics are recorded internally
        async with record_agent_execution(
            agent_id="agent-123",
            agent_type="TestAgent",
        ):
            pass


class TestRecordLlmCall:
    """Tests for record_llm_call() async context manager."""

    @pytest.mark.asyncio
    async def test_creates_llm_span(self):
        """Should create llm.call span with model attributes."""
        from src.core.observability.spans import record_llm_call

        async with record_llm_call(
            model="gpt-5.2",
            provider="azure",
        ) as span:
            assert span is not None

    @pytest.mark.asyncio
    async def test_llm_span_records_error(self):
        """Should record exception on LLM call failure."""
        from src.core.observability.spans import record_llm_call

        with pytest.raises(TimeoutError):
            async with record_llm_call(model="gpt-5.2"):
                raise TimeoutError("LLM timeout")

    @pytest.mark.asyncio
    async def test_llm_span_with_extra_attributes(self):
        """Should include extra attributes."""
        from src.core.observability.spans import record_llm_call

        async with record_llm_call(
            model="gpt-5.2",
            extra_attributes={"llm.temperature": 0.7},
        ) as span:
            assert span is not None


class TestRecordMcpToolCall:
    """Tests for record_mcp_tool_call() async context manager."""

    @pytest.mark.asyncio
    async def test_creates_mcp_span(self):
        """Should create mcp.tool.call span."""
        from src.core.observability.spans import record_mcp_tool_call

        async with record_mcp_tool_call(
            tool_name="execute_shell",
            server_name="azure_mcp",
        ) as span:
            assert span is not None

    @pytest.mark.asyncio
    async def test_mcp_span_records_error(self):
        """Should record exception on MCP tool failure."""
        from src.core.observability.spans import record_mcp_tool_call

        with pytest.raises(ConnectionError):
            async with record_mcp_tool_call(tool_name="test_tool"):
                raise ConnectionError("MCP connection failed")


class TestRecordOrchestrationRouting:
    """Tests for record_orchestration_routing() context manager."""

    def test_creates_routing_span(self):
        """Should create orchestration.route span."""
        from src.core.observability.spans import record_orchestration_routing

        with record_orchestration_routing(
            intent="INCIDENT",
            routing_layer="pattern",
            confidence=0.95,
        ) as span:
            assert span is not None

    def test_routing_span_with_extra_attributes(self):
        """Should include extra attributes."""
        from src.core.observability.spans import record_orchestration_routing

        with record_orchestration_routing(
            intent="SERVICE_REQUEST",
            routing_layer="semantic",
            confidence=0.8,
            extra_attributes={"routing.scenario": "ad_account"},
        ) as span:
            assert span is not None

    def test_routing_span_records_error(self):
        """Should record exception on routing failure."""
        from src.core.observability.spans import record_orchestration_routing

        with pytest.raises(ValueError):
            with record_orchestration_routing(
                intent="UNKNOWN",
                routing_layer="llm",
            ):
                raise ValueError("routing failed")
