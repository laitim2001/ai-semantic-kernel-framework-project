# =============================================================================
# IPA Platform - Sprint 24 Adapter Tests
# =============================================================================
# Sprint 24: S24-5 Tests and Documentation (3 points)
#
# Unit tests for PlanningAdapter and MultiTurnAdapter.
# =============================================================================

import pytest
from datetime import datetime
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch


# =============================================================================
# PlanningAdapter Tests
# =============================================================================

class TestPlanningAdapter:
    """Tests for PlanningAdapter."""

    @pytest.fixture
    def mock_magentic_builder(self):
        """Mock MagenticBuilder."""
        with patch('src.integrations.agent_framework.builders.planning.MagenticBuilder') as mock:
            builder_instance = MagicMock()
            builder_instance.build.return_value = MagicMock()
            mock.return_value = builder_instance
            yield mock

    def test_planning_adapter_import(self):
        """Test that PlanningAdapter can be imported."""
        from src.integrations.agent_framework.builders import (
            PlanningAdapter,
            PlanningMode,
            DecompositionStrategy,
            PlanningConfig,
            PlanStatus,
            create_planning_adapter,
        )

        assert PlanningAdapter is not None
        assert PlanningMode is not None
        assert DecompositionStrategy is not None
        assert PlanningConfig is not None
        assert PlanStatus is not None
        assert create_planning_adapter is not None

    def test_planning_mode_values(self):
        """Test PlanningMode enum values."""
        from src.integrations.agent_framework.builders import PlanningMode

        assert PlanningMode.SIMPLE.value == "simple"
        assert PlanningMode.DECOMPOSED.value == "decomposed"
        assert PlanningMode.DECISION_DRIVEN.value == "decision"  # Actual value is "decision"
        assert PlanningMode.ADAPTIVE.value == "adaptive"
        assert PlanningMode.FULL.value == "full"

    def test_decomposition_strategy_values(self):
        """Test DecompositionStrategy enum values."""
        from src.integrations.agent_framework.builders import DecompositionStrategy

        assert DecompositionStrategy.SEQUENTIAL.value == "sequential"
        assert DecompositionStrategy.HIERARCHICAL.value == "hierarchical"
        assert DecompositionStrategy.PARALLEL.value == "parallel"
        assert DecompositionStrategy.HYBRID.value == "hybrid"

    def test_planning_config_defaults(self):
        """Test PlanningConfig default values."""
        from src.integrations.agent_framework.builders import (
            PlanningConfig,
        )

        config = PlanningConfig()

        # Actual attributes from implementation
        assert config.max_subtasks == 20
        assert config.max_depth == 3
        assert config.timeout_seconds == 300.0
        assert config.require_approval is False
        assert config.enable_learning is False

    def test_decision_rule_creation(self):
        """Test DecisionRule creation."""
        from src.integrations.agent_framework.builders import DecisionRule

        rule = DecisionRule(
            name="test_rule",
            condition="input.priority > 5",
            action="escalate",
            priority=1,
        )

        assert rule.name == "test_rule"
        assert rule.condition == "input.priority > 5"
        assert rule.action == "escalate"
        assert rule.priority == 1

    def test_planning_result_dataclass(self):
        """Test PlanningResult dataclass."""
        from src.integrations.agent_framework.builders import (
            PlanningResult,
            PlanStatus,
        )

        result = PlanningResult(
            plan_id="test-plan-1",
            goal="Test goal",
            status=PlanStatus.COMPLETED,
            subtasks=[],  # Actual attribute name
            decisions=[],
            duration_ms=100,
        )

        assert result.plan_id == "test-plan-1"
        assert result.goal == "Test goal"
        assert result.status == PlanStatus.COMPLETED
        assert result.duration_ms == 100

    def test_create_simple_planner(self, mock_magentic_builder):
        """Test create_simple_planner factory function."""
        from src.integrations.agent_framework.builders import create_simple_planner

        adapter = create_simple_planner("simple-planner")

        assert adapter is not None
        assert adapter._id == "simple-planner"

    def test_create_decomposed_planner(self, mock_magentic_builder):
        """Test create_decomposed_planner factory function."""
        from src.integrations.agent_framework.builders import (
            create_decomposed_planner,
            DecompositionStrategy,
        )

        adapter = create_decomposed_planner(
            id="decomposed-planner",
            strategy=DecompositionStrategy.HIERARCHICAL,
        )

        assert adapter is not None
        assert adapter._id == "decomposed-planner"


# =============================================================================
# MultiTurnAdapter Tests
# =============================================================================

class TestMultiTurnAdapter:
    """Tests for MultiTurnAdapter."""

    @pytest.fixture
    def mock_checkpoint_storage(self):
        """Mock CheckpointStorage."""
        with patch('src.integrations.agent_framework.multiturn.adapter.InMemoryCheckpointStorage') as mock:
            storage_instance = MagicMock()
            storage_instance.save = AsyncMock()
            storage_instance.load = AsyncMock(return_value=None)
            storage_instance.delete = AsyncMock(return_value=True)
            mock.return_value = storage_instance
            yield mock

    def test_multiturn_adapter_import(self):
        """Test that MultiTurnAdapter can be imported."""
        from src.integrations.agent_framework.multiturn import (
            MultiTurnAdapter,
            TurnResult,
            SessionState,
            SessionInfo,
            MultiTurnConfig,
            create_multiturn_adapter,
        )

        assert MultiTurnAdapter is not None
        assert TurnResult is not None
        assert SessionState is not None
        assert SessionInfo is not None
        assert MultiTurnConfig is not None
        assert create_multiturn_adapter is not None

    def test_session_state_values(self):
        """Test SessionState enum values."""
        from src.integrations.agent_framework.multiturn import SessionState

        assert SessionState.CREATED.value == "created"
        assert SessionState.ACTIVE.value == "active"
        assert SessionState.PAUSED.value == "paused"
        assert SessionState.COMPLETED.value == "completed"

    def test_message_role_values(self):
        """Test MessageRole enum values."""
        from src.integrations.agent_framework.multiturn import MessageRole

        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"
        assert MessageRole.SYSTEM.value == "system"

    def test_context_scope_values(self):
        """Test ContextScope enum values."""
        from src.integrations.agent_framework.multiturn import ContextScope

        assert ContextScope.TURN.value == "turn"
        assert ContextScope.SESSION.value == "session"
        assert ContextScope.PERSISTENT.value == "persistent"

    def test_multiturn_config_defaults(self):
        """Test MultiTurnConfig default values."""
        from src.integrations.agent_framework.multiturn import MultiTurnConfig

        config = MultiTurnConfig()

        assert config.max_turns == 100
        assert config.max_history_length == 50
        assert config.session_timeout_seconds == 3600
        assert config.auto_save is True

    def test_message_creation(self):
        """Test Message creation."""
        from src.integrations.agent_framework.multiturn import Message, MessageRole

        message = Message(
            role=MessageRole.USER,
            content="Hello, how are you?",
        )

        assert message.role == MessageRole.USER
        assert message.content == "Hello, how are you?"
        assert message.timestamp is not None

    def test_message_to_dict(self):
        """Test Message to_dict method."""
        from src.integrations.agent_framework.multiturn import Message, MessageRole

        message = Message(
            role=MessageRole.ASSISTANT,
            content="I'm doing well!",
            metadata={"token_count": 5},
        )

        result = message.to_dict()

        assert result["role"] == "assistant"
        assert result["content"] == "I'm doing well!"
        assert result["metadata"] == {"token_count": 5}
        assert "timestamp" in result

    def test_context_manager_operations(self):
        """Test ContextManager operations."""
        from src.integrations.agent_framework.multiturn import (
            ContextManager,
            ContextScope,
        )

        manager = ContextManager()

        # Set values in different scopes
        manager.set("user_id", "user-123", ContextScope.SESSION)
        manager.set("current_intent", "greeting", ContextScope.TURN)
        manager.set("language", "en", ContextScope.PERSISTENT)

        # Get values
        assert manager.get("user_id") == "user-123"
        assert manager.get("current_intent") == "greeting"
        assert manager.get("language") == "en"
        assert manager.get("nonexistent", "default") == "default"

    def test_context_manager_scope_priority(self):
        """Test ContextManager scope priority (turn > session > persistent)."""
        from src.integrations.agent_framework.multiturn import (
            ContextManager,
            ContextScope,
        )

        manager = ContextManager()

        # Set same key in different scopes
        manager.set("key", "persistent", ContextScope.PERSISTENT)
        manager.set("key", "session", ContextScope.SESSION)
        manager.set("key", "turn", ContextScope.TURN)

        # Turn scope should take priority
        assert manager.get("key") == "turn"

        # Clear turn scope
        manager.clear_turn()
        assert manager.get("key") == "session"

        # Clear session scope
        manager.clear_session()
        assert manager.get("key") == "persistent"

    def test_turn_tracker_operations(self):
        """Test TurnTracker operations."""
        from src.integrations.agent_framework.multiturn import (
            TurnTracker,
            Message,
            MessageRole,
        )

        tracker = TurnTracker(max_history=10)

        # Add messages
        tracker.add_message(Message(role=MessageRole.USER, content="Hello"))
        tracker.add_message(Message(role=MessageRole.ASSISTANT, content="Hi there!"))

        assert len(tracker.history) == 2
        assert tracker.current_turn == 0

    def test_turn_tracker_max_history(self):
        """Test TurnTracker respects max_history limit."""
        from src.integrations.agent_framework.multiturn import (
            TurnTracker,
            Message,
            MessageRole,
        )

        tracker = TurnTracker(max_history=5)

        # Add more messages than max_history
        for i in range(10):
            tracker.add_message(Message(role=MessageRole.USER, content=f"Message {i}"))

        # Should only keep last 5 messages
        assert len(tracker.history) == 5
        assert tracker.history[0].content == "Message 5"
        assert tracker.history[4].content == "Message 9"

    def test_create_multiturn_adapter(self, mock_checkpoint_storage):
        """Test create_multiturn_adapter factory function."""
        from src.integrations.agent_framework.multiturn import create_multiturn_adapter

        adapter = create_multiturn_adapter(session_id="test-session")

        assert adapter is not None
        assert adapter.session_id == "test-session"
        assert adapter.state == "created"

    @pytest.mark.asyncio
    async def test_multiturn_adapter_lifecycle(self, mock_checkpoint_storage):
        """Test MultiTurnAdapter lifecycle operations."""
        from src.integrations.agent_framework.multiturn import (
            MultiTurnAdapter,
            SessionState,
        )

        adapter = MultiTurnAdapter(session_id="lifecycle-test")

        # Initial state
        assert adapter.state == SessionState.CREATED

        # Start session
        await adapter.start()
        assert adapter.state == SessionState.ACTIVE

        # Pause session
        await adapter.pause()
        assert adapter.state == SessionState.PAUSED

        # Resume session
        await adapter.resume()
        assert adapter.state == SessionState.ACTIVE

        # Complete session
        info = await adapter.complete()
        assert adapter.state == SessionState.COMPLETED
        assert info is not None

    @pytest.mark.asyncio
    async def test_multiturn_adapter_add_turn(self, mock_checkpoint_storage):
        """Test MultiTurnAdapter add_turn operation."""
        from src.integrations.agent_framework.multiturn import MultiTurnAdapter

        adapter = MultiTurnAdapter(session_id="turn-test")
        await adapter.start()

        # Add a turn
        result = await adapter.add_turn(
            user_input="What is the weather?",
            assistant_response="The weather is sunny today.",
        )

        assert result.success is True
        assert result.session_id == "turn-test"
        assert result.input_message.content == "What is the weather?"
        assert result.output_message.content == "The weather is sunny today."

    @pytest.mark.asyncio
    async def test_multiturn_adapter_get_history(self, mock_checkpoint_storage):
        """Test MultiTurnAdapter get_history operation."""
        from src.integrations.agent_framework.multiturn import MultiTurnAdapter

        adapter = MultiTurnAdapter(session_id="history-test")
        await adapter.start()

        # Add turns
        await adapter.add_turn("Hello", "Hi!")
        await adapter.add_turn("How are you?", "I'm great!")

        # Get history
        history = adapter.get_history()
        assert len(history) == 4  # 2 user + 2 assistant messages

        # Get limited history
        limited = adapter.get_history(n=2)
        assert len(limited) == 2


# =============================================================================
# CheckpointStorage Tests
# =============================================================================

class TestCheckpointStorage:
    """Tests for CheckpointStorage implementations."""

    def test_checkpoint_storage_import(self):
        """Test that CheckpointStorage classes can be imported."""
        from src.integrations.agent_framework.multiturn import (
            BaseCheckpointStorage,
            RedisCheckpointStorage,
            PostgresCheckpointStorage,
            FileCheckpointStorage,
        )

        assert BaseCheckpointStorage is not None
        assert RedisCheckpointStorage is not None
        assert PostgresCheckpointStorage is not None
        assert FileCheckpointStorage is not None

    @pytest.mark.asyncio
    async def test_file_checkpoint_storage_save_load(self, tmp_path):
        """Test FileCheckpointStorage save and load operations."""
        from src.integrations.agent_framework.multiturn import FileCheckpointStorage

        storage = FileCheckpointStorage(base_path=str(tmp_path))

        # Save state
        test_state = {"history": ["msg1", "msg2"], "context": {"user_id": "test"}}
        await storage.save("session-1", test_state)

        # Load state
        loaded = await storage.load("session-1")
        assert loaded is not None
        assert loaded["history"] == ["msg1", "msg2"]
        assert loaded["context"]["user_id"] == "test"

    @pytest.mark.asyncio
    async def test_file_checkpoint_storage_delete(self, tmp_path):
        """Test FileCheckpointStorage delete operation."""
        from src.integrations.agent_framework.multiturn import FileCheckpointStorage

        storage = FileCheckpointStorage(base_path=str(tmp_path))

        # Save and delete
        await storage.save("session-2", {"test": "data"})
        result = await storage.delete("session-2")
        assert result is True

        # Verify deleted
        loaded = await storage.load("session-2")
        assert loaded is None

    @pytest.mark.asyncio
    async def test_file_checkpoint_storage_list(self, tmp_path):
        """Test FileCheckpointStorage list operation."""
        from src.integrations.agent_framework.multiturn import FileCheckpointStorage

        storage = FileCheckpointStorage(base_path=str(tmp_path))

        # Save multiple sessions
        await storage.save("session-a", {"data": 1})
        await storage.save("session-b", {"data": 2})
        await storage.save("session-c", {"data": 3})

        # List all sessions
        sessions = await storage.list()
        assert len(sessions) == 3
        assert "session-a" in sessions
        assert "session-b" in sessions
        assert "session-c" in sessions


# =============================================================================
# Integration Tests
# =============================================================================

class TestSprint24Integration:
    """Integration tests for Sprint 24 adapters."""

    def test_builders_init_exports(self):
        """Test that builders/__init__.py exports Sprint 24 components."""
        from src.integrations.agent_framework.builders import (
            # Sprint 24: PlanningAdapter
            PlanningAdapter,
            DecompositionStrategy,
            PlanningMode,
            PlanStatus,
            DecisionRule,
            PlanningConfig,
            PlanningResult,
            create_planning_adapter,
            create_simple_planner,
            create_decomposed_planner,
            create_full_planner,
            # Sprint 24: MultiTurnAdapter
            MultiTurnAdapter,
            TurnResult,
            SessionState,
            create_multiturn_adapter,
            create_redis_multiturn_adapter,
            RedisCheckpointStorage,
            PostgresCheckpointStorage,
            FileCheckpointStorage,
        )

        # All imports should be successful
        assert True

    def test_multiturn_init_exports(self):
        """Test that multiturn/__init__.py exports all components."""
        from src.integrations.agent_framework.multiturn import (
            MultiTurnAdapter,
            TurnResult,
            SessionState,
            SessionInfo,
            MultiTurnConfig,
            Message,
            MessageRole,
            ContextScope,
            ContextManager,
            TurnTracker,
            create_multiturn_adapter,
            create_redis_multiturn_adapter,
            BaseCheckpointStorage,
            RedisCheckpointStorage,
            PostgresCheckpointStorage,
            FileCheckpointStorage,
        )

        # All imports should be successful
        assert True
