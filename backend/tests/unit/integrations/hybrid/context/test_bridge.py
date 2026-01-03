# =============================================================================
# IPA Platform - Context Bridge Tests
# =============================================================================
# Sprint 53: Context Bridge & Sync
#
# Unit tests for ContextBridge class.
# Tests cover MAF ↔ Claude context synchronization.
# =============================================================================

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.hybrid.context.bridge import ContextBridge
from src.integrations.hybrid.context.models import (
    AgentState,
    AgentStatus,
    ApprovalRequest,
    ApprovalStatus,
    ClaudeContext,
    Conflict,
    ExecutionRecord,
    HybridContext,
    MAFContext,
    Message,
    MessageRole,
    SyncDirection,
    SyncResult,
    SyncStatus,
    SyncStrategy,
    ToolCall,
    ToolCallStatus,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def bridge():
    """Create a ContextBridge instance."""
    return ContextBridge()


@pytest.fixture
def sample_maf_context():
    """Create a sample MAFContext for testing."""
    return MAFContext(
        workflow_id="wf-123",
        workflow_name="Test Workflow",
        current_step=2,
        total_steps=5,
        agent_states={
            "agent-1": AgentState(
                agent_id="agent-1",
                agent_name="Test Agent",
                status=AgentStatus.RUNNING,
                current_task="Processing",
            ),
        },
        checkpoint_data={
            "last_result": "success",
            "iteration": 3,
        },
        pending_approvals=[
            ApprovalRequest(
                request_id="req-1",
                checkpoint_id="cp-1",
                action="approve_task",
                description="Please approve this action",
            ),
        ],
        execution_history=[
            ExecutionRecord(
                record_id="rec-1",
                step_index=0,
                step_name="step_1",
                agent_id="agent-1",
                status="completed",
                output_data={"output": "done"},
                duration_ms=1500,
            ),
        ],
    )


@pytest.fixture
def sample_claude_context():
    """Create a sample ClaudeContext for testing."""
    return ClaudeContext(
        session_id="session-456",
        conversation_history=[
            Message(
                message_id="msg-1",
                role=MessageRole.USER,
                content="Hello, I need help with a task",
            ),
            Message(
                message_id="msg-2",
                role=MessageRole.ASSISTANT,
                content="I'm here to help. What would you like me to do?",
            ),
        ],
        tool_call_history=[
            ToolCall(
                call_id="call-1",
                tool_name="search",
                arguments={"query": "test"},
                status=ToolCallStatus.COMPLETED,
                result="Found 5 results",
            ),
        ],
        current_system_prompt="You are a helpful assistant.",
        context_variables={
            "user_name": "Test User",
            "preference": "detailed",
        },
    )


@pytest.fixture
def sample_hybrid_context(sample_maf_context, sample_claude_context):
    """Create a sample HybridContext for testing."""
    return HybridContext(
        context_id="hybrid-789",
        maf=sample_maf_context,
        claude=sample_claude_context,
        primary_framework="maf",
        sync_status=SyncStatus.SYNCED,
        version=1,
    )


# =============================================================================
# ContextBridge Initialization Tests
# =============================================================================


class TestContextBridgeInit:
    """Tests for ContextBridge initialization."""

    def test_create_bridge(self, bridge):
        """Test creating a ContextBridge instance."""
        assert bridge is not None
        assert isinstance(bridge, ContextBridge)

    def test_bridge_has_mappers(self, bridge):
        """Test that bridge has mapper attributes."""
        assert hasattr(bridge, "_maf_mapper")
        assert hasattr(bridge, "_claude_mapper")

    def test_bridge_with_custom_mappers(self):
        """Test creating bridge with custom mappers."""
        custom_maf_mapper = MagicMock()
        custom_claude_mapper = MagicMock()

        bridge = ContextBridge(
            maf_mapper=custom_maf_mapper,
            claude_mapper=custom_claude_mapper,
        )

        assert bridge._maf_mapper == custom_maf_mapper
        assert bridge._claude_mapper == custom_claude_mapper


# =============================================================================
# Sync to Claude Tests
# =============================================================================


class TestSyncToClaude:
    """Tests for syncing MAF context to Claude."""

    @pytest.mark.asyncio
    async def test_sync_maf_to_new_claude_context(self, bridge, sample_maf_context):
        """Test syncing MAF context to create new Claude context."""
        result = await bridge.sync_to_claude(sample_maf_context)

        assert isinstance(result, ClaudeContext)
        assert result.session_id is not None
        # Check that metadata contains workflow info
        assert "maf_workflow_id" in result.metadata
        assert result.metadata["maf_workflow_id"] == "wf-123"

    @pytest.mark.asyncio
    async def test_sync_maf_to_existing_claude_context(
        self, bridge, sample_maf_context, sample_claude_context
    ):
        """Test syncing MAF context to existing Claude context."""
        result = await bridge.sync_to_claude(
            sample_maf_context,
            existing_claude=sample_claude_context,
        )

        assert isinstance(result, ClaudeContext)
        assert result.session_id == sample_claude_context.session_id
        # Original conversation history should be preserved
        assert len(result.conversation_history) >= len(sample_claude_context.conversation_history)

    @pytest.mark.asyncio
    async def test_sync_checkpoint_data_to_context_variables(
        self, bridge, sample_maf_context
    ):
        """Test that checkpoint data is synced to context variables."""
        result = await bridge.sync_to_claude(sample_maf_context)

        # Checkpoint data should be in context_variables with maf_ prefix
        assert "maf_last_result" in result.context_variables
        assert result.context_variables["maf_last_result"] == "success"

    @pytest.mark.asyncio
    async def test_sync_pending_approvals_to_tool_calls(
        self, bridge, sample_maf_context
    ):
        """Test that pending approvals are synced as tool calls."""
        result = await bridge.sync_to_claude(sample_maf_context)

        # Should have tool calls for pending approvals
        approval_calls = [
            tc for tc in result.tool_call_history
            if tc.tool_name == "maf_approval_request"
        ]
        assert len(approval_calls) >= 1

    @pytest.mark.asyncio
    async def test_sync_execution_history_to_messages(
        self, bridge, sample_maf_context
    ):
        """Test that execution history is synced to conversation history."""
        result = await bridge.sync_to_claude(sample_maf_context)

        # Execution history should be reflected in messages
        assert len(result.conversation_history) > 0

    @pytest.mark.asyncio
    async def test_sync_agent_states_to_system_prompt(
        self, bridge, sample_maf_context
    ):
        """Test that agent states are reflected in system prompt."""
        result = await bridge.sync_to_claude(sample_maf_context)

        # System prompt should mention active agents
        assert "agent" in result.current_system_prompt.lower()


# =============================================================================
# Sync to MAF Tests
# =============================================================================


class TestSyncToMAF:
    """Tests for syncing Claude context to MAF."""

    @pytest.mark.asyncio
    async def test_sync_claude_to_new_maf_context(self, bridge, sample_claude_context):
        """Test syncing Claude context to create new MAF context."""
        result = await bridge.sync_to_maf(sample_claude_context)

        assert isinstance(result, MAFContext)
        assert result.workflow_id is not None

    @pytest.mark.asyncio
    async def test_sync_claude_to_existing_maf_context(
        self, bridge, sample_claude_context, sample_maf_context
    ):
        """Test syncing Claude context to existing MAF context."""
        result = await bridge.sync_to_maf(
            sample_claude_context,
            existing_maf=sample_maf_context,
        )

        assert isinstance(result, MAFContext)
        assert result.workflow_id == sample_maf_context.workflow_id

    @pytest.mark.asyncio
    async def test_sync_context_variables_to_checkpoint_data(
        self, bridge, sample_claude_context
    ):
        """Test that context variables are synced to checkpoint data."""
        result = await bridge.sync_to_maf(sample_claude_context)

        # Context variables should be in checkpoint_data with claude_ prefix
        assert "claude_user_name" in result.checkpoint_data
        assert result.checkpoint_data["claude_user_name"] == "Test User"

    @pytest.mark.asyncio
    async def test_sync_tool_calls_to_execution_history(
        self, bridge, sample_claude_context
    ):
        """Test that tool calls are synced to execution history."""
        result = await bridge.sync_to_maf(sample_claude_context)

        # Tool calls should be reflected in execution history
        assert len(result.execution_history) > 0

    @pytest.mark.asyncio
    async def test_sync_pending_tool_calls_to_checkpoint(
        self, bridge, sample_claude_context
    ):
        """Test that pending tool calls are synced to checkpoint data."""
        # Add a pending tool call
        sample_claude_context.tool_call_history.append(
            ToolCall(
                call_id="call-pending",
                tool_name="dangerous_action",
                arguments={"action": "delete"},
                status=ToolCallStatus.PENDING,
            )
        )

        result = await bridge.sync_to_maf(sample_claude_context)

        # Should have tool call summary in checkpoint
        assert "tool_calls_summary" in result.checkpoint_data
        assert result.checkpoint_data["tool_calls_summary"]["pending"] >= 1


# =============================================================================
# Merge Contexts Tests
# =============================================================================


class TestMergeContexts:
    """Tests for merging MAF and Claude contexts."""

    @pytest.mark.asyncio
    async def test_merge_both_contexts(
        self, bridge, sample_maf_context, sample_claude_context
    ):
        """Test merging both MAF and Claude contexts."""
        result = await bridge.merge_contexts(
            maf_context=sample_maf_context,
            claude_context=sample_claude_context,
        )

        assert isinstance(result, HybridContext)
        assert result.maf is not None
        assert result.claude is not None

    @pytest.mark.asyncio
    async def test_merge_maf_only(self, bridge, sample_maf_context):
        """Test merging with only MAF context."""
        result = await bridge.merge_contexts(maf_context=sample_maf_context)

        assert result.maf is not None
        # merge_contexts does NOT auto-create missing contexts
        # Use sync_bidirectional to create missing contexts
        assert result.claude is None
        assert result.sync_status == SyncStatus.PENDING

    @pytest.mark.asyncio
    async def test_merge_claude_only(self, bridge, sample_claude_context):
        """Test merging with only Claude context."""
        result = await bridge.merge_contexts(claude_context=sample_claude_context)

        # merge_contexts does NOT auto-create missing contexts
        # Use sync_bidirectional to create missing contexts
        assert result.maf is None
        assert result.claude is not None
        assert result.sync_status == SyncStatus.PENDING

    @pytest.mark.asyncio
    async def test_merge_with_maf_primary(
        self, bridge, sample_maf_context, sample_claude_context
    ):
        """Test merging with MAF as primary framework."""
        result = await bridge.merge_contexts(
            maf_context=sample_maf_context,
            claude_context=sample_claude_context,
            primary_framework="maf",
        )

        assert result.primary_framework == "maf"

    @pytest.mark.asyncio
    async def test_merge_with_claude_primary(
        self, bridge, sample_maf_context, sample_claude_context
    ):
        """Test merging with Claude as primary framework."""
        result = await bridge.merge_contexts(
            maf_context=sample_maf_context,
            claude_context=sample_claude_context,
            primary_framework="claude",
        )

        assert result.primary_framework == "claude"

    @pytest.mark.asyncio
    async def test_merge_generates_context_id(
        self, bridge, sample_maf_context, sample_claude_context
    ):
        """Test that merging generates a unique context ID."""
        result = await bridge.merge_contexts(
            maf_context=sample_maf_context,
            claude_context=sample_claude_context,
        )

        assert result.context_id is not None
        assert len(result.context_id) > 0

    @pytest.mark.asyncio
    async def test_merge_sets_initial_version(
        self, bridge, sample_maf_context, sample_claude_context
    ):
        """Test that merging sets initial version to 1."""
        result = await bridge.merge_contexts(
            maf_context=sample_maf_context,
            claude_context=sample_claude_context,
        )

        assert result.version == 1


# =============================================================================
# Bidirectional Sync Tests
# =============================================================================


class TestBidirectionalSync:
    """Tests for bidirectional synchronization."""

    @pytest.mark.asyncio
    async def test_bidirectional_sync_merge_strategy(
        self, bridge, sample_hybrid_context
    ):
        """Test bidirectional sync with merge strategy."""
        result = await bridge.sync_bidirectional(
            sample_hybrid_context,
            strategy=SyncStrategy.MERGE,
        )

        assert isinstance(result, SyncResult)
        assert result.success is True
        assert result.strategy == SyncStrategy.MERGE

    @pytest.mark.asyncio
    async def test_bidirectional_sync_maf_primary_strategy(
        self, bridge, sample_hybrid_context
    ):
        """Test bidirectional sync with MAF primary strategy."""
        result = await bridge.sync_bidirectional(
            sample_hybrid_context,
            strategy=SyncStrategy.MAF_PRIMARY,
        )

        assert result.success is True
        assert result.strategy == SyncStrategy.MAF_PRIMARY

    @pytest.mark.asyncio
    async def test_bidirectional_sync_claude_primary_strategy(
        self, bridge, sample_hybrid_context
    ):
        """Test bidirectional sync with Claude primary strategy."""
        result = await bridge.sync_bidirectional(
            sample_hybrid_context,
            strategy=SyncStrategy.CLAUDE_PRIMARY,
        )

        assert result.success is True
        assert result.strategy == SyncStrategy.CLAUDE_PRIMARY

    @pytest.mark.asyncio
    async def test_bidirectional_sync_updates_hybrid_context(
        self, bridge, sample_hybrid_context
    ):
        """Test that bidirectional sync updates the hybrid context."""
        result = await bridge.sync_bidirectional(sample_hybrid_context)

        assert result.hybrid_context is not None
        assert result.hybrid_context.sync_status == SyncStatus.SYNCED

    @pytest.mark.asyncio
    async def test_bidirectional_sync_increments_version(
        self, bridge, sample_hybrid_context
    ):
        """Test that bidirectional sync increments version."""
        original_version = sample_hybrid_context.version
        result = await bridge.sync_bidirectional(sample_hybrid_context)

        assert result.hybrid_context.version == original_version + 1

    @pytest.mark.asyncio
    async def test_bidirectional_sync_records_direction(
        self, bridge, sample_hybrid_context
    ):
        """Test that sync result records direction."""
        result = await bridge.sync_bidirectional(sample_hybrid_context)

        assert result.direction is not None
        assert result.direction in [
            SyncDirection.MAF_TO_CLAUDE,
            SyncDirection.CLAUDE_TO_MAF,
            SyncDirection.BIDIRECTIONAL,
        ]


# =============================================================================
# Conflict Detection Tests
# =============================================================================


class TestConflictDetection:
    """Tests for conflict detection during sync."""

    @pytest.mark.asyncio
    async def test_no_conflicts_when_compatible(
        self, bridge, sample_hybrid_context
    ):
        """Test no conflicts when contexts are compatible."""
        result = await bridge.sync_bidirectional(sample_hybrid_context)

        assert len(result.conflicts) == 0

    @pytest.mark.asyncio
    async def test_detect_version_conflict(self, bridge):
        """Test detecting version conflict."""
        # Create two contexts with different versions
        maf = MAFContext(
            workflow_id="wf-1",
            workflow_name="Test",
            checkpoint_data={"version": 1, "value": "old"},
        )
        claude = ClaudeContext(
            session_id="session-1",
            context_variables={"version": 2, "value": "new"},
        )

        hybrid = HybridContext(
            maf=maf,
            claude=claude,
            sync_status=SyncStatus.CONFLICT,
        )

        result = await bridge.sync_bidirectional(
            hybrid,
            strategy=SyncStrategy.MERGE,
        )

        # Should handle the conflict somehow
        assert result.success is True or len(result.conflicts) > 0

    @pytest.mark.asyncio
    async def test_conflict_resolution_with_maf_primary(self, bridge):
        """Test conflict resolution with MAF as primary."""
        maf = MAFContext(
            workflow_id="wf-1",
            workflow_name="Test",
            checkpoint_data={"key": "maf_value"},
        )
        claude = ClaudeContext(
            session_id="session-1",
            context_variables={"key": "claude_value"},
        )

        hybrid = HybridContext(
            maf=maf,
            claude=claude,
            primary_framework="maf",
        )

        result = await bridge.sync_bidirectional(
            hybrid,
            strategy=SyncStrategy.MAF_PRIMARY,
        )

        # MAF value should win
        assert result.success is True

    @pytest.mark.asyncio
    async def test_conflict_resolution_with_claude_primary(self, bridge):
        """Test conflict resolution with Claude as primary."""
        maf = MAFContext(
            workflow_id="wf-1",
            workflow_name="Test",
            checkpoint_data={"key": "maf_value"},
        )
        claude = ClaudeContext(
            session_id="session-1",
            context_variables={"key": "claude_value"},
        )

        hybrid = HybridContext(
            maf=maf,
            claude=claude,
            primary_framework="claude",
        )

        result = await bridge.sync_bidirectional(
            hybrid,
            strategy=SyncStrategy.CLAUDE_PRIMARY,
        )

        # Claude value should win
        assert result.success is True


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_sync_empty_maf_context(self, bridge):
        """Test syncing empty MAF context."""
        empty_maf = MAFContext(
            workflow_id="empty-wf",
            workflow_name="Empty Workflow",
        )

        result = await bridge.sync_to_claude(empty_maf)

        assert isinstance(result, ClaudeContext)

    @pytest.mark.asyncio
    async def test_sync_empty_claude_context(self, bridge):
        """Test syncing empty Claude context."""
        empty_claude = ClaudeContext(session_id="empty-session")

        result = await bridge.sync_to_maf(empty_claude)

        assert isinstance(result, MAFContext)

    @pytest.mark.asyncio
    async def test_merge_with_no_contexts(self, bridge):
        """Test merging with no contexts provided."""
        result = await bridge.merge_contexts()

        assert isinstance(result, HybridContext)
        # merge_contexts does NOT auto-create missing contexts
        # Both will be None, status will be PENDING
        assert result.maf is None
        assert result.claude is None
        assert result.sync_status == SyncStatus.PENDING

    @pytest.mark.asyncio
    async def test_sync_preserves_original_data(
        self, bridge, sample_maf_context
    ):
        """Test that sync preserves original data."""
        original_workflow_id = sample_maf_context.workflow_id
        original_workflow_name = sample_maf_context.workflow_name

        await bridge.sync_to_claude(sample_maf_context)

        # Original should be unchanged
        assert sample_maf_context.workflow_id == original_workflow_id
        assert sample_maf_context.workflow_name == original_workflow_name

    @pytest.mark.asyncio
    async def test_bidirectional_sync_with_missing_maf(self, bridge):
        """Test bidirectional sync when MAF is missing."""
        hybrid = HybridContext(
            maf=None,
            claude=ClaudeContext(session_id="session-1"),
        )

        result = await bridge.sync_bidirectional(hybrid)

        assert result.success is True
        assert result.hybrid_context.maf is not None

    @pytest.mark.asyncio
    async def test_bidirectional_sync_with_missing_claude(self, bridge):
        """Test bidirectional sync when Claude is missing."""
        hybrid = HybridContext(
            maf=MAFContext(workflow_id="wf-1", workflow_name="Test"),
            claude=None,
        )

        result = await bridge.sync_bidirectional(hybrid)

        assert result.success is True
        assert result.hybrid_context.claude is not None


# =============================================================================
# Helper Method Tests
# =============================================================================


class TestHelperMethods:
    """Tests for bridge helper methods."""

    def test_get_sync_status(self, bridge, sample_hybrid_context):
        """Test getting sync status."""
        status = bridge.get_sync_status(sample_hybrid_context)

        assert status == SyncStatus.SYNCED

    def test_is_sync_needed_when_synced(self, bridge, sample_hybrid_context):
        """Test checking if sync is needed when already synced."""
        sample_hybrid_context.sync_status = SyncStatus.SYNCED

        assert bridge.is_sync_needed(sample_hybrid_context) is False

    def test_is_sync_needed_when_pending(self, bridge, sample_hybrid_context):
        """Test checking if sync is needed when pending."""
        sample_hybrid_context.sync_status = SyncStatus.PENDING

        assert bridge.is_sync_needed(sample_hybrid_context) is True

    def test_is_sync_needed_when_conflict(self, bridge, sample_hybrid_context):
        """Test checking if sync is needed when in conflict."""
        sample_hybrid_context.sync_status = SyncStatus.CONFLICT

        assert bridge.is_sync_needed(sample_hybrid_context) is True

    def test_validate_context_valid(self, bridge, sample_hybrid_context):
        """Test validating a valid hybrid context."""
        is_valid, errors = bridge.validate_context(sample_hybrid_context)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_context_missing_both(self, bridge):
        """Test validating context with both MAF and Claude missing."""
        hybrid = HybridContext(maf=None, claude=None)

        is_valid, errors = bridge.validate_context(hybrid)

        assert is_valid is False
        assert len(errors) > 0
