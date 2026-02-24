"""Structured logging configuration using structlog.

Sprint 122, Story 122-3: Configures structlog for JSON-formatted log
output with automatic request_id injection and OTel trace correlation.

Usage:
    from src.core.logging import setup_logging, get_logger

    # In FastAPI startup:
    setup_logging(json_output=True, log_level="INFO")

    # In application code:
    logger = get_logger(__name__)
    logger.info("agent_executed", agent_id="agent-123", duration_ms=450)
"""

import logging
import sys
from typing import Any, Optional

import structlog

from src.core.logging.filters import SensitiveInfoFilter


def setup_logging(
    json_output: bool = True,
    log_level: str = "INFO",
    enable_otel_correlation: bool = True,
) -> None:
    """Initialize structlog with JSON renderer and request_id injection.

    Configures both structlog and the standard logging module to produce
    consistent JSON output. Integrates with the RequestIdMiddleware's
    ContextVar for automatic request_id inclusion.

    Args:
        json_output: If True, use JSON renderer. If False, use console
            renderer (for local development).
        log_level: Root log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        enable_otel_correlation: If True, inject OTel trace_id and span_id
            into log events.
    """
    # Build processor chain
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _add_request_id,
        SensitiveInfoFilter(),
    ]

    if enable_otel_correlation:
        processors.append(_add_otel_context)

    processors.append(structlog.processors.StackInfoRenderer())
    processors.append(structlog.processors.format_exc_info)

    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging to use structlog
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Add structlog-compatible handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer() if json_output
        else structlog.dev.ConsoleRenderer(),
        foreign_pre_chain=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _add_request_id,
            SensitiveInfoFilter(),
        ],
    ))
    root_logger.addHandler(handler)


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """Get a bound structlog logger.

    This is the primary way to create loggers in the IPA Platform.
    Returns a structlog BoundLogger that automatically includes
    request_id, timestamp, and log level.

    Args:
        name: Logger name, typically __name__ of the calling module.

    Returns:
        A bound structlog logger instance.
    """
    return structlog.get_logger(name)


def _add_request_id(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Structlog processor that injects request_id from ContextVar.

    Reads the current request_id from the RequestIdMiddleware's ContextVar
    and adds it to the log event dictionary.

    Args:
        logger: The wrapped logger object.
        method_name: The name of the log method called.
        event_dict: The event dictionary being processed.

    Returns:
        The event dictionary with request_id added.
    """
    from src.core.logging.middleware import request_id_var

    request_id = request_id_var.get("")
    if request_id:
        event_dict["request_id"] = request_id
    return event_dict


def _add_otel_context(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Structlog processor that injects OTel trace_id and span_id.

    Reads the current OpenTelemetry span context and adds trace_id
    and span_id to the log event for correlation in Azure Monitor.

    Args:
        logger: The wrapped logger object.
        method_name: The name of the log method called.
        event_dict: The event dictionary being processed.

    Returns:
        The event dictionary with OTel context added.
    """
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span and span.is_recording():
            ctx = span.get_span_context()
            if ctx and ctx.trace_id:
                event_dict["trace_id"] = format(ctx.trace_id, "032x")
                event_dict["span_id"] = format(ctx.span_id, "016x")
    except ImportError:
        pass
    return event_dict
