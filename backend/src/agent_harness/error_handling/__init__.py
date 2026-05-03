"""Category 8: Error Handling. See README.md."""

from agent_harness.error_handling._abc import (
    CircuitBreaker,
    ErrorClass,
    ErrorPolicy,
    ErrorTerminator,
)
from agent_harness.error_handling.policy import DefaultErrorPolicy
from agent_harness.error_handling.retry import (
    RetryConfig,
    RetryPolicyMatrix,
    compute_backoff,
)

__all__ = [
    "ErrorPolicy",
    "DefaultErrorPolicy",
    "CircuitBreaker",
    "ErrorTerminator",
    "ErrorClass",
    "RetryConfig",
    "RetryPolicyMatrix",
    "compute_backoff",
]
