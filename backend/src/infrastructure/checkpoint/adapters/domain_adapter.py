"""Domain Checkpoint Adapter.

Sprint 121 -- Story 121-1: Adapter that wraps the existing
DatabaseCheckpointStorage from the domain checkpoints module to
implement the CheckpointProvider protocol.

The domain checkpoint system (Phase 1, Sprint 2) uses PostgreSQL via the
CheckpointRepository. It operates on UUID-based execution_id and
checkpoint_id values. This adapter translates between string-based
checkpoint IDs and the UUID-based domain interface, and converts
domain checkpoint dicts to the unified CheckpointEntry format.

Usage:
    from src.domain.checkpoints.storage import DatabaseCheckpointStorage
    from src.infrastructure.checkpoint.adapters import DomainCheckpointAdapter

    storage = DatabaseCheckpointStorage(repository)
    adapter = DomainCheckpointAdapter(storage)
    registry.register_provider(adapter)
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.domain.checkpoints.storage import DatabaseCheckpointStorage
from src.infrastructure.checkpoint.protocol import CheckpointEntry

logger = logging.getLogger(__name__)

# Default UUID used when no execution_id is provided in checkpoint data
_DEFAULT_EXECUTION_UUID = UUID("00000000-0000-0000-0000-000000000000")


class DomainCheckpointAdapter:
    """Adapter wrapping DatabaseCheckpointStorage as a CheckpointProvider.

    Translates between the domain checkpoint system's UUID-based interface
    and the unified string-based CheckpointProvider protocol.

    The domain system generates its own UUID for each saved checkpoint. This
    adapter returns that generated UUID (as a string) from save_checkpoint,
    and expects it to be passed back for load/delete operations.

    Attributes:
        _storage: The underlying domain checkpoint storage backend.
        _provider_name: Provider identifier for registry registration.
    """

    def __init__(
        self,
        storage: DatabaseCheckpointStorage,
        name: str = "domain",
    ) -> None:
        """Initialize the adapter with an existing domain storage backend.

        Args:
            storage: An instance of DatabaseCheckpointStorage backed by
                PostgreSQL via CheckpointRepository.
            name: Provider name for registry identification.
                Defaults to 'domain'.
        """
        self._storage = storage
        self._provider_name = name
        logger.info(
            "DomainCheckpointAdapter initialized: provider_name=%s",
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
        """Save checkpoint data via the domain storage.

        Extracts execution_id and node_id from the data payload to match
        the domain interface. The domain system generates its own UUID for
        the checkpoint record; that UUID is returned as the canonical
        checkpoint_id.

        Args:
            checkpoint_id: Hint identifier. Not used as the actual DB key
                since the domain system auto-generates a UUID.
            data: Checkpoint data payload. May contain:
                - 'execution_id': Parent execution UUID string
                    (defaults to null UUID).
                - 'node_id': Workflow node identifier
                    (defaults to 'checkpoint').
            metadata: Optional additional metadata dictionary.

        Returns:
            The domain-generated checkpoint UUID as a string.

        Raises:
            ValueError: If execution_id cannot be parsed as a UUID.
            Exception: If the underlying storage fails to save.
        """
        # Extract domain-specific fields
        execution_id_str = data.get("execution_id", str(_DEFAULT_EXECUTION_UUID))
        node_id = data.get("node_id", "checkpoint")

        try:
            execution_id_uuid = UUID(str(execution_id_str))
        except ValueError:
            logger.error(
                "DomainCheckpointAdapter: invalid execution_id format: %s",
                execution_id_str,
            )
            raise

        try:
            result_uuid = await self._storage.save_checkpoint(
                execution_id=execution_id_uuid,
                node_id=node_id,
                state=data,
                metadata=metadata,
            )
        except Exception:
            logger.error(
                "DomainCheckpointAdapter failed to save: checkpoint_id=%s, "
                "execution_id=%s",
                checkpoint_id,
                execution_id_str,
                exc_info=True,
            )
            raise

        result_id = str(result_uuid)

        logger.info(
            "DomainCheckpointAdapter saved checkpoint: domain_id=%s, "
            "execution_id=%s, node_id=%s",
            result_id,
            execution_id_str,
            node_id,
        )

        return result_id

    async def load_checkpoint(
        self,
        checkpoint_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Load checkpoint data from the domain storage.

        Converts the string checkpoint_id to a UUID and delegates to the
        domain storage. Returns the checkpoint data dict or None.

        Args:
            checkpoint_id: Checkpoint UUID string to load.

        Returns:
            Checkpoint data dictionary (containing 'id', 'execution_id',
            'node_id', 'status', 'state', 'metadata', etc.), or None
            if not found.
        """
        try:
            checkpoint_uuid = UUID(checkpoint_id)
        except ValueError:
            logger.error(
                "DomainCheckpointAdapter: invalid checkpoint_id format: %s",
                checkpoint_id,
            )
            return None

        try:
            result = await self._storage.load_checkpoint(checkpoint_uuid)
        except Exception:
            logger.error(
                "DomainCheckpointAdapter failed to load: checkpoint_id=%s",
                checkpoint_id,
                exc_info=True,
            )
            raise

        if result is None:
            logger.debug(
                "DomainCheckpointAdapter: checkpoint not found: checkpoint_id=%s",
                checkpoint_id,
            )
            return None

        logger.debug(
            "DomainCheckpointAdapter loaded checkpoint: checkpoint_id=%s",
            checkpoint_id,
        )

        return result

    async def list_checkpoints(
        self,
        session_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[CheckpointEntry]:
        """List checkpoints from the domain storage.

        The domain storage requires an execution_id (UUID) to list
        checkpoints. If session_id is provided, it is interpreted as an
        execution_id. If not provided, an empty list is returned since
        the domain system cannot enumerate all checkpoints without an
        execution_id.

        Args:
            session_id: Optional execution_id filter (as UUID string).
                When provided, checkpoints for that execution are listed.
                When absent, returns an empty list.
            limit: Maximum entries to return.

        Returns:
            List of CheckpointEntry instances.
        """
        if session_id is None:
            logger.debug(
                "DomainCheckpointAdapter: no session_id provided, "
                "returning empty list (domain requires execution_id)"
            )
            return []

        try:
            execution_uuid = UUID(session_id)
        except ValueError:
            logger.error(
                "DomainCheckpointAdapter: invalid session_id (execution_id) format: %s",
                session_id,
            )
            return []

        try:
            checkpoints = await self._storage.list_checkpoints(execution_uuid)
        except Exception:
            logger.error(
                "DomainCheckpointAdapter failed to list: session_id=%s",
                session_id,
                exc_info=True,
            )
            raise

        entries: List[CheckpointEntry] = []

        for cp_dict in checkpoints[:limit]:
            entry = self._to_checkpoint_entry(cp_dict, session_id)
            entries.append(entry)

        logger.debug(
            "DomainCheckpointAdapter listed %d checkpoints (session_id=%s)",
            len(entries),
            session_id,
        )

        return entries

    async def delete_checkpoint(
        self,
        checkpoint_id: str,
    ) -> bool:
        """Delete a checkpoint from the domain storage.

        Args:
            checkpoint_id: Checkpoint UUID string to delete.

        Returns:
            True if deleted, False if not found or invalid ID.
        """
        try:
            checkpoint_uuid = UUID(checkpoint_id)
        except ValueError:
            logger.error(
                "DomainCheckpointAdapter: invalid checkpoint_id format for delete: %s",
                checkpoint_id,
            )
            return False

        try:
            result = await self._storage.delete_checkpoint(checkpoint_uuid)
        except Exception:
            logger.error(
                "DomainCheckpointAdapter failed to delete: checkpoint_id=%s",
                checkpoint_id,
                exc_info=True,
            )
            raise

        if result:
            logger.info(
                "DomainCheckpointAdapter deleted checkpoint: checkpoint_id=%s",
                checkpoint_id,
            )
        else:
            logger.debug(
                "DomainCheckpointAdapter: checkpoint not found for delete: "
                "checkpoint_id=%s",
                checkpoint_id,
            )

        return result

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    def _to_checkpoint_entry(
        self,
        cp_dict: Dict[str, Any],
        session_id: str,
    ) -> CheckpointEntry:
        """Convert a domain checkpoint dict to a CheckpointEntry.

        Args:
            cp_dict: Dictionary from DatabaseCheckpointStorage.list_checkpoints.
                Expected keys: 'id', 'execution_id', 'node_id', 'status',
                'payload', 'created_at'.
            session_id: The execution_id used for the query.

        Returns:
            A CheckpointEntry with data from the domain checkpoint.
        """
        checkpoint_id = cp_dict.get("id", "")
        created_at_str = cp_dict.get("created_at")

        # Parse created_at if available
        created_at = datetime.utcnow()
        if created_at_str:
            try:
                created_at = datetime.fromisoformat(str(created_at_str))
            except (ValueError, TypeError):
                pass

        # Build metadata from domain fields
        entry_metadata: Dict[str, Any] = {
            "node_id": cp_dict.get("node_id", ""),
            "status": cp_dict.get("status", ""),
        }

        # Extract state from payload if present
        payload = cp_dict.get("payload", {})
        data = payload.get("state", payload) if isinstance(payload, dict) else {}

        return CheckpointEntry(
            checkpoint_id=str(checkpoint_id),
            provider_name=self._provider_name,
            session_id=session_id,
            data=data,
            metadata=entry_metadata,
            created_at=created_at,
        )
