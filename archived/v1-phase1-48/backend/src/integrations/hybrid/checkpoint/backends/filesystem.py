# =============================================================================
# IPA Platform - Filesystem Checkpoint Storage
# =============================================================================
# Phase 14: Human-in-the-Loop & Approval
# Sprint 57: Unified Checkpoint & Polish
#
# Filesystem storage backend for HybridCheckpoint.
# Suitable for backup storage and offline/development scenarios.
#
# Key Features:
#   - Persistent storage on local filesystem
#   - Session-based directory organization
#   - Automatic compression for space efficiency
#   - No external dependencies
#
# Directory Structure:
#   {base_path}/
#   ├── sessions/
#   │   ├── {session_id}/
#   │   │   ├── {checkpoint_id}.json
#   │   │   └── ...
#   │   └── ...
#   └── index.json
#
# Dependencies:
#   - UnifiedCheckpointStorage (storage)
#   - HybridCheckpoint (models)
# =============================================================================

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models import CheckpointStatus, CheckpointType, HybridCheckpoint, RestoreResult
from ..storage import (
    CheckpointQuery,
    StorageConfig,
    StorageError,
    StorageStats,
    UnifiedCheckpointStorage,
)


class FilesystemCheckpointStorage(UnifiedCheckpointStorage):
    """
    Filesystem storage backend for checkpoints.

    Stores checkpoints as JSON files organized by session.
    Suitable for backup, archival, and development scenarios.

    Example:
        >>> storage = FilesystemCheckpointStorage(base_path="/data/checkpoints")
        >>> checkpoint_id = await storage.save(checkpoint)
        >>> loaded = await storage.load(checkpoint_id)

    Directory Structure:
        base_path/
        ├── sessions/
        │   └── {session_id}/
        │       └── {checkpoint_id}.json
        └── index.json
    """

    def __init__(
        self,
        base_path: Optional[str] = None,
        config: Optional[StorageConfig] = None,
    ):
        """
        Initialize filesystem storage.

        Args:
            base_path: Base directory for checkpoint storage.
                      Defaults to ~/.ipa/checkpoints
            config: Storage configuration
        """
        super().__init__(config)

        if base_path is None:
            base_path = os.path.expanduser("~/.ipa/checkpoints")

        self._base_path = Path(base_path)
        self._sessions_path = self._base_path / "sessions"
        self._index_path = self._base_path / "index.json"

        # Ensure directories exist
        self._sessions_path.mkdir(parents=True, exist_ok=True)

    def _checkpoint_path(self, session_id: str, checkpoint_id: str) -> Path:
        """Get file path for checkpoint."""
        return self._sessions_path / session_id / f"{checkpoint_id}.json"

    def _session_path(self, session_id: str) -> Path:
        """Get directory path for session."""
        return self._sessions_path / session_id

    async def save(self, checkpoint: HybridCheckpoint) -> str:
        """
        Save checkpoint to filesystem.

        Args:
            checkpoint: Checkpoint to save

        Returns:
            Checkpoint ID

        Raises:
            StorageError: If save operation fails
        """
        checkpoint_id = checkpoint.checkpoint_id
        session_id = checkpoint.session_id

        try:
            # Ensure session directory exists
            session_path = self._session_path(session_id)
            session_path.mkdir(parents=True, exist_ok=True)

            # Serialize and write checkpoint
            checkpoint_path = self._checkpoint_path(session_id, checkpoint_id)
            data = self._serialize(checkpoint)

            with open(checkpoint_path, "wb") as f:
                f.write(data)

            # Update index
            await self._update_index(session_id, checkpoint_id, "add")

            # Enforce retention limits
            await self.enforce_retention(session_id)

            return checkpoint_id

        except Exception as e:
            raise StorageError(f"Failed to save checkpoint: {e}")

    async def load(self, checkpoint_id: str) -> Optional[HybridCheckpoint]:
        """
        Load checkpoint from filesystem.

        Args:
            checkpoint_id: ID of checkpoint to load

        Returns:
            HybridCheckpoint if found, None otherwise
        """
        try:
            # Find checkpoint in any session
            session_id = await self._find_session_for_checkpoint(checkpoint_id)
            if session_id is None:
                return None

            checkpoint_path = self._checkpoint_path(session_id, checkpoint_id)

            if not checkpoint_path.exists():
                return None

            with open(checkpoint_path, "rb") as f:
                data = f.read()

            checkpoint = self._deserialize(data)

            # Check expiration
            if checkpoint.is_expired():
                await self.delete(checkpoint_id)
                return None

            return checkpoint

        except Exception as e:
            raise StorageError(f"Failed to load checkpoint: {e}")

    async def delete(self, checkpoint_id: str) -> bool:
        """
        Delete checkpoint from filesystem.

        Args:
            checkpoint_id: ID of checkpoint to delete

        Returns:
            True if deleted, False if not found
        """
        try:
            # Find checkpoint
            session_id = await self._find_session_for_checkpoint(checkpoint_id)
            if session_id is None:
                return False

            checkpoint_path = self._checkpoint_path(session_id, checkpoint_id)

            if not checkpoint_path.exists():
                return False

            # Delete file
            checkpoint_path.unlink()

            # Update index
            await self._update_index(session_id, checkpoint_id, "remove")

            # Clean up empty session directories
            session_path = self._session_path(session_id)
            if session_path.exists() and not any(session_path.iterdir()):
                session_path.rmdir()

            return True

        except Exception as e:
            raise StorageError(f"Failed to delete checkpoint: {e}")

    async def exists(self, checkpoint_id: str) -> bool:
        """
        Check if checkpoint exists on filesystem.

        Args:
            checkpoint_id: ID of checkpoint to check

        Returns:
            True if exists, False otherwise
        """
        try:
            session_id = await self._find_session_for_checkpoint(checkpoint_id)
            if session_id is None:
                return False

            checkpoint_path = self._checkpoint_path(session_id, checkpoint_id)
            return checkpoint_path.exists()

        except Exception:
            return False

    async def query(self, query: CheckpointQuery) -> List[HybridCheckpoint]:
        """
        Query checkpoints based on criteria.

        Args:
            query: Query parameters

        Returns:
            List of matching checkpoints
        """
        try:
            results: List[HybridCheckpoint] = []

            # Determine which sessions to scan
            if query.session_id:
                session_dirs = [self._session_path(query.session_id)]
            else:
                session_dirs = [
                    d for d in self._sessions_path.iterdir() if d.is_dir()
                ]

            # Scan session directories
            for session_dir in session_dirs:
                if not session_dir.exists():
                    continue

                for checkpoint_file in session_dir.glob("*.json"):
                    try:
                        with open(checkpoint_file, "rb") as f:
                            data = f.read()
                        checkpoint = self._deserialize(data)

                        # Skip expired
                        if checkpoint.is_expired():
                            continue

                        # Apply filters
                        if query.checkpoint_type and checkpoint.checkpoint_type != query.checkpoint_type:
                            continue
                        if query.status and checkpoint.status != query.status:
                            continue
                        if query.execution_mode and checkpoint.execution_mode != query.execution_mode:
                            continue
                        if query.created_after and checkpoint.created_at < query.created_after:
                            continue
                        if query.created_before and checkpoint.created_at > query.created_before:
                            continue

                        results.append(checkpoint)

                    except Exception:
                        # Skip corrupted files
                        continue

            # Sort results
            if query.order_by == "created_at":
                results.sort(key=lambda c: c.created_at, reverse=not query.ascending)
            elif query.order_by == "updated_at":
                results.sort(key=lambda c: c.updated_at, reverse=not query.ascending)

            # Apply pagination
            start = query.offset
            end = start + query.limit if query.limit > 0 else None

            return results[start:end]

        except Exception as e:
            raise StorageError(f"Failed to query checkpoints: {e}")

    async def get_stats(self) -> StorageStats:
        """
        Get storage statistics.

        Returns:
            StorageStats with current statistics
        """
        try:
            total = 0
            active = 0
            expired = 0
            total_size = 0
            oldest: Optional[datetime] = None
            newest: Optional[datetime] = None
            sessions = set()

            # Scan all checkpoints
            for session_dir in self._sessions_path.iterdir():
                if not session_dir.is_dir():
                    continue

                sessions.add(session_dir.name)

                for checkpoint_file in session_dir.glob("*.json"):
                    total += 1
                    total_size += checkpoint_file.stat().st_size

                    try:
                        with open(checkpoint_file, "rb") as f:
                            data = f.read()
                        checkpoint = self._deserialize(data)

                        if checkpoint.is_expired():
                            expired += 1
                        else:
                            active += 1

                        if oldest is None or checkpoint.created_at < oldest:
                            oldest = checkpoint.created_at
                        if newest is None or checkpoint.created_at > newest:
                            newest = checkpoint.created_at

                    except Exception:
                        # Count as expired if can't parse
                        expired += 1

            return StorageStats(
                total_checkpoints=total,
                active_checkpoints=active,
                expired_checkpoints=expired,
                total_size_bytes=total_size,
                sessions_count=len(sessions),
                oldest_checkpoint=oldest,
                newest_checkpoint=newest,
            )

        except Exception as e:
            raise StorageError(f"Failed to get storage stats: {e}")

    async def cleanup_expired(self) -> int:
        """
        Remove expired checkpoints.

        Returns:
            Number of checkpoints removed
        """
        try:
            removed = 0

            for session_dir in self._sessions_path.iterdir():
                if not session_dir.is_dir():
                    continue

                for checkpoint_file in session_dir.glob("*.json"):
                    try:
                        with open(checkpoint_file, "rb") as f:
                            data = f.read()
                        checkpoint = self._deserialize(data)

                        if checkpoint.is_expired():
                            checkpoint_file.unlink()
                            removed += 1

                    except Exception:
                        # Delete corrupted files
                        checkpoint_file.unlink()
                        removed += 1

                # Clean up empty session directories
                if not any(session_dir.iterdir()):
                    session_dir.rmdir()

            return removed

        except Exception as e:
            raise StorageError(f"Failed to cleanup expired checkpoints: {e}")

    async def _find_session_for_checkpoint(self, checkpoint_id: str) -> Optional[str]:
        """Find which session contains a checkpoint."""
        # First check index
        index = await self._load_index()
        for session_id, checkpoints in index.items():
            if checkpoint_id in checkpoints:
                return session_id

        # Fall back to filesystem scan
        for session_dir in self._sessions_path.iterdir():
            if not session_dir.is_dir():
                continue

            checkpoint_path = session_dir / f"{checkpoint_id}.json"
            if checkpoint_path.exists():
                return session_dir.name

        return None

    async def _load_index(self) -> Dict[str, List[str]]:
        """Load the index file."""
        try:
            if self._index_path.exists():
                with open(self._index_path, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    async def _save_index(self, index: Dict[str, List[str]]) -> None:
        """Save the index file."""
        try:
            with open(self._index_path, "w") as f:
                json.dump(index, f, indent=2)
        except Exception:
            pass

    async def _update_index(
        self, session_id: str, checkpoint_id: str, action: str
    ) -> None:
        """Update the index file."""
        index = await self._load_index()

        if session_id not in index:
            index[session_id] = []

        if action == "add":
            if checkpoint_id not in index[session_id]:
                index[session_id].append(checkpoint_id)
        elif action == "remove":
            if checkpoint_id in index[session_id]:
                index[session_id].remove(checkpoint_id)

            # Remove empty sessions from index
            if not index[session_id]:
                del index[session_id]

        await self._save_index(index)

    def clear_all(self) -> None:
        """
        Clear all checkpoints from filesystem.

        WARNING: This removes all data. Use with caution.
        """
        if self._sessions_path.exists():
            shutil.rmtree(self._sessions_path)
            self._sessions_path.mkdir(parents=True, exist_ok=True)

        if self._index_path.exists():
            self._index_path.unlink()
