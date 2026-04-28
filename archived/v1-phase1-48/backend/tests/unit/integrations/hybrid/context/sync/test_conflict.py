# =============================================================================
# IPA Platform - Conflict Resolver Tests
# =============================================================================
# Sprint 53: Context Bridge & Sync
#
# Unit tests for ConflictResolver class.
# =============================================================================

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any

from src.integrations.hybrid.context.sync.conflict import (
    ConflictResolver,
    ConflictSeverity,
    ConflictType,
)
from src.integrations.hybrid.context.models import (
    ClaudeContext,
    Conflict,
    HybridContext,
    MAFContext,
    SyncStrategy,
)


class TestConflictResolverInit:
    """Test ConflictResolver initialization."""

    def test_default_initialization(self):
        """Test default initialization."""
        resolver = ConflictResolver()
        assert resolver.default_strategy == SyncStrategy.MERGE
        assert resolver.auto_resolve_threshold == ConflictSeverity.MEDIUM

    def test_custom_initialization(self):
        """Test custom initialization."""
        resolver = ConflictResolver(
            default_strategy=SyncStrategy.MAF_PRIMARY,
            auto_resolve_threshold=ConflictSeverity.LOW,
        )
        assert resolver.default_strategy == SyncStrategy.MAF_PRIMARY
        assert resolver.auto_resolve_threshold == ConflictSeverity.LOW


class TestDetectConflicts:
    """Test conflict detection."""

    @pytest.fixture
    def local_context(self) -> HybridContext:
        """Create local context."""
        return HybridContext(
            context_id="sess-123",
            version=1,
            maf=MAFContext(
                workflow_id="wf-1",
                workflow_name="Test",
                current_step=3,
            ),
            claude=ClaudeContext(
                session_id="sess-123",
                context_variables={"key1": "local_value"},
            ),
            last_sync_at=datetime(2025, 1, 1, 12, 0, 0),
        )

    @pytest.fixture
    def remote_context(self) -> HybridContext:
        """Create remote context."""
        return HybridContext(
            context_id="sess-123",
            version=1,
            maf=MAFContext(
                workflow_id="wf-1",
                workflow_name="Test",
                current_step=3,
            ),
            claude=ClaudeContext(
                session_id="sess-123",
                context_variables={"key1": "local_value"},
            ),
            last_sync_at=datetime(2025, 1, 1, 12, 0, 0),
        )

    def test_no_conflict_same_contexts(self, local_context, remote_context):
        """Test no conflict when contexts are identical."""
        resolver = ConflictResolver()
        conflict = resolver.detect_conflicts(local_context, remote_context)
        assert conflict is None

    def test_version_mismatch_conflict(self, local_context, remote_context):
        """Test version mismatch detection."""
        local_context.version = 5
        remote_context.version = 2  # Big gap

        resolver = ConflictResolver()
        conflict = resolver.detect_conflicts(local_context, remote_context)

        assert conflict is not None
        assert conflict.field_path == "version"

    def test_concurrent_update_conflict(self, local_context, remote_context):
        """Test concurrent update detection."""
        local_context.last_sync_at = datetime(2025, 1, 1, 12, 0, 0)
        remote_context.last_sync_at = datetime(2025, 1, 1, 12, 1, 0)

        # Change values in both
        local_context.maf.current_step = 4
        remote_context.maf.current_step = 5

        resolver = ConflictResolver()
        conflict = resolver.detect_conflicts(local_context, remote_context)

        assert conflict is not None

    def test_context_variable_conflict(self, local_context, remote_context):
        """Test context variable conflict detection."""
        local_context.claude.context_variables = {"key1": "value1", "key2": "value2"}
        remote_context.claude.context_variables = {"key1": "different", "key2": "value2"}
        local_context.last_sync_at = datetime(2025, 1, 1, 12, 0, 0)
        remote_context.last_sync_at = datetime(2025, 1, 1, 12, 1, 0)

        resolver = ConflictResolver()
        conflict = resolver.detect_conflicts(local_context, remote_context)

        assert conflict is not None
        assert "key1" in conflict.field_path or "vars" in conflict.field_path


class TestResolveConflict:
    """Test conflict resolution."""

    @pytest.fixture
    def local_context(self) -> HybridContext:
        """Create local context."""
        return HybridContext(
            context_id="sess-123",
            version=2,
            maf=MAFContext(
                workflow_id="wf-1",
                workflow_name="Local Workflow",
                current_step=3,
                checkpoint_data={"local_key": "local_value"},
            ),
            claude=ClaudeContext(
                session_id="sess-123",
                context_variables={"claude_var": "local"},
            ),
        )

    @pytest.fixture
    def remote_context(self) -> HybridContext:
        """Create remote context."""
        return HybridContext(
            context_id="sess-123",
            version=3,
            maf=MAFContext(
                workflow_id="wf-1",
                workflow_name="Remote Workflow",
                current_step=5,
                checkpoint_data={"remote_key": "remote_value"},
            ),
            claude=ClaudeContext(
                session_id="sess-123",
                context_variables={"claude_var": "remote"},
            ),
        )

    @pytest.fixture
    def sample_conflict(self) -> Conflict:
        """Create sample conflict."""
        return Conflict(
            conflict_id="conflict-123",
            field_path="maf.current_step",
            local_value=3,
            remote_value=5,
            local_timestamp=datetime.utcnow(),
            remote_timestamp=datetime.utcnow(),
        )

    def test_resolve_source_wins(self, sample_conflict, local_context, remote_context):
        """Test SOURCE_WINS resolution."""
        resolver = ConflictResolver()
        resolved = resolver.resolve(
            conflict=sample_conflict,
            local=local_context,
            remote=remote_context,
            strategy=SyncStrategy.SOURCE_WINS,
        )

        assert resolved.maf.workflow_name == "Local Workflow"
        assert resolved.version > max(local_context.version, remote_context.version)

    def test_resolve_target_wins(self, sample_conflict, local_context, remote_context):
        """Test TARGET_WINS resolution."""
        resolver = ConflictResolver()
        resolved = resolver.resolve(
            conflict=sample_conflict,
            local=local_context,
            remote=remote_context,
            strategy=SyncStrategy.TARGET_WINS,
        )

        assert resolved.maf.workflow_name == "Remote Workflow"
        assert resolved.version > max(local_context.version, remote_context.version)

    def test_resolve_maf_primary(self, sample_conflict, local_context, remote_context):
        """Test MAF_PRIMARY resolution."""
        resolver = ConflictResolver()
        resolved = resolver.resolve(
            conflict=sample_conflict,
            local=local_context,
            remote=remote_context,
            strategy=SyncStrategy.MAF_PRIMARY,
        )

        # Local MAF should be used
        assert resolved.maf.workflow_name == "Local Workflow"
        # Remote Claude should be used
        assert resolved.claude.context_variables["claude_var"] == "remote"

    def test_resolve_claude_primary(self, sample_conflict, local_context, remote_context):
        """Test CLAUDE_PRIMARY resolution."""
        resolver = ConflictResolver()
        resolved = resolver.resolve(
            conflict=sample_conflict,
            local=local_context,
            remote=remote_context,
            strategy=SyncStrategy.CLAUDE_PRIMARY,
        )

        # Remote MAF should be used
        assert resolved.maf.workflow_name == "Remote Workflow"
        # Local Claude should be used
        assert resolved.claude.context_variables["claude_var"] == "local"

    def test_resolve_merge(self, sample_conflict, local_context, remote_context):
        """Test MERGE resolution."""
        resolver = ConflictResolver()
        resolved = resolver.resolve(
            conflict=sample_conflict,
            local=local_context,
            remote=remote_context,
            strategy=SyncStrategy.MERGE,
        )

        # Should use more advanced state (higher step)
        assert resolved.maf.current_step == 5

    def test_resolve_manual_returns_local(self, sample_conflict, local_context, remote_context):
        """Test MANUAL resolution returns local context."""
        resolver = ConflictResolver()
        resolved = resolver.resolve(
            conflict=sample_conflict,
            local=local_context,
            remote=remote_context,
            strategy=SyncStrategy.MANUAL,
        )

        assert resolved.context_id == local_context.context_id


class TestMergeContexts:
    """Test context merging."""

    def test_merge_maf_contexts_uses_more_advanced(self):
        """Test MAF merge uses more advanced state."""
        resolver = ConflictResolver()

        local_maf = MAFContext(
            workflow_id="wf-1",
            workflow_name="Test",
            current_step=3,
            total_steps=10,
        )

        remote_maf = MAFContext(
            workflow_id="wf-1",
            workflow_name="Test",
            current_step=7,
            total_steps=10,
        )

        merged = resolver._merge_maf_contexts(local_maf, remote_maf)

        assert merged.current_step == 7  # Remote is ahead

    def test_merge_maf_contexts_merges_checkpoint_data(self):
        """Test checkpoint data is merged."""
        resolver = ConflictResolver()

        local_maf = MAFContext(
            workflow_id="wf-1",
            workflow_name="Test",
            current_step=5,
            checkpoint_data={"local_key": "local_value"},
        )

        remote_maf = MAFContext(
            workflow_id="wf-1",
            workflow_name="Test",
            current_step=3,
            checkpoint_data={"remote_key": "remote_value"},
        )

        merged = resolver._merge_maf_contexts(local_maf, remote_maf)

        # Local is ahead, but checkpoint data should be merged
        assert "local_key" in merged.checkpoint_data
        # Remote checkpoint should also be present (merged in)
        assert "remote_key" in merged.checkpoint_data

    def test_merge_claude_contexts_uses_more_messages(self):
        """Test Claude merge uses context with more messages."""
        resolver = ConflictResolver()
        from src.integrations.hybrid.context.models import Message, MessageRole

        local_claude = ClaudeContext(
            session_id="sess-1",
            conversation_history=[
                Message(
                    message_id="1",
                    role=MessageRole.USER,
                    content="Hello",
                    timestamp=datetime.utcnow(),
                )
            ],
        )

        remote_claude = ClaudeContext(
            session_id="sess-1",
            conversation_history=[
                Message(
                    message_id="1",
                    role=MessageRole.USER,
                    content="Hello",
                    timestamp=datetime.utcnow(),
                ),
                Message(
                    message_id="2",
                    role=MessageRole.ASSISTANT,
                    content="Hi!",
                    timestamp=datetime.utcnow(),
                ),
            ],
        )

        merged = resolver._merge_claude_contexts(local_claude, remote_claude)

        assert len(merged.conversation_history) == 2  # Remote has more


class TestCanAutoResolve:
    """Test auto-resolve capability."""

    def test_can_auto_resolve_simple_fields(self):
        """Test simple fields can be auto-resolved."""
        resolver = ConflictResolver()
        conflict = Conflict(
            conflict_id="c-1",
            field_path="version",
            local_value=1,
            remote_value=2,
        )

        assert resolver.can_auto_resolve(conflict) is True

    def test_can_auto_resolve_already_resolved(self):
        """Test already resolved conflict."""
        resolver = ConflictResolver()
        conflict = Conflict(
            conflict_id="c-1",
            field_path="field1",
            local_value=1,
            remote_value=2,
            resolved=True,
        )

        assert resolver.can_auto_resolve(conflict) is True

    def test_can_auto_resolve_with_strategy(self):
        """Test conflict with non-manual resolution strategy."""
        resolver = ConflictResolver()
        conflict = Conflict(
            conflict_id="c-1",
            field_path="field1",
            local_value=1,
            remote_value=2,
            resolution=SyncStrategy.MERGE.value,
        )

        assert resolver.can_auto_resolve(conflict) is True


class TestConflictHistory:
    """Test conflict history tracking."""

    def test_conflict_history_tracked(self):
        """Test conflicts are added to history."""
        resolver = ConflictResolver()

        local = HybridContext(
            context_id="sess-1",
            version=5,
        )
        remote = HybridContext(
            context_id="sess-1",
            version=1,
        )

        conflict = resolver.detect_conflicts(local, remote)

        history = resolver.get_conflict_history()
        assert len(history) > 0

    def test_clear_conflict_history(self):
        """Test clearing conflict history."""
        resolver = ConflictResolver()

        local = HybridContext(
            context_id="sess-1",
            version=5,
        )
        remote = HybridContext(
            context_id="sess-1",
            version=1,
        )

        resolver.detect_conflicts(local, remote)
        resolver.clear_conflict_history()

        assert len(resolver.get_conflict_history()) == 0
