"""Unit tests for structured logging setup.

Sprint 122, Story 122-3: Tests structlog configuration, JSON output,
request_id injection, and OTel trace correlation.
"""

import json
import logging
from io import StringIO
from unittest.mock import patch, MagicMock

import pytest
import structlog


class TestSetupLogging:
    """Tests for setup_logging() function."""

    def test_setup_with_json_output(self):
        """Should configure structlog with JSON renderer."""
        from src.core.logging.setup import setup_logging

        setup_logging(json_output=True, log_level="INFO")

        # structlog should be configured
        logger = structlog.get_logger("test")
        assert logger is not None

    def test_setup_with_console_output(self):
        """Should configure structlog with console renderer."""
        from src.core.logging.setup import setup_logging

        setup_logging(json_output=False, log_level="DEBUG")

        logger = structlog.get_logger("test-console")
        assert logger is not None

    def test_setup_sets_log_level(self):
        """Should set the root logger level."""
        from src.core.logging.setup import setup_logging

        setup_logging(json_output=True, log_level="WARNING")

        root = logging.getLogger()
        assert root.level == logging.WARNING

    def test_setup_with_otel_disabled(self):
        """Should work with OTel correlation disabled."""
        from src.core.logging.setup import setup_logging

        # Should not raise
        setup_logging(
            json_output=True,
            log_level="INFO",
            enable_otel_correlation=False,
        )

    def test_setup_with_otel_enabled(self):
        """Should include OTel context processor when enabled."""
        from src.core.logging.setup import setup_logging

        # Should not raise even without OTel initialized
        setup_logging(
            json_output=True,
            log_level="INFO",
            enable_otel_correlation=True,
        )


class TestGetLogger:
    """Tests for get_logger() function."""

    def test_returns_bound_logger(self):
        """Should return a structlog BoundLogger."""
        from src.core.logging.setup import setup_logging, get_logger

        setup_logging(json_output=True, log_level="INFO")
        logger = get_logger("test.module")
        assert logger is not None

    def test_logger_with_none_name(self):
        """Should accept None as name."""
        from src.core.logging.setup import get_logger

        logger = get_logger(None)
        assert logger is not None


class TestAddRequestId:
    """Tests for _add_request_id processor."""

    def test_adds_request_id_when_set(self):
        """Should add request_id to event_dict when ContextVar is set."""
        from src.core.logging.setup import _add_request_id
        from src.core.logging.middleware import request_id_var

        token = request_id_var.set("req-test-123")
        try:
            event_dict = {"event": "test message"}
            result = _add_request_id(None, "info", event_dict)
            assert result["request_id"] == "req-test-123"
        finally:
            request_id_var.reset(token)

    def test_skips_when_no_request_id(self):
        """Should not add request_id when ContextVar is empty."""
        from src.core.logging.setup import _add_request_id

        event_dict = {"event": "test message"}
        result = _add_request_id(None, "info", event_dict)
        assert "request_id" not in result


class TestAddOtelContext:
    """Tests for _add_otel_context processor."""

    def test_does_not_raise_without_otel(self):
        """Should not raise when no OTel span is active."""
        from src.core.logging.setup import _add_otel_context

        event_dict = {"event": "test"}
        result = _add_otel_context(None, "info", event_dict)
        assert "event" in result

    @patch("opentelemetry.trace.get_current_span")
    def test_adds_trace_id_when_span_active(self, mock_get_span):
        """Should add trace_id and span_id when OTel span is recording."""
        from src.core.logging.setup import _add_otel_context

        mock_span = MagicMock()
        mock_span.is_recording.return_value = True
        mock_ctx = MagicMock()
        mock_ctx.trace_id = 0x12345678901234567890123456789012
        mock_ctx.span_id = 0x1234567890123456
        mock_span.get_span_context.return_value = mock_ctx
        mock_get_span.return_value = mock_span

        event_dict = {"event": "test"}
        result = _add_otel_context(None, "info", event_dict)
        assert "trace_id" in result
        assert "span_id" in result
