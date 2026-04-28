"""Unified Checkpoint Registry.

Sprint 120 -- Story 120-2: Central registry that coordinates the platform's
4 independent checkpoint systems through a unified interface.

The registry maintains a collection of CheckpointProvider instances and
delegates operations to the appropriate provider based on provider name.

Usage:
    registry = UnifiedCheckpointRegistry()
    registry.register_provider(hybrid_adapter)
    await registry.save("hybrid", "cp-001", {"state": "data"})
    data = await registry.load("hybrid", "cp-001")
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.infrastructure.checkpoint.protocol import CheckpointEntry, CheckpointProvider

logger = logging.getLogger(__name__)


class UnifiedCheckpointRegistry:
    """Central registry for all checkpoint providers.

    Provides a unified interface for saving, loading, listing, and deleting
    checkpoints across all registered providers. Uses asyncio.Lock for
    thread-safe provider registration.

    Attributes:
        _providers: Dictionary mapping provider names to CheckpointProvider instances.
        _lock: Async lock for thread-safe provider registration/unregistration.
    """

    def __init__(self) -> None:
        """Initialize the registry with empty provider collection."""
        self._providers: Dict[str, CheckpointProvider] = {}
        self._lock = asyncio.Lock()
        logger.info("UnifiedCheckpointRegistry initialized")

    # =========================================================================
    # Provider Management
    # =========================================================================

    async def register_provider(self, provider: CheckpointProvider) -> None:
        """Register a checkpoint provider.

        Args:
            provider: A CheckpointProvider implementation to register.

        Raises:
            ValueError: If a provider with the same name is already registered.
            TypeError: If the provider does not implement CheckpointProvider.
        """
        if not isinstance(provider, CheckpointProvider):
            raise TypeError(
                f"Provider must implement CheckpointProvider protocol, "
                f"got {type(provider).__name__}"
            )

        name = provider.provider_name

        async with self._lock:
            if name in self._providers:
                raise ValueError(
                    f"Provider '{name}' is already registered. "
                    f"Unregister it first before re-registering."
                )
            self._providers[name] = provider

        logger.info(
            "Registered checkpoint provider: %s (total: %d)",
            name,
            len(self._providers),
        )

    async def unregister_provider(self, name: str) -> None:
        """Unregister a checkpoint provider by name.

        Args:
            name: The provider name to unregister.

        Raises:
            ValueError: If no provider with the given name is registered.
        """
        async with self._lock:
            if name not in self._providers:
                raise ValueError(
                    f"Provider '{name}' is not registered. "
                    f"Available providers: {list(self._providers.keys())}"
                )
            del self._providers[name]

        logger.info(
            "Unregistered checkpoint provider: %s (remaining: %d)",
            name,
            len(self._providers),
        )

    def list_providers(self) -> List[str]:
        """Return list of registered provider names.

        Returns:
            List of provider name strings.
        """
        return list(self._providers.keys())

    def _get_provider(self, provider_name: str) -> CheckpointProvider:
        """Get a provider by name with validation.

        Args:
            provider_name: Name of the provider to retrieve.

        Returns:
            The matching CheckpointProvider instance.

        Raises:
            ValueError: If no provider with the given name is registered.
        """
        provider = self._providers.get(provider_name)
        if provider is None:
            raise ValueError(
                f"Provider '{provider_name}' is not registered. "
                f"Available providers: {list(self._providers.keys())}"
            )
        return provider

    # =========================================================================
    # Checkpoint Operations
    # =========================================================================

    async def save(
        self,
        provider_name: str,
        checkpoint_id: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Save a checkpoint through the specified provider.

        Args:
            provider_name: Name of the provider to save through.
            checkpoint_id: Unique checkpoint identifier.
            data: Checkpoint data payload.
            metadata: Optional metadata dictionary.

        Returns:
            The checkpoint_id.

        Raises:
            ValueError: If the provider is not registered.
        """
        provider = self._get_provider(provider_name)
        logger.debug(
            "Saving checkpoint via provider '%s': checkpoint_id=%s",
            provider_name,
            checkpoint_id,
        )

        result = await provider.save_checkpoint(
            checkpoint_id=checkpoint_id,
            data=data,
            metadata=metadata,
        )

        logger.info(
            "Saved checkpoint via provider '%s': checkpoint_id=%s",
            provider_name,
            checkpoint_id,
        )
        return result

    async def load(
        self,
        provider_name: str,
        checkpoint_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Load a checkpoint from the specified provider.

        Args:
            provider_name: Name of the provider to load from.
            checkpoint_id: Checkpoint to load.

        Returns:
            Checkpoint data dictionary, or None if not found.

        Raises:
            ValueError: If the provider is not registered.
        """
        provider = self._get_provider(provider_name)
        logger.debug(
            "Loading checkpoint via provider '%s': checkpoint_id=%s",
            provider_name,
            checkpoint_id,
        )

        result = await provider.load_checkpoint(checkpoint_id=checkpoint_id)

        if result is None:
            logger.debug(
                "Checkpoint not found via provider '%s': checkpoint_id=%s",
                provider_name,
                checkpoint_id,
            )
        else:
            logger.debug(
                "Loaded checkpoint via provider '%s': checkpoint_id=%s",
                provider_name,
                checkpoint_id,
            )

        return result

    async def delete(
        self,
        provider_name: str,
        checkpoint_id: str,
    ) -> bool:
        """Delete a checkpoint from the specified provider.

        Args:
            provider_name: Name of the provider to delete from.
            checkpoint_id: Checkpoint to delete.

        Returns:
            True if deleted, False if not found.

        Raises:
            ValueError: If the provider is not registered.
        """
        provider = self._get_provider(provider_name)
        logger.debug(
            "Deleting checkpoint via provider '%s': checkpoint_id=%s",
            provider_name,
            checkpoint_id,
        )

        result = await provider.delete_checkpoint(checkpoint_id=checkpoint_id)

        if result:
            logger.info(
                "Deleted checkpoint via provider '%s': checkpoint_id=%s",
                provider_name,
                checkpoint_id,
            )
        else:
            logger.debug(
                "Checkpoint not found for deletion via provider '%s': checkpoint_id=%s",
                provider_name,
                checkpoint_id,
            )

        return result

    # =========================================================================
    # Aggregate Operations
    # =========================================================================

    async def list_all(
        self,
        session_id: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, List[CheckpointEntry]]:
        """List checkpoints from all registered providers.

        Aggregates checkpoint listings from all providers. Individual provider
        errors are logged and skipped to ensure partial results are returned.

        Args:
            session_id: Optional session filter applied to all providers.
            limit: Maximum entries per provider.

        Returns:
            Dictionary mapping provider names to their checkpoint entry lists.
        """
        results: Dict[str, List[CheckpointEntry]] = {}

        for name, provider in self._providers.items():
            try:
                entries = await provider.list_checkpoints(
                    session_id=session_id,
                    limit=limit,
                )
                results[name] = entries
            except Exception:
                logger.error(
                    "Failed to list checkpoints from provider '%s'",
                    name,
                    exc_info=True,
                )
                results[name] = []

        total_count = sum(len(entries) for entries in results.values())
        logger.debug(
            "Listed checkpoints from %d providers: total_entries=%d, session_id=%s",
            len(results),
            total_count,
            session_id,
        )

        return results

    async def cleanup_expired(self, max_age_hours: int = 24) -> Dict[str, int]:
        """Clean up expired checkpoints across all providers.

        Iterates through all providers and deletes checkpoints that have
        exceeded the specified maximum age. Individual provider errors are
        logged and skipped.

        Args:
            max_age_hours: Maximum age in hours before a checkpoint is
                considered expired.

        Returns:
            Dictionary mapping provider names to the count of deleted checkpoints.
        """
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        cleanup_results: Dict[str, int] = {}

        for name, provider in self._providers.items():
            deleted_count = 0
            try:
                entries = await provider.list_checkpoints(limit=1000)
                for entry in entries:
                    if entry.created_at < cutoff or entry.is_expired():
                        try:
                            was_deleted = await provider.delete_checkpoint(
                                entry.checkpoint_id,
                            )
                            if was_deleted:
                                deleted_count += 1
                        except Exception:
                            logger.error(
                                "Failed to delete expired checkpoint '%s' "
                                "from provider '%s'",
                                entry.checkpoint_id,
                                name,
                                exc_info=True,
                            )
            except Exception:
                logger.error(
                    "Failed to cleanup expired checkpoints from provider '%s'",
                    name,
                    exc_info=True,
                )

            cleanup_results[name] = deleted_count

        total_deleted = sum(cleanup_results.values())
        logger.info(
            "Expired checkpoint cleanup completed: total_deleted=%d, "
            "max_age_hours=%d, results=%s",
            total_deleted,
            max_age_hours,
            json.dumps(cleanup_results, default=str, ensure_ascii=False),
        )

        return cleanup_results

    async def get_stats(self) -> Dict[str, Any]:
        """Get registration and checkpoint statistics for all providers.

        Returns:
            Dictionary with provider count, names, and per-provider stats.
        """
        provider_stats: Dict[str, Any] = {}

        for name, provider in self._providers.items():
            try:
                entries = await provider.list_checkpoints(limit=10000)
                provider_stats[name] = {
                    "registered": True,
                    "checkpoint_count": len(entries),
                    "provider_type": type(provider).__name__,
                }
            except Exception:
                logger.error(
                    "Failed to get stats from provider '%s'",
                    name,
                    exc_info=True,
                )
                provider_stats[name] = {
                    "registered": True,
                    "checkpoint_count": -1,
                    "provider_type": type(provider).__name__,
                    "error": "Failed to retrieve stats",
                }

        stats = {
            "provider_count": len(self._providers),
            "provider_names": list(self._providers.keys()),
            "providers": provider_stats,
        }

        logger.debug(
            "Registry stats: %s",
            json.dumps(stats, default=str, ensure_ascii=False),
        )

        return stats
