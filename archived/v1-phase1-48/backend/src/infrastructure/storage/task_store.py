"""Task Store — persistent storage for task entities.

Uses the unified StorageBackend abstraction from Sprint 110, defaulting
to PostgreSQL for production durability.

Sprint 113 — Phase 37 E2E Assembly B.
"""

import logging
from typing import Any, Dict, List, Optional

from src.infrastructure.storage.backends.base import StorageBackendABC
from src.infrastructure.storage.backends.factory import StorageFactory

logger = logging.getLogger(__name__)

_KEY_PREFIX = "task:"


class TaskStore:
    """Key-value store for Task entities.

    Wraps a ``StorageBackendABC`` with task-specific key prefixing and
    list-all support.

    Args:
        backend: Optional explicit backend; when ``None`` the
            ``StorageFactory`` selects the best available backend.
        namespace: Key prefix namespace (default ``"task:"``).
    """

    def __init__(
        self,
        backend: Optional[StorageBackendABC] = None,
        namespace: str = _KEY_PREFIX,
    ) -> None:
        self._backend = backend
        self._namespace = namespace
        self._initialized = False

    async def _ensure_backend(self) -> StorageBackendABC:
        """Lazy-initialise the storage backend."""
        if self._backend is None:
            self._backend = await StorageFactory.create(
                name="task_store",
                backend_type="auto",
            )
            self._initialized = True
            logger.info(
                "TaskStore: backend initialised (%s)",
                type(self._backend).__name__,
            )
        return self._backend

    def _key(self, task_id: str) -> str:
        return f"{self._namespace}{task_id}"

    async def save(self, task_id: str, data: Dict[str, Any]) -> None:
        """Persist a task."""
        backend = await self._ensure_backend()
        await backend.set(self._key(task_id), data)

    async def get(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a task by ID."""
        backend = await self._ensure_backend()
        return await backend.get(self._key(task_id))

    async def delete(self, task_id: str) -> None:
        """Remove a task."""
        backend = await self._ensure_backend()
        await backend.delete(self._key(task_id))

    async def exists(self, task_id: str) -> bool:
        """Check if a task exists."""
        backend = await self._ensure_backend()
        return await backend.exists(self._key(task_id))

    async def list_all(self) -> List[Dict[str, Any]]:
        """List all stored tasks.

        Uses the backend's ``keys()`` method to enumerate task keys,
        then retrieves each value. For backends that do not support
        ``keys()`` (or raise), returns an empty list.
        """
        backend = await self._ensure_backend()
        results: List[Dict[str, Any]] = []
        try:
            all_keys = await backend.keys(pattern=f"{self._namespace}*")
        except (AttributeError, NotImplementedError):
            logger.warning("TaskStore: backend does not support keys(); returning empty list")
            return results

        for key in all_keys:
            data = await backend.get(key)
            if data is not None:
                results.append(data)
        return results
