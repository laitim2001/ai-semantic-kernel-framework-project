"""Agent Framework Checkpoint Adapter.

Sprint 121 -- Story 121-1: Adapter that wraps the existing
BaseCheckpointStorage from the agent_framework multiturn module to
implement the CheckpointProvider protocol.

The agent framework checkpoint system (Phase 1, Sprint 24) has 3 backends:
Redis, PostgreSQL, and Filesystem. This adapter translates between the
IPA custom save/load/delete/list interface and the unified CheckpointEntry
format.

Usage:
    from src.integrations.agent_framework.multiturn.checkpoint_storage import (
        RedisCheckpointStorage,
    )
    from src.infrastructure.checkpoint.adapters import AgentFrameworkCheckpointAdapter

    storage = RedisCheckpointStorage(redis_client)
    adapter = AgentFrameworkCheckpointAdapter(storage)
    registry.register_provider(adapter)
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.infrastructure.checkpoint.protocol import CheckpointEntry
from src.integrations.agent_framework.multiturn.checkpoint_storage import (
    BaseCheckpointStorage,
)

logger = logging.getLogger(__name__)


class AgentFrameworkCheckpointAdapter:
    """Adapter wrapping BaseCheckpointStorage as a CheckpointProvider.

    Translates between the agent framework's custom save/load/delete/list
    interface and the unified CheckpointEntry format used by the
    UnifiedCheckpointRegistry.

    The agent framework storage uses session_id-based keys with a namespace
    prefix. This adapter maps the unified checkpoint_id to the session_id
    parameter expected by the underlying storage.

    Attributes:
        _storage: The underlying agent framework checkpoint storage backend.
        _provider_name: Provider identifier for registry registration.
    """

    def __init__(
        self,
        storage: BaseCheckpointStorage,
        name: str = "agent_framework",
    ) -> None:
        """Initialize the adapter with an existing agent framework storage backend.

        Args:
            storage: An instance of BaseCheckpointStorage (Redis, Postgres,
                or Filesystem backend).
            name: Provider name for registry identification.
                Defaults to 'agent_framework'.
        """
        self._storage = storage
        self._provider_name = name
        logger.info(
            "AgentFrameworkCheckpointAdapter initialized: provider_name=%s, backend=%s",
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
        """Save checkpoint data via the agent framework storage.

        Wraps the provided data and metadata into a single payload and
        delegates to the underlying storage's save() method, using
        checkpoint_id as the session_id.

        Args:
            checkpoint_id: Unique checkpoint identifier (used as session_id
                in the underlying storage).
            data: Checkpoint data payload.
            metadata: Optional additional metadata dictionary.

        Returns:
            The checkpoint_id.

        Raises:
            Exception: If the underlying storage fails to save.
        """
        payload = {
            "unified_data": data,
            "metadata": metadata or {},
        }

        try:
            await self._storage.save(checkpoint_id, payload)
        except Exception:
            logger.error(
                "AgentFrameworkCheckpointAdapter failed to save: checkpoint_id=%s",
                checkpoint_id,
                exc_info=True,
            )
            raise

        logger.info(
            "AgentFrameworkCheckpointAdapter saved checkpoint: checkpoint_id=%s",
            checkpoint_id,
        )

        return checkpoint_id

    async def load_checkpoint(
        self,
        checkpoint_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Load checkpoint data from the agent framework storage.

        Loads the raw payload from the underlying storage. If the payload
        contains a 'unified_data' key (saved via this adapter), that inner
        dict is returned. Otherwise, the full payload is returned as-is
        to support data saved directly through the agent framework.

        Args:
            checkpoint_id: Checkpoint to load (used as session_id in the
                underlying storage).

        Returns:
            Checkpoint data dictionary, or None if not found.
        """
        try:
            result = await self._storage.load(checkpoint_id)
        except Exception:
            logger.error(
                "AgentFrameworkCheckpointAdapter failed to load: checkpoint_id=%s",
                checkpoint_id,
                exc_info=True,
            )
            raise

        if result is None:
            logger.debug(
                "AgentFrameworkCheckpointAdapter: checkpoint not found: checkpoint_id=%s",
                checkpoint_id,
            )
            return None

        # If saved via this adapter, return the unified_data portion
        if isinstance(result, dict) and "unified_data" in result:
            logger.debug(
                "AgentFrameworkCheckpointAdapter loaded checkpoint (unified): "
                "checkpoint_id=%s",
                checkpoint_id,
            )
            return result["unified_data"]

        # Otherwise return the raw result for backwards compatibility
        logger.debug(
            "AgentFrameworkCheckpointAdapter loaded checkpoint (raw): checkpoint_id=%s",
            checkpoint_id,
        )
        return result

    async def list_checkpoints(
        self,
        session_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[CheckpointEntry]:
        """List checkpoints by querying the agent framework storage.

        Calls the underlying storage's list() method to enumerate all
        known session_ids, then loads each to build CheckpointEntry
        instances. If a session_id filter is provided, only matching
        entries are included.

        Note: This operation may be expensive for large datasets as it
        loads each checkpoint individually.

        Args:
            session_id: Optional session filter. When provided, only
                checkpoints whose checkpoint_id matches are returned.
            limit: Maximum entries to return.

        Returns:
            List of CheckpointEntry instances.
        """
        try:
            all_session_ids = await self._storage.list("*")
        except Exception:
            logger.error(
                "AgentFrameworkCheckpointAdapter failed to list checkpoints",
                exc_info=True,
            )
            raise

        entries: List[CheckpointEntry] = []

        for sid in all_session_ids:
            if len(entries) >= limit:
                break

            # Apply session_id filter if provided
            if session_id is not None and sid != session_id:
                continue

            entry = await self._load_as_entry(sid)
            if entry is not None:
                entries.append(entry)

        logger.debug(
            "AgentFrameworkCheckpointAdapter listed %d checkpoints (session_id=%s)",
            len(entries),
            session_id,
        )

        return entries

    async def delete_checkpoint(
        self,
        checkpoint_id: str,
    ) -> bool:
        """Delete a checkpoint from the agent framework storage.

        Args:
            checkpoint_id: Checkpoint to delete (used as session_id in the
                underlying storage).

        Returns:
            True if deleted, False if not found.
        """
        try:
            result = await self._storage.delete(checkpoint_id)
        except Exception:
            logger.error(
                "AgentFrameworkCheckpointAdapter failed to delete: checkpoint_id=%s",
                checkpoint_id,
                exc_info=True,
            )
            raise

        if result:
            logger.info(
                "AgentFrameworkCheckpointAdapter deleted checkpoint: checkpoint_id=%s",
                checkpoint_id,
            )
        else:
            logger.debug(
                "AgentFrameworkCheckpointAdapter: checkpoint not found for delete: "
                "checkpoint_id=%s",
                checkpoint_id,
            )

        return result

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    async def _load_as_entry(self, session_id: str) -> Optional[CheckpointEntry]:
        """Load a single checkpoint and convert to CheckpointEntry.

        Args:
            session_id: The session_id (checkpoint_id) to load.

        Returns:
            A CheckpointEntry, or None if the checkpoint could not be loaded.
        """
        try:
            raw = await self._storage.load(session_id)
        except Exception:
            logger.warning(
                "AgentFrameworkCheckpointAdapter: failed to load entry: session_id=%s",
                session_id,
                exc_info=True,
            )
            return None

        if raw is None:
            return None

        # Extract unified_data and metadata if present
        if isinstance(raw, dict) and "unified_data" in raw:
            data = raw["unified_data"]
            entry_metadata = raw.get("metadata", {})
        else:
            data = raw if isinstance(raw, dict) else {"raw": raw}
            entry_metadata = {}

        return CheckpointEntry(
            checkpoint_id=session_id,
            provider_name=self._provider_name,
            session_id=session_id,
            data=data,
            metadata=entry_metadata,
            created_at=datetime.utcnow(),
        )
