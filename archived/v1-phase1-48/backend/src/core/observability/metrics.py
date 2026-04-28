"""Custom business metrics for IPA Platform.

Sprint 122, Story 122-2: Defines IPA-specific metrics collected via
OpenTelemetry MeterProvider and exported to Azure Monitor.

Metrics:
    agent.execution.duration  — Histogram, agent execution latency in seconds
    agent.execution.count     — Counter, total agent executions
    llm.call.duration         — Histogram, LLM API call latency in seconds
    llm.tokens.used           — Counter, total LLM tokens consumed
    mcp.tool.call.duration    — Histogram, MCP tool call latency in seconds
    api.request.duration      — Histogram, API request latency in seconds
    api.request.error_count   — Counter, total API errors
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from opentelemetry import metrics

logger = logging.getLogger(__name__)

_SERVICE_NAME = "ipa-platform"

# Module-level meter (lazy-initialized)
_meter: Optional[metrics.Meter] = None


def get_meter() -> metrics.Meter:
    """Get or create the IPA Platform meter instance.

    Returns:
        An OpenTelemetry Meter bound to the IPA service name.
    """
    global _meter
    if _meter is None:
        _meter = metrics.get_meter(_SERVICE_NAME)
    return _meter


@dataclass
class IPAMetrics:
    """Collection of IPA Platform business metrics.

    Lazily creates metric instruments on first access. This allows the
    metrics module to be imported before OTel initialization without errors.

    Attributes:
        agent_execution_duration: Histogram for agent execution time.
        agent_execution_count: Counter for agent execution events.
        llm_call_duration: Histogram for LLM API call time.
        llm_tokens_used: Counter for LLM token consumption.
        mcp_tool_call_duration: Histogram for MCP tool call time.
        api_request_duration: Histogram for HTTP request time.
        api_request_error_count: Counter for HTTP error events.
    """

    _initialized: bool = field(default=False, init=False, repr=False)

    # Histogram instruments
    agent_execution_duration: metrics.Histogram = field(init=False)
    llm_call_duration: metrics.Histogram = field(init=False)
    mcp_tool_call_duration: metrics.Histogram = field(init=False)
    api_request_duration: metrics.Histogram = field(init=False)

    # Counter instruments
    agent_execution_count: metrics.Counter = field(init=False)
    llm_tokens_used: metrics.Counter = field(init=False)
    api_request_error_count: metrics.Counter = field(init=False)

    def __post_init__(self) -> None:
        """Initialize all metric instruments from the global meter."""
        self._create_instruments()

    def _create_instruments(self) -> None:
        """Create OTel metric instruments.

        Uses the global meter from get_meter(). Instruments are safe to
        create even before OTel initialization — they will be no-ops
        until a real MeterProvider is set.
        """
        meter = get_meter()

        # --- Histograms ---
        self.agent_execution_duration = meter.create_histogram(
            name="agent.execution.duration",
            description="Agent execution duration in seconds",
            unit="s",
        )

        self.llm_call_duration = meter.create_histogram(
            name="llm.call.duration",
            description="LLM API call duration in seconds",
            unit="s",
        )

        self.mcp_tool_call_duration = meter.create_histogram(
            name="mcp.tool.call.duration",
            description="MCP tool call duration in seconds",
            unit="s",
        )

        self.api_request_duration = meter.create_histogram(
            name="api.request.duration",
            description="HTTP API request duration in seconds",
            unit="s",
        )

        # --- Counters ---
        self.agent_execution_count = meter.create_counter(
            name="agent.execution.count",
            description="Total number of agent executions",
            unit="1",
        )

        self.llm_tokens_used = meter.create_counter(
            name="llm.tokens.used",
            description="Total LLM tokens consumed",
            unit="1",
        )

        self.api_request_error_count = meter.create_counter(
            name="api.request.error_count",
            description="Total number of API request errors",
            unit="1",
        )

        self._initialized = True
        logger.debug("IPA metrics instruments created")


# Singleton metrics instance
IPA_METRICS = IPAMetrics()
