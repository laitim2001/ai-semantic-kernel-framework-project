"""
Security Middleware

Sprint 3 - Story S3-2: API Security Hardening

Provides security headers and request validation middleware.
"""
import logging
import time
import uuid
from typing import Callable, Optional

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .config import SecurityConfig, security_config

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses.

    Adds the following security headers:
    - Strict-Transport-Security (HSTS)
    - Content-Security-Policy (CSP)
    - X-Frame-Options
    - X-Content-Type-Options
    - X-XSS-Protection
    - Referrer-Policy
    - Permissions-Policy
    """

    def __init__(self, app: ASGIApp, config: Optional[SecurityConfig] = None):
        """Initialize SecurityHeadersMiddleware.

        Args:
            app: ASGI application
            config: Security configuration (uses global if not provided)
        """
        super().__init__(app)
        self.config = config or security_config

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add security headers to response."""
        response = await call_next(request)

        # Add security headers
        if self.config.enable_hsts:
            response.headers["Strict-Transport-Security"] = self.config.get_hsts_header()

        if self.config.enable_csp:
            response.headers["Content-Security-Policy"] = self.config.csp_directives

        if self.config.enable_xframe_options:
            response.headers["X-Frame-Options"] = self.config.xframe_options_value

        if self.config.enable_content_type_nosniff:
            response.headers["X-Content-Type-Options"] = "nosniff"

        if self.config.enable_xss_protection:
            response.headers["X-XSS-Protection"] = "1; mode=block"

        if self.config.enable_referrer_policy:
            response.headers["Referrer-Policy"] = self.config.referrer_policy_value

        if self.config.enable_permissions_policy:
            response.headers["Permissions-Policy"] = self.config.permissions_policy_value

        # Remove potentially sensitive headers
        response.headers["X-Powered-By"] = ""
        response.headers["Server"] = "IPA-Platform"

        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Middleware to validate and sanitize incoming requests.

    Performs:
    - Request ID generation/validation
    - Request size validation
    - Basic request logging for security audit
    """

    def __init__(
        self,
        app: ASGIApp,
        config: Optional[SecurityConfig] = None,
        max_body_size: Optional[int] = None,
    ):
        """Initialize RequestValidationMiddleware.

        Args:
            app: ASGI application
            config: Security configuration
            max_body_size: Maximum request body size in bytes
        """
        super().__init__(app)
        self.config = config or security_config
        self.max_body_size = max_body_size or (self.config.max_request_size_mb * 1024 * 1024)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate request and add request ID."""
        start_time = time.time()

        # Generate or validate request ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        # Store request ID in state for logging
        request.state.request_id = request_id

        # Check content length
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > self.max_body_size:
                    logger.warning(
                        f"Request too large: {length} bytes (max: {self.max_body_size})",
                        extra={"request_id": request_id}
                    )
                    return Response(
                        content='{"detail": "Request body too large"}',
                        status_code=413,
                        media_type="application/json",
                        headers={"X-Request-ID": request_id},
                    )
            except ValueError:
                pass

        # Log request for security audit (if enabled)
        if self.config.log_security_events:
            client_ip = _get_client_ip(request)
            logger.info(
                f"Request: {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "client_ip": client_ip,
                    "user_agent": request.headers.get("user-agent", "unknown"),
                    "method": request.method,
                    "path": request.url.path,
                }
            )

        # Process request
        response = await call_next(request)

        # Add request ID to response
        response.headers["X-Request-ID"] = request_id

        # Log response
        duration = time.time() - start_time
        if self.config.log_security_events:
            logger.info(
                f"Response: {response.status_code} in {duration:.3f}s",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "duration_seconds": duration,
                }
            )

        return response


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Middleware to add request timing headers."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add timing information to response."""
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        return response


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies.

    Args:
        request: FastAPI request

    Returns:
        Client IP address
    """
    # Check for forwarded headers (when behind proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs; first is the client
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fall back to direct connection
    if request.client:
        return request.client.host

    return "unknown"


def setup_security_middleware(
    app: FastAPI,
    config: Optional[SecurityConfig] = None,
) -> None:
    """Set up all security middleware for the application.

    This function should be called during app initialization to set up:
    - CORS middleware
    - Trusted host middleware
    - Security headers middleware
    - Request validation middleware

    Args:
        app: FastAPI application instance
        config: Security configuration (uses global if not provided)
    """
    config = config or security_config

    # Note: Middleware is added in reverse order of execution
    # Last added = first executed

    # 1. Request timing (outermost)
    app.add_middleware(RequestTimingMiddleware)

    # 2. Security headers
    app.add_middleware(SecurityHeadersMiddleware, config=config)

    # 3. Request validation
    app.add_middleware(RequestValidationMiddleware, config=config)

    # 4. Trusted hosts (if configured with specific hosts)
    if config.trusted_hosts and "*" not in config.trusted_hosts:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=config.trusted_hosts,
        )

    # 5. CORS (innermost - closest to route handlers)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=config.cors_allow_credentials,
        allow_methods=config.cors_allow_methods,
        allow_headers=config.cors_allow_headers,
        max_age=config.cors_max_age,
        expose_headers=["X-Request-ID", "X-Response-Time"],
    )

    logger.info(
        f"Security middleware configured: "
        f"CORS origins={config.cors_origins}, "
        f"HSTS={config.enable_hsts}, "
        f"CSP={config.enable_csp}"
    )
