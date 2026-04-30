# =============================================================================
# IPA Platform - Retry Policy
# =============================================================================
# Sprint 80: S80-3 - Trial-and-Error 智能回退 (6 pts)
#
# This module provides retry policies with exponential backoff for
# handling transient failures in autonomous operations.
# =============================================================================

import asyncio
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar

logger = logging.getLogger(__name__)


class FailureType(str, Enum):
    """Classification of failure types."""

    TRANSIENT = "transient"  # Can retry (network, timeout, rate limit)
    RECOVERABLE = "recoverable"  # Can retry with modifications
    FATAL = "fatal"  # Cannot retry (auth error, invalid input)
    UNKNOWN = "unknown"  # Unknown, apply default policy


# Error patterns for failure classification
TRANSIENT_ERRORS = [
    "timeout",
    "connection",
    "network",
    "rate_limit",
    "429",
    "503",
    "504",
    "gateway",
    "temporarily",
    "retry",
    "overloaded",
]

FATAL_ERRORS = [
    "authentication",
    "authorization",
    "forbidden",
    "invalid_api_key",
    "not_found",
    "invalid_request",
    "invalid_parameter",
    "permission",
    "401",
    "403",
    "404",
]


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True  # Add randomness to prevent thundering herd
    jitter_factor: float = 0.1  # 10% jitter

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "max_retries": self.max_retries,
            "initial_delay_seconds": self.initial_delay_seconds,
            "max_delay_seconds": self.max_delay_seconds,
            "exponential_base": self.exponential_base,
            "jitter": self.jitter,
            "jitter_factor": self.jitter_factor,
        }


@dataclass
class RetryAttempt:
    """Record of a retry attempt."""

    attempt_number: int
    timestamp: datetime
    error: str
    failure_type: FailureType
    delay_seconds: float
    success: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "attempt_number": self.attempt_number,
            "timestamp": self.timestamp.isoformat(),
            "error": self.error,
            "failure_type": self.failure_type.value,
            "delay_seconds": self.delay_seconds,
            "success": self.success,
        }


@dataclass
class RetryResult:
    """Result of retry operation."""

    success: bool
    result: Optional[Any] = None
    total_attempts: int = 0
    attempts: List[RetryAttempt] = field(default_factory=list)
    final_error: Optional[str] = None
    total_delay_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "total_attempts": self.total_attempts,
            "attempts": [a.to_dict() for a in self.attempts],
            "final_error": self.final_error,
            "total_delay_seconds": self.total_delay_seconds,
        }


# Default configuration
DEFAULT_RETRY_CONFIG = RetryConfig()


T = TypeVar("T")


class RetryPolicy:
    """
    Retry policy with exponential backoff.

    Provides intelligent retry behavior with:
    - Exponential backoff delays: 1s → 2s → 4s → 8s
    - Failure type classification
    - Jitter to prevent thundering herd
    - Configurable retry limits
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        """
        Initialize retry policy.

        Args:
            config: Retry configuration. Uses defaults if not provided.
        """
        self.config = config or DEFAULT_RETRY_CONFIG

    def classify_failure(self, error: Exception) -> FailureType:
        """
        Classify failure type from exception.

        Args:
            error: The exception that occurred.

        Returns:
            Classified FailureType.
        """
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()

        # Check for transient errors
        for pattern in TRANSIENT_ERRORS:
            if pattern in error_str or pattern in error_type:
                return FailureType.TRANSIENT

        # Check for fatal errors
        for pattern in FATAL_ERRORS:
            if pattern in error_str or pattern in error_type:
                return FailureType.FATAL

        # Check for specific exception types
        if isinstance(error, (TimeoutError, asyncio.TimeoutError)):
            return FailureType.TRANSIENT

        if isinstance(error, (ValueError, TypeError)):
            return FailureType.FATAL

        if isinstance(error, ConnectionError):
            return FailureType.TRANSIENT

        return FailureType.UNKNOWN

    def should_retry(
        self,
        attempt: int,
        failure_type: FailureType,
    ) -> bool:
        """
        Determine if operation should be retried.

        Args:
            attempt: Current attempt number (1-indexed).
            failure_type: Type of failure that occurred.

        Returns:
            True if should retry, False otherwise.
        """
        # Check max retries
        if attempt >= self.config.max_retries:
            logger.debug(f"Max retries ({self.config.max_retries}) reached")
            return False

        # Check failure type
        if failure_type == FailureType.FATAL:
            logger.debug("Fatal error - not retrying")
            return False

        # Transient and recoverable errors should retry
        if failure_type in (FailureType.TRANSIENT, FailureType.RECOVERABLE):
            return True

        # Unknown errors - retry with caution
        if failure_type == FailureType.UNKNOWN:
            # Only retry unknown errors once
            return attempt < 2

        return False

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for next retry using exponential backoff.

        Args:
            attempt: Current attempt number (1-indexed).

        Returns:
            Delay in seconds before next retry.
        """
        # Calculate base delay: initial * base^attempt
        delay = self.config.initial_delay_seconds * (
            self.config.exponential_base ** (attempt - 1)
        )

        # Apply max delay cap
        delay = min(delay, self.config.max_delay_seconds)

        # Add jitter if enabled
        if self.config.jitter:
            jitter_range = delay * self.config.jitter_factor
            delay += random.uniform(-jitter_range, jitter_range)
            delay = max(0.1, delay)  # Ensure minimum delay

        return delay

    async def exponential_backoff(self, attempt: int) -> float:
        """
        Wait with exponential backoff.

        Args:
            attempt: Current attempt number.

        Returns:
            Actual delay used.
        """
        delay = self.calculate_delay(attempt)
        logger.debug(f"Backoff: waiting {delay:.2f}s before retry #{attempt + 1}")
        await asyncio.sleep(delay)
        return delay

    async def execute_with_retry(
        self,
        operation: Callable[[], T],
        operation_name: str = "operation",
    ) -> RetryResult:
        """
        Execute operation with retry logic.

        Args:
            operation: Async callable to execute.
            operation_name: Name for logging.

        Returns:
            RetryResult with success status and attempts.
        """
        attempts: List[RetryAttempt] = []
        total_delay = 0.0

        for attempt in range(1, self.config.max_retries + 1):
            try:
                logger.debug(f"Attempt {attempt}/{self.config.max_retries}: {operation_name}")

                # Execute operation
                if asyncio.iscoroutinefunction(operation):
                    result = await operation()
                else:
                    result = operation()

                # Success!
                attempts.append(
                    RetryAttempt(
                        attempt_number=attempt,
                        timestamp=datetime.utcnow(),
                        error="",
                        failure_type=FailureType.TRANSIENT,
                        delay_seconds=0.0,
                        success=True,
                    )
                )

                logger.info(
                    f"{operation_name} succeeded on attempt {attempt}"
                )

                return RetryResult(
                    success=True,
                    result=result,
                    total_attempts=attempt,
                    attempts=attempts,
                    total_delay_seconds=total_delay,
                )

            except Exception as e:
                error_str = str(e)
                failure_type = self.classify_failure(e)

                logger.warning(
                    f"{operation_name} failed (attempt {attempt}): "
                    f"{error_str} ({failure_type.value})"
                )

                # Calculate delay for this attempt
                delay = 0.0
                should_continue = self.should_retry(attempt, failure_type)

                if should_continue:
                    delay = await self.exponential_backoff(attempt)
                    total_delay += delay

                attempts.append(
                    RetryAttempt(
                        attempt_number=attempt,
                        timestamp=datetime.utcnow(),
                        error=error_str,
                        failure_type=failure_type,
                        delay_seconds=delay,
                        success=False,
                    )
                )

                if not should_continue:
                    logger.error(
                        f"{operation_name} failed after {attempt} attempts: {error_str}"
                    )
                    return RetryResult(
                        success=False,
                        total_attempts=attempt,
                        attempts=attempts,
                        final_error=error_str,
                        total_delay_seconds=total_delay,
                    )

        # Should not reach here, but handle it
        return RetryResult(
            success=False,
            total_attempts=len(attempts),
            attempts=attempts,
            final_error="Max retries exceeded",
            total_delay_seconds=total_delay,
        )


# Convenience function for quick retries
async def with_retry(
    operation: Callable[[], T],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    operation_name: str = "operation",
) -> RetryResult:
    """
    Execute operation with default retry policy.

    Args:
        operation: Async callable to execute.
        max_retries: Maximum retry attempts.
        initial_delay: Initial delay in seconds.
        operation_name: Name for logging.

    Returns:
        RetryResult with success status.
    """
    config = RetryConfig(
        max_retries=max_retries,
        initial_delay_seconds=initial_delay,
    )
    policy = RetryPolicy(config)
    return await policy.execute_with_retry(operation, operation_name)
