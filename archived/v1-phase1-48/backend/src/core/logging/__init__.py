"""Structured logging module — structlog + Request ID tracking.

Sprint 122, Story 122-3: Provides JSON-structured logging with
X-Request-ID propagation and sensitive information filtering.

Exports:
    setup_logging: Initialize structlog with JSON renderer.
    get_logger: Get a bound structlog logger for a module.
    RequestIdMiddleware: FastAPI middleware for X-Request-ID tracking.
    request_id_var: ContextVar holding the current request ID.
    SensitiveInfoFilter: Filter that masks sensitive fields in log output.
"""

from src.core.logging.filters import SensitiveInfoFilter
from src.core.logging.middleware import RequestIdMiddleware, request_id_var
from src.core.logging.setup import get_logger, setup_logging

__all__ = [
    "setup_logging",
    "get_logger",
    "RequestIdMiddleware",
    "request_id_var",
    "SensitiveInfoFilter",
]
