# =============================================================================
# IPA Platform - Mode Switching Models Unit Tests
# =============================================================================
# Sprint 56: Mode Switcher & HITL
#
# 測試模式切換相關的資料模型
# =============================================================================

import pytest
from datetime import datetime
from typing import Any, Dict

from src.integrations.hybrid.switching.models import (
    ExecutionState,
    MigrationDirection,
    MigratedState,
    ModeTransition,
    SwitchCheckpoint,
    SwitchConfig,
    SwitchResult,
    SwitchStatus,
    SwitchTrigger,
    SwitchTriggerType,
    SwitchValidation,
    ValidationStatus,
)
from src.integrations.hybrid.intent.models import ExecutionMode


class TestSwitchTriggerType:
    """Test SwitchTriggerType enum."""

    def test_enum_values(self):
        """Test all enum values exist."""
        assert SwitchTriggerType.COMPLEXITY == "complexity"
        assert SwitchTriggerType.USER_REQUEST == "user_request"
        assert SwitchTriggerType.FAILURE == "failure"
        assert SwitchTriggerType.RESOURCE == "resource"
        assert SwitchTriggerType.TIMEOUT == "timeout"
        assert SwitchTriggerType.MANUAL == "manual"

    def test_enum_count(self):
        """Test enum has expected number of values."""
        assert len(SwitchTriggerType) == 6

    def test_string_value(self):
        """Test enum value as string."""
        assert SwitchTriggerType.COMPLEXITY.value == "complexity"
        assert SwitchTriggerType.FAILURE.value == "failure"


class TestSwitchStatus:
    """Test SwitchStatus enum."""

    def test_enum_values(self):
        """Test all enum values exist."""
        assert SwitchStatus.PENDING == "pending"
        assert SwitchStatus.IN_PROGRESS == "in_progress"
        assert SwitchStatus.COMPLETED == "completed"
        assert SwitchStatus.FAILED == "failed"
        assert SwitchStatus.ROLLED_BACK == "rolled_back"

    def test_enum_count(self):
        """Test enum has expected number of values."""
        assert len(SwitchStatus) == 5


class TestMigrationDirection:
    """Test MigrationDirection enum."""

    def test_enum_values(self):
        """Test all enum values exist."""
        assert MigrationDirection.WORKFLOW_TO_CHAT == "workflow_to_chat"
        assert MigrationDirection.CHAT_TO_WORKFLOW == "chat_to_workflow"
        assert MigrationDirection.WORKFLOW_TO_HYBRID == "workflow_to_hybrid"
        assert MigrationDirection.CHAT_TO_HYBRID == "chat_to_hybrid"
        assert MigrationDirection.HYBRID_TO_WORKFLOW == "hybrid_to_workflow"
        assert MigrationDirection.HYBRID_TO_CHAT == "hybrid_to_chat"

    def test_enum_count(self):
        """Test enum has expected number of values."""
        assert len(MigrationDirection) == 6


class TestValidationStatus:
    """Test ValidationStatus enum."""

    def test_enum_values(self):
        """Test all enum values exist."""
        assert ValidationStatus.VALID == "valid"
        assert ValidationStatus.INVALID == "invalid"
        assert ValidationStatus.WARNING == "warning"

    def test_enum_count(self):
        """Test enum has expected number of values."""
        assert len(ValidationStatus) == 3


class TestSwitchConfig:
    """Test SwitchConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = SwitchConfig()
        assert config.enable_auto_switch is True
        assert config.complexity_threshold == 0.7
        assert config.failure_threshold == 3
        assert config.timeout_seconds == 300
        assert config.enable_rollback is True
        assert config.max_rollback_attempts == 3
        assert config.require_approval_for_switch is False
        assert config.preserve_history is True
        assert config.preserve_tool_results is True

    def test_custom_values(self):
        """Test custom configuration values."""
        config = SwitchConfig(
            enable_auto_switch=False,
            complexity_threshold=0.5,
            failure_threshold=5,
            timeout_seconds=600,
            enable_rollback=False,
            max_rollback_attempts=5,
            require_approval_for_switch=True,
            preserve_history=False,
            preserve_tool_results=False,
        )
        assert config.enable_auto_switch is False
        assert config.complexity_threshold == 0.5
        assert config.failure_threshold == 5
        assert config.timeout_seconds == 600
        assert config.enable_rollback is False
        assert config.max_rollback_attempts == 5
        assert config.require_approval_for_switch is True
        assert config.preserve_history is False
        assert config.preserve_tool_results is False

    def test_to_dict(self):
        """Test to_dict method."""
        config = SwitchConfig()
        data = config.to_dict()
        assert data["enable_auto_switch"] is True
        assert data["complexity_threshold"] == 0.7
        assert "max_rollback_attempts" in data

    def test_from_dict(self):
        """Test from_dict method."""
        data = {
            "enable_auto_switch": False,
            "complexity_threshold": 0.8,
            "failure_threshold": 5,
        }
        config = SwitchConfig.from_dict(data)
        assert config.enable_auto_switch is False
        assert config.complexity_threshold == 0.8
        assert config.failure_threshold == 5


class TestSwitchTrigger:
    """Test SwitchTrigger dataclass."""

    def test_minimal_creation(self):
        """Test creating trigger with minimal required fields."""
        trigger = SwitchTrigger(
            trigger_type=SwitchTriggerType.COMPLEXITY,
            source_mode=ExecutionMode.WORKFLOW_MODE.value,
            target_mode=ExecutionMode.CHAT_MODE.value,
            reason="Task complexity exceeded threshold",
        )
        assert trigger.trigger_type == SwitchTriggerType.COMPLEXITY
        assert trigger.source_mode == "workflow"
        assert trigger.target_mode == "chat"
        assert trigger.reason == "Task complexity exceeded threshold"
        assert trigger.confidence == 0.5
        assert trigger.metadata == {}
        assert isinstance(trigger.detected_at, datetime)
        assert trigger.trigger_id is not None

    def test_full_creation(self):
        """Test creating trigger with all fields."""
        now = datetime.utcnow()
        trigger = SwitchTrigger(
            trigger_type=SwitchTriggerType.USER_REQUEST,
            source_mode=ExecutionMode.CHAT_MODE.value,
            target_mode=ExecutionMode.WORKFLOW_MODE.value,
            reason="User requested structured workflow",
            confidence=0.95,
            trigger_id="trigger-123",
            metadata={"user_id": "user123", "request_id": "req456"},
            detected_at=now,
        )
        assert trigger.trigger_type == SwitchTriggerType.USER_REQUEST
        assert trigger.confidence == 0.95
        assert trigger.trigger_id == "trigger-123"
        assert trigger.metadata == {"user_id": "user123", "request_id": "req456"}
        assert trigger.detected_at == now

    def test_trigger_types(self):
        """Test all trigger types can be used."""
        for trigger_type in SwitchTriggerType:
            trigger = SwitchTrigger(
                trigger_type=trigger_type,
                source_mode="workflow",
                target_mode="chat",
                reason=f"Test {trigger_type.value}",
            )
            assert trigger.trigger_type == trigger_type

    def test_is_high_confidence(self):
        """Test is_high_confidence method."""
        low_confidence = SwitchTrigger(
            trigger_type=SwitchTriggerType.COMPLEXITY,
            source_mode="workflow",
            target_mode="chat",
            reason="Low confidence",
            confidence=0.5,
        )
        assert low_confidence.is_high_confidence(0.7) is False

        high_confidence = SwitchTrigger(
            trigger_type=SwitchTriggerType.USER_REQUEST,
            source_mode="workflow",
            target_mode="chat",
            reason="High confidence",
            confidence=0.9,
        )
        assert high_confidence.is_high_confidence(0.7) is True

    def test_to_dict(self):
        """Test to_dict method."""
        trigger = SwitchTrigger(
            trigger_type=SwitchTriggerType.MANUAL,
            source_mode="workflow",
            target_mode="chat",
            reason="Test",
        )
        data = trigger.to_dict()
        assert data["trigger_type"] == "manual"
        assert data["source_mode"] == "workflow"
        assert "trigger_id" in data

    def test_from_dict(self):
        """Test from_dict method."""
        data = {
            "trigger_type": "complexity",
            "source_mode": "workflow",
            "target_mode": "chat",
            "reason": "Test",
            "confidence": 0.8,
        }
        trigger = SwitchTrigger.from_dict(data)
        assert trigger.trigger_type == SwitchTriggerType.COMPLEXITY
        assert trigger.confidence == 0.8


class TestMigratedState:
    """Test MigratedState dataclass."""

    def test_minimal_creation(self):
        """Test creating with minimal fields."""
        state = MigratedState(direction=MigrationDirection.WORKFLOW_TO_CHAT)
        assert state.direction == MigrationDirection.WORKFLOW_TO_CHAT
        assert state.preserved_history is True
        assert state.preserved_tool_results is True
        assert state.conversation_history == []
        assert state.tool_call_results == []
        assert state.workflow_state == {}
        assert state.warnings == []
        assert isinstance(state.created_at, datetime)

    def test_full_creation(self):
        """Test creating with all fields."""
        now = datetime.utcnow()
        state = MigratedState(
            direction=MigrationDirection.CHAT_TO_WORKFLOW,
            preserved_history=True,
            preserved_tool_results=True,
            migration_id="mig-123",
            context_summary="5 messages migrated",
            transformed_variables={"key": "value"},
            conversation_history=[{"role": "user", "content": "Hello"}],
            tool_call_results=[{"tool": "search", "result": "found"}],
            workflow_state={"step": 1},
            warnings=["Some warning"],
            migration_time_ms=150,
            created_at=now,
        )
        assert state.direction == MigrationDirection.CHAT_TO_WORKFLOW
        assert state.migration_id == "mig-123"
        assert len(state.conversation_history) == 1
        assert len(state.tool_call_results) == 1
        assert state.migration_time_ms == 150
        assert state.created_at == now

    def test_has_warnings(self):
        """Test has_warnings method."""
        no_warnings = MigratedState(direction=MigrationDirection.WORKFLOW_TO_CHAT)
        assert no_warnings.has_warnings() is False

        with_warnings = MigratedState(
            direction=MigrationDirection.WORKFLOW_TO_CHAT,
            warnings=["Warning 1"],
        )
        assert with_warnings.has_warnings() is True

    def test_to_dict(self):
        """Test to_dict method."""
        state = MigratedState(direction=MigrationDirection.WORKFLOW_TO_CHAT)
        data = state.to_dict()
        assert data["direction"] == "workflow_to_chat"
        assert "migration_id" in data


class TestSwitchValidation:
    """Test SwitchValidation dataclass."""

    def test_default_values(self):
        """Test default validation values."""
        validation = SwitchValidation()
        assert validation.status == ValidationStatus.VALID
        assert validation.success is True
        assert validation.checks_passed == []
        assert validation.checks_failed == []
        assert validation.warnings == []
        assert validation.error is None

    def test_failed_validation(self):
        """Test failed validation."""
        validation = SwitchValidation(
            status=ValidationStatus.INVALID,
            success=False,
            checks_passed=["check1"],
            checks_failed=["check2", "check3"],
            error="Validation failed",
        )
        assert validation.success is False
        assert len(validation.checks_failed) == 2
        assert validation.error == "Validation failed"

    def test_warning_validation(self):
        """Test validation with warnings."""
        validation = SwitchValidation(
            status=ValidationStatus.WARNING,
            success=True,
            checks_passed=["check1", "check2"],
            warnings=["Warning 1"],
        )
        assert validation.success is True
        assert validation.status == ValidationStatus.WARNING
        assert len(validation.warnings) == 1

    def test_to_dict(self):
        """Test to_dict method."""
        validation = SwitchValidation(
            status=ValidationStatus.VALID,
            success=True,
            checks_passed=["check1"],
        )
        data = validation.to_dict()
        assert data["status"] == "valid"
        assert data["success"] is True


class TestSwitchCheckpoint:
    """Test SwitchCheckpoint dataclass."""

    def test_default_creation(self):
        """Test creating checkpoint with defaults."""
        checkpoint = SwitchCheckpoint()
        assert checkpoint.checkpoint_id is not None
        assert checkpoint.switch_id == ""
        assert checkpoint.context_snapshot == {}
        assert checkpoint.mode_before == ""
        assert isinstance(checkpoint.created_at, datetime)

    def test_full_creation(self):
        """Test creating checkpoint with all fields."""
        now = datetime.utcnow()
        checkpoint = SwitchCheckpoint(
            checkpoint_id="chk-123",
            switch_id="switch-456",
            context_snapshot={"key": "value", "mode": "workflow"},
            mode_before="workflow",
            created_at=now,
        )
        assert checkpoint.checkpoint_id == "chk-123"
        assert checkpoint.switch_id == "switch-456"
        assert checkpoint.context_snapshot["key"] == "value"
        assert checkpoint.mode_before == "workflow"
        assert checkpoint.created_at == now

    def test_to_dict(self):
        """Test to_dict method."""
        checkpoint = SwitchCheckpoint(
            checkpoint_id="chk-123",
            switch_id="switch-456",
            mode_before="workflow",
        )
        data = checkpoint.to_dict()
        assert data["checkpoint_id"] == "chk-123"
        assert data["switch_id"] == "switch-456"

    def test_from_dict(self):
        """Test from_dict method."""
        data = {
            "checkpoint_id": "chk-789",
            "switch_id": "switch-abc",
            "mode_before": "chat",
            "context_snapshot": {"test": True},
        }
        checkpoint = SwitchCheckpoint.from_dict(data)
        assert checkpoint.checkpoint_id == "chk-789"
        assert checkpoint.switch_id == "switch-abc"
        assert checkpoint.mode_before == "chat"


class TestSwitchResult:
    """Test SwitchResult dataclass."""

    def test_success_result(self):
        """Test creating successful switch result."""
        trigger = SwitchTrigger(
            trigger_type=SwitchTriggerType.COMPLEXITY,
            source_mode="workflow",
            target_mode="chat",
            reason="Complexity threshold",
        )
        migrated = MigratedState(direction=MigrationDirection.WORKFLOW_TO_CHAT)

        result = SwitchResult(
            success=True,
            switch_id="switch-123",
            status=SwitchStatus.COMPLETED,
            trigger=trigger,
            new_mode="chat",
            migrated_state=migrated,
            checkpoint_id="chk-456",
        )
        assert result.success is True
        assert result.switch_id == "switch-123"
        assert result.status == SwitchStatus.COMPLETED
        assert result.trigger == trigger
        assert result.new_mode == "chat"
        assert result.migrated_state == migrated
        assert result.checkpoint_id == "chk-456"
        assert result.error is None
        assert result.switch_time_ms == 0

    def test_failure_result(self):
        """Test creating failed switch result."""
        result = SwitchResult(
            success=False,
            switch_id="switch-789",
            status=SwitchStatus.FAILED,
            error="State migration failed",
            switch_time_ms=1500,
        )
        assert result.success is False
        assert result.status == SwitchStatus.FAILED
        assert result.error == "State migration failed"
        assert result.switch_time_ms == 1500
        assert result.trigger is None
        assert result.new_mode is None

    def test_rolled_back_result(self):
        """Test creating rolled back switch result."""
        result = SwitchResult(
            success=False,
            switch_id="switch-abc",
            status=SwitchStatus.ROLLED_BACK,
            error="Validation failed, rollback executed",
            checkpoint_id="chk-def",
        )
        assert result.status == SwitchStatus.ROLLED_BACK
        assert result.checkpoint_id == "chk-def"

    def test_is_rollbackable(self):
        """Test is_rollbackable method."""
        rollbackable = SwitchResult(
            success=True,
            status=SwitchStatus.COMPLETED,
            checkpoint_id="chk-123",
        )
        assert rollbackable.is_rollbackable() is True

        not_rollbackable = SwitchResult(
            success=False,
            status=SwitchStatus.ROLLED_BACK,
            checkpoint_id="chk-123",
        )
        assert not_rollbackable.is_rollbackable() is False

        no_checkpoint = SwitchResult(
            success=True,
            status=SwitchStatus.COMPLETED,
        )
        assert no_checkpoint.is_rollbackable() is False

    def test_to_dict(self):
        """Test to_dict method."""
        result = SwitchResult(
            success=True,
            switch_id="switch-123",
            status=SwitchStatus.COMPLETED,
            new_mode="chat",
        )
        data = result.to_dict()
        assert data["success"] is True
        assert data["switch_id"] == "switch-123"
        assert data["status"] == "completed"


class TestModeTransition:
    """Test ModeTransition dataclass."""

    def test_minimal_creation(self):
        """Test creating with minimal fields."""
        transition = ModeTransition(
            session_id="session-123",
            source_mode="workflow",
            target_mode="chat",
        )
        assert transition.session_id == "session-123"
        assert transition.source_mode == "workflow"
        assert transition.target_mode == "chat"
        assert transition.trigger is None
        assert transition.result is None
        assert transition.rollback_of is None
        assert isinstance(transition.transition_id, str)
        assert isinstance(transition.created_at, datetime)

    def test_full_creation(self):
        """Test creating with all fields."""
        trigger = SwitchTrigger(
            trigger_type=SwitchTriggerType.MANUAL,
            source_mode="workflow",
            target_mode="chat",
            reason="Manual switch",
        )
        result = SwitchResult(
            success=True,
            switch_id="switch-xyz",
            status=SwitchStatus.COMPLETED,
        )
        now = datetime.utcnow()

        transition = ModeTransition(
            session_id="session-456",
            source_mode="workflow",
            target_mode="chat",
            trigger=trigger,
            result=result,
            transition_id="trans-789",
            rollback_of="trans-123",
            created_at=now,
        )
        assert transition.trigger == trigger
        assert transition.result == result
        assert transition.transition_id == "trans-789"
        assert transition.rollback_of == "trans-123"
        assert transition.created_at == now

    def test_is_rollback(self):
        """Test is_rollback method."""
        normal = ModeTransition(
            session_id="s1",
            source_mode="workflow",
            target_mode="chat",
        )
        assert normal.is_rollback() is False

        rollback = ModeTransition(
            session_id="s1",
            source_mode="chat",
            target_mode="workflow",
            rollback_of="trans-123",
        )
        assert rollback.is_rollback() is True

    def test_was_successful(self):
        """Test was_successful method."""
        no_result = ModeTransition(
            session_id="s1",
            source_mode="workflow",
            target_mode="chat",
        )
        assert no_result.was_successful() is False

        failed = ModeTransition(
            session_id="s1",
            source_mode="workflow",
            target_mode="chat",
            result=SwitchResult(success=False, status=SwitchStatus.FAILED),
        )
        assert failed.was_successful() is False

        successful = ModeTransition(
            session_id="s1",
            source_mode="workflow",
            target_mode="chat",
            result=SwitchResult(success=True, status=SwitchStatus.COMPLETED),
        )
        assert successful.was_successful() is True


class TestExecutionState:
    """Test ExecutionState dataclass."""

    def test_default_values(self):
        """Test default state values."""
        state = ExecutionState(
            session_id="session-123",
            current_mode="workflow",
        )
        assert state.session_id == "session-123"
        assert state.current_mode == "workflow"
        assert state.consecutive_failures == 0
        assert state.has_pending_steps is False
        assert state.step_count == 0
        assert state.message_count == 0
        assert state.tool_call_count == 0
        assert state.resource_usage == {}
        assert isinstance(state.last_activity, datetime)
        assert state.metadata == {}

    def test_custom_values(self):
        """Test custom state values."""
        now = datetime.utcnow()
        state = ExecutionState(
            session_id="session-456",
            current_mode="chat",
            consecutive_failures=2,
            has_pending_steps=True,
            step_count=5,
            message_count=10,
            tool_call_count=3,
            resource_usage={"cpu": 75.5, "memory": 60.0},
            last_activity=now,
            metadata={"key": "value"},
        )
        assert state.consecutive_failures == 2
        assert state.has_pending_steps is True
        assert state.step_count == 5
        assert state.message_count == 10
        assert state.tool_call_count == 3
        assert state.resource_usage["cpu"] == 75.5
        assert state.last_activity == now
        assert state.metadata["key"] == "value"

    def test_to_dict(self):
        """Test to_dict method."""
        state = ExecutionState(
            session_id="s1",
            current_mode="workflow",
            consecutive_failures=1,
        )
        data = state.to_dict()
        assert data["session_id"] == "s1"
        assert data["current_mode"] == "workflow"
        assert data["consecutive_failures"] == 1

    def test_from_dict(self):
        """Test from_dict method."""
        data = {
            "session_id": "s2",
            "current_mode": "chat",
            "consecutive_failures": 3,
            "step_count": 10,
        }
        state = ExecutionState.from_dict(data)
        assert state.session_id == "s2"
        assert state.current_mode == "chat"
        assert state.consecutive_failures == 3
        assert state.step_count == 10


class TestEnumStringBehavior:
    """Test enum string behavior and serialization."""

    def test_switch_trigger_type_serialization(self):
        """Test SwitchTriggerType can be used in dictionaries."""
        data = {"type": SwitchTriggerType.COMPLEXITY}
        assert data["type"] == SwitchTriggerType.COMPLEXITY
        assert data["type"].value == "complexity"

    def test_switch_status_in_conditions(self):
        """Test SwitchStatus in conditional logic."""
        status = SwitchStatus.COMPLETED
        assert status == SwitchStatus.COMPLETED
        assert status != SwitchStatus.FAILED
        assert status in [SwitchStatus.COMPLETED, SwitchStatus.ROLLED_BACK]

    def test_migration_direction_string_match(self):
        """Test MigrationDirection string matching."""
        direction = MigrationDirection.WORKFLOW_TO_CHAT
        assert direction.value == "workflow_to_chat"


class TestDataclassModification:
    """Test dataclass field modification."""

    def test_switch_config_can_be_modified(self):
        """Test SwitchConfig fields can be modified."""
        config = SwitchConfig()
        config.complexity_threshold = 0.9
        assert config.complexity_threshold == 0.9

    def test_switch_trigger_metadata_mutable(self):
        """Test SwitchTrigger metadata can be updated."""
        trigger = SwitchTrigger(
            trigger_type=SwitchTriggerType.COMPLEXITY,
            source_mode="workflow",
            target_mode="chat",
            reason="Test",
        )
        trigger.metadata["key"] = "value"
        assert trigger.metadata["key"] == "value"

    def test_execution_state_update(self):
        """Test ExecutionState can be updated."""
        state = ExecutionState(session_id="s1", current_mode="workflow")
        state.consecutive_failures += 1
        state.step_count += 1
        assert state.consecutive_failures == 1
        assert state.step_count == 1


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_metadata(self):
        """Test empty metadata handling."""
        trigger = SwitchTrigger(
            trigger_type=SwitchTriggerType.MANUAL,
            source_mode="workflow",
            target_mode="chat",
            reason="Test",
            metadata={},
        )
        assert trigger.metadata == {}
        assert len(trigger.metadata) == 0

    def test_zero_values(self):
        """Test zero value handling."""
        state = ExecutionState(
            session_id="s1",
            current_mode="workflow",
            consecutive_failures=0,
            step_count=0,
            message_count=0,
            tool_call_count=0,
        )
        assert state.consecutive_failures == 0
        assert state.step_count == 0

    def test_confidence_boundaries(self):
        """Test confidence value boundaries."""
        # Low confidence
        low = SwitchTrigger(
            trigger_type=SwitchTriggerType.COMPLEXITY,
            source_mode="workflow",
            target_mode="chat",
            reason="Low confidence",
            confidence=0.0,
        )
        assert low.confidence == 0.0

        # High confidence
        high = SwitchTrigger(
            trigger_type=SwitchTriggerType.USER_REQUEST,
            source_mode="workflow",
            target_mode="chat",
            reason="High confidence",
            confidence=1.0,
        )
        assert high.confidence == 1.0

    def test_long_reason_string(self):
        """Test handling of long reason strings."""
        long_reason = "A" * 1000
        trigger = SwitchTrigger(
            trigger_type=SwitchTriggerType.MANUAL,
            source_mode="workflow",
            target_mode="chat",
            reason=long_reason,
        )
        assert len(trigger.reason) == 1000
