# =============================================================================
# IPA Platform - Failure Trigger Detector Tests
# =============================================================================
# Sprint 56: Mode Switcher & HITL - S56-2 Trigger Detectors
#
# Unit tests for FailureTriggerDetector.
# =============================================================================

import pytest
from datetime import datetime

from src.integrations.hybrid.intent.models import ExecutionMode
from src.integrations.hybrid.switching.models import (
    ExecutionState,
    SwitchTriggerType,
)
from src.integrations.hybrid.switching.triggers.failure import (
    FailureConfig,
    FailureTriggerDetector,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def detector():
    """Create default failure detector."""
    return FailureTriggerDetector()


@pytest.fixture
def custom_config():
    """Create custom configuration."""
    return FailureConfig(
        failure_threshold=2,
        base_confidence=0.8,
        confidence_per_failure=0.05,
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


# =============================================================================
# Test Configuration
# =============================================================================


class TestFailureConfig:
    """Tests for FailureConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = FailureConfig()
        assert config.failure_threshold == 3
        assert config.base_confidence == 0.7
        assert config.confidence_per_failure == 0.1
        assert len(config.error_keywords) > 0
        assert "error" in config.error_keywords
        assert "failed" in config.error_keywords

    def test_custom_values(self):
        """Test custom configuration values."""
        config = FailureConfig(
            failure_threshold=5,
            base_confidence=0.8,
            confidence_per_failure=0.05,
        )
        assert config.failure_threshold == 5
        assert config.base_confidence == 0.8
        assert config.confidence_per_failure == 0.05


# =============================================================================
# Test Detection - Workflow to Chat (Failure Recovery)
# =============================================================================


class TestWorkflowFailureDetection:
    """Tests for detecting switch from Workflow to Chat on failures."""

    @pytest.mark.asyncio
    async def test_consecutive_failures_trigger_switch(self, detector):
        """Test that consecutive failures above threshold trigger switch."""
        state = ExecutionState(
            session_id="test",
            current_mode="workflow",
            consecutive_failures=3,  # Meets threshold
        )
        trigger = await detector.detect(
            ExecutionMode.WORKFLOW_MODE,
            state,
            "The process keeps failing",
        )
        assert trigger is not None
        assert trigger.target_mode == "chat"
        assert trigger.trigger_type == SwitchTriggerType.FAILURE
        assert trigger.confidence >= 0.7

    @pytest.mark.asyncio
    async def test_failures_below_threshold_no_switch(self, detector, workflow_state):
        """Test that failures below threshold don't trigger switch."""
        workflow_state.consecutive_failures = 2  # Below threshold
        trigger = await detector.detect(
            ExecutionMode.WORKFLOW_MODE,
            workflow_state,
            "Continue with next step",
        )
        assert trigger is None

    @pytest.mark.asyncio
    async def test_error_keywords_lower_threshold(self, detector):
        """Test that error keywords in input can lower effective threshold."""
        state = ExecutionState(
            session_id="test",
            current_mode="workflow",
            consecutive_failures=2,  # One below threshold
        )
        # Multiple error keywords should help trigger
        trigger = await detector.detect(
            ExecutionMode.WORKFLOW_MODE,
            state,
            "This is broken, there's an error and it's not working",
        )
        assert trigger is not None
        assert trigger.target_mode == "chat"

    @pytest.mark.asyncio
    async def test_high_failures_increase_confidence(self, detector):
        """Test that more failures increase confidence."""
        state = ExecutionState(
            session_id="test",
            current_mode="workflow",
            consecutive_failures=5,  # Well above threshold
        )
        trigger = await detector.detect(
            ExecutionMode.WORKFLOW_MODE,
            state,
            "This keeps failing",
        )
        assert trigger is not None
        assert trigger.confidence >= 0.8  # Higher due to extra failures


# =============================================================================
# Test Detection - Chat to Workflow (Structured Recovery)
# =============================================================================


class TestChatFailureDetection:
    """Tests for detecting switch from Chat to Workflow on failures."""

    @pytest.mark.asyncio
    async def test_chat_failures_trigger_workflow_switch(self, detector):
        """Test that consecutive failures in chat trigger workflow switch."""
        state = ExecutionState(
            session_id="test",
            current_mode="chat",
            consecutive_failures=3,
        )
        trigger = await detector.detect(
            ExecutionMode.CHAT_MODE,
            state,
            "Help, nothing is working",
        )
        assert trigger is not None
        assert trigger.target_mode == "workflow"
        assert "recovery" in trigger.reason.lower()

    @pytest.mark.asyncio
    async def test_chat_recovery_type_is_workflow(self, detector):
        """Test that recovery type in metadata is 'structured workflow'."""
        state = ExecutionState(
            session_id="test",
            current_mode="chat",
            consecutive_failures=4,
        )
        trigger = await detector.detect(
            ExecutionMode.CHAT_MODE,
            state,
            "I need help fixing this problem",
        )
        assert trigger is not None
        assert trigger.metadata.get("recovery_type") == "structured workflow"


# =============================================================================
# Test Error Keyword Detection
# =============================================================================


class TestErrorKeywordDetection:
    """Tests for error keyword detection in user input."""

    @pytest.mark.asyncio
    async def test_single_error_keyword_detected(self, detector):
        """Test detection of single error keyword."""
        state = ExecutionState(
            session_id="test",
            current_mode="workflow",
            consecutive_failures=3,
        )
        trigger = await detector.detect(
            ExecutionMode.WORKFLOW_MODE,
            state,
            "There is an error in the process",
        )
        assert trigger is not None
        assert trigger.metadata.get("error_keyword_count", 0) >= 1

    @pytest.mark.asyncio
    async def test_multiple_error_keywords_detected(self, detector):
        """Test detection of multiple error keywords."""
        state = ExecutionState(
            session_id="test",
            current_mode="workflow",
            consecutive_failures=3,
        )
        trigger = await detector.detect(
            ExecutionMode.WORKFLOW_MODE,
            state,
            "The process failed, it's broken and not working at all",
        )
        assert trigger is not None
        assert trigger.metadata.get("error_keyword_count", 0) >= 3

    @pytest.mark.asyncio
    async def test_case_insensitive_keyword_matching(self, detector):
        """Test that keyword matching is case-insensitive."""
        state = ExecutionState(
            session_id="test",
            current_mode="workflow",
            consecutive_failures=3,
        )
        trigger = await detector.detect(
            ExecutionMode.WORKFLOW_MODE,
            state,
            "ERROR: The system is BROKEN",
        )
        assert trigger is not None
        assert trigger.metadata.get("error_keyword_count", 0) >= 2


# =============================================================================
# Test Configuration Effects
# =============================================================================


class TestConfigurationEffects:
    """Tests for configuration effects on detection."""

    @pytest.mark.asyncio
    async def test_disabled_detector_returns_none(self):
        """Test that disabled detector returns None."""
        config = FailureConfig(enabled=False)
        detector = FailureTriggerDetector(config)
        state = ExecutionState(
            session_id="test",
            current_mode="workflow",
            consecutive_failures=10,
        )
        trigger = await detector.detect(
            ExecutionMode.WORKFLOW_MODE,
            state,
            "Everything is failing",
        )
        assert trigger is None

    @pytest.mark.asyncio
    async def test_custom_threshold(self):
        """Test custom failure threshold."""
        config = FailureConfig(failure_threshold=5)
        detector = FailureTriggerDetector(config)

        # Below new threshold
        state = ExecutionState(
            session_id="test",
            current_mode="workflow",
            consecutive_failures=4,
        )
        trigger = await detector.detect(
            ExecutionMode.WORKFLOW_MODE,
            state,
            "Continue",
        )
        assert trigger is None

        # At new threshold
        state.consecutive_failures = 5
        trigger = await detector.detect(
            ExecutionMode.WORKFLOW_MODE,
            state,
            "Continue",
        )
        assert trigger is not None


# =============================================================================
# Test Trigger Properties
# =============================================================================


class TestTriggerProperties:
    """Tests for trigger object properties."""

    @pytest.mark.asyncio
    async def test_trigger_has_correct_type(self, detector):
        """Test that trigger has correct type."""
        state = ExecutionState(
            session_id="test",
            current_mode="workflow",
            consecutive_failures=3,
        )
        trigger = await detector.detect(
            ExecutionMode.WORKFLOW_MODE,
            state,
            "This workflow keeps failing",
        )
        assert trigger is not None
        assert trigger.trigger_type == SwitchTriggerType.FAILURE

    @pytest.mark.asyncio
    async def test_trigger_has_metadata(self, detector):
        """Test that trigger contains metadata."""
        state = ExecutionState(
            session_id="test",
            current_mode="workflow",
            consecutive_failures=4,
        )
        trigger = await detector.detect(
            ExecutionMode.WORKFLOW_MODE,
            state,
            "Error occurred, please help",
        )
        assert trigger is not None
        assert "consecutive_failures" in trigger.metadata
        assert "error_keyword_count" in trigger.metadata
        assert "recovery_type" in trigger.metadata

    @pytest.mark.asyncio
    async def test_trigger_confidence_clamped(self, detector):
        """Test that confidence is clamped to valid range."""
        state = ExecutionState(
            session_id="test",
            current_mode="workflow",
            consecutive_failures=20,  # Very high
        )
        trigger = await detector.detect(
            ExecutionMode.WORKFLOW_MODE,
            state,
            "error error error error error",  # Many keywords
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
        assert detector.trigger_type == SwitchTriggerType.FAILURE

    def test_is_enabled(self, detector):
        """Test is_enabled method."""
        assert detector.is_enabled() is True

    def test_get_priority(self, detector):
        """Test get_priority method."""
        priority = detector.get_priority()
        assert isinstance(priority, int)
        assert priority == 10  # Failure has high priority

    def test_get_detection_count_initial(self, detector):
        """Test initial detection count is zero."""
        assert detector.get_detection_count() == 0

    @pytest.mark.asyncio
    async def test_detection_count_increments(self, detector):
        """Test that detection count increments on trigger."""
        state = ExecutionState(
            session_id="test",
            current_mode="workflow",
            consecutive_failures=3,
        )
        await detector.detect(
            ExecutionMode.WORKFLOW_MODE,
            state,
            "Failed again, need help",
        )
        assert detector.get_detection_count() == 1

    def test_repr(self, detector):
        """Test string representation."""
        repr_str = repr(detector)
        assert "FailureTriggerDetector" in repr_str
        assert "failure" in repr_str
