"""
Orchestration Layer Contracts — L4a <-> L4b Interface Definitions.

Sprint 116: Defines the shared contracts between Input Processing (L4a)
and Decision Engine (L4b), enabling clean separation of concerns.

L4a (Input Processing): Receives raw inputs, normalizes, validates
L4b (Decision Engine): Routes, classifies, makes workflow decisions

Data flow: InputEvent -> RoutingRequest -> RoutingResult
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class InputSource(str, Enum):
    """Source of the input event."""

    WEBHOOK_SERVICENOW = "webhook_servicenow"
    WEBHOOK_PROMETHEUS = "webhook_prometheus"
    HTTP_API = "http_api"
    SSE_STREAM = "sse_stream"
    USER_CHAT = "user_chat"
    RITM = "ritm"
    UNKNOWN = "unknown"


@dataclass
class RoutingRequest:
    """
    Routing Request — L4a output, L4b input.

    The normalized request format passed from Input Processing
    to the Decision Engine for routing analysis.

    Attributes:
        query: The normalized text query for routing
        intent_hint: Optional pre-classified intent hint from source
        context: Additional context from the input source
        source: Origin of this request
        request_id: Unique identifier for tracing
        timestamp: When the request was created
        metadata: Source-specific metadata
        priority: Optional priority hint (1=highest, 5=lowest)
    """

    query: str
    intent_hint: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    source: InputSource = InputSource.UNKNOWN
    request_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "query": self.query,
            "intent_hint": self.intent_hint,
            "context": self.context,
            "source": self.source.value,
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RoutingRequest":
        """Deserialize from dictionary."""
        source = data.get("source", "unknown")
        if isinstance(source, str):
            try:
                source = InputSource(source)
            except ValueError:
                source = InputSource.UNKNOWN

        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.utcnow()

        return cls(
            query=data.get("query", ""),
            intent_hint=data.get("intent_hint"),
            context=data.get("context", {}),
            source=source,
            request_id=data.get("request_id"),
            timestamp=timestamp,
            metadata=data.get("metadata", {}),
            priority=data.get("priority"),
        )


@dataclass
class RoutingResult:
    """
    Routing Result — L4b output.

    The decision made by the Decision Engine after routing analysis.

    Attributes:
        intent: Classified intent category
        sub_intent: Specific sub-intent within category
        confidence: Confidence score (0.0-1.0)
        matched_layer: Which routing tier matched (pattern/semantic/llm)
        workflow_type: Recommended workflow execution type
        risk_level: Assessed risk level
        completeness: Whether sufficient info is available
        missing_fields: List of missing required fields
        metadata: Additional routing metadata
    """

    intent: str
    sub_intent: str = ""
    confidence: float = 0.0
    matched_layer: str = ""
    workflow_type: str = ""
    risk_level: str = "LOW"
    completeness: bool = True
    missing_fields: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "intent": self.intent,
            "sub_intent": self.sub_intent,
            "confidence": self.confidence,
            "matched_layer": self.matched_layer,
            "workflow_type": self.workflow_type,
            "risk_level": self.risk_level,
            "completeness": self.completeness,
            "missing_fields": self.missing_fields,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RoutingResult":
        """Deserialize from dictionary."""
        return cls(
            intent=data.get("intent", ""),
            sub_intent=data.get("sub_intent", ""),
            confidence=data.get("confidence", 0.0),
            matched_layer=data.get("matched_layer", ""),
            workflow_type=data.get("workflow_type", ""),
            risk_level=data.get("risk_level", "LOW"),
            completeness=data.get("completeness", True),
            missing_fields=data.get("missing_fields", []),
            metadata=data.get("metadata", {}),
        )


class InputGatewayProtocol(ABC):
    """
    Protocol for Input Gateway implementations (L4a).

    All input gateways must implement this interface to produce
    RoutingRequest objects for the Decision Engine.
    """

    @abstractmethod
    async def receive(self, raw_input: Any) -> RoutingRequest:
        """
        Receive and normalize raw input into a RoutingRequest.

        Args:
            raw_input: Raw input from any source

        Returns:
            Normalized RoutingRequest
        """
        ...

    @abstractmethod
    async def validate(self, raw_input: Any) -> bool:
        """
        Validate that the raw input is acceptable.

        Args:
            raw_input: Raw input to validate

        Returns:
            True if valid, False otherwise
        """
        ...


class RouterProtocol(ABC):
    """
    Protocol for Router implementations (L4b).

    All routers must implement this interface to consume
    RoutingRequest and produce RoutingResult objects.
    """

    @abstractmethod
    async def route(self, request: RoutingRequest) -> RoutingResult:
        """
        Route the request and produce a routing decision.

        Args:
            request: Normalized routing request from L4a

        Returns:
            RoutingResult with classification and workflow decision
        """
        ...

    @abstractmethod
    def get_available_layers(self) -> List[str]:
        """
        Get list of available routing layers.

        Returns:
            List of layer names (e.g., ["pattern", "semantic", "llm"])
        """
        ...


# =============================================================================
# Adapter functions — bridge existing models to contracts
# =============================================================================


def incoming_request_to_routing_request(
    incoming: Any,
    source: InputSource = InputSource.UNKNOWN,
) -> RoutingRequest:
    """
    Convert an existing IncomingRequest to a RoutingRequest.

    Bridges Sprint 95 IncomingRequest to Sprint 116 RoutingRequest contract.

    Args:
        incoming: IncomingRequest instance
        source: InputSource to assign (used as fallback if source_type mapping fails)

    Returns:
        RoutingRequest
    """
    # Map source_type string to InputSource
    source_type = getattr(incoming, "source_type", None) or "unknown"
    source_map = {
        "servicenow": InputSource.WEBHOOK_SERVICENOW,
        "prometheus": InputSource.WEBHOOK_PROMETHEUS,
        "user": InputSource.USER_CHAT,
        "api": InputSource.HTTP_API,
    }
    mapped_source = source_map.get(str(source_type).lower(), source)

    # Extract content — IncomingRequest uses "content" field
    query = getattr(incoming, "content", "")

    # Extract context — IncomingRequest uses "data" field for structured payload
    context = getattr(incoming, "data", {})
    if context is None:
        context = {}

    # Extract request_id
    request_id = getattr(incoming, "request_id", None)

    # Extract timestamp with fallback
    timestamp = getattr(incoming, "timestamp", None)
    if timestamp is None:
        timestamp = datetime.utcnow()

    # Extract metadata
    metadata = getattr(incoming, "metadata", {})
    if metadata is None:
        metadata = {}

    return RoutingRequest(
        query=query if query is not None else "",
        context=context,
        source=mapped_source,
        request_id=request_id,
        timestamp=timestamp,
        metadata=metadata,
    )


def routing_decision_to_routing_result(decision: Any) -> RoutingResult:
    """
    Convert an existing RoutingDecision to a RoutingResult.

    Bridges Sprint 93 RoutingDecision to Sprint 116 RoutingResult contract.

    Args:
        decision: RoutingDecision instance

    Returns:
        RoutingResult
    """
    # Extract intent_category — may be enum with .value
    intent = getattr(decision, "intent_category", "")
    if hasattr(intent, "value"):
        intent = intent.value

    # Extract workflow_type — may be enum with .value
    workflow_type = getattr(decision, "workflow_type", "")
    if hasattr(workflow_type, "value"):
        workflow_type = workflow_type.value

    # Extract risk_level — may be enum with .value
    risk_level = getattr(decision, "risk_level", "LOW")
    if hasattr(risk_level, "value"):
        risk_level = risk_level.value

    # Extract sub_intent
    sub_intent = getattr(decision, "sub_intent", "") or ""

    # Extract confidence — RoutingDecision uses "confidence" (not "confidence_score")
    # but some versions may use "confidence_score", handle both
    confidence = getattr(decision, "confidence", None)
    if confidence is None:
        confidence = getattr(decision, "confidence_score", 0.0)
    if confidence is None:
        confidence = 0.0

    # Extract routing_layer
    matched_layer = getattr(decision, "routing_layer", "") or ""

    # Extract completeness info
    completeness_info = getattr(decision, "completeness", None)
    completeness = True
    missing_fields: List[str] = []
    if completeness_info is not None:
        # CompletenessInfo uses "is_complete" (not "is_sufficient")
        completeness = getattr(completeness_info, "is_complete", True)
        if completeness is None:
            completeness = True
        missing_fields = getattr(completeness_info, "missing_fields", [])
        if missing_fields is None:
            missing_fields = []

    # Extract metadata
    metadata = getattr(decision, "metadata", {})
    if metadata is None:
        metadata = {}

    return RoutingResult(
        intent=str(intent) if intent else "",
        sub_intent=str(sub_intent),
        confidence=float(confidence),
        matched_layer=str(matched_layer),
        workflow_type=str(workflow_type) if workflow_type else "",
        risk_level=str(risk_level) if risk_level else "LOW",
        completeness=bool(completeness),
        missing_fields=list(missing_fields),
        metadata=dict(metadata),
    )
