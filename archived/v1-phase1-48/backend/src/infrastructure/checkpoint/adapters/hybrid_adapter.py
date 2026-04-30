"""Hybrid Checkpoint Adapter.

Sprint 120 -- Story 120-2: Adapter that wraps the existing
UnifiedCheckpointStorage from the hybrid integration module to implement
the CheckpointProvider protocol.

The hybrid checkpoint system (Phase 14, Sprint 57) has 4 backends:
Memory, Redis, Postgres, and Filesystem. This adapter translates between
the HybridCheckpoint data model and the unified CheckpointEntry format.

Usage:
    from src.integrations.hybrid.checkpoint.backends.memory import (
        MemoryCheckpointStorage,
    )
    from src.infrastructure.checkpoint.adapters import HybridCheckpointAdapter

    storage = MemoryCheckpointStorage()
    adapter = HybridCheckpointAdapter(storage)
    registry.register_provider(adapter)
"""

import logging
from typing import Any, Dict, List, Optional

from src.infrastructure.checkpoint.protocol import CheckpointEntry
from src.integrations.hybrid.checkpoint.models import (
    CheckpointStatus,
    CheckpointType,
    HybridCheckpoint,
)
from src.integrations.hybrid.checkpoint.storage import (
    CheckpointQuery,
    UnifiedCheckpointStorage,
)

logger = logging.getLogger(__name__)


class HybridCheckpointAdapter:
    """Adapter wrapping UnifiedCheckpointStorage as a CheckpointProvider.

    Translates between the hybrid checkpoint's HybridCheckpoint model and the
    unified CheckpointEntry format used by the UnifiedCheckpointRegistry.

    The adapter delegates all persistence operations to the underlying
    UnifiedCheckpointStorage backend (Memory, Redis, Postgres, or Filesystem).

    Attributes:
        _storage: The underlying hybrid checkpoint storage backend.
        _provider_name: Provider identifier for registry registration.
    """

    def __init__(
        self,
        storage: UnifiedCheckpointStorage,
        name: str = "hybrid",
    ) -> None:
        """Initialize the adapter with an existing hybrid storage backend.

        Args:
            storage: An instance of UnifiedCheckpointStorage (any backend).
            name: Provider name for registry identification. Defaults to 'hybrid'.
        """
        self._storage = storage
        self._provider_name = name
        logger.info(
            "HybridCheckpointAdapter initialized: provider_name=%s, backend=%s",
            name,
            type(storage).__name__,
        )

    @property
    def provider_name(self) -> str:
        """Unique provider identifier."""
        return self._provider_name

    async def save_checkpoint(
        self,
        checkpoint_id: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Save checkpoint data by converting to HybridCheckpoint.

        Creates a HybridCheckpoint from the provided data and metadata,
        then delegates to the underlying storage backend.

        Args:
            checkpoint_id: Unique checkpoint identifier.
            data: Checkpoint data payload. May contain 'session_id',
                'execution_mode', 'checkpoint_type', etc.
            metadata: Optional additional metadata dictionary.

        Returns:
            The checkpoint_id.
        """
        session_id = data.get("session_id", "")
        execution_mode = data.get("execution_mode", "chat")
        checkpoint_type_str = data.get("checkpoint_type", "auto")

        try:
            checkpoint_type = CheckpointType(checkpoint_type_str)
        except ValueError:
            checkpoint_type = CheckpointType.AUTO

        checkpoint = HybridCheckpoint(
            checkpoint_id=checkpoint_id,
            session_id=session_id,
            execution_mode=execution_mode,
            checkpoint_type=checkpoint_type,
            status=CheckpointStatus.ACTIVE,
            metadata={
                **(metadata or {}),
                "unified_data": data,
            },
        )

        result_id = await self._storage.save(checkpoint)

        logger.debug(
            "HybridCheckpointAdapter saved checkpoint: checkpoint_id=%s, session_id=%s",
            result_id,
            session_id,
        )

        return result_id

    async def load_checkpoint(
        self,
        checkpoint_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Load checkpoint data by converting from HybridCheckpoint.

        Loads the HybridCheckpoint from the underlying storage and converts
        it to a plain dictionary.

        Args:
            checkpoint_id: Checkpoint to load.

        Returns:
            Checkpoint data dictionary, or None if not found or expired.
        """
        checkpoint = await self._storage.load(checkpoint_id)

        if checkpoint is None:
            logger.debug(
                "HybridCheckpointAdapter: checkpoint not found: checkpoint_id=%s",
                checkpoint_id,
            )
            return None

        # If original unified_data was stored in metadata, return it
        unified_data = checkpoint.metadata.get("unified_data")
        if unified_data is not None:
            return unified_data

        # Otherwise, return the full HybridCheckpoint as dict
        return checkpoint.to_dict()

    async def list_checkpoints(
        self,
        session_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[CheckpointEntry]:
        """List checkpoints by querying the hybrid storage.

        Queries the underlying storage and converts each HybridCheckpoint
        to a CheckpointEntry.

        Args:
            session_id: Optional session filter.
            limit: Maximum entries to return.

        Returns:
            List of CheckpointEntry instances.
        """
        query = CheckpointQuery(
            session_id=session_id,
            limit=limit,
        )

        checkpoints = await self._storage.query(query)
        entries: List[CheckpointEntry] = []

        for cp in checkpoints:
            entry = self._to_checkpoint_entry(cp)
            entries.append(entry)

        logger.debug(
            "HybridCheckpointAdapter listed %d checkpoints (session_id=%s)",
            len(entries),
            session_id,
        )

        return entries

    async def delete_checkpoint(
        self,
        checkpoint_id: str,
    ) -> bool:
        """Delete a checkpoint from the hybrid storage.

        Args:
            checkpoint_id: Checkpoint to delete.

        Returns:
            True if deleted, False if not found.
        """
        result = await self._storage.delete(checkpoint_id)

        logger.debug(
            "HybridCheckpointAdapter delete checkpoint: checkpoint_id=%s, deleted=%s",
            checkpoint_id,
            result,
        )

        return result

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    def _to_checkpoint_entry(self, checkpoint: HybridCheckpoint) -> CheckpointEntry:
        """Convert a HybridCheckpoint to a CheckpointEntry.

        Args:
            checkpoint: The HybridCheckpoint to convert.

        Returns:
            A CheckpointEntry with data from the HybridCheckpoint.
        """
        # Extract unified_data from metadata if present, otherwise use full dict
        unified_data = checkpoint.metadata.get("unified_data")
        data = unified_data if unified_data is not None else checkpoint.to_dict()

        # Build metadata without unified_data to avoid duplication
        entry_metadata = {
            k: v for k, v in checkpoint.metadata.items() if k != "unified_data"
        }
        entry_metadata["checkpoint_type"] = checkpoint.checkpoint_type.value
        entry_metadata["status"] = checkpoint.status.value
        entry_metadata["execution_mode"] = checkpoint.execution_mode

        return CheckpointEntry(
            checkpoint_id=checkpoint.checkpoint_id,
            provider_name=self._provider_name,
            session_id=checkpoint.session_id,
            data=data,
            metadata=entry_metadata,
            created_at=checkpoint.created_at,
            expires_at=checkpoint.expires_at,
        )
