"""
IPA Platform - Performance Middleware

Provides middleware for performance optimization including:
- Response compression (Gzip/Brotli)
- Request timing and metrics
- ETag support for caching

Author: IPA Platform Team
Version: 1.0.0
"""

import gzip
import hashlib
import time
from typing import Callable, Optional
from io import BytesIO

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send
import structlog

logger = structlog.get_logger(__name__)


# =============================================================================
# Compression Middleware
# =============================================================================

class CompressionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to compress responses using Gzip.

    Only compresses responses that:
    - Are larger than minimum size threshold
    - Have compressible content types
    - Client accepts gzip encoding
    """

    COMPRESSIBLE_TYPES = {
        "application/json",
        "text/html",
        "text/plain",
        "text/css",
        "text/javascript",
        "application/javascript",
        "application/xml",
        "text/xml",
    }

    def __init__(
        self,
        app: ASGIApp,
        minimum_size: int = 500,
        compression_level: int = 6,
    ):
        """
        Initialize compression middleware.

        Args:
            app: The ASGI application
            minimum_size: Minimum response size to compress (bytes)
            compression_level: Gzip compression level (1-9)
        """
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compression_level = compression_level

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process request and optionally compress response."""
        # Check if client accepts gzip
        accept_encoding = request.headers.get("accept-encoding", "")

        if "gzip" not in accept_encoding.lower():
            return await call_next(request)

        # Get response
        response = await call_next(request)

        # Check if should compress
        content_type = response.headers.get("content-type", "")
        base_content_type = content_type.split(";")[0].strip()

        if base_content_type not in self.COMPRESSIBLE_TYPES:
            return response

        # Read response body
        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        # Check size threshold
        if len(body) < self.minimum_size:
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        # Compress
        compressed = gzip.compress(body, compresslevel=self.compression_level)

        # Only use compressed if smaller
        if len(compressed) < len(body):
            headers = dict(response.headers)
            headers["content-encoding"] = "gzip"
            headers["content-length"] = str(len(compressed))
            # Remove transfer-encoding if present
            headers.pop("transfer-encoding", None)

            return Response(
                content=compressed,
                status_code=response.status_code,
                headers=headers,
                media_type=response.media_type,
            )

        return Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )


# =============================================================================
# Timing Middleware
# =============================================================================

class TimingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track request timing and add performance headers.

    Adds headers:
    - X-Response-Time: Request processing time in ms
    - X-Request-ID: Unique request identifier
    """

    def __init__(self, app: ASGIApp, include_db_time: bool = False):
        """
        Initialize timing middleware.

        Args:
            app: The ASGI application
            include_db_time: Whether to track database query time
        """
        super().__init__(app)
        self.include_db_time = include_db_time

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process request and add timing headers."""
        start_time = time.perf_counter()

        # Generate request ID
        request_id = request.headers.get(
            "x-request-id",
            hashlib.md5(f"{time.time()}".encode()).hexdigest()[:12]
        )

        # Store in request state
        request.state.request_id = request_id
        request.state.start_time = start_time

        # Process request
        response = await call_next(request)

        # Calculate timing
        process_time = (time.perf_counter() - start_time) * 1000  # ms

        # Add headers
        response.headers["X-Response-Time"] = f"{process_time:.2f}ms"
        response.headers["X-Request-ID"] = request_id

        # Log slow requests
        if process_time > 1000:  # > 1 second
            logger.warning(
                "slow_request",
                path=request.url.path,
                method=request.method,
                response_time_ms=process_time,
                request_id=request_id,
            )

        return response


# =============================================================================
# ETag Middleware
# =============================================================================

class ETagMiddleware(BaseHTTPMiddleware):
    """
    Middleware to support ETag-based caching.

    Generates ETag headers for responses and handles
    If-None-Match conditional requests.
    """

    CACHEABLE_METHODS = {"GET", "HEAD"}
    CACHEABLE_STATUS_CODES = {200, 201}

    def __init__(self, app: ASGIApp, weak_etag: bool = True):
        """
        Initialize ETag middleware.

        Args:
            app: The ASGI application
            weak_etag: Whether to use weak ETags (W/"...")
        """
        super().__init__(app)
        self.weak_etag = weak_etag

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process request and handle ETag caching."""
        # Only handle cacheable methods
        if request.method not in self.CACHEABLE_METHODS:
            return await call_next(request)

        # Get response
        response = await call_next(request)

        # Only add ETag for cacheable responses
        if response.status_code not in self.CACHEABLE_STATUS_CODES:
            return response

        # Read response body
        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        # Generate ETag
        etag = self._generate_etag(body)

        # Check If-None-Match
        if_none_match = request.headers.get("if-none-match")
        if if_none_match and self._etag_matches(etag, if_none_match):
            return Response(
                status_code=304,
                headers={"ETag": etag},
            )

        # Add ETag to response
        headers = dict(response.headers)
        headers["ETag"] = etag

        return Response(
            content=body,
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type,
        )

    def _generate_etag(self, content: bytes) -> str:
        """Generate ETag from content."""
        hash_value = hashlib.md5(content).hexdigest()
        if self.weak_etag:
            return f'W/"{hash_value}"'
        return f'"{hash_value}"'

    def _etag_matches(self, etag: str, if_none_match: str) -> bool:
        """Check if ETag matches If-None-Match header."""
        # Handle multiple ETags
        client_etags = [e.strip() for e in if_none_match.split(",")]

        for client_etag in client_etags:
            if client_etag == "*":
                return True
            # Strip weak indicator for comparison
            if client_etag.startswith("W/"):
                client_etag = client_etag[2:]
            etag_value = etag[2:] if etag.startswith("W/") else etag
            if client_etag == etag_value:
                return True

        return False


# =============================================================================
# Performance Metrics Collector
# =============================================================================

class PerformanceMetrics:
    """
    Collects and reports performance metrics.

    Tracks:
    - Request latency (P50, P95, P99)
    - Request throughput
    - Error rates
    - Database query times
    """

    def __init__(self):
        """Initialize metrics collector."""
        self.request_times: list[float] = []
        self.error_count: int = 0
        self.total_requests: int = 0
        self.db_query_times: list[float] = []

    def record_request(self, duration_ms: float, is_error: bool = False) -> None:
        """Record a request timing."""
        self.request_times.append(duration_ms)
        self.total_requests += 1
        if is_error:
            self.error_count += 1

        # Keep only last 1000 samples
        if len(self.request_times) > 1000:
            self.request_times = self.request_times[-1000:]

    def record_db_query(self, duration_ms: float) -> None:
        """Record a database query timing."""
        self.db_query_times.append(duration_ms)

        if len(self.db_query_times) > 1000:
            self.db_query_times = self.db_query_times[-1000:]

    def get_percentile(self, times: list[float], percentile: float) -> float:
        """Calculate percentile from list of times."""
        if not times:
            return 0.0
        sorted_times = sorted(times)
        index = int(len(sorted_times) * percentile / 100)
        return sorted_times[min(index, len(sorted_times) - 1)]

    def get_metrics(self) -> dict:
        """Get current performance metrics."""
        return {
            "request_latency": {
                "p50": self.get_percentile(self.request_times, 50),
                "p95": self.get_percentile(self.request_times, 95),
                "p99": self.get_percentile(self.request_times, 99),
                "mean": sum(self.request_times) / len(self.request_times) if self.request_times else 0,
            },
            "throughput": {
                "total_requests": self.total_requests,
                "error_count": self.error_count,
                "error_rate": self.error_count / self.total_requests if self.total_requests else 0,
            },
            "database": {
                "query_p50": self.get_percentile(self.db_query_times, 50),
                "query_p95": self.get_percentile(self.db_query_times, 95),
            },
        }


# Global metrics instance
performance_metrics = PerformanceMetrics()
