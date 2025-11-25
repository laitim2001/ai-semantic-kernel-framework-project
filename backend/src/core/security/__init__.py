"""
Security Module for IPA Platform

Sprint 3 - Story S3-2: API Security Hardening

Provides security middleware, rate limiting, input validation, and security headers.
"""
from .middleware import (
    SecurityHeadersMiddleware,
    RequestValidationMiddleware,
    setup_security_middleware,
)
from .rate_limiter import (
    RateLimiter,
    RateLimitExceeded,
    get_rate_limiter,
    rate_limit,
)
from .validators import (
    sanitize_string,
    validate_uuid,
    validate_email,
    validate_url,
    SafeString,
    InputValidator,
)
from .config import SecurityConfig

__all__ = [
    # Middleware
    "SecurityHeadersMiddleware",
    "RequestValidationMiddleware",
    "setup_security_middleware",
    # Rate Limiting
    "RateLimiter",
    "RateLimitExceeded",
    "get_rate_limiter",
    "rate_limit",
    # Validators
    "sanitize_string",
    "validate_uuid",
    "validate_email",
    "validate_url",
    "SafeString",
    "InputValidator",
    # Config
    "SecurityConfig",
]
