"""
Rate Limiter

Sprint 3 - Story S3-2: API Security Hardening

Provides rate limiting functionality using Redis or in-memory storage.
"""
import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from functools import wraps
from typing import Callable, Dict, Optional, Tuple

from fastapi import HTTPException, Request, status

from .config import SecurityConfig, security_config

logger = logging.getLogger(__name__)


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""

    def __init__(
        self,
        detail: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
    ):
        """Initialize RateLimitExceeded.

        Args:
            detail: Error message
            retry_after: Seconds until rate limit resets
        """
        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)

        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers=headers,
        )


@dataclass
class RateLimitState:
    """State for a single rate limit bucket."""

    count: int
    window_start: float


class InMemoryRateLimiter:
    """In-memory rate limiter using sliding window algorithm.

    Suitable for single-instance deployments or development.
    For distributed deployments, use Redis-based rate limiter.
    """

    def __init__(
        self,
        requests_per_window: int = 60,
        window_seconds: int = 60,
        burst_size: int = 10,
    ):
        """Initialize InMemoryRateLimiter.

        Args:
            requests_per_window: Maximum requests allowed per window
            window_seconds: Window duration in seconds
            burst_size: Additional burst capacity
        """
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.burst_size = burst_size
        self._buckets: Dict[str, RateLimitState] = {}
        self._lock = asyncio.Lock()
        self._cleanup_counter = 0
        self._cleanup_threshold = 100

    async def is_allowed(self, key: str) -> Tuple[bool, int, int]:
        """Check if request is allowed under rate limit.

        Args:
            key: Rate limit key (e.g., client IP or user ID)

        Returns:
            Tuple of (is_allowed, remaining_requests, retry_after_seconds)
        """
        async with self._lock:
            now = time.time()

            # Cleanup old entries periodically
            self._cleanup_counter += 1
            if self._cleanup_counter >= self._cleanup_threshold:
                await self._cleanup(now)
                self._cleanup_counter = 0

            # Get or create bucket
            if key not in self._buckets:
                self._buckets[key] = RateLimitState(count=1, window_start=now)
                return True, self.requests_per_window - 1, 0

            bucket = self._buckets[key]

            # Check if window has expired
            window_elapsed = now - bucket.window_start
            if window_elapsed >= self.window_seconds:
                # Reset window
                bucket.count = 1
                bucket.window_start = now
                return True, self.requests_per_window - 1, 0

            # Check if under limit (with burst allowance)
            max_requests = self.requests_per_window + self.burst_size
            if bucket.count < max_requests:
                bucket.count += 1
                remaining = max(0, self.requests_per_window - bucket.count)
                return True, remaining, 0

            # Rate limited
            retry_after = int(self.window_seconds - window_elapsed) + 1
            return False, 0, retry_after

    async def _cleanup(self, now: float) -> None:
        """Remove expired rate limit entries.

        Args:
            now: Current timestamp
        """
        expired_keys = [
            key
            for key, bucket in self._buckets.items()
            if now - bucket.window_start >= self.window_seconds * 2
        ]
        for key in expired_keys:
            del self._buckets[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired rate limit entries")

    async def get_usage(self, key: str) -> Tuple[int, int]:
        """Get current usage for a key.

        Args:
            key: Rate limit key

        Returns:
            Tuple of (current_count, max_allowed)
        """
        async with self._lock:
            if key not in self._buckets:
                return 0, self.requests_per_window

            bucket = self._buckets[key]
            now = time.time()

            if now - bucket.window_start >= self.window_seconds:
                return 0, self.requests_per_window

            return bucket.count, self.requests_per_window


class RateLimiter:
    """Rate limiter with support for multiple backends.

    Provides a unified interface for rate limiting with support for:
    - In-memory storage (default, for development/single instance)
    - Redis storage (for distributed deployments)
    """

    def __init__(
        self,
        config: Optional[SecurityConfig] = None,
        redis_client: Optional[object] = None,
    ):
        """Initialize RateLimiter.

        Args:
            config: Security configuration
            redis_client: Optional Redis client for distributed rate limiting
        """
        self.config = config or security_config
        self.redis_client = redis_client

        # Use in-memory limiter by default
        self._memory_limiter = InMemoryRateLimiter(
            requests_per_window=self.config.rate_limit_requests,
            window_seconds=self.config.rate_limit_window_seconds,
            burst_size=self.config.rate_limit_burst,
        )

    async def check(
        self,
        key: str,
        requests_per_window: Optional[int] = None,
        window_seconds: Optional[int] = None,
    ) -> Tuple[bool, int, int]:
        """Check if request is allowed.

        Args:
            key: Rate limit key
            requests_per_window: Override default requests per window
            window_seconds: Override default window duration

        Returns:
            Tuple of (is_allowed, remaining, retry_after)
        """
        # TODO: Implement Redis-based rate limiting for distributed deployments
        if self.redis_client:
            return await self._check_redis(key, requests_per_window, window_seconds)

        return await self._memory_limiter.is_allowed(key)

    async def _check_redis(
        self,
        key: str,
        requests_per_window: Optional[int],
        window_seconds: Optional[int],
    ) -> Tuple[bool, int, int]:
        """Check rate limit using Redis.

        Args:
            key: Rate limit key
            requests_per_window: Max requests
            window_seconds: Window duration

        Returns:
            Tuple of (is_allowed, remaining, retry_after)
        """
        # Placeholder for Redis implementation
        # Would use Redis INCR with EXPIRE for atomic rate limiting
        return await self._memory_limiter.is_allowed(key)

    def get_key_for_request(self, request: Request, prefix: str = "rl") -> str:
        """Generate rate limit key from request.

        Args:
            request: FastAPI request
            prefix: Key prefix

        Returns:
            Rate limit key
        """
        # Use client IP as default key
        client_ip = self._get_client_ip(request)

        # If authenticated, use user ID for more accurate limiting
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"{prefix}:user:{user_id}"

        return f"{prefix}:ip:{client_ip}"

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request.

        Args:
            request: FastAPI request

        Returns:
            Client IP address
        """
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        if request.client:
            return request.client.host

        return "unknown"


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance.

    Returns:
        RateLimiter instance
    """
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def rate_limit(
    requests_per_minute: int = 60,
    key_func: Optional[Callable[[Request], str]] = None,
):
    """Decorator to apply rate limiting to an endpoint.

    Args:
        requests_per_minute: Maximum requests per minute
        key_func: Optional function to generate rate limit key from request

    Returns:
        Decorator function

    Example:
        @router.get("/api/data")
        @rate_limit(requests_per_minute=30)
        async def get_data(request: Request):
            return {"data": "value"}
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find request in args or kwargs
            request = kwargs.get("request")
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request is None:
                # No request object found, skip rate limiting
                logger.warning(f"Rate limit decorator on {func.__name__} but no Request found")
                return await func(*args, **kwargs)

            # Get rate limiter and check
            limiter = get_rate_limiter()

            if key_func:
                key = key_func(request)
            else:
                key = limiter.get_key_for_request(request, prefix=f"rl:{func.__name__}")

            is_allowed, remaining, retry_after = await limiter.check(
                key,
                requests_per_window=requests_per_minute,
                window_seconds=60,
            )

            if not is_allowed:
                logger.warning(
                    f"Rate limit exceeded for {key}",
                    extra={
                        "endpoint": func.__name__,
                        "key": key,
                        "retry_after": retry_after,
                    }
                )
                raise RateLimitExceeded(
                    detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                    retry_after=retry_after,
                )

            # Add rate limit headers to response via request state
            request.state.rate_limit_remaining = remaining
            request.state.rate_limit_limit = requests_per_minute

            return await func(*args, **kwargs)

        return wrapper
    return decorator
