"""Session Recovery Checkpoint Adapter.

Sprint 121 -- Story 121-1: Adapter that wraps the existing
SessionRecoveryManager from the domain sessions module to implement
the CheckpointProvider protocol.

The session recovery system (Phase 11, Sprint 47) uses a CacheProtocol
backend (typically Redis) for fast session checkpoint persistence. It
stores a single checkpoint per session_id with a TTL-based expiry.
This adapter translates between the recovery manager's session-oriented
interface and the unified CheckpointEntry format.

Usage:
    from src.domain.sessions.recovery import SessionRecoveryManager
    from src.infrastructure.checkpoint.adapters import (
        SessionRecoveryCheckpointAdapter,
    )

    manager = SessionRecoveryManager(cache=redis_cache)
    adapter = SessionRecoveryCheckpointAdapter(manager)
    registry.register_provider(adapter)
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.domain.sessions.recovery import (
    CheckpointType as SessionCheckpointType,
    SessionCheckpoint,
    SessionRecoveryManager,
)
from src.infrastructure.checkpoint.protocol import CheckpointEntry

logger = logging.getLogger(__name__)

# Mapping from string values to SessionCheckpointType enum members
_CHECKPOINT_TYPE_MAP: Dict[str, SessionCheckpointType] = {
    member.value: member for member in SessionCheckpointType
}


class SessionRecoveryCheckpointAdapter:
    """Adapter wrapping SessionRecoveryManager as a CheckpointProvider.

    Translates between the session recovery manager's session-oriented
    interface and the unified CheckpointProvider protocol.

    The recovery manager stores one checkpoint per session_id. The
    checkpoint_id parameter maps directly to session_id in the
    underlying manager.

    Attributes:
        _manager: The underlying session recovery manager.
        _provider_name: Provider identifier for registry registration.
    """

    def __init__(
        self,
        manager: SessionRecoveryManager,
        name: str = "session_recovery",
    ) -> None:
        """Initialize the adapter with an existing session recovery manager.

        Args:
            manager: An instance of SessionRecoveryManager backed by a
                CacheProtocol implementation (typically Redis).
            name: Provider name for registry identification.
                Defaults to 'session_recovery'.
        """
        self._manager = manager
        self._provider_name = name
        logger.info(
            "SessionRecoveryCheckpointAdapter initialized: provider_name=%s",
            name,
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
        """Save checkpoint data via the session recovery manager.

        Uses checkpoint_id as the session_id. Extracts checkpoint_type and
        execution_id from the data payload to match the recovery manager's
        interface.

        Args:
            checkpoint_id: Unique checkpoint identifier (used as session_id
                in the underlying manager).
            data: Checkpoint data payload. May contain:
                - 'checkpoint_type': One of the SessionCheckpointType values
                    (defaults to 'execution_start').
                - 'execution_id': Optional execution identifier.
            metadata: Optional additional metadata dictionary.

        Returns:
            The checkpoint_id.

        Raises:
            Exception: If the underlying manager fails to save.
        """
        # Extract checkpoint type from data
        checkpoint_type_str = data.get("checkpoint_type", "execution_start")
        checkpoint_type_enum = _CHECKPOINT_TYPE_MAP.get(
            checkpoint_type_str,
            SessionCheckpointType.EXECUTION_START,
        )

        # Extract execution_id from data
        execution_id = data.get("execution_id")

        try:
            await self._manager.save_checkpoint(
                session_id=checkpoint_id,
                checkpoint_type=checkpoint_type_enum,
                state=data,
                execution_id=execution_id,
                metadata=metadata,
            )
        except Exception:
            logger.error(
                "SessionRecoveryCheckpointAdapter failed to save: checkpoint_id=%s",
                checkpoint_id,
                exc_info=True,
            )
            raise

        logger.info(
            "SessionRecoveryCheckpointAdapter saved checkpoint: checkpoint_id=%s, "
            "checkpoint_type=%s",
            checkpoint_id,
            checkpoint_type_enum.value,
        )

        return checkpoint_id

    async def load_checkpoint(
        self,
        checkpoint_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Load checkpoint data from the session recovery manager.

        Calls get_checkpoint with checkpoint_id as session_id. If found,
        converts the SessionCheckpoint to a dictionary via to_dict().

        Args:
            checkpoint_id: Checkpoint to load (used as session_id in the
                underlying manager).

        Returns:
            Checkpoint data dictionary (from SessionCheckpoint.to_dict()),
            or None if not found or expired.
        """
        try:
            checkpoint = await self._manager.get_checkpoint(checkpoint_id)
        except Exception:
            logger.error(
                "SessionRecoveryCheckpointAdapter failed to load: checkpoint_id=%s",
                checkpoint_id,
                exc_info=True,
            )
            raise

        if checkpoint is None:
            logger.debug(
                "SessionRecoveryCheckpointAdapter: checkpoint not found: "
                "checkpoint_id=%s",
                checkpoint_id,
            )
            return None

        logger.debug(
            "SessionRecoveryCheckpointAdapter loaded checkpoint: checkpoint_id=%s, "
            "checkpoint_type=%s",
            checkpoint_id,
            checkpoint.checkpoint_type.value,
        )

        return checkpoint.to_dict()

    async def list_checkpoints(
        self,
        session_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[CheckpointEntry]:
        """List checkpoints from the session recovery manager.

        The recovery manager stores one checkpoint per session and operates
        on a CacheProtocol that does not support scanning. If session_id
        is provided, attempts to load that single checkpoint and returns a
        0-or-1 element list. If no session_id is provided, returns an empty
        list.

        Args:
            session_id: Optional session filter. When provided, the single
                checkpoint for that session is returned (if it exists).
                When absent, returns an empty list.
            limit: Maximum entries to return (at most 1 for this provider).

        Returns:
            List of CheckpointEntry instances (0 or 1 elements).
        """
        if session_id is None:
            logger.debug(
                "SessionRecoveryCheckpointAdapter: no session_id provided, "
                "returning empty list (cache does not support scanning)"
            )
            return []

        try:
            checkpoint = await self._manager.get_checkpoint(session_id)
        except Exception:
            logger.error(
                "SessionRecoveryCheckpointAdapter failed to list: session_id=%s",
                session_id,
                exc_info=True,
            )
            raise

        if checkpoint is None:
            logger.debug(
                "SessionRecoveryCheckpointAdapter: no checkpoint for session: "
                "session_id=%s",
                session_id,
            )
            return []

        entry = self._to_checkpoint_entry(checkpoint)
        entries = [entry]

        logger.debug(
            "SessionRecoveryCheckpointAdapter listed %d checkpoints (session_id=%s)",
            len(entries),
            session_id,
        )

        return entries[:limit]

    async def delete_checkpoint(
        self,
        checkpoint_id: str,
    ) -> bool:
        """Delete a checkpoint from the session recovery manager.

        The recovery manager's delete_checkpoint returns None (not bool).
        This adapter first checks existence via get_checkpoint, then calls
        delete, returning True if the checkpoint existed and False otherwise.

        Args:
            checkpoint_id: Checkpoint to delete (used as session_id in the
                underlying manager).

        Returns:
            True if the checkpoint existed and was deleted, False if not found.
        """
        # Check existence first since delete_checkpoint returns None
        try:
            existing = await self._manager.get_checkpoint(checkpoint_id)
        except Exception:
            logger.error(
                "SessionRecoveryCheckpointAdapter failed to check existence: "
                "checkpoint_id=%s",
                checkpoint_id,
                exc_info=True,
            )
            raise

        if existing is None:
            logger.debug(
                "SessionRecoveryCheckpointAdapter: checkpoint not found for delete: "
                "checkpoint_id=%s",
                checkpoint_id,
            )
            return False

        try:
            await self._manager.delete_checkpoint(checkpoint_id)
        except Exception:
            logger.error(
                "SessionRecoveryCheckpointAdapter failed to delete: checkpoint_id=%s",
                checkpoint_id,
                exc_info=True,
            )
            raise

        logger.info(
            "SessionRecoveryCheckpointAdapter deleted checkpoint: checkpoint_id=%s",
            checkpoint_id,
        )

        return True

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    def _to_checkpoint_entry(
        self,
        checkpoint: SessionCheckpoint,
    ) -> CheckpointEntry:
        """Convert a SessionCheckpoint to a CheckpointEntry.

        Args:
            checkpoint: The SessionCheckpoint to convert.

        Returns:
            A CheckpointEntry with data from the SessionCheckpoint.
        """
        # Build metadata from session recovery fields
        entry_metadata: Dict[str, Any] = {
            "checkpoint_type": checkpoint.checkpoint_type.value,
        }
        if checkpoint.execution_id:
            entry_metadata["execution_id"] = checkpoint.execution_id
        if checkpoint.metadata:
            entry_metadata.update(checkpoint.metadata)

        return CheckpointEntry(
            checkpoint_id=checkpoint.session_id,
            provider_name=self._provider_name,
            session_id=checkpoint.session_id,
            data=checkpoint.state,
            metadata=entry_metadata,
            created_at=checkpoint.created_at,
            expires_at=checkpoint.expires_at,
        )
