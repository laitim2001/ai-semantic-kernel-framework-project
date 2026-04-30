# =============================================================================
# IPA Platform - Checkpoint Models Unit Tests
# =============================================================================
# Phase 14: Human-in-the-Loop & Approval
# Sprint 57: Unified Checkpoint & Polish
#
# Tests for HybridCheckpoint, MAFCheckpointState, ClaudeCheckpointState models.
# =============================================================================

from datetime import datetime, timedelta

import pytest

from src.integrations.hybrid.checkpoint.models import (
    CheckpointStatus,
    CheckpointType,
    ClaudeCheckpointState,
    CompressionAlgorithm,
    HybridCheckpoint,
    MAFCheckpointState,
    RestoreResult,
    RestoreStatus,
    RiskSnapshot,
)
from src.integrations.hybrid.context.models import SyncStatus


# =============================================================================
# MAFCheckpointState Tests
# =============================================================================


class TestMAFCheckpointState:
    """Tests for MAFCheckpointState model."""

    def test_create_basic_state(self):
        """Test creating a basic MAF checkpoint state."""
        state = MAFCheckpointState(
            workflow_id="wf_123",
            workflow_name="Test Workflow",
            current_step=2,
            total_steps=5,
        )

        assert state.workflow_id == "wf_123"
        assert state.workflow_name == "Test Workflow"
        assert state.current_step == 2
        assert state.total_steps == 5
        assert state.agent_states == {}
        assert state.variables == {}

    def test_create_with_agent_states(self):
        """Test creating state with agent states."""
        agent_states = {
            "agent1": {"status": "completed", "output": "result1"},
            "agent2": {"status": "running"},
        }

        state = MAFCheckpointState(
            workflow_id="wf_123",
            workflow_name="Test",
            agent_states=agent_states,
        )

        assert len(state.agent_states) == 2
        assert state.agent_states["agent1"]["status"] == "completed"

    def test_to_dict_and_from_dict(self):
        """Test serialization round-trip."""
        state = MAFCheckpointState(
            workflow_id="wf_123",
            workflow_name="Test Workflow",
            current_step=3,
            total_steps=5,
            variables={"key": "value"},
            pending_approvals=["approval_1"],
        )

        data = state.to_dict()
        restored = MAFCheckpointState.from_dict(data)

        assert restored.workflow_id == state.workflow_id
        assert restored.workflow_name == state.workflow_name
        assert restored.current_step == state.current_step
        assert restored.total_steps == state.total_steps
        assert restored.variables == state.variables
        assert restored.pending_approvals == state.pending_approvals

    def test_get_progress(self):
        """Test progress calculation."""
        state = MAFCheckpointState(
            workflow_id="wf_123",
            workflow_name="Test",
            current_step=2,
            total_steps=4,
        )

        assert state.get_progress() == 0.5

    def test_get_progress_zero_steps(self):
        """Test progress with zero total steps."""
        state = MAFCheckpointState(
            workflow_id="wf_123",
            workflow_name="Test",
            total_steps=0,
        )

        assert state.get_progress() == 0.0

    def test_has_pending_approvals(self):
        """Test pending approvals check."""
        state = MAFCheckpointState(
            workflow_id="wf_123",
            workflow_name="Test",
        )
        assert not state.has_pending_approvals()

        state.pending_approvals = ["approval_1"]
        assert state.has_pending_approvals()


# =============================================================================
# ClaudeCheckpointState Tests
# =============================================================================


class TestClaudeCheckpointState:
    """Tests for ClaudeCheckpointState model."""

    def test_create_basic_state(self):
        """Test creating a basic Claude checkpoint state."""
        state = ClaudeCheckpointState(session_id="sess_123")

        assert state.session_id == "sess_123"
        assert state.conversation_history == []
        assert state.tool_call_history == []
        assert state.context_variables == {}

    def test_create_with_history(self):
        """Test creating state with conversation history."""
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        state = ClaudeCheckpointState(
            session_id="sess_123",
            conversation_history=history,
        )

        assert len(state.conversation_history) == 2
        assert state.get_message_count() == 2

    def test_to_dict_and_from_dict(self):
        """Test serialization round-trip."""
        state = ClaudeCheckpointState(
            session_id="sess_123",
            conversation_history=[{"role": "user", "content": "Hello"}],
            context_variables={"user_id": "u_456"},
            active_hooks=["hook1", "hook2"],
        )

        data = state.to_dict()
        restored = ClaudeCheckpointState.from_dict(data)

        assert restored.session_id == state.session_id
        assert restored.conversation_history == state.conversation_history
        assert restored.context_variables == state.context_variables
        assert restored.active_hooks == state.active_hooks

    def test_get_tool_call_count(self):
        """Test tool call count."""
        state = ClaudeCheckpointState(
            session_id="sess_123",
            tool_call_history=[
                {"tool": "search", "result": "found"},
                {"tool": "calculate", "result": "42"},
            ],
        )

        assert state.get_tool_call_count() == 2

    def test_has_pending_tool_calls(self):
        """Test pending tool calls check."""
        state = ClaudeCheckpointState(session_id="sess_123")
        assert not state.has_pending_tool_calls()

        state.pending_tool_calls = ["tc_1", "tc_2"]
        assert state.has_pending_tool_calls()


# =============================================================================
# RiskSnapshot Tests
# =============================================================================


class TestRiskSnapshot:
    """Tests for RiskSnapshot model."""

    def test_create_default(self):
        """Test creating default risk snapshot."""
        snapshot = RiskSnapshot()

        assert snapshot.overall_risk_level == "low"
        assert snapshot.risk_score == 0.0
        assert snapshot.risk_factors == []

    def test_create_with_values(self):
        """Test creating risk snapshot with values."""
        snapshot = RiskSnapshot(
            overall_risk_level="high",
            risk_score=0.85,
            risk_factors=[{"type": "data_access", "severity": "high"}],
        )

        assert snapshot.overall_risk_level == "high"
        assert snapshot.risk_score == 0.85
        assert len(snapshot.risk_factors) == 1

    def test_to_dict_and_from_dict(self):
        """Test serialization round-trip."""
        snapshot = RiskSnapshot(
            overall_risk_level="medium",
            risk_score=0.5,
            mitigation_applied=["mitigation1"],
        )

        data = snapshot.to_dict()
        restored = RiskSnapshot.from_dict(data)

        assert restored.overall_risk_level == snapshot.overall_risk_level
        assert restored.risk_score == snapshot.risk_score
        assert restored.mitigation_applied == snapshot.mitigation_applied


# =============================================================================
# HybridCheckpoint Tests
# =============================================================================


class TestHybridCheckpoint:
    """Tests for HybridCheckpoint model."""

    def test_create_default(self):
        """Test creating default hybrid checkpoint."""
        checkpoint = HybridCheckpoint()

        assert checkpoint.checkpoint_id  # Should have UUID
        assert checkpoint.version == 2
        assert checkpoint.status == CheckpointStatus.ACTIVE
        assert checkpoint.checkpoint_type == CheckpointType.AUTO

    def test_create_with_session(self):
        """Test creating checkpoint with session ID."""
        checkpoint = HybridCheckpoint(
            session_id="sess_123",
            execution_mode="workflow",
        )

        assert checkpoint.session_id == "sess_123"
        assert checkpoint.execution_mode == "workflow"

    def test_create_with_maf_state(self):
        """Test creating checkpoint with MAF state."""
        maf_state = MAFCheckpointState(
            workflow_id="wf_123",
            workflow_name="Test",
        )

        checkpoint = HybridCheckpoint(
            session_id="sess_123",
            maf_state=maf_state,
        )

        assert checkpoint.has_maf_state()
        assert not checkpoint.has_claude_state()
        assert checkpoint.maf_state.workflow_id == "wf_123"

    def test_create_with_claude_state(self):
        """Test creating checkpoint with Claude state."""
        claude_state = ClaudeCheckpointState(session_id="sess_123")

        checkpoint = HybridCheckpoint(
            session_id="sess_123",
            claude_state=claude_state,
        )

        assert checkpoint.has_claude_state()
        assert not checkpoint.has_maf_state()

    def test_create_with_both_states(self):
        """Test creating checkpoint with both states."""
        maf_state = MAFCheckpointState(
            workflow_id="wf_123",
            workflow_name="Test",
        )
        claude_state = ClaudeCheckpointState(session_id="sess_123")

        checkpoint = HybridCheckpoint(
            session_id="sess_123",
            maf_state=maf_state,
            claude_state=claude_state,
            execution_mode="hybrid",
        )

        assert checkpoint.has_both_states()
        assert checkpoint.execution_mode == "hybrid"

    def test_to_dict_and_from_dict(self):
        """Test serialization round-trip."""
        maf_state = MAFCheckpointState(
            workflow_id="wf_123",
            workflow_name="Test",
            current_step=2,
        )
        risk_snapshot = RiskSnapshot(risk_score=0.3)

        checkpoint = HybridCheckpoint(
            session_id="sess_123",
            checkpoint_type=CheckpointType.MODE_SWITCH,
            maf_state=maf_state,
            risk_snapshot=risk_snapshot,
            execution_mode="workflow",
            sync_version=5,
        )

        data = checkpoint.to_dict()
        restored = HybridCheckpoint.from_dict(data)

        assert restored.session_id == checkpoint.session_id
        assert restored.checkpoint_type == checkpoint.checkpoint_type
        assert restored.execution_mode == checkpoint.execution_mode
        assert restored.sync_version == checkpoint.sync_version
        assert restored.maf_state.workflow_id == "wf_123"
        assert restored.risk_snapshot.risk_score == 0.3

    def test_is_active(self):
        """Test active status check."""
        checkpoint = HybridCheckpoint()
        assert checkpoint.is_active()

        checkpoint.status = CheckpointStatus.EXPIRED
        assert not checkpoint.is_active()

    def test_is_expired(self):
        """Test expiration check."""
        checkpoint = HybridCheckpoint()
        assert not checkpoint.is_expired()

        checkpoint.expires_at = datetime.utcnow() - timedelta(hours=1)
        assert checkpoint.is_expired()

        checkpoint.expires_at = datetime.utcnow() + timedelta(hours=1)
        assert not checkpoint.is_expired()

    def test_mark_restored(self):
        """Test marking checkpoint as restored."""
        checkpoint = HybridCheckpoint()
        assert checkpoint.status == CheckpointStatus.ACTIVE
        assert checkpoint.restored_at is None

        checkpoint.mark_restored()

        assert checkpoint.status == CheckpointStatus.RESTORED
        assert checkpoint.restored_at is not None

    def test_mark_expired(self):
        """Test marking checkpoint as expired."""
        checkpoint = HybridCheckpoint()
        checkpoint.mark_expired()

        assert checkpoint.status == CheckpointStatus.EXPIRED

    def test_get_age_seconds(self):
        """Test age calculation."""
        checkpoint = HybridCheckpoint()
        age = checkpoint.get_age_seconds()

        assert age >= 0
        assert age < 1  # Should be less than 1 second

    def test_compression_fields(self):
        """Test compression-related fields."""
        checkpoint = HybridCheckpoint(
            session_id="sess_123",
            compressed=True,
            compression_algorithm=CompressionAlgorithm.ZLIB,
            checksum="abc123",
        )

        assert checkpoint.compressed is True
        assert checkpoint.compression_algorithm == CompressionAlgorithm.ZLIB
        assert checkpoint.checksum == "abc123"


# =============================================================================
# RestoreResult Tests
# =============================================================================


class TestRestoreResult:
    """Tests for RestoreResult model."""

    def test_create_success(self):
        """Test creating successful restore result."""
        result = RestoreResult(
            success=True,
            status=RestoreStatus.SUCCESS,
            checkpoint_id="cp_123",
            restored_maf=True,
            restored_claude=True,
            restored_mode="hybrid",
        )

        assert result.success
        assert result.status == RestoreStatus.SUCCESS
        assert result.restored_maf
        assert result.restored_claude

    def test_create_failure(self):
        """Test creating failure result."""
        result = RestoreResult.create_failure("cp_123", "Connection timeout")

        assert not result.success
        assert result.status == RestoreStatus.FAILED
        assert result.error == "Connection timeout"

    def test_create_validation_failure(self):
        """Test creating validation failure result."""
        result = RestoreResult.create_validation_failure(
            "cp_123", ["Invalid checksum", "Missing maf_state"]
        )

        assert not result.success
        assert result.status == RestoreStatus.VALIDATION_FAILED
        assert len(result.validation_errors) == 2

    def test_to_dict_and_from_dict(self):
        """Test serialization round-trip."""
        result = RestoreResult(
            success=True,
            checkpoint_id="cp_123",
            restored_maf=True,
            warnings=["Minor issue"],
            restore_time_ms=150,
        )

        data = result.to_dict()
        restored = RestoreResult.from_dict(data)

        assert restored.success == result.success
        assert restored.checkpoint_id == result.checkpoint_id
        assert restored.restored_maf == result.restored_maf
        assert restored.warnings == result.warnings
        assert restored.restore_time_ms == result.restore_time_ms

    def test_has_warnings(self):
        """Test warnings check."""
        result = RestoreResult(success=True)
        assert not result.has_warnings()

        result.warnings = ["Warning 1"]
        assert result.has_warnings()

    def test_has_validation_errors(self):
        """Test validation errors check."""
        result = RestoreResult(success=True)
        assert not result.has_validation_errors()

        result.validation_errors = ["Error 1"]
        assert result.has_validation_errors()


# =============================================================================
# Enum Tests
# =============================================================================


class TestEnums:
    """Tests for checkpoint enums."""

    def test_checkpoint_status_values(self):
        """Test CheckpointStatus enum values."""
        assert CheckpointStatus.ACTIVE.value == "active"
        assert CheckpointStatus.EXPIRED.value == "expired"
        assert CheckpointStatus.RESTORED.value == "restored"
        assert CheckpointStatus.DELETED.value == "deleted"
        assert CheckpointStatus.CORRUPTED.value == "corrupted"

    def test_checkpoint_type_values(self):
        """Test CheckpointType enum values."""
        assert CheckpointType.AUTO.value == "auto"
        assert CheckpointType.MANUAL.value == "manual"
        assert CheckpointType.MODE_SWITCH.value == "mode_switch"
        assert CheckpointType.HITL.value == "hitl"
        assert CheckpointType.RECOVERY.value == "recovery"

    def test_compression_algorithm_values(self):
        """Test CompressionAlgorithm enum values."""
        assert CompressionAlgorithm.NONE.value == "none"
        assert CompressionAlgorithm.ZLIB.value == "zlib"
        assert CompressionAlgorithm.GZIP.value == "gzip"
        assert CompressionAlgorithm.LZ4.value == "lz4"

    def test_restore_status_values(self):
        """Test RestoreStatus enum values."""
        assert RestoreStatus.SUCCESS.value == "success"
        assert RestoreStatus.PARTIAL.value == "partial"
        assert RestoreStatus.FAILED.value == "failed"
        assert RestoreStatus.VALIDATION_FAILED.value == "validation_failed"
