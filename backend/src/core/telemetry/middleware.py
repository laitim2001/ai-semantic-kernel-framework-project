"""
Tracing Middleware

Sprint 3 - Story S3-6: Distributed Tracing with Jaeger

Custom middleware for:
- Adding trace context to responses
- Enriching spans with custom attributes
- Correlating logs with traces
"""
from __future__ import annotations

import logging
import time
from typing import Callable, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .setup import (
    get_trace_id,
    get_span_id,
    get_current_span,
    add_span_attributes,
    add_span_event,
)

logger = logging.getLogger(__name__)


class TracingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enriches traces with request/response information
    and adds trace context to response headers.
    """

    def __init__(
        self,
        app,
        excluded_paths: Optional[list] = None,
        add_response_headers: bool = True,
    ):
        """
        Initialize the tracing middleware.

        Args:
            app: The ASGI application
            excluded_paths: Paths to exclude from tracing enrichment
            add_response_headers: Whether to add trace context to response headers
        """
        super().__init__(app)
        self.excluded_paths = excluded_paths or ["/health", "/ready", "/live"]
        self.add_response_headers = add_response_headers

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and enrich the trace."""
        # Skip excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        start_time = time.time()

        # Add request attributes to span
        span = get_current_span()
        if span:
            add_span_attributes({
                "http.client_ip": request.client.host if request.client else "unknown",
                "http.user_agent": request.headers.get("user-agent", "unknown"),
                "http.request_id": request.headers.get("x-request-id", ""),
            })

            # Add event for request received
            add_span_event("request.received", {
                "path": request.url.path,
                "method": request.method,
            })

        # Process the request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Add response attributes
        if span:
            add_span_attributes({
                "http.response.duration_ms": int(duration * 1000),
            })
            add_span_event("request.completed", {
                "status_code": response.status_code,
                "duration_ms": int(duration * 1000),
            })

        # Add trace context to response headers
        if self.add_response_headers:
            trace_id = get_trace_id()
            span_id = get_span_id()
            if trace_id:
                response.headers["X-Trace-ID"] = trace_id
            if span_id:
                response.headers["X-Span-ID"] = span_id

        return response


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that ensures correlation IDs are propagated
    and available for logging.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and ensure correlation ID is set."""
        # Get or generate correlation ID
        correlation_id = request.headers.get("x-correlation-id")
        if not correlation_id:
            correlation_id = get_trace_id() or f"req-{int(time.time() * 1000)}"

        # Store in request state for access in route handlers
        request.state.correlation_id = correlation_id

        # Add to span attributes
        span = get_current_span()
        if span:
            add_span_attributes({
                "correlation.id": correlation_id,
            })

        # Process request
        response = await call_next(request)

        # Add to response headers
        response.headers["X-Correlation-ID"] = correlation_id

        return response


def get_correlation_id(request: Request) -> Optional[str]:
    """
    Get the correlation ID from the request.

    Args:
        request: The current request

    Returns:
        The correlation ID if available
    """
    return getattr(request.state, "correlation_id", None)
