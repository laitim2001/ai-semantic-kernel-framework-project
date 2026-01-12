# =============================================================================
# IPA Platform - A2A Communication Protocol
# =============================================================================
# Sprint 81: S81-2 - A2A 通信協議完善 (8 pts)
#
# This module defines the Agent-to-Agent communication protocol,
# including message formats and agent capabilities.
# =============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class MessageType(str, Enum):
    """Types of A2A messages."""

    # Task related
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    TASK_PROGRESS = "task_progress"
    TASK_CANCEL = "task_cancel"

    # Status
    STATUS_UPDATE = "status_update"
    HEARTBEAT = "heartbeat"

    # Discovery
    CAPABILITY_QUERY = "capability_query"
    CAPABILITY_RESPONSE = "capability_response"
    REGISTER = "register"
    UNREGISTER = "unregister"

    # Error
    ERROR = "error"
    ACK = "ack"


class MessagePriority(str, Enum):
    """Message priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class MessageStatus(str, Enum):
    """Message delivery status."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    PROCESSED = "processed"
    FAILED = "failed"
    EXPIRED = "expired"


class A2AAgentStatus(str, Enum):
    """Agent status for A2A communication."""

    ONLINE = "online"
    BUSY = "busy"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


@dataclass
class A2AMessage:
    """
    Standard A2A message format.

    All agent-to-agent communication uses this format.
    """

    message_id: str
    from_agent: str
    to_agent: str
    type: MessageType
    payload: Dict[str, Any]
    context: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None  # For tracking conversation chains
    timestamp: datetime = field(default_factory=datetime.utcnow)
    ttl_seconds: int = 300  # Time to live
    priority: MessagePriority = MessagePriority.NORMAL
    status: MessageStatus = MessageStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        from_agent: str,
        to_agent: str,
        type: MessageType,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        ttl_seconds: int = 300,
    ) -> "A2AMessage":
        """Create a new message with auto-generated ID."""
        return cls(
            message_id=str(uuid4()),
            from_agent=from_agent,
            to_agent=to_agent,
            type=type,
            payload=payload,
            correlation_id=correlation_id,
            priority=priority,
            ttl_seconds=ttl_seconds,
        )

    @property
    def is_expired(self) -> bool:
        """Check if message has expired."""
        elapsed = (datetime.utcnow() - self.timestamp).total_seconds()
        return elapsed > self.ttl_seconds

    @property
    def can_retry(self) -> bool:
        """Check if message can be retried."""
        return self.retry_count < self.max_retries

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "message_id": self.message_id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "type": self.type.value,
            "payload": self.payload,
            "context": self.context,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "ttl_seconds": self.ttl_seconds,
            "priority": self.priority.value,
            "status": self.status.value,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "A2AMessage":
        """Create from dictionary."""
        return cls(
            message_id=data["message_id"],
            from_agent=data["from_agent"],
            to_agent=data["to_agent"],
            type=MessageType(data["type"]),
            payload=data.get("payload", {}),
            context=data.get("context", {}),
            correlation_id=data.get("correlation_id"),
            timestamp=datetime.fromisoformat(data["timestamp"])
            if isinstance(data.get("timestamp"), str)
            else data.get("timestamp", datetime.utcnow()),
            ttl_seconds=data.get("ttl_seconds", 300),
            priority=MessagePriority(data.get("priority", "normal")),
            status=MessageStatus(data.get("status", "pending")),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            metadata=data.get("metadata", {}),
        )


@dataclass
class AgentCapability:
    """
    Agent capability declaration.

    Agents declare their capabilities for discovery and matching.
    """

    agent_id: str
    name: str
    description: str = ""
    capabilities: List[str] = field(default_factory=list)
    skills: Dict[str, float] = field(default_factory=dict)  # skill -> proficiency
    version: str = "1.0.0"
    endpoint: Optional[str] = None
    max_concurrent_tasks: int = 5
    current_load: int = 0
    status: A2AAgentStatus = A2AAgentStatus.ONLINE
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    registered_at: datetime = field(default_factory=datetime.utcnow)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)

    @property
    def availability_score(self) -> float:
        """Calculate availability (0-1)."""
        if self.status != A2AAgentStatus.ONLINE:
            return 0.0
        if self.max_concurrent_tasks == 0:
            return 0.0
        return 1.0 - (self.current_load / self.max_concurrent_tasks)

    def can_handle(self, required: List[str]) -> bool:
        """Check if agent can handle required capabilities."""
        return all(cap in self.capabilities for cap in required)

    def matches_tags(self, tags: List[str]) -> bool:
        """Check if agent matches any of the tags."""
        return bool(set(self.tags) & set(tags))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "skills": self.skills,
            "version": self.version,
            "endpoint": self.endpoint,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "current_load": self.current_load,
            "status": self.status.value,
            "availability_score": self.availability_score,
            "tags": self.tags,
            "metadata": self.metadata,
            "registered_at": self.registered_at.isoformat(),
            "last_heartbeat": self.last_heartbeat.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentCapability":
        """Create from dictionary."""
        return cls(
            agent_id=data["agent_id"],
            name=data["name"],
            description=data.get("description", ""),
            capabilities=data.get("capabilities", []),
            skills=data.get("skills", {}),
            version=data.get("version", "1.0.0"),
            endpoint=data.get("endpoint"),
            max_concurrent_tasks=data.get("max_concurrent_tasks", 5),
            current_load=data.get("current_load", 0),
            status=A2AAgentStatus(data.get("status", "online")),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            registered_at=datetime.fromisoformat(data["registered_at"])
            if isinstance(data.get("registered_at"), str)
            else data.get("registered_at", datetime.utcnow()),
            last_heartbeat=datetime.fromisoformat(data["last_heartbeat"])
            if isinstance(data.get("last_heartbeat"), str)
            else data.get("last_heartbeat", datetime.utcnow()),
        )


@dataclass
class DiscoveryQuery:
    """Query for discovering agents."""

    required_capabilities: List[str] = field(default_factory=list)
    required_tags: List[str] = field(default_factory=list)
    min_availability: float = 0.1
    max_results: int = 10
    include_busy: bool = False
    metadata_filters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "required_capabilities": self.required_capabilities,
            "required_tags": self.required_tags,
            "min_availability": self.min_availability,
            "max_results": self.max_results,
            "include_busy": self.include_busy,
            "metadata_filters": self.metadata_filters,
        }


@dataclass
class DiscoveryResult:
    """Result of agent discovery."""

    query: DiscoveryQuery
    agents: List[AgentCapability] = field(default_factory=list)
    total_found: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query": self.query.to_dict(),
            "agents": [a.to_dict() for a in self.agents],
            "total_found": self.total_found,
            "timestamp": self.timestamp.isoformat(),
        }
