# =============================================================================
# IPA Platform - Context Synchronizer Tests
# =============================================================================
# Sprint 53: Context Bridge & Sync
#
# Unit tests for ContextSynchronizer class.
# =============================================================================

import pytest
import asyncio
from datetime import datetime
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.hybrid.context.sync.synchronizer import (
    ContextSynchronizer,
    SyncError,
    SyncTimeoutError,
    VersionConflictError,
)
from src.integrations.hybrid.context.sync.conflict import ConflictResolver
from src.integrations.hybrid.context.sync.events import SyncEventPublisher, SyncEvent
from src.integrations.hybrid.context.models import (
    ClaudeContext,
    Conflict,
    HybridContext,
    MAFContext,
    SyncDirection,
    SyncResult,
    SyncStrategy,
)


class TestContextSynchronizerInit:
    """Test ContextSynchronizer initialization."""

    def test_default_initialization(self):
        """Test default initialization."""
        sync = ContextSynchronizer()
        assert sync._max_retries == 3
        assert sync._timeout_ms == 30000
        assert sync._auto_resolve_conflicts is True
        assert isinstance(sync._conflict_resolver, ConflictResolver)
        assert isinstance(sync._event_publisher, SyncEventPublisher)

    def test_custom_initialization(self):
        """Test custom initialization."""
        resolver = ConflictResolver()
        publisher = SyncEventPublisher()

        sync = ContextSynchronizer(
            conflict_resolver=resolver,
            event_publisher=publisher,
            max_retries=5,
            timeout_ms=60000,
            auto_resolve_conflicts=False,
        )

        assert sync._conflict_resolver is resolver
        assert sync._event_publisher is publisher
        assert sync._max_retries == 5
        assert sync._timeout_ms == 60000
        assert sync._auto_resolve_conflicts is False


class TestSyncExceptions:
    """Test sync exception classes."""

    def test_sync_error(self):
        """Test SyncError exception."""
        error = SyncError("Test error", recoverable=True)
        assert str(error) == "Test error"
        assert error.recoverable is True

    def test_sync_error_non_recoverable(self):
        """Test non-recoverable SyncError."""
        error = SyncError("Fatal error", recoverable=False)
        assert error.recoverable is False

    def test_version_conflict_error(self):
        """Test VersionConflictError exception."""
        error = VersionConflictError(local_version=5, remote_version=8)
        assert error.local_version == 5
        assert error.remote_version == 8
        assert "5" in str(error)
        assert "8" in str(error)
        assert error.recoverable is True

    def test_sync_timeout_error(self):
        """Test SyncTimeoutError exception."""
        error = SyncTimeoutError(timeout_ms=30000)
        assert error.timeout_ms == 30000
        assert "30000" in str(error)
        assert error.recoverable is True


class TestSync:
    """Test sync operations."""

    @pytest.fixture
    def synchronizer(self):
        """Create synchronizer with mocked publisher."""
        publisher = SyncEventPublisher(enable_logging=False)
        return ContextSynchronizer(event_publisher=publisher)

    @pytest.fixture
    def hybrid_context(self) -> HybridContext:
        """Create test hybrid context."""
        return HybridContext(
            context_id="sess-123",
            version=1,
            maf=MAFContext(
                workflow_id="wf-1",
                workflow_name="Test Workflow",
                current_step=2,
                checkpoint_data={"key1": "value1"},
            ),
            claude=ClaudeContext(
                session_id="sess-123",
                context_variables={"claude_var": "test", "shared": "data"},
            ),
        )

    @pytest.mark.asyncio
    async def test_sync_to_maf(self, synchronizer, hybrid_context):
        """Test sync to MAF target."""
        result = await synchronizer.sync(
            source=hybrid_context,
            target_type="maf",
            strategy=SyncStrategy.MERGE,
        )

        assert result.success is True
        assert result.target_version == 2  # Incremented
        assert result.hybrid_context is not None
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_sync_to_claude(self, synchronizer, hybrid_context):
        """Test sync to Claude target."""
        result = await synchronizer.sync(
            source=hybrid_context,
            target_type="claude",
            strategy=SyncStrategy.MERGE,
        )

        assert result.success is True
        assert result.target_version == 2
        assert result.hybrid_context is not None

    @pytest.mark.asyncio
    async def test_sync_creates_maf_context_if_missing(self, synchronizer):
        """Test sync creates MAF context if missing."""
        context = HybridContext(
            context_id="sess-456",
            version=1,
            claude=ClaudeContext(
                session_id="sess-456",
                context_variables={"maf_key": "maf_value"},
            ),
        )

        result = await synchronizer.sync(
            source=context,
            target_type="maf",
            strategy=SyncStrategy.MERGE,
        )

        assert result.success is True
        assert result.hybrid_context.maf is not None
        assert result.hybrid_context.maf.workflow_id == "sess-456"

    @pytest.mark.asyncio
    async def test_sync_creates_claude_context_if_missing(self, synchronizer):
        """Test sync creates Claude context if missing."""
        context = HybridContext(
            context_id="sess-789",
            version=1,
            maf=MAFContext(
                workflow_id="wf-1",
                workflow_name="Test",
                checkpoint_data={"checkpoint_key": "value"},
            ),
        )

        result = await synchronizer.sync(
            source=context,
            target_type="claude",
            strategy=SyncStrategy.MERGE,
        )

        assert result.success is True
        assert result.hybrid_context.claude is not None
        # MAF data should be transferred with prefix
        assert "maf_workflow_id" in result.hybrid_context.claude.context_variables

    @pytest.mark.asyncio
    async def test_sync_updates_version_tracking(self, synchronizer, hybrid_context):
        """Test sync updates version tracking."""
        assert synchronizer.get_version(hybrid_context.context_id) == 0

        await synchronizer.sync(
            source=hybrid_context,
            target_type="maf",
            strategy=SyncStrategy.MERGE,
        )

        assert synchronizer.get_version(hybrid_context.context_id) == 2

    @pytest.mark.asyncio
    async def test_sync_saves_snapshot(self, synchronizer, hybrid_context):
        """Test sync saves snapshot for rollback."""
        await synchronizer.sync(
            source=hybrid_context,
            target_type="maf",
            strategy=SyncStrategy.MERGE,
        )

        snapshots = synchronizer.get_snapshots(hybrid_context.context_id)
        assert len(snapshots) == 1
        assert snapshots[0].version == 1


class TestSyncWithRetry:
    """Test sync retry behavior."""

    @pytest.mark.asyncio
    async def test_sync_retries_on_recoverable_error(self):
        """Test sync retries on recoverable error."""
        publisher = SyncEventPublisher(enable_logging=False)
        synchronizer = ContextSynchronizer(
            event_publisher=publisher,
            max_retries=3,
        )

        context = HybridContext(context_id="sess-123", version=1)

        # Mock _do_sync to fail twice then succeed
        call_count = 0

        async def mock_do_sync(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise SyncError("Temporary error", recoverable=True)
            return SyncResult(
                success=True,
                direction=SyncDirection.MAF_TO_CLAUDE,
                strategy=SyncStrategy.MERGE,
                hybrid_context=context,
                target_version=2,
                source_version=1,
                changes_applied=1,
            )

        with patch.object(synchronizer, "_do_sync", side_effect=mock_do_sync):
            result = await synchronizer.sync(
                source=context,
                target_type="maf",
                strategy=SyncStrategy.MERGE,
            )

            assert result.success is True
            assert call_count == 3

    @pytest.mark.asyncio
    async def test_sync_fails_on_non_recoverable_error(self):
        """Test sync fails on non-recoverable error."""
        publisher = SyncEventPublisher(enable_logging=False)
        synchronizer = ContextSynchronizer(event_publisher=publisher)

        context = HybridContext(context_id="sess-123", version=1)

        async def mock_do_sync(*args, **kwargs):
            raise SyncError("Fatal error", recoverable=False)

        with patch.object(synchronizer, "_do_sync", side_effect=mock_do_sync):
            result = await synchronizer.sync(
                source=context,
                target_type="maf",
                strategy=SyncStrategy.MERGE,
            )

            assert result.success is False
            assert "Fatal error" in result.error


class TestConflictDetection:
    """Test conflict detection."""

    @pytest.fixture
    def synchronizer(self):
        """Create synchronizer."""
        publisher = SyncEventPublisher(enable_logging=False)
        return ContextSynchronizer(event_publisher=publisher)

    @pytest.mark.asyncio
    async def test_detect_conflict_no_conflict(self, synchronizer):
        """Test no conflict detected for identical contexts."""
        context1 = HybridContext(context_id="sess-1", version=1)
        context2 = HybridContext(context_id="sess-1", version=1)

        conflict = await synchronizer.detect_conflict(context1, context2)
        assert conflict is None

    @pytest.mark.asyncio
    async def test_detect_conflict_version_mismatch(self, synchronizer):
        """Test conflict detected for version mismatch."""
        context1 = HybridContext(context_id="sess-1", version=5)
        context2 = HybridContext(context_id="sess-1", version=1)

        conflict = await synchronizer.detect_conflict(context1, context2)
        assert conflict is not None


class TestConflictResolution:
    """Test conflict resolution."""

    @pytest.fixture
    def synchronizer(self):
        """Create synchronizer."""
        publisher = SyncEventPublisher(enable_logging=False)
        return ContextSynchronizer(event_publisher=publisher)

    @pytest.fixture
    def local_context(self) -> HybridContext:
        """Create local context."""
        return HybridContext(
            context_id="sess-123",
            version=2,
            maf=MAFContext(
                workflow_id="wf-1",
                workflow_name="Local",
                current_step=3,
            ),
            claude=ClaudeContext(session_id="sess-123"),
        )

    @pytest.fixture
    def remote_context(self) -> HybridContext:
        """Create remote context."""
        return HybridContext(
            context_id="sess-123",
            version=3,
            maf=MAFContext(
                workflow_id="wf-1",
                workflow_name="Remote",
                current_step=5,
            ),
            claude=ClaudeContext(session_id="sess-123"),
        )

    @pytest.fixture
    def conflict(self) -> Conflict:
        """Create test conflict."""
        return Conflict(
            conflict_id="conflict-123",
            field_path="maf.current_step",
            local_value=3,
            remote_value=5,
            local_timestamp=datetime.utcnow(),
            remote_timestamp=datetime.utcnow(),
            resolution=SyncStrategy.MERGE.value,
        )

    @pytest.mark.asyncio
    async def test_resolve_conflict_success(
        self, synchronizer, local_context, remote_context, conflict
    ):
        """Test successful conflict resolution."""
        result = await synchronizer.resolve_conflict(
            local=local_context,
            remote=remote_context,
            conflict=conflict,
            strategy=SyncStrategy.MAF_PRIMARY,
        )

        assert result.success is True
        assert result.hybrid_context is not None

    @pytest.mark.asyncio
    async def test_resolve_conflict_uses_suggested_strategy(
        self, synchronizer, local_context, remote_context, conflict
    ):
        """Test resolution uses suggested strategy when none provided."""
        conflict.resolution = SyncStrategy.TARGET_WINS.value

        result = await synchronizer.resolve_conflict(
            local=local_context,
            remote=remote_context,
            conflict=conflict,
            strategy=None,  # Use suggested
        )

        assert result.success is True


class TestRollback:
    """Test rollback functionality."""

    @pytest.fixture
    def synchronizer(self):
        """Create synchronizer."""
        publisher = SyncEventPublisher(enable_logging=False)
        return ContextSynchronizer(event_publisher=publisher)

    @pytest.mark.asyncio
    async def test_rollback_no_snapshots(self, synchronizer):
        """Test rollback fails when no snapshots available."""
        result = await synchronizer.rollback(context_id="sess-new")

        assert result.success is False
        assert "No snapshots" in result.error

    @pytest.mark.asyncio
    async def test_rollback_to_latest(self, synchronizer):
        """Test rollback to latest snapshot."""
        # Create snapshots
        context1 = HybridContext(context_id="sess-123", version=1)
        context2 = HybridContext(context_id="sess-123", version=2)

        synchronizer._save_snapshot(context1)
        synchronizer._save_snapshot(context2)

        result = await synchronizer.rollback(context_id="sess-123")

        assert result.success is True
        assert result.target_version == 2
        assert result.hybrid_context is context2

    @pytest.mark.asyncio
    async def test_rollback_to_specific_version(self, synchronizer):
        """Test rollback to specific version."""
        # Create snapshots
        context1 = HybridContext(context_id="sess-123", version=1)
        context2 = HybridContext(context_id="sess-123", version=2)
        context3 = HybridContext(context_id="sess-123", version=3)

        synchronizer._save_snapshot(context1)
        synchronizer._save_snapshot(context2)
        synchronizer._save_snapshot(context3)

        result = await synchronizer.rollback(context_id="sess-123", to_version=2)

        assert result.success is True
        assert result.target_version == 2
        assert result.hybrid_context is context2

    @pytest.mark.asyncio
    async def test_rollback_version_not_found(self, synchronizer):
        """Test rollback fails when version not found."""
        context = HybridContext(context_id="sess-123", version=1)
        synchronizer._save_snapshot(context)

        result = await synchronizer.rollback(context_id="sess-123", to_version=99)

        assert result.success is False
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_rollback_updates_version_tracking(self, synchronizer):
        """Test rollback updates version tracking."""
        context = HybridContext(context_id="sess-123", version=5)
        synchronizer._save_snapshot(context)
        synchronizer._context_versions["sess-123"] = 10

        await synchronizer.rollback(context_id="sess-123")

        assert synchronizer.get_version("sess-123") == 5


class TestSnapshotManagement:
    """Test snapshot management."""

    @pytest.fixture
    def synchronizer(self):
        """Create synchronizer."""
        publisher = SyncEventPublisher(enable_logging=False)
        return ContextSynchronizer(event_publisher=publisher)

    def test_save_snapshot(self, synchronizer):
        """Test saving a snapshot."""
        context = HybridContext(context_id="sess-123", version=1)
        synchronizer._save_snapshot(context)

        snapshots = synchronizer.get_snapshots("sess-123")
        assert len(snapshots) == 1

    def test_snapshot_limit_enforced(self, synchronizer):
        """Test snapshot limit is enforced."""
        for i in range(10):
            context = HybridContext(context_id="sess-123", version=i)
            synchronizer._save_snapshot(context)

        snapshots = synchronizer.get_snapshots("sess-123")
        assert len(snapshots) == 5  # Max snapshots

    def test_get_snapshots_returns_copy(self, synchronizer):
        """Test get_snapshots returns a copy."""
        context = HybridContext(context_id="sess-123", version=1)
        synchronizer._save_snapshot(context)

        snapshots1 = synchronizer.get_snapshots("sess-123")
        snapshots2 = synchronizer.get_snapshots("sess-123")

        assert snapshots1 is not snapshots2

    def test_clear_snapshots(self, synchronizer):
        """Test clearing snapshots."""
        context = HybridContext(context_id="sess-123", version=1)
        synchronizer._save_snapshot(context)

        synchronizer.clear_snapshots("sess-123")

        assert len(synchronizer.get_snapshots("sess-123")) == 0


class TestEventPublishing:
    """Test event publishing during sync operations."""

    @pytest.mark.asyncio
    async def test_sync_publishes_started_and_completed_events(self):
        """Test sync publishes started and completed events."""
        publisher = SyncEventPublisher(enable_logging=False)
        events: List[SyncEvent] = []

        async def handler(event):
            events.append(event)

        publisher.subscribe(handler)

        synchronizer = ContextSynchronizer(event_publisher=publisher)
        context = HybridContext(
            context_id="sess-123",
            version=1,
            maf=MAFContext(
                workflow_id="wf-1",
                workflow_name="Test",
                current_step=1,
            ),
        )

        await synchronizer.sync(
            source=context,
            target_type="maf",
            strategy=SyncStrategy.MERGE,
        )

        event_types = [e.event_type.value for e in events]
        assert "sync_started" in event_types
        assert "sync_completed" in event_types
        assert "version_updated" in event_types

    @pytest.mark.asyncio
    async def test_sync_failure_publishes_failed_event(self):
        """Test sync failure publishes failed event."""
        publisher = SyncEventPublisher(enable_logging=False)
        events: List[SyncEvent] = []

        async def handler(event):
            events.append(event)

        publisher.subscribe(handler)

        synchronizer = ContextSynchronizer(event_publisher=publisher)
        context = HybridContext(context_id="sess-123", version=1)

        async def mock_do_sync(*args, **kwargs):
            raise Exception("Unexpected error")

        with patch.object(synchronizer, "_do_sync", side_effect=mock_do_sync):
            await synchronizer.sync(
                source=context,
                target_type="maf",
                strategy=SyncStrategy.MERGE,
            )

        event_types = [e.event_type.value for e in events]
        assert "sync_started" in event_types
        assert "sync_failed" in event_types

    @pytest.mark.asyncio
    async def test_rollback_publishes_events(self):
        """Test rollback publishes rollback events."""
        publisher = SyncEventPublisher(enable_logging=False)
        events: List[SyncEvent] = []

        async def handler(event):
            events.append(event)

        publisher.subscribe(handler)

        synchronizer = ContextSynchronizer(event_publisher=publisher)
        context = HybridContext(context_id="sess-123", version=5)
        synchronizer._save_snapshot(context)
        synchronizer._context_versions["sess-123"] = 10

        await synchronizer.rollback(context_id="sess-123")

        event_types = [e.event_type.value for e in events]
        assert "rollback_started" in event_types
        assert "rollback_completed" in event_types


class TestProperties:
    """Test synchronizer properties."""

    def test_event_publisher_property(self):
        """Test event_publisher property."""
        publisher = SyncEventPublisher()
        synchronizer = ContextSynchronizer(event_publisher=publisher)

        assert synchronizer.event_publisher is publisher

    def test_conflict_resolver_property(self):
        """Test conflict_resolver property."""
        resolver = ConflictResolver()
        synchronizer = ContextSynchronizer(conflict_resolver=resolver)

        assert synchronizer.conflict_resolver is resolver
