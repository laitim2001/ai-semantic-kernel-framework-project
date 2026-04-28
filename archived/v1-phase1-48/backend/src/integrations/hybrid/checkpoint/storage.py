# =============================================================================
# IPA Platform - Unified Checkpoint Storage
# =============================================================================
# Phase 14: Human-in-the-Loop & Approval
# Sprint 57: Unified Checkpoint & Polish
#
# Abstract storage interface for HybridCheckpoint with multiple backend support.
# Provides consistent API for checkpoint persistence across different storage systems.
#
# Key Features:
#   - Abstract storage interface (Protocol)
#   - Save/Load/Delete operations
#   - Query by session, status, time range
#   - Expiration and cleanup management
#
# Dependencies:
#   - HybridCheckpoint, CheckpointStatus (models)
#   - CheckpointSerializer (serialization)
# =============================================================================

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from .models import CheckpointStatus, CheckpointType, HybridCheckpoint, RestoreResult
from .serialization import CheckpointSerializer, SerializationConfig


# =============================================================================
# Storage Configuration
# =============================================================================


class StorageBackend(str, Enum):
    """Available storage backends."""

    REDIS = "redis"
    POSTGRES = "postgres"
    FILESYSTEM = "filesystem"
    MEMORY = "memory"


@dataclass
class StorageConfig:
    """
    Configuration for checkpoint storage.

    Attributes:
        backend: Storage backend to use
        ttl_seconds: Time-to-live for checkpoints (default: 24 hours)
        max_checkpoints_per_session: Maximum checkpoints per session
        enable_compression: Whether to compress stored data
        enable_encryption: Whether to encrypt stored data (future)
        cleanup_interval_seconds: Interval for automatic cleanup
    """

    backend: StorageBackend = StorageBackend.REDIS
    ttl_seconds: int = 86400  # 24 hours
    max_checkpoints_per_session: int = 100
    enable_compression: bool = True
    enable_encryption: bool = False
    cleanup_interval_seconds: int = 3600  # 1 hour
    serialization_config: Optional[SerializationConfig] = None


# =============================================================================
# Storage Query
# =============================================================================


@dataclass
class CheckpointQuery:
    """
    Query parameters for checkpoint retrieval.

    Attributes:
        session_id: Filter by session ID
        checkpoint_type: Filter by checkpoint type
        status: Filter by checkpoint status
        execution_mode: Filter by execution mode
        created_after: Filter by creation time (after)
        created_before: Filter by creation time (before)
        limit: Maximum number of results
        offset: Offset for pagination
        order_by: Field to order by
        ascending: Sort order
    """

    session_id: Optional[str] = None
    checkpoint_type: Optional[CheckpointType] = None
    status: Optional[CheckpointStatus] = None
    execution_mode: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    limit: int = 100
    offset: int = 0
    order_by: str = "created_at"
    ascending: bool = False  # Most recent first


@dataclass
class StorageStats:
    """
    Statistics about checkpoint storage.

    Attributes:
        total_checkpoints: Total number of stored checkpoints
        active_checkpoints: Number of active checkpoints
        expired_checkpoints: Number of expired checkpoints
        total_size_bytes: Total storage size in bytes
        sessions_count: Number of unique sessions
        oldest_checkpoint: Timestamp of oldest checkpoint
        newest_checkpoint: Timestamp of newest checkpoint
    """

    total_checkpoints: int = 0
    active_checkpoints: int = 0
    expired_checkpoints: int = 0
    total_size_bytes: int = 0
    sessions_count: int = 0
    oldest_checkpoint: Optional[datetime] = None
    newest_checkpoint: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_checkpoints": self.total_checkpoints,
            "active_checkpoints": self.active_checkpoints,
            "expired_checkpoints": self.expired_checkpoints,
            "total_size_bytes": self.total_size_bytes,
            "sessions_count": self.sessions_count,
            "oldest_checkpoint": (
                self.oldest_checkpoint.isoformat() if self.oldest_checkpoint else None
            ),
            "newest_checkpoint": (
                self.newest_checkpoint.isoformat() if self.newest_checkpoint else None
            ),
        }


# =============================================================================
# Storage Protocol
# =============================================================================


@runtime_checkable
class CheckpointStorageProtocol(Protocol):
    """Protocol defining checkpoint storage interface."""

    async def save(self, checkpoint: HybridCheckpoint) -> str:
        """Save checkpoint and return its ID."""
        ...

    async def load(self, checkpoint_id: str) -> Optional[HybridCheckpoint]:
        """Load checkpoint by ID."""
        ...

    async def delete(self, checkpoint_id: str) -> bool:
        """Delete checkpoint by ID."""
        ...

    async def exists(self, checkpoint_id: str) -> bool:
        """Check if checkpoint exists."""
        ...


# =============================================================================
# Abstract Storage Base
# =============================================================================


class UnifiedCheckpointStorage(ABC):
    """
    Abstract base class for checkpoint storage backends.

    Provides common functionality and defines the interface that all
    storage backends must implement.

    Example:
        >>> storage = RedisCheckpointStorage(config)
        >>> checkpoint_id = await storage.save(checkpoint)
        >>> restored = await storage.load(checkpoint_id)
    """

    def __init__(self, config: Optional[StorageConfig] = None):
        """
        Initialize storage with configuration.

        Args:
            config: Storage configuration. Uses defaults if not provided.
        """
        self.config = config or StorageConfig()
        self.serializer = CheckpointSerializer(self.config.serialization_config)

    # =========================================================================
    # Abstract Methods - Must be implemented by backends
    # =========================================================================

    @abstractmethod
    async def save(self, checkpoint: HybridCheckpoint) -> str:
        """
        Save a checkpoint to storage.

        Args:
            checkpoint: Checkpoint to save

        Returns:
            Checkpoint ID

        Raises:
            StorageError: If save operation fails
        """
        pass

    @abstractmethod
    async def load(self, checkpoint_id: str) -> Optional[HybridCheckpoint]:
        """
        Load a checkpoint from storage.

        Args:
            checkpoint_id: ID of checkpoint to load

        Returns:
            HybridCheckpoint if found, None otherwise
        """
        pass

    @abstractmethod
    async def delete(self, checkpoint_id: str) -> bool:
        """
        Delete a checkpoint from storage.

        Args:
            checkpoint_id: ID of checkpoint to delete

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def exists(self, checkpoint_id: str) -> bool:
        """
        Check if a checkpoint exists in storage.

        Args:
            checkpoint_id: ID of checkpoint to check

        Returns:
            True if exists, False otherwise
        """
        pass

    @abstractmethod
    async def query(self, query: CheckpointQuery) -> List[HybridCheckpoint]:
        """
        Query checkpoints based on criteria.

        Args:
            query: Query parameters

        Returns:
            List of matching checkpoints
        """
        pass

    @abstractmethod
    async def get_stats(self) -> StorageStats:
        """
        Get storage statistics.

        Returns:
            StorageStats with current statistics
        """
        pass

    @abstractmethod
    async def cleanup_expired(self) -> int:
        """
        Remove expired checkpoints.

        Returns:
            Number of checkpoints removed
        """
        pass

    # =========================================================================
    # Common Methods - Shared across backends
    # =========================================================================

    async def save_with_restore_point(
        self, checkpoint: HybridCheckpoint, restore_point_name: str
    ) -> str:
        """
        Save checkpoint with a named restore point for easy retrieval.

        Args:
            checkpoint: Checkpoint to save
            restore_point_name: Human-readable name for restore point

        Returns:
            Checkpoint ID
        """
        checkpoint.metadata["restore_point_name"] = restore_point_name
        return await self.save(checkpoint)

    async def load_by_session(
        self, session_id: str, limit: int = 10
    ) -> List[HybridCheckpoint]:
        """
        Load recent checkpoints for a session.

        Args:
            session_id: Session ID
            limit: Maximum number of checkpoints to return

        Returns:
            List of checkpoints, most recent first
        """
        query = CheckpointQuery(session_id=session_id, limit=limit)
        return await self.query(query)

    async def load_latest(self, session_id: str) -> Optional[HybridCheckpoint]:
        """
        Load the most recent checkpoint for a session.

        Args:
            session_id: Session ID

        Returns:
            Latest checkpoint or None
        """
        checkpoints = await self.load_by_session(session_id, limit=1)
        return checkpoints[0] if checkpoints else None

    async def load_by_type(
        self, session_id: str, checkpoint_type: CheckpointType
    ) -> List[HybridCheckpoint]:
        """
        Load checkpoints of a specific type for a session.

        Args:
            session_id: Session ID
            checkpoint_type: Type of checkpoints to load

        Returns:
            List of matching checkpoints
        """
        query = CheckpointQuery(session_id=session_id, checkpoint_type=checkpoint_type)
        return await self.query(query)

    async def count_by_session(self, session_id: str) -> int:
        """
        Count checkpoints for a session.

        Args:
            session_id: Session ID

        Returns:
            Number of checkpoints
        """
        query = CheckpointQuery(session_id=session_id, limit=0)
        checkpoints = await self.query(query)
        return len(checkpoints)

    async def delete_by_session(self, session_id: str) -> int:
        """
        Delete all checkpoints for a session.

        Args:
            session_id: Session ID

        Returns:
            Number of checkpoints deleted
        """
        checkpoints = await self.load_by_session(session_id, limit=1000)
        deleted = 0
        for checkpoint in checkpoints:
            if await self.delete(checkpoint.checkpoint_id):
                deleted += 1
        return deleted

    async def restore(self, checkpoint_id: str) -> RestoreResult:
        """
        Restore a checkpoint and mark it as restored.

        Args:
            checkpoint_id: ID of checkpoint to restore

        Returns:
            RestoreResult with restoration details
        """
        start_time = datetime.utcnow()

        checkpoint = await self.load(checkpoint_id)
        if not checkpoint:
            return RestoreResult.create_failure(
                checkpoint_id, f"Checkpoint not found: {checkpoint_id}"
            )

        # Check if checkpoint is expired
        if checkpoint.is_expired():
            return RestoreResult.create_failure(
                checkpoint_id, "Checkpoint has expired"
            )

        # Check if checkpoint is corrupted
        if checkpoint.status == CheckpointStatus.CORRUPTED:
            return RestoreResult.create_failure(checkpoint_id, "Checkpoint is corrupted")

        # Mark as restored
        checkpoint.mark_restored()

        # Save the updated status
        await self.save(checkpoint)

        elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return RestoreResult(
            success=True,
            checkpoint_id=checkpoint_id,
            restored_maf=checkpoint.has_maf_state(),
            restored_claude=checkpoint.has_claude_state(),
            restored_mode=checkpoint.execution_mode,
            restore_time_ms=elapsed_ms,
        )

    async def enforce_retention(self, session_id: str) -> int:
        """
        Enforce retention policy by removing old checkpoints.

        Keeps only the most recent N checkpoints per session.

        Args:
            session_id: Session ID

        Returns:
            Number of checkpoints removed
        """
        query = CheckpointQuery(
            session_id=session_id,
            limit=self.config.max_checkpoints_per_session + 100,  # Get extra for deletion
        )
        checkpoints = await self.query(query)

        if len(checkpoints) <= self.config.max_checkpoints_per_session:
            return 0

        # Keep the most recent, delete the rest
        to_delete = checkpoints[self.config.max_checkpoints_per_session :]
        deleted = 0
        for checkpoint in to_delete:
            if await self.delete(checkpoint.checkpoint_id):
                deleted += 1

        return deleted

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _generate_key(self, checkpoint_id: str) -> str:
        """Generate storage key for checkpoint."""
        return f"checkpoint:{checkpoint_id}"

    def _generate_session_key(self, session_id: str) -> str:
        """Generate storage key for session index."""
        return f"session:{session_id}:checkpoints"

    def _serialize(self, checkpoint: HybridCheckpoint) -> bytes:
        """Serialize checkpoint to bytes."""
        result = self.serializer.serialize(checkpoint)
        return result.data

    def _deserialize(self, data: bytes) -> HybridCheckpoint:
        """Deserialize bytes to checkpoint."""
        result = self.serializer.deserialize(data)
        return result.checkpoint


# =============================================================================
# Storage Errors
# =============================================================================


class StorageError(Exception):
    """Base exception for storage errors."""

    pass


class CheckpointNotFoundError(StorageError):
    """Raised when a checkpoint is not found."""

    def __init__(self, checkpoint_id: str):
        self.checkpoint_id = checkpoint_id
        super().__init__(f"Checkpoint not found: {checkpoint_id}")


class StorageConnectionError(StorageError):
    """Raised when storage connection fails."""

    pass


class StorageCapacityError(StorageError):
    """Raised when storage capacity is exceeded."""

    pass
