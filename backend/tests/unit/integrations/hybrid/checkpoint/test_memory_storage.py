# =============================================================================
# IPA Platform - Memory Checkpoint Storage Unit Tests
# =============================================================================
# Phase 14: Human-in-the-Loop & Approval
# Sprint 57: Unified Checkpoint & Polish
#
# Tests for MemoryCheckpointStorage implementation.
# =============================================================================

from datetime import datetime, timedelta

import pytest

from src.integrations.hybrid.checkpoint.backends.memory import MemoryCheckpointStorage
from src.integrations.hybrid.checkpoint.models import (
    CheckpointStatus,
    CheckpointType,
    ClaudeCheckpointState,
    HybridCheckpoint,
    MAFCheckpointState,
)
from src.integrations.hybrid.checkpoint.storage import (
    CheckpointQuery,
    StorageConfig,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def storage() -> MemoryCheckpointStorage:
    """Create a memory storage instance."""
    return MemoryCheckpointStorage()


@pytest.fixture
def simple_checkpoint() -> HybridCheckpoint:
    """Create a simple checkpoint for testing."""
    return HybridCheckpoint(
        session_id="sess_123",
        execution_mode="chat",
    )


@pytest.fixture
def complex_checkpoint() -> HybridCheckpoint:
    """Create a complex checkpoint with both states."""
    maf_state = MAFCheckpointState(
        workflow_id="wf_123",
        workflow_name="Test Workflow",
        current_step=2,
        total_steps=5,
        agent_states={"agent_1": {"status": "completed"}},
        variables={"key": "value"},
    )

    claude_state = ClaudeCheckpointState(
        session_id="sess_123",
        conversation_history=[
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ],
    )

    return HybridCheckpoint(
        session_id="sess_123",
        checkpoint_type=CheckpointType.HITL,
        maf_state=maf_state,
        claude_state=claude_state,
        execution_mode="hybrid",
    )


# =============================================================================
# Basic Operations Tests
# =============================================================================


class TestBasicOperations:
    """Tests for basic CRUD operations."""

    @pytest.mark.asyncio
    async def test_save_and_load(self, storage, simple_checkpoint):
        """Test saving and loading a checkpoint."""
        # Save
        checkpoint_id = await storage.save(simple_checkpoint)
        assert checkpoint_id == simple_checkpoint.checkpoint_id

        # Load
        loaded = await storage.load(checkpoint_id)
        assert loaded is not None
        assert loaded.session_id == simple_checkpoint.session_id
        assert loaded.checkpoint_id == checkpoint_id

    @pytest.mark.asyncio
    async def test_save_complex_checkpoint(self, storage, complex_checkpoint):
        """Test saving a complex checkpoint with both states."""
        checkpoint_id = await storage.save(complex_checkpoint)
        loaded = await storage.load(checkpoint_id)

        assert loaded is not None
        assert loaded.maf_state is not None
        assert loaded.claude_state is not None
        assert loaded.maf_state.workflow_id == "wf_123"
        assert loaded.claude_state.get_message_count() == 2

    @pytest.mark.asyncio
    async def test_load_nonexistent(self, storage):
        """Test loading a nonexistent checkpoint."""
        loaded = await storage.load("nonexistent_id")
        assert loaded is None

    @pytest.mark.asyncio
    async def test_delete(self, storage, simple_checkpoint):
        """Test deleting a checkpoint."""
        checkpoint_id = await storage.save(simple_checkpoint)

        # Delete
        deleted = await storage.delete(checkpoint_id)
        assert deleted is True

        # Verify deleted
        loaded = await storage.load(checkpoint_id)
        assert loaded is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, storage):
        """Test deleting a nonexistent checkpoint."""
        deleted = await storage.delete("nonexistent_id")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_exists(self, storage, simple_checkpoint):
        """Test checking checkpoint existence."""
        checkpoint_id = await storage.save(simple_checkpoint)

        assert await storage.exists(checkpoint_id) is True
        assert await storage.exists("nonexistent_id") is False

    @pytest.mark.asyncio
    async def test_update_checkpoint(self, storage, simple_checkpoint):
        """Test updating an existing checkpoint."""
        checkpoint_id = await storage.save(simple_checkpoint)

        # Modify and save again
        simple_checkpoint.execution_mode = "workflow"
        await storage.save(simple_checkpoint)

        # Load and verify
        loaded = await storage.load(checkpoint_id)
        assert loaded.execution_mode == "workflow"


# =============================================================================
# Query Tests
# =============================================================================


class TestQueryOperations:
    """Tests for query operations."""

    @pytest.mark.asyncio
    async def test_query_by_session(self, storage):
        """Test querying by session ID."""
        # Create checkpoints for different sessions
        cp1 = HybridCheckpoint(session_id="sess_A")
        cp2 = HybridCheckpoint(session_id="sess_A")
        cp3 = HybridCheckpoint(session_id="sess_B")

        await storage.save(cp1)
        await storage.save(cp2)
        await storage.save(cp3)

        # Query session A
        query = CheckpointQuery(session_id="sess_A")
        results = await storage.query(query)

        assert len(results) == 2
        assert all(r.session_id == "sess_A" for r in results)

    @pytest.mark.asyncio
    async def test_query_by_type(self, storage):
        """Test querying by checkpoint type."""
        cp1 = HybridCheckpoint(session_id="sess_1", checkpoint_type=CheckpointType.AUTO)
        cp2 = HybridCheckpoint(session_id="sess_1", checkpoint_type=CheckpointType.HITL)
        cp3 = HybridCheckpoint(session_id="sess_1", checkpoint_type=CheckpointType.AUTO)

        await storage.save(cp1)
        await storage.save(cp2)
        await storage.save(cp3)

        query = CheckpointQuery(
            session_id="sess_1",
            checkpoint_type=CheckpointType.AUTO,
        )
        results = await storage.query(query)

        assert len(results) == 2
        assert all(r.checkpoint_type == CheckpointType.AUTO for r in results)

    @pytest.mark.asyncio
    async def test_query_by_status(self, storage):
        """Test querying by status."""
        cp1 = HybridCheckpoint(session_id="sess_1")
        cp2 = HybridCheckpoint(session_id="sess_1")
        cp2.mark_restored()

        await storage.save(cp1)
        await storage.save(cp2)

        query = CheckpointQuery(
            session_id="sess_1",
            status=CheckpointStatus.ACTIVE,
        )
        results = await storage.query(query)

        assert len(results) == 1
        assert results[0].status == CheckpointStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_query_by_execution_mode(self, storage):
        """Test querying by execution mode."""
        cp1 = HybridCheckpoint(session_id="sess_1", execution_mode="chat")
        cp2 = HybridCheckpoint(session_id="sess_1", execution_mode="workflow")
        cp3 = HybridCheckpoint(session_id="sess_1", execution_mode="chat")

        await storage.save(cp1)
        await storage.save(cp2)
        await storage.save(cp3)

        query = CheckpointQuery(
            session_id="sess_1",
            execution_mode="chat",
        )
        results = await storage.query(query)

        assert len(results) == 2
        assert all(r.execution_mode == "chat" for r in results)

    @pytest.mark.asyncio
    async def test_query_pagination(self, storage):
        """Test query pagination."""
        # Create 10 checkpoints
        for i in range(10):
            cp = HybridCheckpoint(session_id="sess_1")
            await storage.save(cp)

        # Query with limit
        query = CheckpointQuery(session_id="sess_1", limit=5)
        results = await storage.query(query)
        assert len(results) == 5

        # Query with offset
        query = CheckpointQuery(session_id="sess_1", limit=5, offset=5)
        results = await storage.query(query)
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_query_ordering(self, storage):
        """Test query ordering."""
        import asyncio

        # Create checkpoints with slight delays
        checkpoints = []
        for i in range(3):
            cp = HybridCheckpoint(session_id="sess_1")
            await storage.save(cp)
            checkpoints.append(cp)
            await asyncio.sleep(0.01)  # Small delay

        # Query descending (default)
        query = CheckpointQuery(session_id="sess_1", ascending=False)
        results = await storage.query(query)
        assert len(results) == 3
        # Most recent should be first
        assert results[0].created_at >= results[1].created_at
        assert results[1].created_at >= results[2].created_at

        # Query ascending
        query = CheckpointQuery(session_id="sess_1", ascending=True)
        results = await storage.query(query)
        # Oldest should be first
        assert results[0].created_at <= results[1].created_at
        assert results[1].created_at <= results[2].created_at


# =============================================================================
# Session Operations Tests
# =============================================================================


class TestSessionOperations:
    """Tests for session-related operations."""

    @pytest.mark.asyncio
    async def test_load_by_session(self, storage):
        """Test loading checkpoints by session."""
        for i in range(5):
            cp = HybridCheckpoint(session_id="sess_1")
            await storage.save(cp)

        results = await storage.load_by_session("sess_1", limit=3)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_load_latest(self, storage):
        """Test loading the latest checkpoint."""
        import asyncio

        for i in range(3):
            cp = HybridCheckpoint(session_id="sess_1")
            await storage.save(cp)
            await asyncio.sleep(0.01)
            last_cp = cp

        latest = await storage.load_latest("sess_1")
        assert latest is not None
        assert latest.checkpoint_id == last_cp.checkpoint_id

    @pytest.mark.asyncio
    async def test_load_latest_empty_session(self, storage):
        """Test loading latest from empty session."""
        latest = await storage.load_latest("nonexistent_session")
        assert latest is None

    @pytest.mark.asyncio
    async def test_count_by_session(self, storage):
        """Test counting checkpoints by session."""
        for i in range(5):
            cp = HybridCheckpoint(session_id="sess_1")
            await storage.save(cp)

        count = await storage.count_by_session("sess_1")
        assert count == 5

    @pytest.mark.asyncio
    async def test_delete_by_session(self, storage):
        """Test deleting all checkpoints for a session."""
        for i in range(5):
            cp = HybridCheckpoint(session_id="sess_1")
            await storage.save(cp)

        deleted = await storage.delete_by_session("sess_1")
        assert deleted == 5

        count = await storage.count_by_session("sess_1")
        assert count == 0


# =============================================================================
# Statistics Tests
# =============================================================================


class TestStatistics:
    """Tests for storage statistics."""

    @pytest.mark.asyncio
    async def test_get_stats_empty(self, storage):
        """Test statistics for empty storage."""
        stats = await storage.get_stats()

        assert stats.total_checkpoints == 0
        assert stats.active_checkpoints == 0
        assert stats.sessions_count == 0

    @pytest.mark.asyncio
    async def test_get_stats_with_data(self, storage):
        """Test statistics with data."""
        for i in range(10):
            cp = HybridCheckpoint(session_id=f"sess_{i % 3}")
            await storage.save(cp)

        stats = await storage.get_stats()

        assert stats.total_checkpoints == 10
        assert stats.active_checkpoints == 10
        assert stats.sessions_count == 3
        assert stats.oldest_checkpoint is not None
        assert stats.newest_checkpoint is not None


# =============================================================================
# Expiration Tests
# =============================================================================


class TestExpiration:
    """Tests for checkpoint expiration."""

    @pytest.mark.asyncio
    async def test_expired_checkpoint_not_loaded(self, storage):
        """Test that expired checkpoints are not loaded."""
        cp = HybridCheckpoint(
            session_id="sess_1",
            # Set expiration in the past
            expires_at=datetime.utcnow() - timedelta(hours=1),
        )

        checkpoint_id = await storage.save(cp)
        loaded = await storage.load(checkpoint_id)

        assert loaded is None

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, storage):
        """Test cleanup of expired checkpoints."""
        # Create some checkpoints
        for i in range(5):
            if i < 2:
                # Make these expired
                cp = HybridCheckpoint(
                    session_id="sess_1",
                    expires_at=datetime.utcnow() - timedelta(hours=1),
                )
            else:
                cp = HybridCheckpoint(session_id="sess_1")
            await storage.save(cp)

        # Cleanup
        removed = await storage.cleanup_expired()
        assert removed == 2

        # Verify remaining
        count = await storage.count_by_session("sess_1")
        assert count == 3


# =============================================================================
# Restore Tests
# =============================================================================


class TestRestore:
    """Tests for checkpoint restoration."""

    @pytest.mark.asyncio
    async def test_restore_success(self, storage, complex_checkpoint):
        """Test successful checkpoint restoration."""
        checkpoint_id = await storage.save(complex_checkpoint)
        result = await storage.restore(checkpoint_id)

        assert result.success is True
        assert result.checkpoint_id == checkpoint_id
        assert result.restored_maf is True
        assert result.restored_claude is True
        assert result.restore_time_ms >= 0

    @pytest.mark.asyncio
    async def test_restore_nonexistent(self, storage):
        """Test restoring nonexistent checkpoint."""
        result = await storage.restore("nonexistent_id")

        assert result.success is False
        assert result.error is not None
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_restore_expired(self, storage):
        """Test restoring expired checkpoint."""
        cp = HybridCheckpoint(
            session_id="sess_1",
            expires_at=datetime.utcnow() - timedelta(hours=1),
        )
        checkpoint_id = await storage.save(cp)

        # Since checkpoint is expired, load() will return None
        # and restore() should fail
        result = await storage.restore(checkpoint_id)
        assert result.success is False
        assert result.error is not None
        assert "not found" in result.error.lower() or "expired" in result.error.lower()


# =============================================================================
# Retention Tests
# =============================================================================


class TestRetention:
    """Tests for retention policy enforcement."""

    @pytest.mark.asyncio
    async def test_enforce_retention(self):
        """Test retention policy enforcement."""
        config = StorageConfig(max_checkpoints_per_session=5)
        storage = MemoryCheckpointStorage(config)

        # Create more than max checkpoints
        for i in range(10):
            cp = HybridCheckpoint(session_id="sess_1")
            await storage.save(cp)

        # Should have enforced retention
        count = await storage.count_by_session("sess_1")
        assert count == 5


# =============================================================================
# Utility Tests
# =============================================================================


class TestUtilities:
    """Tests for utility methods."""

    @pytest.mark.asyncio
    async def test_clear(self, storage, simple_checkpoint):
        """Test clearing all checkpoints."""
        await storage.save(simple_checkpoint)
        storage.clear()

        assert storage.get_checkpoint_count() == 0
        assert storage.get_session_count() == 0

    def test_get_checkpoint_count(self, storage):
        """Test getting checkpoint count."""
        assert storage.get_checkpoint_count() == 0

    def test_get_session_count(self, storage):
        """Test getting session count."""
        assert storage.get_session_count() == 0

    @pytest.mark.asyncio
    async def test_save_with_restore_point(self, storage, simple_checkpoint):
        """Test saving with restore point name."""
        checkpoint_id = await storage.save_with_restore_point(
            simple_checkpoint,
            "before_migration",
        )

        loaded = await storage.load(checkpoint_id)
        assert loaded.metadata.get("restore_point_name") == "before_migration"

    @pytest.mark.asyncio
    async def test_load_by_type(self, storage):
        """Test loading by checkpoint type."""
        cp1 = HybridCheckpoint(session_id="sess_1", checkpoint_type=CheckpointType.AUTO)
        cp2 = HybridCheckpoint(session_id="sess_1", checkpoint_type=CheckpointType.HITL)
        cp3 = HybridCheckpoint(session_id="sess_1", checkpoint_type=CheckpointType.AUTO)

        await storage.save(cp1)
        await storage.save(cp2)
        await storage.save(cp3)

        results = await storage.load_by_type("sess_1", CheckpointType.AUTO)
        assert len(results) == 2
