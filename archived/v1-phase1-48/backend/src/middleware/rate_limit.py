# =============================================================================
# IPA Platform - Rate Limiting Middleware
# =============================================================================
# Sprint 111: S111-9 - Rate Limiting
# Phase 31: Security Hardening + Quick Wins
#
# Uses slowapi for per-IP rate limiting on API endpoints.
#
# Rate limits:
#   - Global: 100 requests/minute per IP
#   - Login endpoints: 10 requests/minute per IP
#   - Sensitive operations: 30 requests/minute per IP
#   - Development mode: 1000 requests/minute (relaxed)
#
# Dependencies:
#   - slowapi>=0.1.9
#   - Settings (src.core.config)
# =============================================================================

import logging

from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.core.config import get_settings

logger = logging.getLogger(__name__)


def _get_rate_limit_key(request: Request) -> str:
    """Extract rate limit key from request.

    Uses the client's remote address (IP) as the rate limit key.
    In production behind a reverse proxy, ensure X-Forwarded-For is set.
    """
    return get_remote_address(request)


def _get_default_limit() -> str:
    """Get the default rate limit based on environment.

    Development: 1000/minute (relaxed for testing)
    Production: 100/minute
    """
    settings = get_settings()
    if settings.app_env == "development":
        return "1000/minute"
    return "100/minute"


# Create the global Limiter instance
limiter = Limiter(
    key_func=_get_rate_limit_key,
    default_limits=[_get_default_limit()],
    storage_uri=None,  # Uses in-memory storage; upgrade to Redis in Sprint 119
)


def setup_rate_limiting(app: FastAPI) -> None:
    """Configure rate limiting middleware on the FastAPI application.

    Attaches the slowapi Limiter to the app state and registers
    the rate limit exceeded exception handler.

    Args:
        app: The FastAPI application instance
    """
    settings = get_settings()

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    logger.info(
        f"Rate limiting configured: default={_get_default_limit()}, "
        f"env={settings.app_env}"
    )


# =============================================================================
# Route-specific rate limit decorators
# =============================================================================
# Usage in route files:
#
#   from src.middleware.rate_limit import limiter
#
#   @router.post("/login")
#   @limiter.limit("10/minute")
#   async def login(request: Request, ...):
#       ...
#
#   @router.post("/sensitive-action")
#   @limiter.limit("30/minute")
#   async def sensitive_action(request: Request, ...):
#       ...
# =============================================================================
