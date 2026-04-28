# =============================================================================
# IPA Platform - ModeSwitcher Unit Tests
# =============================================================================
# Sprint 56: Mode Switcher & HITL
#
# 測試 ModeSwitcher 核心功能，包含觸發檢測、執行切換、Rollback 等
# =============================================================================

import pytest
from datetime import datetime, timedelta
from typing import Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

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
from src.integrations.hybrid.switching.switcher import (
    CheckpointStorageProtocol,
    ContextBridgeProtocol,
    InMemoryCheckpointStorage,
    ModeSwitcher,
    StateMigratorProtocol,
    SwitcherMetrics,
    TriggerDetectorProtocol,
    create_mode_switcher,
)
from src.integrations.hybrid.intent.models import ExecutionMode


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def default_config() -> SwitchConfig:
    """Create default switch configuration."""
    return SwitchConfig()


@pytest.fixture
def strict_config() -> SwitchConfig:
    """Create strict configuration with low thresholds."""
    return SwitchConfig(
        enable_auto_switch=True,
        complexity_threshold=0.5,
        failure_threshold=2,
        timeout_seconds=60,
        enable_rollback=True,
        max_rollback_attempts=5,
    )


@pytest.fixture
def execution_state() -> ExecutionState:
    """Create default execution state."""
    return ExecutionState(
        session_id="test-session-123",
        current_mode=ExecutionMode.WORKFLOW_MODE.value,
    )


@pytest.fixture
def chat_execution_state() -> ExecutionState:
    """Create chat mode execution state."""
    return ExecutionState(
        session_id="test-session-456",
        current_mode=ExecutionMode.CHAT_MODE.value,
    )


@pytest.fixture
def switch_trigger() -> SwitchTrigger:
    """Create sample switch trigger."""
    return SwitchTrigger(
        trigger_type=SwitchTriggerType.COMPLEXITY,
        source_mode=ExecutionMode.WORKFLOW_MODE.value,
        target_mode=ExecutionMode.CHAT_MODE.value,
        reason="Complexity threshold exceeded",
        confidence=0.85,
    )


@pytest.fixture
def migrated_state() -> MigratedState:
    """Create sample migrated state."""
    return MigratedState(
        direction=MigrationDirection.WORKFLOW_TO_CHAT,
        preserved_history=True,
        preserved_tool_results=True,
        conversation_history=[{"role": "user", "content": "Hello"}],
        tool_results=[],
    )


# =============================================================================
# Mock Protocol Implementations
# =============================================================================


class MockTriggerDetector:
    """Mock trigger detector for testing."""

    def __init__(
        self,
        should_trigger: bool = False,
        trigger_type: SwitchTriggerType = SwitchTriggerType.COMPLEXITY,
        confidence: float = 0.8,
    ):
        self.should_trigger = should_trigger
        self.trigger_type = trigger_type
        self.confidence = confidence
        self.detect_called = False

    async def detect(
        self,
        current_mode: ExecutionMode,
        state: ExecutionState,
        new_input: str,
    ) -> Optional[SwitchTrigger]:
        self.detect_called = True
        if self.should_trigger:
            return SwitchTrigger(
                trigger_type=self.trigger_type,
                source_mode=current_mode.value,
                target_mode=ExecutionMode.CHAT_MODE.value,
                reason=f"Mock trigger: {self.trigger_type.value}",
                confidence=self.confidence,
            )
        return None


class MockStateMigrator:
    """Mock state migrator for testing."""

    def __init__(
        self,
        should_succeed: bool = True,
        migration_direction: MigrationDirection = MigrationDirection.WORKFLOW_TO_CHAT,
    ):
        self.should_succeed = should_succeed
        self.migration_direction = migration_direction
        self.migrate_called = False

    async def migrate(
        self,
        context: Any,
        source_mode: ExecutionMode,
        target_mode: ExecutionMode,
    ) -> MigratedState:
        """Migrate state between modes - matches StateMigratorProtocol signature."""
        self.migrate_called = True
        if not self.should_succeed:
            raise RuntimeError("Migration failed")
        return MigratedState(
            direction=self.migration_direction,
            preserved_history=True,
            preserved_tool_results=True,
        )


class MockContextBridge:
    """Mock context bridge for testing."""

    def __init__(self, should_succeed: bool = True):
        self.should_succeed = should_succeed
        self.get_called = False
        self.update_called = False
        self._contexts: dict = {}

    async def get_context(self, session_id: str) -> Optional[Any]:
        """Get hybrid context for session."""
        self.get_called = True
        if not self.should_succeed:
            raise RuntimeError("Get context failed")
        return self._contexts.get(session_id, {"current_mode": "workflow"})

    async def update_context(self, session_id: str, context: Any) -> bool:
        """Update hybrid context."""
        self.update_called = True
        if not self.should_succeed:
            raise RuntimeError("Update context failed")
        self._contexts[session_id] = context
        return True


# =============================================================================
# Test SwitcherMetrics
# =============================================================================


class TestSwitcherMetrics:
    """Test SwitcherMetrics class."""

    def test_initial_state(self):
        """Test initial metrics state."""
        metrics = SwitcherMetrics()

        assert metrics.total_switches == 0
        assert metrics.successful_switches == 0
        assert metrics.failed_switches == 0
        assert metrics.rollbacks == 0
        assert metrics.average_switch_time_ms == 0.0
        assert metrics.last_switch_at is None

    def test_record_successful_switch(self):
        """Test recording successful switch."""
        metrics = SwitcherMetrics()

        metrics.record_switch(
            success=True,
            trigger_type="complexity",
            direction="workflow_to_chat",
            time_ms=150,
        )

        assert metrics.total_switches == 1
        assert metrics.successful_switches == 1
        assert metrics.failed_switches == 0
        assert metrics.switches_by_trigger["complexity"] == 1
        assert metrics.switches_by_direction["workflow_to_chat"] == 1
        assert metrics.average_switch_time_ms == 150.0

    def test_record_failed_switch(self):
        """Test recording failed switch."""
        metrics = SwitcherMetrics()

        metrics.record_switch(
            success=False,
            trigger_type="failure",
            direction="chat_to_workflow",
            time_ms=50,
        )

        assert metrics.total_switches == 1
        assert metrics.successful_switches == 0
        assert metrics.failed_switches == 1

    def test_record_rollback(self):
        """Test recording rollback."""
        metrics = SwitcherMetrics()

        metrics.record_rollback()

        assert metrics.rollbacks == 1

    def test_get_success_rate(self):
        """Test success rate calculation."""
        metrics = SwitcherMetrics()

        # No switches
        assert metrics.get_success_rate() == 0.0

        # Add switches
        metrics.record_switch(True, "test", "test", 100)
        metrics.record_switch(True, "test", "test", 100)
        metrics.record_switch(False, "test", "test", 100)

        assert metrics.get_success_rate() == pytest.approx(2 / 3)

    def test_to_dict(self):
        """Test to_dict conversion."""
        metrics = SwitcherMetrics()
        metrics.record_switch(True, "complexity", "workflow_to_chat", 100)

        result = metrics.to_dict()

        assert result["total_switches"] == 1
        assert result["successful_switches"] == 1
        assert result["success_rate"] == 1.0
        assert "last_switch_at" in result


# =============================================================================
# Test InMemoryCheckpointStorage
# =============================================================================


class TestInMemoryCheckpointStorage:
    """Test InMemoryCheckpointStorage implementation."""

    @pytest.fixture
    def storage(self) -> InMemoryCheckpointStorage:
        """Create fresh storage instance."""
        return InMemoryCheckpointStorage()

    @pytest.fixture
    def sample_checkpoint(self) -> SwitchCheckpoint:
        """Create sample checkpoint."""
        return SwitchCheckpoint(
            checkpoint_id="chk-123",
            switch_id="switch-123",
            context_snapshot={"key": "value", "session_id": "session-123"},
            mode_before="workflow",
        )

    @pytest.mark.asyncio
    async def test_save_and_get_checkpoint(self, storage, sample_checkpoint):
        """Test saving and retrieving checkpoint."""
        await storage.save_checkpoint(sample_checkpoint)
        retrieved = await storage.get_checkpoint(sample_checkpoint.checkpoint_id)

        assert retrieved is not None
        assert retrieved.checkpoint_id == sample_checkpoint.checkpoint_id
        assert retrieved.switch_id == sample_checkpoint.switch_id
        assert retrieved.mode_before == sample_checkpoint.mode_before

    @pytest.mark.asyncio
    async def test_get_nonexistent_checkpoint(self, storage):
        """Test getting checkpoint that doesn't exist."""
        result = await storage.get_checkpoint("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_checkpoint(self, storage, sample_checkpoint):
        """Test deleting checkpoint."""
        await storage.save_checkpoint(sample_checkpoint)
        result = await storage.delete_checkpoint(sample_checkpoint.checkpoint_id)

        assert result is True
        assert await storage.get_checkpoint(sample_checkpoint.checkpoint_id) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_checkpoint(self, storage):
        """Test deleting checkpoint that doesn't exist."""
        result = await storage.delete_checkpoint("nonexistent-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_multiple_checkpoints(self, storage):
        """Test storing multiple checkpoints."""
        for i in range(3):
            checkpoint = SwitchCheckpoint(
                checkpoint_id=f"chk-{i}",
                switch_id=f"switch-{i}",
                context_snapshot={"index": i},
                mode_before="workflow",
            )
            await storage.save_checkpoint(checkpoint)

        for i in range(3):
            retrieved = await storage.get_checkpoint(f"chk-{i}")
            assert retrieved is not None
            assert retrieved.checkpoint_id == f"chk-{i}"

    def test_clear_storage(self, storage):
        """Test clearing all checkpoints."""
        storage._checkpoints["chk-1"] = SwitchCheckpoint(
            switch_id="s1", mode_before="workflow"
        )
        storage._checkpoints["chk-2"] = SwitchCheckpoint(
            switch_id="s2", mode_before="chat"
        )

        storage.clear()

        assert len(storage._checkpoints) == 0


# =============================================================================
# Test ModeSwitcher Initialization
# =============================================================================


class TestModeSwitcherInit:
    """Test ModeSwitcher initialization."""

    def test_default_initialization(self):
        """Test default initialization."""
        switcher = ModeSwitcher()

        assert switcher.config is not None
        assert switcher.config.enable_auto_switch is True
        assert len(switcher.trigger_detectors) == 0
        assert switcher.state_migrator is None
        assert isinstance(switcher.checkpoint_storage, InMemoryCheckpointStorage)
        assert switcher.context_bridge is None
        assert len(switcher._transition_history) == 0

    def test_custom_config(self, strict_config):
        """Test initialization with custom config."""
        switcher = ModeSwitcher(config=strict_config)

        assert switcher.config == strict_config
        assert switcher.config.complexity_threshold == 0.5
        assert switcher.config.failure_threshold == 2

    def test_with_trigger_detectors(self):
        """Test initialization with trigger detectors."""
        detectors = [MockTriggerDetector(), MockTriggerDetector()]
        switcher = ModeSwitcher(trigger_detectors=detectors)

        assert len(switcher.trigger_detectors) == 2

    def test_with_state_migrator(self):
        """Test initialization with state migrator."""
        migrator = MockStateMigrator()
        switcher = ModeSwitcher(state_migrator=migrator)

        assert switcher.state_migrator == migrator

    def test_with_checkpoint_storage(self):
        """Test initialization with custom checkpoint storage."""
        storage = InMemoryCheckpointStorage()
        switcher = ModeSwitcher(checkpoint_storage=storage)

        assert switcher.checkpoint_storage == storage

    def test_with_context_bridge(self):
        """Test initialization with context bridge."""
        bridge = MockContextBridge()
        switcher = ModeSwitcher(context_bridge=bridge)

        assert switcher.context_bridge == bridge


# =============================================================================
# Test should_switch Method
# =============================================================================


class TestShouldSwitch:
    """Test ModeSwitcher.should_switch method."""

    @pytest.mark.asyncio
    async def test_no_detectors_returns_none(self, execution_state):
        """Test with no detectors returns None."""
        switcher = ModeSwitcher()
        result = await switcher.should_switch(
            current_mode=ExecutionMode.WORKFLOW_MODE,
            current_state=execution_state,
            new_input="test input",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_auto_switch_disabled(self, execution_state):
        """Test returns None when auto-switch is disabled."""
        config = SwitchConfig(enable_auto_switch=False)
        detector = MockTriggerDetector(should_trigger=True)
        switcher = ModeSwitcher(config=config, trigger_detectors=[detector])

        result = await switcher.should_switch(
            current_mode=ExecutionMode.WORKFLOW_MODE,
            current_state=execution_state,
            new_input="test input",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_detector_triggers_switch(self, execution_state):
        """Test detector can trigger switch."""
        detector = MockTriggerDetector(
            should_trigger=True,
            trigger_type=SwitchTriggerType.COMPLEXITY,
            confidence=0.9,
        )
        switcher = ModeSwitcher(trigger_detectors=[detector])

        result = await switcher.should_switch(
            current_mode=ExecutionMode.WORKFLOW_MODE,
            current_state=execution_state,
            new_input="complex task",
        )

        assert result is not None
        assert result.trigger_type == SwitchTriggerType.COMPLEXITY
        assert result.confidence == 0.9
        assert detector.detect_called is True

    @pytest.mark.asyncio
    async def test_multiple_detectors_first_wins(self, execution_state):
        """Test first triggering detector wins."""
        detector1 = MockTriggerDetector(
            should_trigger=True,
            trigger_type=SwitchTriggerType.COMPLEXITY,
            confidence=0.8,
        )
        detector2 = MockTriggerDetector(
            should_trigger=True,
            trigger_type=SwitchTriggerType.USER_REQUEST,
            confidence=0.95,
        )
        switcher = ModeSwitcher(trigger_detectors=[detector1, detector2])

        result = await switcher.should_switch(
            current_mode=ExecutionMode.WORKFLOW_MODE,
            current_state=execution_state,
            new_input="test",
        )

        assert result is not None
        assert result.trigger_type == SwitchTriggerType.COMPLEXITY

    @pytest.mark.asyncio
    async def test_no_detector_triggers(self, execution_state):
        """Test when no detector triggers switch."""
        detector1 = MockTriggerDetector(should_trigger=False)
        detector2 = MockTriggerDetector(should_trigger=False)
        switcher = ModeSwitcher(trigger_detectors=[detector1, detector2])

        result = await switcher.should_switch(
            current_mode=ExecutionMode.WORKFLOW_MODE,
            current_state=execution_state,
            new_input="simple task",
        )

        assert result is None
        assert detector1.detect_called is True
        assert detector2.detect_called is True

    @pytest.mark.asyncio
    async def test_low_confidence_not_triggered(self, execution_state):
        """Test low confidence trigger is not triggered."""
        config = SwitchConfig(complexity_threshold=0.9)  # High threshold
        detector = MockTriggerDetector(
            should_trigger=True,
            trigger_type=SwitchTriggerType.COMPLEXITY,
            confidence=0.5,  # Below threshold
        )
        switcher = ModeSwitcher(config=config, trigger_detectors=[detector])

        result = await switcher.should_switch(
            current_mode=ExecutionMode.WORKFLOW_MODE,
            current_state=execution_state,
            new_input="test",
        )

        # Low confidence should not trigger
        assert result is None


# =============================================================================
# Test execute_switch Method
# =============================================================================


class TestExecuteSwitch:
    """Test ModeSwitcher.execute_switch method."""

    @pytest.mark.asyncio
    async def test_successful_switch(self, switch_trigger):
        """Test successful mode switch."""
        migrator = MockStateMigrator(should_succeed=True)
        bridge = MockContextBridge(should_succeed=True)
        switcher = ModeSwitcher(state_migrator=migrator, context_bridge=bridge)

        result = await switcher.execute_switch(
            trigger=switch_trigger,
            context={"test": "context"},
            session_id="session-123",
        )

        assert result.success is True
        assert result.status == SwitchStatus.COMPLETED
        assert result.new_mode == ExecutionMode.CHAT_MODE.value
        assert result.migrated_state is not None
        assert migrator.migrate_called is True
        assert bridge.update_called is True

    @pytest.mark.asyncio
    async def test_switch_creates_checkpoint(self, switch_trigger):
        """Test switch creates checkpoint when enabled."""
        config = SwitchConfig(enable_rollback=True)
        storage = InMemoryCheckpointStorage()
        migrator = MockStateMigrator()
        switcher = ModeSwitcher(
            config=config,
            checkpoint_storage=storage,
            state_migrator=migrator,
        )

        result = await switcher.execute_switch(
            trigger=switch_trigger,
            context={"test": "context"},
            session_id="session-123",
        )

        assert result.success is True
        assert result.checkpoint_id is not None
        # Verify checkpoint was saved
        checkpoint = await storage.get_checkpoint(result.checkpoint_id)
        assert checkpoint is not None

    @pytest.mark.asyncio
    async def test_switch_failure_on_migration(self, switch_trigger):
        """Test switch failure during migration."""
        migrator = MockStateMigrator(should_succeed=False)
        config = SwitchConfig(enable_rollback=True)
        storage = InMemoryCheckpointStorage()
        switcher = ModeSwitcher(
            config=config,
            checkpoint_storage=storage,
            state_migrator=migrator,
        )

        result = await switcher.execute_switch(
            trigger=switch_trigger,
            context={"test": "context"},
            session_id="session-123",
        )

        assert result.success is False
        assert result.status == SwitchStatus.FAILED
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_switch_records_transition(self, switch_trigger):
        """Test switch records transition in history."""
        migrator = MockStateMigrator()
        switcher = ModeSwitcher(state_migrator=migrator)

        result = await switcher.execute_switch(
            trigger=switch_trigger,
            context={},
            session_id="session-123",
        )

        assert result.success is True
        assert len(switcher._transition_history) == 1
        transition = switcher._transition_history[0]
        assert transition.session_id == "session-123"
        assert transition.source_mode == "workflow"
        assert transition.target_mode == "chat"

    @pytest.mark.asyncio
    async def test_switch_without_migrator(self, switch_trigger):
        """Test switch without state migrator uses default behavior."""
        switcher = ModeSwitcher()

        result = await switcher.execute_switch(
            trigger=switch_trigger,
            context={},
        )

        assert result.success is True
        assert result.migrated_state is not None

    @pytest.mark.asyncio
    async def test_switch_measures_duration(self, switch_trigger):
        """Test switch measures execution duration."""
        migrator = MockStateMigrator()
        switcher = ModeSwitcher(state_migrator=migrator)

        result = await switcher.execute_switch(
            trigger=switch_trigger,
            context={},
        )

        assert result.success is True
        assert result.switch_time_ms is not None
        assert result.switch_time_ms >= 0


# =============================================================================
# Test rollback_switch Method
# =============================================================================


class TestRollbackSwitch:
    """Test ModeSwitcher.rollback_switch method."""

    @pytest.mark.asyncio
    async def test_rollback_with_checkpoint_id(self):
        """Test rollback using checkpoint ID."""
        storage = InMemoryCheckpointStorage()
        switcher = ModeSwitcher(checkpoint_storage=storage)

        # Create and save checkpoint
        checkpoint = SwitchCheckpoint(
            checkpoint_id="chk-123",
            switch_id="switch-123",
            context_snapshot={"original": True, "session_id": "s1", "current_mode": "workflow"},
            mode_before="workflow",
        )
        await storage.save_checkpoint(checkpoint)

        result = await switcher.rollback_switch("chk-123")

        assert result is True
        # Verify rollback recorded in history
        assert len(switcher._transition_history) == 1
        assert switcher._transition_history[0].rollback_of == "switch-123"

    @pytest.mark.asyncio
    async def test_rollback_with_checkpoint_object(self):
        """Test rollback using checkpoint object."""
        switcher = ModeSwitcher()
        checkpoint = SwitchCheckpoint(
            checkpoint_id="chk-456",
            switch_id="switch-456",
            context_snapshot={"session_id": "s1", "current_mode": "chat"},
            mode_before="chat",
        )

        result = await switcher.rollback_switch(checkpoint)

        assert result is True
        assert len(switcher._transition_history) == 1

    @pytest.mark.asyncio
    async def test_rollback_nonexistent_checkpoint(self):
        """Test rollback with nonexistent checkpoint ID."""
        switcher = ModeSwitcher()

        result = await switcher.rollback_switch("nonexistent-id")

        assert result is False

    @pytest.mark.asyncio
    async def test_rollback_updates_metrics(self):
        """Test rollback updates metrics."""
        storage = InMemoryCheckpointStorage()
        switcher = ModeSwitcher(checkpoint_storage=storage)

        checkpoint = SwitchCheckpoint(
            checkpoint_id="chk-789",
            switch_id="switch-789",
            context_snapshot={"session_id": "s1", "current_mode": "workflow"},
            mode_before="workflow",
        )
        await storage.save_checkpoint(checkpoint)

        await switcher.rollback_switch("chk-789")

        assert switcher.metrics.rollbacks == 1


# =============================================================================
# Test manual_switch Method
# =============================================================================


class TestManualSwitch:
    """Test ModeSwitcher.manual_switch method."""

    @pytest.mark.asyncio
    async def test_manual_switch_workflow_to_chat(self):
        """Test manual switch from workflow to chat."""
        migrator = MockStateMigrator()
        switcher = ModeSwitcher(state_migrator=migrator)

        result = await switcher.manual_switch(
            session_id="session-123",
            target_mode=ExecutionMode.CHAT_MODE,
            reason="User requested chat mode",
        )

        assert result.success is True
        assert result.new_mode == "chat"
        assert result.trigger is not None
        assert result.trigger.trigger_type == SwitchTriggerType.MANUAL

    @pytest.mark.asyncio
    async def test_manual_switch_chat_to_workflow(self):
        """Test manual switch from chat to workflow."""
        migrator = MockStateMigrator(
            migration_direction=MigrationDirection.CHAT_TO_WORKFLOW
        )
        switcher = ModeSwitcher(state_migrator=migrator)

        result = await switcher.manual_switch(
            session_id="session-456",
            target_mode=ExecutionMode.WORKFLOW_MODE,
            reason="User wants structured workflow",
        )

        assert result.success is True
        assert result.new_mode == "workflow"

    @pytest.mark.asyncio
    async def test_manual_switch_with_context(self):
        """Test manual switch with context."""
        migrator = MockStateMigrator()
        bridge = MockContextBridge()
        switcher = ModeSwitcher(state_migrator=migrator, context_bridge=bridge)

        context = {"workflow_id": "wf-123", "step": 5, "current_mode": "workflow"}
        result = await switcher.manual_switch(
            session_id="session-789",
            target_mode=ExecutionMode.HYBRID_MODE,
            reason="Switch to hybrid",
            context=context,
        )

        assert result.success is True
        assert bridge.update_called is True

    @pytest.mark.asyncio
    async def test_manual_switch_custom_reason(self):
        """Test manual switch with custom reason."""
        switcher = ModeSwitcher()

        result = await switcher.manual_switch(
            session_id="s1",
            target_mode=ExecutionMode.CHAT_MODE,
            reason="Custom reason for switching",
        )

        assert result.success is True
        assert result.trigger.reason == "Custom reason for switching"


# =============================================================================
# Test Detector Management
# =============================================================================


class TestDetectorManagement:
    """Test detector registration and unregistration."""

    def test_register_detector(self):
        """Test registering a detector."""
        switcher = ModeSwitcher()
        detector = MockTriggerDetector()

        switcher.register_detector(detector)

        assert len(switcher.trigger_detectors) == 1
        assert detector in switcher.trigger_detectors

    def test_unregister_detector(self):
        """Test unregistering a detector."""
        detector = MockTriggerDetector()
        switcher = ModeSwitcher(trigger_detectors=[detector])

        switcher.unregister_detector(detector)

        assert len(switcher.trigger_detectors) == 0

    def test_unregister_nonexistent_detector(self):
        """Test unregistering a detector that wasn't registered."""
        switcher = ModeSwitcher()
        detector = MockTriggerDetector()

        # Should not raise
        switcher.unregister_detector(detector)

        assert len(switcher.trigger_detectors) == 0


# =============================================================================
# Test get_transition_history Method
# =============================================================================


class TestGetTransitionHistory:
    """Test ModeSwitcher.get_transition_history method."""

    def test_empty_history(self):
        """Test empty transition history."""
        switcher = ModeSwitcher()
        history = switcher.get_transition_history()
        assert history == []

    @pytest.mark.asyncio
    async def test_history_after_switches(self):
        """Test history after multiple switches."""
        switcher = ModeSwitcher()

        # Perform multiple switches
        for i in range(3):
            await switcher.manual_switch(
                session_id=f"session-{i}",
                target_mode=ExecutionMode.CHAT_MODE,
                reason=f"Switch {i}",
            )

        history = switcher.get_transition_history()
        assert len(history) == 3

    @pytest.mark.asyncio
    async def test_history_filtered_by_session(self):
        """Test history filtering by session ID."""
        switcher = ModeSwitcher()

        await switcher.manual_switch("s1", ExecutionMode.CHAT_MODE, "Switch 1")
        await switcher.manual_switch("s2", ExecutionMode.CHAT_MODE, "Switch 2")
        await switcher.manual_switch("s1", ExecutionMode.WORKFLOW_MODE, "Switch 3")

        history = switcher.get_transition_history(session_id="s1")
        assert len(history) == 2
        assert all(t.session_id == "s1" for t in history)

    @pytest.mark.asyncio
    async def test_history_with_limit(self):
        """Test history with limit."""
        switcher = ModeSwitcher()

        for i in range(10):
            await switcher.manual_switch(f"s{i}", ExecutionMode.CHAT_MODE, f"Switch {i}")

        history = switcher.get_transition_history(limit=5)
        assert len(history) == 5


# =============================================================================
# Test clear_transition_history Method
# =============================================================================


class TestClearTransitionHistory:
    """Test ModeSwitcher.clear_transition_history method."""

    @pytest.mark.asyncio
    async def test_clear_all_history(self):
        """Test clearing all history."""
        switcher = ModeSwitcher()

        await switcher.manual_switch("s1", ExecutionMode.CHAT_MODE, "Switch 1")
        await switcher.manual_switch("s2", ExecutionMode.CHAT_MODE, "Switch 2")

        cleared = switcher.clear_transition_history()

        assert cleared == 2
        assert len(switcher._transition_history) == 0

    @pytest.mark.asyncio
    async def test_clear_session_history(self):
        """Test clearing history for specific session."""
        switcher = ModeSwitcher()

        await switcher.manual_switch("s1", ExecutionMode.CHAT_MODE, "Switch 1")
        await switcher.manual_switch("s2", ExecutionMode.CHAT_MODE, "Switch 2")
        await switcher.manual_switch("s1", ExecutionMode.WORKFLOW_MODE, "Switch 3")

        cleared = switcher.clear_transition_history(session_id="s1")

        assert cleared == 2
        assert len(switcher._transition_history) == 1
        assert switcher._transition_history[0].session_id == "s2"


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_switch_with_none_context(self, switch_trigger):
        """Test switch with None context."""
        switcher = ModeSwitcher()

        result = await switcher.execute_switch(
            trigger=switch_trigger,
            context=None,
        )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_switch_with_empty_session_id(self, switch_trigger):
        """Test switch generates session ID if not provided."""
        switcher = ModeSwitcher()

        result = await switcher.execute_switch(
            trigger=switch_trigger,
            context={},
            session_id=None,
        )

        assert result.success is True
        assert result.switch_id is not None

    @pytest.mark.asyncio
    async def test_concurrent_switches(self):
        """Test handling concurrent switch requests."""
        switcher = ModeSwitcher()

        async def do_switch(session_id: str):
            return await switcher.manual_switch(
                session_id=session_id,
                target_mode=ExecutionMode.CHAT_MODE,
                reason="Concurrent switch",
            )

        results = await asyncio.gather(
            do_switch("s1"),
            do_switch("s2"),
            do_switch("s3"),
        )

        assert all(r.success for r in results)
        assert len(switcher.get_transition_history()) == 3

    @pytest.mark.asyncio
    async def test_detector_exception_handled(self, execution_state):
        """Test exception in detector is handled gracefully."""

        class FailingDetector:
            async def detect(self, *args):
                raise RuntimeError("Detector failed")

        switcher = ModeSwitcher(trigger_detectors=[FailingDetector()])

        # Should not raise, returns None instead
        result = await switcher.should_switch(
            current_mode=ExecutionMode.WORKFLOW_MODE,
            current_state=execution_state,
            new_input="test",
        )

        assert result is None


# =============================================================================
# Test Factory Function
# =============================================================================


class TestCreateModeSwitcher:
    """Test create_mode_switcher factory function."""

    def test_create_with_defaults(self):
        """Test creating switcher with defaults."""
        switcher = create_mode_switcher()

        assert switcher is not None
        assert isinstance(switcher, ModeSwitcher)

    def test_create_with_config(self):
        """Test creating switcher with config."""
        config = SwitchConfig(enable_auto_switch=False)
        switcher = create_mode_switcher(config=config)

        assert switcher.config.enable_auto_switch is False

    def test_create_with_all_dependencies(self):
        """Test creating switcher with all dependencies."""
        config = SwitchConfig()
        detectors = [MockTriggerDetector()]
        migrator = MockStateMigrator()
        storage = InMemoryCheckpointStorage()
        bridge = MockContextBridge()

        switcher = create_mode_switcher(
            config=config,
            trigger_detectors=detectors,
            state_migrator=migrator,
            checkpoint_storage=storage,
            context_bridge=bridge,
        )

        assert switcher.config == config
        assert len(switcher.trigger_detectors) == 1
        assert switcher.state_migrator == migrator
        assert switcher.checkpoint_storage == storage
        assert switcher.context_bridge == bridge


# =============================================================================
# Test Integration Scenarios
# =============================================================================


class TestIntegrationScenarios:
    """Test complete integration scenarios."""

    @pytest.mark.asyncio
    async def test_full_switch_and_rollback_cycle(self):
        """Test complete switch followed by rollback."""
        config = SwitchConfig(enable_rollback=True)
        storage = InMemoryCheckpointStorage()
        migrator = MockStateMigrator()
        switcher = ModeSwitcher(
            config=config,
            checkpoint_storage=storage,
            state_migrator=migrator,
        )

        # Execute switch
        trigger = SwitchTrigger(
            trigger_type=SwitchTriggerType.COMPLEXITY,
            source_mode="workflow",
            target_mode="chat",
            reason="Test switch",
        )

        switch_result = await switcher.execute_switch(
            trigger=trigger,
            context={"original": True, "session_id": "s1"},
            session_id="s1",
        )

        assert switch_result.success is True
        assert switch_result.checkpoint_id is not None

        # Rollback
        rollback_result = await switcher.rollback_switch(switch_result.checkpoint_id)
        assert rollback_result is True

        # Verify history
        history = switcher.get_transition_history()
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_automatic_detection_and_switch(self):
        """Test automatic detection triggering switch."""
        detector = MockTriggerDetector(
            should_trigger=True,
            trigger_type=SwitchTriggerType.COMPLEXITY,
            confidence=0.9,
        )
        migrator = MockStateMigrator()
        switcher = ModeSwitcher(
            trigger_detectors=[detector],
            state_migrator=migrator,
        )

        state = ExecutionState(session_id="s1", current_mode="workflow")

        # Check if should switch
        trigger = await switcher.should_switch(
            current_mode=ExecutionMode.WORKFLOW_MODE,
            current_state=state,
            new_input="complex task requiring AI reasoning",
        )

        assert trigger is not None

        # Execute the switch
        result = await switcher.execute_switch(
            trigger=trigger,
            context={"state": "original"},
            session_id="s1",
        )

        assert result.success is True
        assert result.new_mode == "chat"

    @pytest.mark.asyncio
    async def test_metrics_tracking_across_operations(self):
        """Test metrics are tracked correctly across operations."""
        switcher = ModeSwitcher()

        # Perform switches
        await switcher.manual_switch("s1", ExecutionMode.CHAT_MODE, "Switch 1")
        await switcher.manual_switch("s2", ExecutionMode.WORKFLOW_MODE, "Switch 2")

        metrics = switcher.get_metrics()
        assert metrics.total_switches == 2
        assert metrics.successful_switches == 2

    def test_reset_metrics(self):
        """Test resetting metrics."""
        switcher = ModeSwitcher()
        switcher.metrics.record_switch(True, "test", "test", 100)

        switcher.reset_metrics()

        assert switcher.metrics.total_switches == 0
