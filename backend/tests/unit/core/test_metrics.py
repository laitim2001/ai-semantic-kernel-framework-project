"""Unit tests for custom business metrics.

Sprint 122, Story 122-2: Tests IPAMetrics creation and instrument
initialization.
"""

import pytest

from src.core.observability.metrics import IPAMetrics, get_meter


class TestGetMeter:
    """Tests for get_meter() function."""

    def test_returns_meter(self):
        """Should return a non-None meter."""
        meter = get_meter()
        assert meter is not None

    def test_returns_same_meter_on_multiple_calls(self):
        """Should return consistent meter instance."""
        meter1 = get_meter()
        meter2 = get_meter()
        assert meter1 is meter2


class TestIPAMetrics:
    """Tests for IPAMetrics dataclass."""

    def test_creates_all_histograms(self):
        """Should create all 4 histogram instruments."""
        m = IPAMetrics()
        assert m.agent_execution_duration is not None
        assert m.llm_call_duration is not None
        assert m.mcp_tool_call_duration is not None
        assert m.api_request_duration is not None

    def test_creates_all_counters(self):
        """Should create all 3 counter instruments."""
        m = IPAMetrics()
        assert m.agent_execution_count is not None
        assert m.llm_tokens_used is not None
        assert m.api_request_error_count is not None

    def test_initialized_flag(self):
        """Should set _initialized to True after creation."""
        m = IPAMetrics()
        assert m._initialized is True

    def test_histogram_record_does_not_raise(self):
        """Recording a histogram value should not raise."""
        m = IPAMetrics()
        m.agent_execution_duration.record(1.5, {"agent.type": "TestAgent"})
        m.llm_call_duration.record(0.8, {"llm.model": "gpt-5.2"})
        m.mcp_tool_call_duration.record(0.3, {"mcp.tool.name": "test"})
        m.api_request_duration.record(0.1, {"method": "GET"})

    def test_counter_add_does_not_raise(self):
        """Adding to a counter should not raise."""
        m = IPAMetrics()
        m.agent_execution_count.add(1, {"agent.type": "TestAgent"})
        m.llm_tokens_used.add(500, {"llm.model": "gpt-5.2"})
        m.api_request_error_count.add(1, {"status_code": "500"})


class TestIPAMetricsSingleton:
    """Tests for the module-level IPA_METRICS singleton."""

    def test_singleton_exists(self):
        """IPA_METRICS should be importable."""
        from src.core.observability.metrics import IPA_METRICS
        assert IPA_METRICS is not None

    def test_singleton_initialized(self):
        """IPA_METRICS should be initialized."""
        from src.core.observability.metrics import IPA_METRICS
        assert IPA_METRICS._initialized is True
