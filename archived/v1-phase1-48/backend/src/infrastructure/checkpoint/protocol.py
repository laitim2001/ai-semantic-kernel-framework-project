"""Unified Checkpoint Provider Protocol.

Sprint 120 -- Story 120-2: Define a common interface for all checkpoint systems.

The IPA Platform has 4 independent checkpoint systems. This Protocol defines
the common interface that each system must implement to participate in the
UnifiedCheckpointRegistry.

Systems:
    1. Domain Checkpoints (PostgreSQL)
    2. Hybrid Checkpoint (Memory/Redis/Postgres/FS)
    3. Agent Framework Checkpoint (Redis/Postgres)
    4. Session Recovery (Cache)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from uuid import uuid4


# =============================================================================
# Checkpoint Entry
# =============================================================================


@dataclass
class CheckpointEntry:
    """Unified checkpoint data entry.

    Attributes:
        checkpoint_id: Unique identifier
        provider_name: Name of the provider that owns this checkpoint
        session_id: Associated session ID
        data: Checkpoint data payload
        metadata: Additional metadata (e.g., version, tags)
        created_at: Creation timestamp
        expires_at: Optional expiration timestamp
    """

    checkpoint_id: str = field(default_factory=lambda: str(uuid4()))
    provider_name: str = ""
    session_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "checkpoint_id": self.checkpoint_id,
            "provider_name": self.provider_name,
            "session_id": self.session_id,
            "data": self.data,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CheckpointEntry":
        """Deserialize from dictionary."""
        return cls(
            checkpoint_id=data.get("checkpoint_id", str(uuid4())),
            provider_name=data.get("provider_name", ""),
            session_id=data.get("session_id", ""),
            data=data.get("data", {}),
            metadata=data.get("metadata", {}),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else datetime.utcnow()
            ),
            expires_at=(
                datetime.fromisoformat(data["expires_at"])
                if data.get("expires_at")
                else None
            ),
        )

    def is_expired(self) -> bool:
        """Check if checkpoint has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


# =============================================================================
# Checkpoint Provider Protocol
# =============================================================================


@runtime_checkable
class CheckpointProvider(Protocol):
    """Protocol for checkpoint providers.

    Each of the 4 checkpoint systems implements this Protocol
    to participate in the UnifiedCheckpointRegistry.
    """

    @property
    def provider_name(self) -> str:
        """Unique provider identifier (e.g., 'hybrid', 'agent_framework')."""
        ...

    async def save_checkpoint(
        self,
        checkpoint_id: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Save checkpoint data.

        Args:
            checkpoint_id: Unique checkpoint identifier
            data: Checkpoint data payload
            metadata: Optional metadata

        Returns:
            The checkpoint_id
        """
        ...

    async def load_checkpoint(
        self,
        checkpoint_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Load checkpoint data.

        Args:
            checkpoint_id: Checkpoint to load

        Returns:
            Checkpoint data, or None if not found
        """
        ...

    async def list_checkpoints(
        self,
        session_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[CheckpointEntry]:
        """List checkpoints, optionally filtered by session.

        Args:
            session_id: Optional session filter
            limit: Maximum entries to return

        Returns:
            List of checkpoint entries
        """
        ...

    async def delete_checkpoint(
        self,
        checkpoint_id: str,
    ) -> bool:
        """Delete a checkpoint.

        Args:
            checkpoint_id: Checkpoint to delete

        Returns:
            True if deleted, False if not found
        """
        ...
