"""Request ID middleware for X-Request-ID header tracking.

Sprint 122, Story 122-3: Implements FastAPI middleware that reads or
generates an X-Request-ID, stores it in a ContextVar for access by
loggers and downstream code, and includes it in the response header.

Request ID Flow:
    Client → X-Request-ID header (or auto-generated UUID)
      → RequestIdMiddleware → ContextVar
        → All log messages include request_id
          → Response header: X-Request-ID

Usage:
    from src.core.logging.middleware import RequestIdMiddleware

    app.add_middleware(RequestIdMiddleware)

    # Access current request_id in any async context:
    from src.core.logging.middleware import request_id_var
    current_id = request_id_var.get("")
"""

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# ContextVar for request-scoped request ID propagation.
# Accessible from any async code within the request lifecycle.
request_id_var: ContextVar[str] = ContextVar("request_id", default="")

# Header name for request ID
REQUEST_ID_HEADER = "X-Request-ID"


class RequestIdMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for X-Request-ID tracking.

    For each incoming request:
    1. Reads X-Request-ID from request headers (if present).
    2. Generates a UUID4 if no X-Request-ID is provided.
    3. Stores the request_id in a ContextVar for downstream access.
    4. Adds X-Request-ID to the response headers.

    This enables full request tracing across all log messages,
    service calls, and OTel spans within a single request lifecycle.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process request with X-Request-ID tracking.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or route handler.

        Returns:
            The HTTP response with X-Request-ID header attached.
        """
        # Read or generate request ID
        request_id = request.headers.get(REQUEST_ID_HEADER, "")
        if not request_id:
            request_id = str(uuid.uuid4())

        # Store in ContextVar for downstream access
        token = request_id_var.set(request_id)

        try:
            response = await call_next(request)
        finally:
            # Reset ContextVar to avoid leaking across requests
            request_id_var.reset(token)

        # Always include request_id in response headers
        response.headers[REQUEST_ID_HEADER] = request_id

        return response
