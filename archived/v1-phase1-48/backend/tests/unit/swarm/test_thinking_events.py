"""
Test suite for Extended Thinking events.

Sprint 104: ExtendedThinking + 工具調用展示優化
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

from src.integrations.swarm.models import (
    ThinkingContent,
    WorkerStatus,
    SwarmMode,
    WorkerType,
)
from src.integrations.swarm.tracker import SwarmTracker, get_swarm_tracker
from src.integrations.swarm.swarm_integration import SwarmIntegration


# =============================================================================
# ThinkingContent Model Tests
# =============================================================================

class TestThinkingContentModel:
    """Tests for ThinkingContent dataclass."""

    def test_create_thinking_content_basic(self):
        """Test basic ThinkingContent creation."""
        thinking = ThinkingContent(
            content="Analyzing the problem...",
            timestamp=datetime.now(),
        )

        assert thinking.content == "Analyzing the problem..."
        assert thinking.timestamp is not None
        assert thinking.token_count is None

    def test_create_thinking_content_with_token_count(self):
        """Test ThinkingContent creation with token count."""
        thinking = ThinkingContent(
            content="Let me think about this step by step.",
            timestamp=datetime.now(),
            token_count=42,
        )

        assert thinking.content == "Let me think about this step by step."
        assert thinking.token_count == 42

    def test_thinking_content_to_dict(self):
        """Test ThinkingContent serialization to dict."""
        now = datetime.now()
        thinking = ThinkingContent(
            content="Test content",
            timestamp=now,
            token_count=100,
        )

        result = thinking.to_dict()

        assert result["content"] == "Test content"
        assert "timestamp" in result
        assert result["token_count"] == 100

    def test_thinking_content_from_dict(self):
        """Test ThinkingContent deserialization from dict."""
        data = {
            "content": "Deserialized content",
            "timestamp": datetime.now().isoformat(),
            "token_count": 50,
        }

        thinking = ThinkingContent.from_dict(data)

        assert thinking.content == "Deserialized content"
        assert thinking.token_count == 50


# =============================================================================
# SwarmTracker Thinking Tests
# =============================================================================

class TestSwarmTrackerThinking:
    """Tests for SwarmTracker thinking-related methods."""

    @pytest.fixture
    def tracker(self):
        """Create a fresh SwarmTracker for each test."""
        return SwarmTracker()

    @pytest.fixture
    def tracker_with_swarm_and_worker(self, tracker):
        """Create tracker with a swarm and worker ready for thinking tests."""
        tracker.create_swarm("swarm-1", SwarmMode.PARALLEL)
        tracker.start_worker(
            swarm_id="swarm-1",
            worker_id="worker-1",
            worker_name="Test Worker",
            worker_type=WorkerType.RESEARCH,
            role="Analyzer",
        )
        return tracker

    def test_add_worker_thinking_basic(self, tracker_with_swarm_and_worker):
        """Test adding basic thinking content to a worker."""
        tracker = tracker_with_swarm_and_worker

        thinking = tracker.add_worker_thinking(
            swarm_id="swarm-1",
            worker_id="worker-1",
            content="First, I need to understand the problem.",
        )

        assert thinking is not None
        assert thinking.content == "First, I need to understand the problem."
        assert thinking.token_count is None

    def test_add_worker_thinking_with_token_count(self, tracker_with_swarm_and_worker):
        """Test adding thinking content with token count."""
        tracker = tracker_with_swarm_and_worker

        thinking = tracker.add_worker_thinking(
            swarm_id="swarm-1",
            worker_id="worker-1",
            content="Analyzing data patterns...",
            token_count=25,
        )

        assert thinking.token_count == 25

    def test_add_worker_thinking_updates_status(self, tracker_with_swarm_and_worker):
        """Test that adding thinking updates worker status to THINKING."""
        tracker = tracker_with_swarm_and_worker

        tracker.add_worker_thinking(
            swarm_id="swarm-1",
            worker_id="worker-1",
            content="Deep analysis...",
        )

        worker = tracker.get_worker("swarm-1", "worker-1")
        assert worker.status == WorkerStatus.THINKING

    def test_add_multiple_thinking_blocks(self, tracker_with_swarm_and_worker):
        """Test adding multiple thinking blocks."""
        tracker = tracker_with_swarm_and_worker

        tracker.add_worker_thinking(
            swarm_id="swarm-1",
            worker_id="worker-1",
            content="First thought.",
            token_count=10,
        )
        tracker.add_worker_thinking(
            swarm_id="swarm-1",
            worker_id="worker-1",
            content="Second thought.",
            token_count=15,
        )
        tracker.add_worker_thinking(
            swarm_id="swarm-1",
            worker_id="worker-1",
            content="Third thought.",
            token_count=20,
        )

        worker = tracker.get_worker("swarm-1", "worker-1")
        assert len(worker.thinking_contents) == 3
        assert worker.thinking_contents[0].content == "First thought."
        assert worker.thinking_contents[2].content == "Third thought."

    def test_add_worker_thinking_invalid_swarm(self, tracker):
        """Test adding thinking to non-existent swarm raises error."""
        with pytest.raises(Exception):  # SwarmNotFoundError
            tracker.add_worker_thinking(
                swarm_id="nonexistent",
                worker_id="worker-1",
                content="Test",
            )

    def test_add_worker_thinking_invalid_worker(self, tracker):
        """Test adding thinking to non-existent worker raises error."""
        tracker.create_swarm("swarm-1", SwarmMode.SEQUENTIAL)

        with pytest.raises(Exception):  # WorkerNotFoundError
            tracker.add_worker_thinking(
                swarm_id="swarm-1",
                worker_id="nonexistent",
                content="Test",
            )


# =============================================================================
# SwarmIntegration Thinking Tests
# =============================================================================

class TestSwarmIntegrationThinking:
    """Tests for SwarmIntegration thinking callback."""

    @pytest.fixture
    def integration(self):
        """Create SwarmIntegration with a fresh tracker."""
        tracker = SwarmTracker()
        return SwarmIntegration(tracker=tracker)

    @pytest.fixture
    def integration_with_active_swarm(self, integration):
        """Create integration with an active swarm and worker."""
        integration.on_coordination_started(
            swarm_id="coord-1",
            mode=SwarmMode.PARALLEL,
            subtasks=[{"id": "sub-1", "description": "Test task"}],
        )
        integration.on_subtask_started(
            swarm_id="coord-1",
            worker_id="worker-1",
            worker_name="Research Worker",
            worker_type=WorkerType.RESEARCH,
            role="Data Analyzer",
            task_description="Analyze the data",
        )
        return integration

    def test_on_thinking_creates_thinking_content(self, integration_with_active_swarm):
        """Test on_thinking callback creates ThinkingContent."""
        integration = integration_with_active_swarm

        result = integration.on_thinking(
            swarm_id="coord-1",
            worker_id="worker-1",
            content="Processing the input data...",
        )

        assert result is not None
        assert result.content == "Processing the input data..."

    def test_on_thinking_with_token_count(self, integration_with_active_swarm):
        """Test on_thinking with token count."""
        integration = integration_with_active_swarm

        result = integration.on_thinking(
            swarm_id="coord-1",
            worker_id="worker-1",
            content="Detailed analysis step.",
            token_count=35,
        )

        assert result.token_count == 35

    def test_on_thinking_updates_tracker(self, integration_with_active_swarm):
        """Test that on_thinking updates the underlying tracker."""
        integration = integration_with_active_swarm

        integration.on_thinking(
            swarm_id="coord-1",
            worker_id="worker-1",
            content="Thinking content",
        )

        worker = integration.tracker.get_worker("coord-1", "worker-1")
        assert len(worker.thinking_contents) == 1
        assert worker.thinking_contents[0].content == "Thinking content"


# =============================================================================
# Thinking Event Flow Tests
# =============================================================================

class TestThinkingEventFlow:
    """Tests for the complete thinking event flow."""

    @pytest.fixture
    def mock_callback(self):
        """Create a mock callback for tracking events."""
        return MagicMock()

    def test_thinking_triggers_worker_update_callback(self, mock_callback):
        """Test that adding thinking triggers on_worker_update callback."""
        tracker = SwarmTracker(on_worker_update=mock_callback)

        tracker.create_swarm("swarm-1", SwarmMode.SEQUENTIAL)
        tracker.start_worker(
            swarm_id="swarm-1",
            worker_id="worker-1",
            worker_name="Test",
            worker_type=WorkerType.ANALYST,
            role="Tester",
        )

        tracker.add_worker_thinking(
            swarm_id="swarm-1",
            worker_id="worker-1",
            content="Thinking...",
        )

        # Callback should have been called
        assert mock_callback.called

    def test_complete_thinking_flow(self, mock_callback):
        """Test complete flow: start -> thinking -> tool call -> complete."""
        tracker = SwarmTracker(
            on_worker_update=mock_callback,
        )

        # Start swarm
        tracker.create_swarm("swarm-1", SwarmMode.SEQUENTIAL)

        # Start worker
        tracker.start_worker(
            swarm_id="swarm-1",
            worker_id="worker-1",
            worker_name="Agent",
            worker_type=WorkerType.CODER,
            role="Developer",
        )

        # Add thinking
        thinking1 = tracker.add_worker_thinking(
            swarm_id="swarm-1",
            worker_id="worker-1",
            content="Let me analyze this code...",
            token_count=20,
        )

        # Add more thinking
        thinking2 = tracker.add_worker_thinking(
            swarm_id="swarm-1",
            worker_id="worker-1",
            content="I should use a recursive approach.",
            token_count=30,
        )

        # Now do a tool call
        tracker.add_worker_tool_call(
            swarm_id="swarm-1",
            worker_id="worker-1",
            tool_id="tool-1",
            tool_name="write_file",
            is_mcp=False,
            input_params={"path": "solution.py"},
        )

        # Complete tool call
        tracker.update_tool_call_result(
            swarm_id="swarm-1",
            worker_id="worker-1",
            tool_id="tool-1",
            result={"success": True},
        )

        # Complete worker
        tracker.complete_worker("swarm-1", "worker-1")

        # Verify final state
        worker = tracker.get_worker("swarm-1", "worker-1")
        assert len(worker.thinking_contents) == 2
        assert worker.thinking_contents[0].token_count == 20
        assert worker.thinking_contents[1].token_count == 30
        assert worker.status == WorkerStatus.COMPLETED


# =============================================================================
# Token Counting Tests
# =============================================================================

class TestThinkingTokenCounting:
    """Tests for thinking content token counting."""

    def test_token_count_accumulation(self):
        """Test that token counts accumulate correctly across thinking blocks."""
        tracker = SwarmTracker()
        tracker.create_swarm("swarm-1", SwarmMode.PARALLEL)
        tracker.start_worker(
            swarm_id="swarm-1",
            worker_id="worker-1",
            worker_name="Test",
            worker_type=WorkerType.ANALYST,
            role="Counter",
        )

        # Add multiple thinking blocks with token counts
        tracker.add_worker_thinking("swarm-1", "worker-1", "Block 1", token_count=100)
        tracker.add_worker_thinking("swarm-1", "worker-1", "Block 2", token_count=150)
        tracker.add_worker_thinking("swarm-1", "worker-1", "Block 3", token_count=200)

        worker = tracker.get_worker("swarm-1", "worker-1")
        total_tokens = sum(
            t.token_count for t in worker.thinking_contents
            if t.token_count is not None
        )

        assert total_tokens == 450

    def test_mixed_token_count_and_none(self):
        """Test handling of mixed token counts (some None)."""
        tracker = SwarmTracker()
        tracker.create_swarm("swarm-1", SwarmMode.SEQUENTIAL)
        tracker.start_worker(
            swarm_id="swarm-1",
            worker_id="worker-1",
            worker_name="Test",
            worker_type=WorkerType.WRITER,
            role="Writer",
        )

        tracker.add_worker_thinking("swarm-1", "worker-1", "With count", token_count=50)
        tracker.add_worker_thinking("swarm-1", "worker-1", "Without count")  # None
        tracker.add_worker_thinking("swarm-1", "worker-1", "With count again", token_count=75)

        worker = tracker.get_worker("swarm-1", "worker-1")

        assert worker.thinking_contents[0].token_count == 50
        assert worker.thinking_contents[1].token_count is None
        assert worker.thinking_contents[2].token_count == 75
