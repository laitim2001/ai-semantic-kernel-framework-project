# =============================================================================
# IPA Platform - Context Models Unit Tests
# =============================================================================
# Sprint 53: Context Bridge & Sync
#
# Unit tests for context data models.
# =============================================================================

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

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
# Test: Enums
# =============================================================================


class TestEnums:
    """Tests for enum types."""

    def test_sync_status_values(self):
        """Test SyncStatus enum values."""
        assert SyncStatus.SYNCED.value == "synced"
        assert SyncStatus.PENDING.value == "pending"
        assert SyncStatus.CONFLICT.value == "conflict"
        assert SyncStatus.SYNCING.value == "syncing"
        assert SyncStatus.FAILED.value == "failed"

    def test_sync_direction_values(self):
        """Test SyncDirection enum values."""
        assert SyncDirection.MAF_TO_CLAUDE.value == "maf_to_claude"
        assert SyncDirection.CLAUDE_TO_MAF.value == "claude_to_maf"
        assert SyncDirection.BIDIRECTIONAL.value == "bidirectional"

    def test_sync_strategy_values(self):
        """Test SyncStrategy enum values."""
        assert SyncStrategy.MERGE.value == "merge"
        assert SyncStrategy.SOURCE_WINS.value == "source_wins"
        assert SyncStrategy.TARGET_WINS.value == "target_wins"
        assert SyncStrategy.MANUAL.value == "manual"

    def test_agent_status_values(self):
        """Test AgentStatus enum values."""
        assert AgentStatus.IDLE.value == "idle"
        assert AgentStatus.RUNNING.value == "running"
        assert AgentStatus.WAITING.value == "waiting"
        assert AgentStatus.COMPLETED.value == "completed"
        assert AgentStatus.FAILED.value == "failed"

    def test_message_role_values(self):
        """Test MessageRole enum values."""
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"
        assert MessageRole.SYSTEM.value == "system"
        assert MessageRole.TOOL.value == "tool"

    def test_tool_call_status_values(self):
        """Test ToolCallStatus enum values."""
        assert ToolCallStatus.PENDING.value == "pending"
        assert ToolCallStatus.EXECUTING.value == "executing"
        assert ToolCallStatus.COMPLETED.value == "completed"
        assert ToolCallStatus.FAILED.value == "failed"
        assert ToolCallStatus.CANCELLED.value == "cancelled"


# =============================================================================
# Test: AgentState
# =============================================================================


class TestAgentState:
    """Tests for AgentState dataclass."""

    def test_create_agent_state(self):
        """Test creating AgentState."""
        state = AgentState(
            agent_id="agent-1",
            agent_name="Test Agent",
        )
        assert state.agent_id == "agent-1"
        assert state.agent_name == "Test Agent"
        assert state.status == AgentStatus.IDLE
        assert state.current_task is None

    def test_agent_state_with_task(self):
        """Test AgentState with current task."""
        state = AgentState(
            agent_id="agent-1",
            agent_name="Worker",
            status=AgentStatus.RUNNING,
            current_task="Processing data",
            last_output="50% complete",
        )
        assert state.status == AgentStatus.RUNNING
        assert state.current_task == "Processing data"
        assert state.last_output == "50% complete"

    def test_agent_state_to_dict(self):
        """Test AgentState serialization."""
        state = AgentState(
            agent_id="agent-1",
            agent_name="Test",
            status=AgentStatus.COMPLETED,
        )
        data = state.to_dict()
        assert data["agent_id"] == "agent-1"
        assert data["agent_name"] == "Test"
        assert data["status"] == "completed"
        assert "updated_at" in data

    def test_agent_state_from_dict(self):
        """Test AgentState deserialization."""
        data = {
            "agent_id": "agent-2",
            "agent_name": "Restored Agent",
            "status": "running",
            "current_task": "Analyzing",
            "metadata": {"key": "value"},
            "updated_at": "2026-01-01T10:00:00",
        }
        state = AgentState.from_dict(data)
        assert state.agent_id == "agent-2"
        assert state.status == AgentStatus.RUNNING
        assert state.metadata["key"] == "value"


# =============================================================================
# Test: ApprovalRequest
# =============================================================================


class TestApprovalRequest:
    """Tests for ApprovalRequest dataclass."""

    def test_create_approval_request(self):
        """Test creating ApprovalRequest."""
        request = ApprovalRequest(
            request_id="req-1",
            checkpoint_id="cp-1",
            action="delete_file",
            description="Delete sensitive file",
        )
        assert request.request_id == "req-1"
        assert request.status == ApprovalStatus.PENDING
        assert request.timeout_seconds == 3600

    def test_approval_request_approved(self):
        """Test approved ApprovalRequest."""
        request = ApprovalRequest(
            request_id="req-1",
            checkpoint_id="cp-1",
            action="deploy",
            description="Deploy to production",
            status=ApprovalStatus.APPROVED,
            responded_at=datetime.utcnow(),
            response_by="admin@example.com",
        )
        assert request.status == ApprovalStatus.APPROVED
        assert request.response_by == "admin@example.com"

    def test_approval_request_serialization(self):
        """Test ApprovalRequest round-trip."""
        original = ApprovalRequest(
            request_id="req-1",
            checkpoint_id="cp-1",
            action="approve_purchase",
            description="Approve $1000 purchase",
            metadata={"amount": 1000},
        )
        data = original.to_dict()
        restored = ApprovalRequest.from_dict(data)
        assert restored.request_id == original.request_id
        assert restored.action == original.action
        assert restored.metadata["amount"] == 1000


# =============================================================================
# Test: ExecutionRecord
# =============================================================================


class TestExecutionRecord:
    """Tests for ExecutionRecord dataclass."""

    def test_create_execution_record(self):
        """Test creating ExecutionRecord."""
        record = ExecutionRecord(
            record_id="rec-1",
            step_index=0,
            step_name="Initialize",
            agent_id="agent-1",
        )
        assert record.record_id == "rec-1"
        assert record.step_index == 0
        assert record.status == "completed"

    def test_execution_record_with_data(self):
        """Test ExecutionRecord with input/output data."""
        record = ExecutionRecord(
            record_id="rec-2",
            step_index=1,
            step_name="Process",
            agent_id="processor",
            input_data={"file": "data.csv"},
            output_data={"rows_processed": 1000},
            duration_ms=250,
        )
        assert record.input_data["file"] == "data.csv"
        assert record.output_data["rows_processed"] == 1000
        assert record.duration_ms == 250

    def test_execution_record_with_error(self):
        """Test ExecutionRecord with error."""
        record = ExecutionRecord(
            record_id="rec-3",
            step_index=2,
            step_name="Validate",
            agent_id="validator",
            status="failed",
            error="Validation failed: invalid format",
        )
        assert record.status == "failed"
        assert "invalid format" in record.error


# =============================================================================
# Test: Message
# =============================================================================


class TestMessage:
    """Tests for Message dataclass."""

    def test_create_user_message(self):
        """Test creating user message."""
        msg = Message(
            message_id="msg-1",
            role=MessageRole.USER,
            content="Hello, how can you help?",
        )
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello, how can you help?"

    def test_create_assistant_message(self):
        """Test creating assistant message."""
        msg = Message(
            message_id="msg-2",
            role=MessageRole.ASSISTANT,
            content="I can help you with many tasks.",
            metadata={"tokens": 15},
        )
        assert msg.role == MessageRole.ASSISTANT
        assert msg.metadata["tokens"] == 15

    def test_message_serialization(self):
        """Test Message round-trip."""
        original = Message(
            message_id="msg-1",
            role=MessageRole.SYSTEM,
            content="You are a helpful assistant.",
        )
        data = original.to_dict()
        restored = Message.from_dict(data)
        assert restored.message_id == original.message_id
        assert restored.role == MessageRole.SYSTEM
        assert restored.content == original.content


# =============================================================================
# Test: ToolCall
# =============================================================================


class TestToolCall:
    """Tests for ToolCall dataclass."""

    def test_create_tool_call(self):
        """Test creating ToolCall."""
        call = ToolCall(
            call_id="call-1",
            tool_name="search_database",
            arguments={"query": "user data"},
        )
        assert call.tool_name == "search_database"
        assert call.status == ToolCallStatus.PENDING
        assert call.arguments["query"] == "user data"

    def test_completed_tool_call(self):
        """Test completed ToolCall."""
        call = ToolCall(
            call_id="call-2",
            tool_name="calculate",
            arguments={"expression": "2 + 2"},
            result=4,
            status=ToolCallStatus.COMPLETED,
            duration_ms=5,
        )
        assert call.result == 4
        assert call.status == ToolCallStatus.COMPLETED
        assert call.duration_ms == 5

    def test_failed_tool_call(self):
        """Test failed ToolCall."""
        call = ToolCall(
            call_id="call-3",
            tool_name="external_api",
            arguments={"endpoint": "/data"},
            status=ToolCallStatus.FAILED,
            error="Connection timeout",
        )
        assert call.status == ToolCallStatus.FAILED
        assert "timeout" in call.error.lower()


# =============================================================================
# Test: MAFContext
# =============================================================================


class TestMAFContext:
    """Tests for MAFContext dataclass."""

    def test_create_maf_context(self):
        """Test creating MAFContext."""
        ctx = MAFContext(
            workflow_id="wf-1",
            workflow_name="Data Processing",
        )
        assert ctx.workflow_id == "wf-1"
        assert ctx.current_step == 0
        assert ctx.total_steps == 0
        assert len(ctx.agent_states) == 0

    def test_maf_context_with_progress(self):
        """Test MAFContext with progress."""
        ctx = MAFContext(
            workflow_id="wf-1",
            workflow_name="Pipeline",
            current_step=3,
            total_steps=5,
        )
        assert ctx.get_progress_percentage() == 60.0

    def test_maf_context_with_agents(self):
        """Test MAFContext with agent states."""
        agent1 = AgentState(agent_id="a1", agent_name="Fetcher", status=AgentStatus.RUNNING)
        agent2 = AgentState(agent_id="a2", agent_name="Processor", status=AgentStatus.WAITING)

        ctx = MAFContext(
            workflow_id="wf-1",
            workflow_name="ETL",
            agent_states={"a1": agent1, "a2": agent2},
        )

        active = ctx.get_active_agents()
        assert len(active) == 2
        assert all(a.status in (AgentStatus.RUNNING, AgentStatus.WAITING) for a in active)

    def test_maf_context_has_pending_approvals(self):
        """Test MAFContext pending approvals check."""
        approval = ApprovalRequest(
            request_id="req-1",
            checkpoint_id="cp-1",
            action="deploy",
            description="Deploy to prod",
        )
        ctx = MAFContext(
            workflow_id="wf-1",
            workflow_name="Deploy",
            pending_approvals=[approval],
        )
        assert ctx.has_pending_approvals()

    def test_maf_context_serialization(self):
        """Test MAFContext round-trip."""
        original = MAFContext(
            workflow_id="wf-1",
            workflow_name="Test Workflow",
            current_step=2,
            total_steps=5,
            checkpoint_data={"key": "value"},
        )
        data = original.to_dict()
        restored = MAFContext.from_dict(data)

        assert restored.workflow_id == original.workflow_id
        assert restored.current_step == 2
        assert restored.checkpoint_data["key"] == "value"


# =============================================================================
# Test: ClaudeContext
# =============================================================================


class TestClaudeContext:
    """Tests for ClaudeContext dataclass."""

    def test_create_claude_context(self):
        """Test creating ClaudeContext."""
        ctx = ClaudeContext(session_id="session-1")
        assert ctx.session_id == "session-1"
        assert len(ctx.conversation_history) == 0
        assert ctx.current_system_prompt == ""

    def test_claude_context_with_history(self):
        """Test ClaudeContext with conversation history."""
        messages = [
            Message(message_id="m1", role=MessageRole.USER, content="Hello"),
            Message(message_id="m2", role=MessageRole.ASSISTANT, content="Hi there!"),
        ]
        ctx = ClaudeContext(
            session_id="session-1",
            conversation_history=messages,
        )
        assert ctx.get_message_count() == 2
        assert ctx.get_last_message().content == "Hi there!"

    def test_claude_context_with_tool_calls(self):
        """Test ClaudeContext with tool calls."""
        calls = [
            ToolCall(call_id="c1", tool_name="search", status=ToolCallStatus.COMPLETED),
            ToolCall(call_id="c2", tool_name="calculate", status=ToolCallStatus.PENDING),
        ]
        ctx = ClaudeContext(
            session_id="session-1",
            tool_call_history=calls,
        )
        assert ctx.get_tool_call_count() == 2
        pending = ctx.get_pending_tool_calls()
        assert len(pending) == 1
        assert pending[0].tool_name == "calculate"

    def test_claude_context_serialization(self):
        """Test ClaudeContext round-trip."""
        original = ClaudeContext(
            session_id="session-1",
            current_system_prompt="You are helpful.",
            context_variables={"user_name": "Alice"},
            active_hooks=["logging", "validation"],
        )
        data = original.to_dict()
        restored = ClaudeContext.from_dict(data)

        assert restored.session_id == original.session_id
        assert restored.current_system_prompt == "You are helpful."
        assert restored.context_variables["user_name"] == "Alice"
        assert len(restored.active_hooks) == 2


# =============================================================================
# Test: HybridContext
# =============================================================================


class TestHybridContext:
    """Tests for HybridContext dataclass."""

    def test_create_hybrid_context(self):
        """Test creating HybridContext."""
        ctx = HybridContext()
        assert ctx.maf is None
        assert ctx.claude is None
        assert ctx.sync_status == SyncStatus.PENDING
        assert ctx.version == 1

    def test_hybrid_context_with_maf(self):
        """Test HybridContext with MAF context."""
        maf = MAFContext(workflow_id="wf-1", workflow_name="Test")
        ctx = HybridContext(maf=maf, primary_framework="maf")

        assert ctx.maf is not None
        assert ctx.get_session_id() == "wf-1"
        assert ctx.primary_framework == "maf"

    def test_hybrid_context_with_claude(self):
        """Test HybridContext with Claude context."""
        claude = ClaudeContext(session_id="session-1")
        ctx = HybridContext(claude=claude, primary_framework="claude")

        assert ctx.claude is not None
        assert ctx.get_session_id() == "session-1"

    def test_hybrid_context_both_frameworks(self):
        """Test HybridContext with both frameworks."""
        maf = MAFContext(workflow_id="wf-1", workflow_name="Test")
        claude = ClaudeContext(session_id="session-1")

        ctx = HybridContext(
            maf=maf,
            claude=claude,
            sync_status=SyncStatus.SYNCED,
        )

        assert ctx.is_synced()
        assert not ctx.has_conflict()

    def test_hybrid_context_increment_version(self):
        """Test HybridContext version increment."""
        ctx = HybridContext()
        assert ctx.version == 1

        ctx.increment_version()
        assert ctx.version == 2

    def test_hybrid_context_conflict_status(self):
        """Test HybridContext with conflict."""
        ctx = HybridContext(
            sync_status=SyncStatus.CONFLICT,
            sync_error="Concurrent modification detected",
        )
        assert ctx.has_conflict()
        assert ctx.sync_error is not None

    def test_hybrid_context_serialization(self):
        """Test HybridContext round-trip."""
        maf = MAFContext(workflow_id="wf-1", workflow_name="Test")
        original = HybridContext(
            maf=maf,
            primary_framework="maf",
            sync_status=SyncStatus.SYNCED,
            version=3,
        )
        data = original.to_dict()
        restored = HybridContext.from_dict(data)

        assert restored.maf.workflow_id == "wf-1"
        assert restored.sync_status == SyncStatus.SYNCED
        assert restored.version == 3


# =============================================================================
# Test: SyncResult
# =============================================================================


class TestSyncResult:
    """Tests for SyncResult dataclass."""

    def test_successful_sync_result(self):
        """Test successful SyncResult."""
        result = SyncResult(
            success=True,
            direction=SyncDirection.MAF_TO_CLAUDE,
            strategy=SyncStrategy.MERGE,
            source_version=1,
            target_version=2,
            changes_applied=5,
            duration_ms=50,
        )
        assert result.success
        assert result.direction == SyncDirection.MAF_TO_CLAUDE
        assert result.changes_applied == 5

    def test_failed_sync_result(self):
        """Test failed SyncResult."""
        result = SyncResult(
            success=False,
            direction=SyncDirection.BIDIRECTIONAL,
            strategy=SyncStrategy.MERGE,
            source_version=1,
            target_version=1,
            error="Lock acquisition timeout",
        )
        assert not result.success
        assert result.error is not None


# =============================================================================
# Test: Conflict
# =============================================================================


class TestConflict:
    """Tests for Conflict dataclass."""

    def test_create_conflict(self):
        """Test creating Conflict."""
        conflict = Conflict(
            field_path="checkpoint_data.status",
            local_value="active",
            remote_value="paused",
            local_timestamp=datetime.utcnow(),
            remote_timestamp=datetime.utcnow() - timedelta(minutes=5),
        )
        assert conflict.field_path == "checkpoint_data.status"
        assert conflict.local_value == "active"
        assert conflict.remote_value == "paused"
        assert not conflict.resolved

    def test_resolved_conflict(self):
        """Test resolved Conflict."""
        conflict = Conflict(
            field_path="context_variables.user_id",
            local_value="user-1",
            remote_value="user-2",
            resolution="local_wins",
            resolved=True,
        )
        assert conflict.resolved
        assert conflict.resolution == "local_wins"
