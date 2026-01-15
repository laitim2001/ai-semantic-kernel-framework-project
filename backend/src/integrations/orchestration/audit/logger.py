"""
Audit Logger for Intent Router

Provides structured logging for routing decisions with support for:
- JSON formatted logs
- Correlation IDs
- Performance metrics
- Integration with standard Python logging

Sprint 91: Pattern Matcher + Rule Definition (Phase 28)
"""

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from ..intent_router.models import RoutingDecision


@dataclass
class AuditEntry:
    """
    Structured audit entry for routing decisions.

    Attributes:
        correlation_id: Unique ID for request tracing
        timestamp: When the entry was created
        event_type: Type of audit event
        user_input: Original user input (truncated for privacy)
        routing_decision: The routing decision made
        layer: Which routing layer made the decision
        processing_time_ms: Time taken to process
        metadata: Additional context
    """
    correlation_id: str
    timestamp: datetime
    event_type: str
    user_input: str
    routing_decision: Optional[Dict[str, Any]] = None
    layer: str = "pattern"
    processing_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "user_input": self.user_input,
            "routing_decision": self.routing_decision,
            "layer": self.layer,
            "processing_time_ms": self.processing_time_ms,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class AuditLogger:
    """
    Structured audit logger for routing decisions.

    Provides methods for logging routing decisions with full context
    in a format suitable for log aggregation and analysis.

    Attributes:
        logger: Python logger instance
        log_level: Logging level (default: INFO)
        max_input_length: Maximum user input length to log (privacy)
    """

    DEFAULT_MAX_INPUT_LENGTH = 500

    def __init__(
        self,
        logger_name: str = "orchestration.audit",
        log_level: int = logging.INFO,
        max_input_length: int = DEFAULT_MAX_INPUT_LENGTH,
    ):
        """
        Initialize the audit logger.

        Args:
            logger_name: Name for the Python logger
            log_level: Logging level
            max_input_length: Max chars of user input to log
        """
        self.logger = logging.getLogger(logger_name)
        self.log_level = log_level
        self.max_input_length = max_input_length

        # Set up JSON formatting if not already configured
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter(
                    '{"timestamp":"%(asctime)s","level":"%(levelname)s",'
                    '"logger":"%(name)s","message":%(message)s}'
                )
            )
            self.logger.addHandler(handler)
            self.logger.setLevel(log_level)

    def _truncate_input(self, user_input: str) -> str:
        """Truncate user input for privacy and log size."""
        if len(user_input) > self.max_input_length:
            return user_input[:self.max_input_length] + "..."
        return user_input

    def _generate_correlation_id(self) -> str:
        """Generate a unique correlation ID."""
        return str(uuid.uuid4())

    def log_routing_decision(
        self,
        user_input: str,
        decision: RoutingDecision,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEntry:
        """
        Log a routing decision.

        Args:
            user_input: The original user input
            decision: The routing decision made
            correlation_id: Optional correlation ID (generated if not provided)
            metadata: Additional context to log

        Returns:
            The created AuditEntry
        """
        entry = AuditEntry(
            correlation_id=correlation_id or self._generate_correlation_id(),
            timestamp=datetime.utcnow(),
            event_type="routing_decision",
            user_input=self._truncate_input(user_input),
            routing_decision=decision.to_dict(),
            layer=decision.routing_layer,
            processing_time_ms=decision.processing_time_ms,
            metadata=metadata or {},
        )

        self.logger.log(self.log_level, entry.to_json())
        return entry

    def log_pattern_match(
        self,
        user_input: str,
        rule_id: Optional[str],
        matched: bool,
        confidence: float,
        processing_time_ms: float,
        correlation_id: Optional[str] = None,
    ) -> AuditEntry:
        """
        Log a pattern match attempt.

        Args:
            user_input: The original user input
            rule_id: ID of matched rule (if any)
            matched: Whether a match was found
            confidence: Match confidence score
            processing_time_ms: Processing time
            correlation_id: Optional correlation ID

        Returns:
            The created AuditEntry
        """
        entry = AuditEntry(
            correlation_id=correlation_id or self._generate_correlation_id(),
            timestamp=datetime.utcnow(),
            event_type="pattern_match",
            user_input=self._truncate_input(user_input),
            routing_decision=None,
            layer="pattern",
            processing_time_ms=processing_time_ms,
            metadata={
                "rule_id": rule_id,
                "matched": matched,
                "confidence": confidence,
            },
        )

        self.logger.log(self.log_level, entry.to_json())
        return entry

    def log_layer_escalation(
        self,
        user_input: str,
        from_layer: str,
        to_layer: str,
        reason: str,
        correlation_id: Optional[str] = None,
    ) -> AuditEntry:
        """
        Log escalation from one routing layer to another.

        Args:
            user_input: The original user input
            from_layer: Source routing layer
            to_layer: Target routing layer
            reason: Reason for escalation
            correlation_id: Optional correlation ID

        Returns:
            The created AuditEntry
        """
        entry = AuditEntry(
            correlation_id=correlation_id or self._generate_correlation_id(),
            timestamp=datetime.utcnow(),
            event_type="layer_escalation",
            user_input=self._truncate_input(user_input),
            routing_decision=None,
            layer=from_layer,
            processing_time_ms=0.0,
            metadata={
                "from_layer": from_layer,
                "to_layer": to_layer,
                "reason": reason,
            },
        )

        self.logger.log(self.log_level, entry.to_json())
        return entry

    def log_error(
        self,
        user_input: str,
        error_type: str,
        error_message: str,
        layer: str = "unknown",
        correlation_id: Optional[str] = None,
    ) -> AuditEntry:
        """
        Log an error during routing.

        Args:
            user_input: The original user input
            error_type: Type of error
            error_message: Error description
            layer: Which layer encountered the error
            correlation_id: Optional correlation ID

        Returns:
            The created AuditEntry
        """
        entry = AuditEntry(
            correlation_id=correlation_id or self._generate_correlation_id(),
            timestamp=datetime.utcnow(),
            event_type="error",
            user_input=self._truncate_input(user_input),
            routing_decision=None,
            layer=layer,
            processing_time_ms=0.0,
            metadata={
                "error_type": error_type,
                "error_message": error_message,
            },
        )

        self.logger.log(logging.ERROR, entry.to_json())
        return entry
