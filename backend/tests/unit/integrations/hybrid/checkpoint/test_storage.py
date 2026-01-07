# =============================================================================
# IPA Platform - Checkpoint Storage Unit Tests
# =============================================================================
# Phase 14: Human-in-the-Loop & Approval
# Sprint 57: Unified Checkpoint & Polish
#
# Tests for UnifiedCheckpointStorage abstract class and related components.
# =============================================================================

from datetime import datetime, timedelta

import pytest

from src.integrations.hybrid.checkpoint.models import (
    CheckpointStatus,
    CheckpointType,
    ClaudeCheckpointState,
    HybridCheckpoint,
    MAFCheckpointState,
)
from src.integrations.hybrid.checkpoint.storage import (
    CheckpointQuery,
    StorageBackend,
    StorageConfig,
    StorageStats,
)


# =============================================================================
# StorageBackend Tests
# =============================================================================


class TestStorageBackend:
    """Tests for StorageBackend enum."""

    def test_backend_values(self):
        """Test all backend values exist."""
        assert StorageBackend.REDIS == "redis"
        assert StorageBackend.POSTGRES == "postgres"
        assert StorageBackend.FILESYSTEM == "filesystem"
        assert StorageBackend.MEMORY == "memory"

    def test_backend_count(self):
        """Test correct number of backends."""
        assert len(StorageBackend) == 4


# =============================================================================
# StorageConfig Tests
# =============================================================================


class TestStorageConfig:
    """Tests for StorageConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = StorageConfig()

        assert config.backend == StorageBackend.REDIS
        assert config.ttl_seconds == 86400  # 24 hours
        assert config.max_checkpoints_per_session == 100
        assert config.enable_compression is True
        assert config.enable_encryption is False
        assert config.cleanup_interval_seconds == 3600  # 1 hour

    def test_custom_config(self):
        """Test custom configuration."""
        config = StorageConfig(
            backend=StorageBackend.POSTGRES,
            ttl_seconds=3600,
            max_checkpoints_per_session=50,
            enable_compression=False,
            enable_encryption=True,
            cleanup_interval_seconds=1800,
        )

        assert config.backend == StorageBackend.POSTGRES
        assert config.ttl_seconds == 3600
        assert config.max_checkpoints_per_session == 50
        assert config.enable_compression is False
        assert config.enable_encryption is True
        assert config.cleanup_interval_seconds == 1800


# =============================================================================
# CheckpointQuery Tests
# =============================================================================


class TestCheckpointQuery:
    """Tests for CheckpointQuery."""

    def test_default_query(self):
        """Test default query parameters."""
        query = CheckpointQuery()

        assert query.session_id is None
        assert query.checkpoint_type is None
        assert query.status is None
        assert query.execution_mode is None
        assert query.created_after is None
        assert query.created_before is None
        assert query.limit == 100
        assert query.offset == 0
        assert query.order_by == "created_at"
        assert query.ascending is False

    def test_session_query(self):
        """Test session-specific query."""
        query = CheckpointQuery(
            session_id="sess_123",
            limit=10,
        )

        assert query.session_id == "sess_123"
        assert query.limit == 10

    def test_filtered_query(self):
        """Test filtered query."""
        now = datetime.utcnow()
        query = CheckpointQuery(
            session_id="sess_123",
            checkpoint_type=CheckpointType.HITL,
            status=CheckpointStatus.ACTIVE,
            execution_mode="hybrid",
            created_after=now - timedelta(hours=1),
            created_before=now,
            limit=50,
            offset=10,
            order_by="updated_at",
            ascending=True,
        )

        assert query.checkpoint_type == CheckpointType.HITL
        assert query.status == CheckpointStatus.ACTIVE
        assert query.execution_mode == "hybrid"
        assert query.created_after is not None
        assert query.created_before is not None
        assert query.limit == 50
        assert query.offset == 10
        assert query.order_by == "updated_at"
        assert query.ascending is True


# =============================================================================
# StorageStats Tests
# =============================================================================


class TestStorageStats:
    """Tests for StorageStats."""

    def test_default_stats(self):
        """Test default statistics."""
        stats = StorageStats()

        assert stats.total_checkpoints == 0
        assert stats.active_checkpoints == 0
        assert stats.expired_checkpoints == 0
        assert stats.total_size_bytes == 0
        assert stats.sessions_count == 0
        assert stats.oldest_checkpoint is None
        assert stats.newest_checkpoint is None

    def test_populated_stats(self):
        """Test populated statistics."""
        now = datetime.utcnow()
        stats = StorageStats(
            total_checkpoints=100,
            active_checkpoints=80,
            expired_checkpoints=20,
            total_size_bytes=1024000,
            sessions_count=10,
            oldest_checkpoint=now - timedelta(days=7),
            newest_checkpoint=now,
        )

        assert stats.total_checkpoints == 100
        assert stats.active_checkpoints == 80
        assert stats.expired_checkpoints == 20
        assert stats.total_size_bytes == 1024000
        assert stats.sessions_count == 10

    def test_to_dict(self):
        """Test to_dict conversion."""
        now = datetime.utcnow()
        stats = StorageStats(
            total_checkpoints=50,
            active_checkpoints=45,
            expired_checkpoints=5,
            total_size_bytes=512000,
            sessions_count=5,
            oldest_checkpoint=now - timedelta(days=1),
            newest_checkpoint=now,
        )

        data = stats.to_dict()

        assert data["total_checkpoints"] == 50
        assert data["active_checkpoints"] == 45
        assert data["expired_checkpoints"] == 5
        assert data["total_size_bytes"] == 512000
        assert data["sessions_count"] == 5
        assert data["oldest_checkpoint"] is not None
        assert data["newest_checkpoint"] is not None

    def test_to_dict_with_none_timestamps(self):
        """Test to_dict with None timestamps."""
        stats = StorageStats()
        data = stats.to_dict()

        assert data["oldest_checkpoint"] is None
        assert data["newest_checkpoint"] is None
