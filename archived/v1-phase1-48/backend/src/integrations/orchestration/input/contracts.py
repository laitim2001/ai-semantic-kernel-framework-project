"""
L4a Input Processing Contracts.

Sprint 116: Interface definitions for input processing layer.
All input sources (Webhook, HTTP, SSE) implement these interfaces.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..contracts import InputSource, RoutingRequest


class InputProcessorProtocol(ABC):
    """
    Protocol for individual input processors.

    Each input source (ServiceNow, Prometheus, User, SSE) implements
    this protocol to normalize its specific input format.
    """

    @abstractmethod
    async def process(self, raw_input: Any) -> RoutingRequest:
        """
        Process raw input and return normalized RoutingRequest.

        Args:
            raw_input: Raw input in source-specific format

        Returns:
            Normalized RoutingRequest
        """
        ...

    @abstractmethod
    def can_handle(self, raw_input: Any) -> bool:
        """
        Check if this processor can handle the given input.

        Args:
            raw_input: Raw input to check

        Returns:
            True if this processor can handle it
        """
        ...

    @abstractmethod
    def get_source_type(self) -> InputSource:
        """Return the InputSource this processor handles."""
        ...


@dataclass
class InputValidationResult:
    """Result of input validation."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    sanitized_input: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class InputValidatorProtocol(ABC):
    """
    Protocol for input validators.

    Validates and sanitizes raw inputs before processing.
    """

    @abstractmethod
    def validate(self, raw_input: Any, source: InputSource) -> InputValidationResult:
        """
        Validate raw input.

        Args:
            raw_input: Input to validate
            source: Expected input source

        Returns:
            InputValidationResult with validation outcome
        """
        ...


@dataclass
class InputProcessingMetrics:
    """Metrics for L4a input processing."""

    total_received: int = 0
    total_validated: int = 0
    total_rejected: int = 0
    by_source: Dict[str, int] = field(default_factory=dict)
    avg_processing_time_ms: float = 0.0

    def record(self, source: InputSource, processing_time_ms: float, accepted: bool) -> None:
        """
        Record a processing event.

        Args:
            source: Input source type
            processing_time_ms: Time taken to process in milliseconds
            accepted: Whether the input was accepted (validated) or rejected
        """
        self.total_received += 1
        source_key = source.value
        self.by_source[source_key] = self.by_source.get(source_key, 0) + 1

        if accepted:
            self.total_validated += 1
        else:
            self.total_rejected += 1

        # Running average
        n = self.total_received
        self.avg_processing_time_ms = (
            self.avg_processing_time_ms * (n - 1) + processing_time_ms
        ) / n

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "total_received": self.total_received,
            "total_validated": self.total_validated,
            "total_rejected": self.total_rejected,
            "by_source": self.by_source,
            "avg_processing_time_ms": round(self.avg_processing_time_ms, 2),
        }
