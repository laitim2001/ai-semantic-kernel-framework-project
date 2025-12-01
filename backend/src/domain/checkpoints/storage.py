# =============================================================================
# IPA Platform - Checkpoint Storage
# =============================================================================
# Sprint 2: Workflow & Checkpoints - Human-in-the-Loop
#
# Storage adapters for checkpoint persistence.
# Provides:
#   - CheckpointStorage: Abstract storage interface
#   - DatabaseCheckpointStorage: PostgreSQL-backed storage
#
# The storage layer handles serialization and persistence of checkpoint state,
# supporting the Agent Framework's checkpoint/restore mechanism.
# =============================================================================

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.infrastructure.database.models.checkpoint import Checkpoint

logger = logging.getLogger(__name__)


class CheckpointStorage(ABC):
    """
    Abstract base class for checkpoint storage adapters.

    Defines the interface for checkpoint persistence operations.
    Implementations can use different backends (database, file, cloud storage).

    Methods:
        save_checkpoint: Persist checkpoint state
        load_checkpoint: Retrieve checkpoint by ID
        list_checkpoints: List checkpoints for an execution
        delete_checkpoint: Remove a checkpoint
    """

    @abstractmethod
    async def save_checkpoint(
        self,
        execution_id: UUID,
        node_id: str,
        state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UUID:
        """
        Save a checkpoint state.

        Args:
            execution_id: Parent execution UUID
            node_id: Workflow node that created the checkpoint
            state: Serializable state data to persist
            metadata: Optional additional metadata

        Returns:
            UUID of the created checkpoint
        """
        pass

    @abstractmethod
    async def load_checkpoint(self, checkpoint_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Load a checkpoint by ID.

        Args:
            checkpoint_id: Checkpoint UUID

        Returns:
            Checkpoint state data or None if not found
        """
        pass

    @abstractmethod
    async def list_checkpoints(
        self,
        execution_id: UUID,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List checkpoints for an execution.

        Args:
            execution_id: Execution UUID
            status: Optional status filter

        Returns:
            List of checkpoint data dictionaries
        """
        pass

    @abstractmethod
    async def delete_checkpoint(self, checkpoint_id: UUID) -> bool:
        """
        Delete a checkpoint.

        Args:
            checkpoint_id: Checkpoint UUID

        Returns:
            True if deleted, False if not found
        """
        pass


class DatabaseCheckpointStorage(CheckpointStorage):
    """
    PostgreSQL-backed checkpoint storage implementation.

    Uses the Checkpoint model to persist checkpoint state in the database.
    Supports full CRUD operations with status tracking.

    Attributes:
        _repository: CheckpointRepository for database operations

    Example:
        storage = DatabaseCheckpointStorage(repository)
        checkpoint_id = await storage.save_checkpoint(
            execution_id=exec_id,
            node_id="approval-node",
            state={"agent_output": "Draft response", "iteration": 1},
        )
    """

    def __init__(self, repository: "CheckpointRepository"):
        """
        Initialize storage with repository.

        Args:
            repository: CheckpointRepository instance
        """
        self._repository = repository

    async def save_checkpoint(
        self,
        execution_id: UUID,
        node_id: str,
        state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UUID:
        """
        Save checkpoint state to database.

        Creates a new checkpoint record with pending status.

        Args:
            execution_id: Parent execution UUID
            node_id: Workflow node ID
            state: State data to persist (stored in payload field)
            metadata: Additional metadata (stored in notes as JSON)

        Returns:
            UUID of created checkpoint
        """
        # Prepare payload with state
        payload = {
            "state": state,
            "saved_at": datetime.utcnow().isoformat(),
        }

        # Prepare notes from metadata
        notes = None
        if metadata:
            notes = json.dumps(metadata)

        # Create checkpoint via repository
        checkpoint = await self._repository.create(
            execution_id=execution_id,
            node_id=node_id,
            payload=payload,
            notes=notes,
        )

        logger.info(f"Saved checkpoint {checkpoint.id} for execution {execution_id}")
        return checkpoint.id

    async def load_checkpoint(self, checkpoint_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Load checkpoint state from database.

        Args:
            checkpoint_id: Checkpoint UUID

        Returns:
            Checkpoint data including state, or None if not found
        """
        checkpoint = await self._repository.get(checkpoint_id)
        if checkpoint is None:
            return None

        # Extract state from payload
        state = checkpoint.payload.get("state", {}) if checkpoint.payload else {}

        # Parse metadata from notes
        metadata = None
        if checkpoint.notes:
            try:
                metadata = json.loads(checkpoint.notes)
            except json.JSONDecodeError:
                metadata = {"raw_notes": checkpoint.notes}

        return {
            "id": str(checkpoint.id),
            "execution_id": str(checkpoint.execution_id),
            "node_id": checkpoint.node_id,
            "status": checkpoint.status,
            "state": state,
            "metadata": metadata,
            "response": checkpoint.response,
            "responded_by": str(checkpoint.responded_by) if checkpoint.responded_by else None,
            "responded_at": checkpoint.responded_at.isoformat() if checkpoint.responded_at else None,
            "expires_at": checkpoint.expires_at.isoformat() if checkpoint.expires_at else None,
            "created_at": checkpoint.created_at.isoformat() if checkpoint.created_at else None,
        }

    async def list_checkpoints(
        self,
        execution_id: UUID,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List checkpoints for an execution.

        Args:
            execution_id: Execution UUID
            status: Optional status filter

        Returns:
            List of checkpoint data dictionaries
        """
        checkpoints = await self._repository.list_by_execution(
            execution_id=execution_id,
            status=status,
        )

        return [
            {
                "id": str(cp.id),
                "execution_id": str(cp.execution_id),
                "node_id": cp.node_id,
                "status": cp.status,
                "payload": cp.payload,
                "response": cp.response,
                "created_at": cp.created_at.isoformat() if cp.created_at else None,
            }
            for cp in checkpoints
        ]

    async def delete_checkpoint(self, checkpoint_id: UUID) -> bool:
        """
        Delete a checkpoint from database.

        Args:
            checkpoint_id: Checkpoint UUID

        Returns:
            True if deleted, False if not found
        """
        return await self._repository.delete(checkpoint_id)

    async def update_checkpoint_status(
        self,
        checkpoint_id: UUID,
        status: str,
        response: Optional[Dict[str, Any]] = None,
        responded_by: Optional[UUID] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Update checkpoint status (approve/reject).

        Args:
            checkpoint_id: Checkpoint UUID
            status: New status (approved, rejected)
            response: Optional response data
            responded_by: User who responded

        Returns:
            Updated checkpoint data or None if not found
        """
        checkpoint = await self._repository.update_status(
            checkpoint_id=checkpoint_id,
            status=status,
            response=response,
            responded_by=responded_by,
            responded_at=datetime.utcnow(),
        )

        if checkpoint is None:
            return None

        return await self.load_checkpoint(checkpoint_id)


# Type hint for repository
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.infrastructure.database.repositories.checkpoint import CheckpointRepository
