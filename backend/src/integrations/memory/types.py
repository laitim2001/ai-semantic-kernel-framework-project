# =============================================================================
# IPA Platform - Memory System Types
# =============================================================================
# Sprint 79: S79-2 - mem0 長期記憶整合 (10 pts)
# Sprint 90: S90-2 - 環境變數配置
#
# This module defines the data types for the unified memory system,
# including memory records, search results, and configuration.
# =============================================================================

import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class MemoryType(str, Enum):
    """Types of memories stored in the system."""

    EVENT_RESOLUTION = "event_resolution"  # How events were resolved
    USER_PREFERENCE = "user_preference"  # User preferences and settings
    SYSTEM_KNOWLEDGE = "system_knowledge"  # System and infrastructure knowledge
    BEST_PRACTICE = "best_practice"  # Best practices and patterns
    CONVERSATION = "conversation"  # Conversation snippets
    FEEDBACK = "feedback"  # User feedback and corrections


class MemoryLayer(str, Enum):
    """Memory storage layers."""

    WORKING = "working"  # Redis - short-term, TTL 30 min
    SESSION = "session"  # PostgreSQL - medium-term, TTL 7 days
    LONG_TERM = "long_term"  # mem0 + Qdrant - permanent


@dataclass
class MemoryMetadata:
    """Metadata associated with a memory."""

    source: str = ""  # Source of the memory (e.g., "chat", "event")
    event_id: Optional[str] = None
    session_id: Optional[str] = None
    confidence: float = 1.0  # Confidence score
    importance: float = 0.5  # Importance score (0.0 to 1.0)
    tags: List[str] = field(default_factory=list)
    custom: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source": self.source,
            "event_id": self.event_id,
            "session_id": self.session_id,
            "confidence": self.confidence,
            "importance": self.importance,
            "tags": self.tags,
            "custom": self.custom,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryMetadata":
        """Create from dictionary."""
        return cls(
            source=data.get("source", ""),
            event_id=data.get("event_id"),
            session_id=data.get("session_id"),
            confidence=data.get("confidence", 1.0),
            importance=data.get("importance", 0.5),
            tags=data.get("tags", []),
            custom=data.get("custom", {}),
        )


@dataclass
class MemoryRecord:
    """A single memory record."""

    id: str
    user_id: str
    content: str
    memory_type: MemoryType
    layer: MemoryLayer
    metadata: MemoryMetadata
    embedding: Optional[List[float]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    accessed_at: Optional[datetime] = None
    access_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "layer": self.layer.value,
            "metadata": self.metadata.to_dict(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "accessed_at": self.accessed_at.isoformat() if self.accessed_at else None,
            "access_count": self.access_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryRecord":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            content=data["content"],
            memory_type=MemoryType(data["memory_type"]),
            layer=MemoryLayer(data.get("layer", "long_term")),
            metadata=MemoryMetadata.from_dict(data.get("metadata", {})),
            embedding=data.get("embedding"),
            created_at=datetime.fromisoformat(data["created_at"])
            if isinstance(data.get("created_at"), str)
            else data.get("created_at", datetime.utcnow()),
            updated_at=datetime.fromisoformat(data["updated_at"])
            if isinstance(data.get("updated_at"), str)
            else data.get("updated_at", datetime.utcnow()),
            accessed_at=datetime.fromisoformat(data["accessed_at"])
            if data.get("accessed_at")
            else None,
            access_count=data.get("access_count", 0),
        )


@dataclass
class MemorySearchResult:
    """Result of a memory search."""

    memory: MemoryRecord
    score: float  # Similarity score (0.0 to 1.0)
    highlights: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "memory": self.memory.to_dict(),
            "score": self.score,
            "highlights": self.highlights,
        }


@dataclass
class MemorySearchQuery:
    """Query for memory search."""

    query: str
    user_id: Optional[str] = None
    memory_types: Optional[List[MemoryType]] = None
    tags: Optional[List[str]] = None
    min_importance: float = 0.0
    limit: int = 10
    offset: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "user_id": self.user_id,
            "memory_types": [t.value for t in self.memory_types]
            if self.memory_types
            else None,
            "tags": self.tags,
            "min_importance": self.min_importance,
            "limit": self.limit,
            "offset": self.offset,
        }


@dataclass
class MemoryConfig:
    """
    Configuration for the memory system.

    All settings can be overridden via environment variables.
    See .env.example for available configuration options.
    """

    # Qdrant settings (from environment or defaults)
    qdrant_path: str = field(
        default_factory=lambda: os.getenv("QDRANT_PATH", "/data/mem0/qdrant")
    )
    qdrant_collection: str = field(
        default_factory=lambda: os.getenv("QDRANT_COLLECTION", "ipa_memories")
    )

    # Embedding settings
    embedding_model: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    )
    embedding_dims: int = 1536

    # LLM settings (for mem0 memory extraction)
    llm_provider: str = field(
        default_factory=lambda: os.getenv("MEMORY_LLM_PROVIDER", "anthropic")
    )
    llm_model: str = field(
        default_factory=lambda: os.getenv("MEMORY_LLM_MODEL", "claude-sonnet-4-20250514")
    )

    # TTL settings (in seconds)
    working_memory_ttl: int = field(
        default_factory=lambda: int(os.getenv("WORKING_MEMORY_TTL", "1800"))
    )
    session_memory_ttl: int = field(
        default_factory=lambda: int(os.getenv("SESSION_MEMORY_TTL", "604800"))
    )

    # Batch settings
    embedding_batch_size: int = 100
    search_batch_size: int = 50

    # Feature flag
    enabled: bool = field(
        default_factory=lambda: os.getenv("MEM0_ENABLED", "true").lower() == "true"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "qdrant_path": self.qdrant_path,
            "qdrant_collection": self.qdrant_collection,
            "embedding_model": self.embedding_model,
            "embedding_dims": self.embedding_dims,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "working_memory_ttl": self.working_memory_ttl,
            "session_memory_ttl": self.session_memory_ttl,
            "embedding_batch_size": self.embedding_batch_size,
            "search_batch_size": self.search_batch_size,
            "enabled": self.enabled,
        }

    @classmethod
    def from_env(cls) -> "MemoryConfig":
        """Create configuration from environment variables."""
        return cls()


def get_memory_config() -> MemoryConfig:
    """Get the memory configuration from environment variables."""
    return MemoryConfig.from_env()


# Default memory configuration (reads from environment)
DEFAULT_MEMORY_CONFIG = MemoryConfig()
