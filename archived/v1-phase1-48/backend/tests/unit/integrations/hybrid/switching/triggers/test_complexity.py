# =============================================================================
# IPA Platform - Complexity Trigger Detector Tests
# =============================================================================
# Sprint 56: Mode Switcher & HITL - S56-2 Trigger Detectors
#
# Unit tests for ComplexityTriggerDetector.
# =============================================================================

import pytest
from datetime import datetime

from src.integrations.hybrid.intent.models import ExecutionMode
from src.integrations.hybrid.switching.models import (
    ExecutionState,
    SwitchTriggerType,
)
from src.integrations.hybrid.switching.triggers.complexity import (
    ComplexityConfig,
    ComplexityTriggerDetector,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def detector():
    """Create default complexity detector."""
    return ComplexityTriggerDetector()


@pytest.fixture
def custom_config():
    """Create custom configuration."""
    return ComplexityConfig(
        step_threshold=2,
        tool_threshold=1,
        base_confidence=0.7,
        keyword_confidence_boost=0.15,
    )


@pytest.fixture
def chat_state():
    """Create execution state for chat mode."""
    return ExecutionState(
        session_id="test-session",
        current_mode="chat",
        consecutive_failures=0,
        step_count=0,
        message_count=5,
        tool_call_count=0,
    )


@pytest.fixture
def workflow_state():
    """Create execution state for workflow mode."""
    return ExecutionState(
        session_id="test-session",
        current_mode="workflow",
        consecutive_failures=0,
        step_count=5,
        message_count=10,
        tool_call_count=3,
    )


# =============================================================================
# Test Configuration
# =============================================================================


class TestComplexityConfig:
    """Tests for ComplexityConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ComplexityConfig()
        assert config.step_threshold == 3
        assert config.tool_threshold == 2
        assert config.base_confidence == 0.6
        assert len(config.multi_step_keywords) > 0
        assert len(config.workflow_keywords) > 0
        assert len(config.chat_keywords) > 0

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ComplexityConfig(
            step_threshold=5,
            tool_threshold=3,
            base_confidence=0.8,
        )
        assert config.step_threshold == 5
        assert config.tool_threshold == 3
        assert config.base_confidence == 0.8


# =============================================================================
# Test Detection - Chat to Workflow
# =============================================================================


class TestChatToWorkflowDetection:
    """Tests for detecting switch from Chat to Workflow mode."""

    @pytest.mark.asyncio
    async def test_multi_step_keywords_trigger_switch(self, detector, chat_state):
        """Test that multi-step keywords trigger workflow switch."""
        trigger = await detector.detect(
            ExecutionMode.CHAT_MODE,
            chat_state,
            "I need to create a step by step process for data migration",
        )
        assert trigger is not None
        assert trigger.target_mode == "workflow"
        assert trigger.trigger_type == SwitchTriggerType.COMPLEXITY
        assert trigger.confidence >= 0.6

    @pytest.mark.asyncio
    async def test_workflow_keywords_trigger_switch(self, detector, chat_state):
        """Test that workflow keywords trigger switch."""
        trigger = await detector.detect(
            ExecutionMode.CHAT_MODE,
            chat_state,
            "I want to automate and orchestrate my deployment pipeline",
        )
        assert trigger is not None
        assert trigger.target_mode == "workflow"

    @pytest.mark.asyncio
    async def test_combined_keywords_increase_confidence(self, detector, chat_state):
        """Test that multiple keyword types increase confidence."""
        trigger = await detector.detect(
            ExecutionMode.CHAT_MODE,
            chat_state,
            "First step is to automate the workflow, then integrate with pipeline",
        )
        assert trigger is not None
        assert trigger.confidence >= 0.7  # Higher due to multiple matches

    @pytest.mark.asyncio
    async def test_high_step_count_triggers_switch(self, detector):
        """Test that high step count contributes to workflow switch."""
        state = ExecutionState(
            session_id="test",
            current_mode="chat",
            step_count=5,  # Above default threshold of 3
            tool_call_count=2,
        )
        trigger = await detector.detect(
            ExecutionMode.CHAT_MODE,
            state,
            "Continue with the next steps in the process",
        )
        assert trigger is not None
        assert trigger.target_mode == "workflow"

    @pytest.mark.asyncio
    async def test_simple_question_no_switch(self, detector, chat_state):
        """Test that simple questions don't trigger switch."""
        trigger = await detector.detect(
            ExecutionMode.CHAT_MODE,
            chat_state,
            "What is the weather today?",
        )
        assert trigger is None


# =============================================================================
# Test Detection - Workflow to Chat
# =============================================================================


class TestWorkflowToChatDetection:
    """Tests for detecting switch from Workflow to Chat mode."""

    @pytest.mark.asyncio
    async def test_chat_keywords_trigger_switch(self, detector, workflow_state):
        """Test that chat keywords trigger chat switch."""
        trigger = await detector.detect(
            ExecutionMode.WORKFLOW_MODE,
            workflow_state,
            "Just explain what this does",
        )
        assert trigger is not None
        assert trigger.target_mode == "chat"

    @pytest.mark.asyncio
    async def test_simple_question_triggers_chat_switch(self, detector, workflow_state):
        """Test that simple questions trigger chat switch."""
        trigger = await detector.detect(
            ExecutionMode.WORKFLOW_MODE,
            workflow_state,
            "Quick question - how do I check the status?",
        )
        assert trigger is not None
        assert trigger.target_mode == "chat"

    @pytest.mark.asyncio
    async def test_complex_task_no_switch_in_workflow(self, detector, workflow_state):
        """Test that complex tasks don't trigger switch in workflow mode."""
        trigger = await detector.detect(
            ExecutionMode.WORKFLOW_MODE,
            workflow_state,
            "Execute the next step in the automation pipeline",
        )
        assert trigger is None


# =============================================================================
# Test Configuration Effects
# =============================================================================


class TestConfigurationEffects:
    """Tests for configuration effects on detection."""

    @pytest.mark.asyncio
    async def test_disabled_detector_returns_none(self, chat_state):
        """Test that disabled detector returns None."""
        config = ComplexityConfig(enabled=False)
        detector = ComplexityTriggerDetector(config)

        trigger = await detector.detect(
            ExecutionMode.CHAT_MODE,
            chat_state,
            "Create a step by step workflow automation",
        )
        assert trigger is None

    @pytest.mark.asyncio
    async def test_custom_thresholds(self):
        """Test custom threshold configuration."""
        config = ComplexityConfig(
            step_threshold=10,  # Higher threshold
            tool_threshold=5,
        )
        detector = ComplexityTriggerDetector(config)
        state = ExecutionState(
            session_id="test",
            current_mode="chat",
            step_count=4,  # Below new threshold
        )

        trigger = await detector.detect(
            ExecutionMode.CHAT_MODE,
            state,
            "Continue with the process",
        )
        # Should not trigger with higher thresholds
        assert trigger is None


# =============================================================================
# Test Trigger Properties
# =============================================================================


class TestTriggerProperties:
    """Tests for trigger object properties."""

    @pytest.mark.asyncio
    async def test_trigger_has_correct_type(self, detector, chat_state):
        """Test that trigger has correct type."""
        trigger = await detector.detect(
            ExecutionMode.CHAT_MODE,
            chat_state,
            "Create a multi-step workflow process",
        )
        assert trigger is not None
        assert trigger.trigger_type == SwitchTriggerType.COMPLEXITY

    @pytest.mark.asyncio
    async def test_trigger_has_metadata(self, detector, chat_state):
        """Test that trigger contains metadata."""
        trigger = await detector.detect(
            ExecutionMode.CHAT_MODE,
            chat_state,
            "First step, then second step, finally third step",
        )
        assert trigger is not None
        assert "complexity_score" in trigger.metadata
        assert "multi_step_matches" in trigger.metadata

    @pytest.mark.asyncio
    async def test_trigger_confidence_clamped(self, detector, chat_state):
        """Test that confidence is clamped to valid range."""
        trigger = await detector.detect(
            ExecutionMode.CHAT_MODE,
            chat_state,
            "Step by step workflow process with multiple steps first then finally",
        )
        assert trigger is not None
        assert 0.0 <= trigger.confidence <= 1.0


# =============================================================================
# Test Detector Properties
# =============================================================================


class TestDetectorProperties:
    """Tests for detector object properties."""

    def test_trigger_type(self, detector):
        """Test detector trigger type."""
        assert detector.trigger_type == SwitchTriggerType.COMPLEXITY

    def test_is_enabled(self, detector):
        """Test is_enabled method."""
        assert detector.is_enabled() is True

    def test_get_priority(self, detector):
        """Test get_priority method."""
        assert isinstance(detector.get_priority(), int)

    def test_get_detection_count_initial(self, detector):
        """Test initial detection count is zero."""
        assert detector.get_detection_count() == 0

    @pytest.mark.asyncio
    async def test_detection_count_increments(self, detector, chat_state):
        """Test that detection count increments on trigger."""
        await detector.detect(
            ExecutionMode.CHAT_MODE,
            chat_state,
            "Create step by step workflow automation process",
        )
        assert detector.get_detection_count() == 1

    def test_repr(self, detector):
        """Test string representation."""
        repr_str = repr(detector)
        assert "ComplexityTriggerDetector" in repr_str
        assert "complexity" in repr_str
