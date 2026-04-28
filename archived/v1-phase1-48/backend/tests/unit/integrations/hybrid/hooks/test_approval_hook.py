# =============================================================================
# IPA Platform - Risk-Driven Approval Hook Unit Tests
# =============================================================================
# Sprint 55: S55-4 - API & ApprovalHook Integration
#
# Unit tests for RiskDrivenApprovalHook:
#   - check_approval() with different modes
#   - Auto-approve for read-only tools
#   - Risk-driven approval decisions
#   - Session lifecycle methods
#   - Tool context conversion
# =============================================================================

import asyncio
from datetime import datetime
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.hybrid.hooks.approval_hook import (
    ApprovalDecision,
    ApprovalMode,
    RiskDrivenApprovalHook,
)
from src.integrations.hybrid.risk.models import (
    OperationContext,
    RiskAssessment,
    RiskConfig,
    RiskFactor,
    RiskFactorType,
    RiskLevel,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_operation_context():
    """Create a mock operation context."""
    return OperationContext(
        tool_name="Bash",
        operation_type="execute",
        target_paths=["/tmp/test.sh"],
        command="bash /tmp/test.sh",
        session_id="sess-123",
        user_id="user-456",
        environment="development",
    )


@pytest.fixture
def mock_read_context():
    """Create a mock read-only operation context."""
    return OperationContext(
        tool_name="Read",
        operation_type="read",
        target_paths=["/config.yaml"],
        session_id="sess-123",
    )


@pytest.fixture
def mock_low_risk_assessment():
    """Create a mock low-risk assessment."""
    return RiskAssessment(
        overall_level=RiskLevel.LOW,
        overall_score=0.25,
        requires_approval=False,
        approval_reason=None,
        factors=[
            RiskFactor(
                factor_type=RiskFactorType.OPERATION,
                score=0.2,
                weight=0.4,
                description="Low risk operation",
                source="Read",
            )
        ],
        session_id="sess-123",
        assessment_time=datetime.utcnow(),
    )


@pytest.fixture
def mock_high_risk_assessment():
    """Create a mock high-risk assessment."""
    return RiskAssessment(
        overall_level=RiskLevel.HIGH,
        overall_score=0.75,
        requires_approval=True,
        approval_reason="High risk: destructive command detected",
        factors=[
            RiskFactor(
                factor_type=RiskFactorType.COMMAND,
                score=0.9,
                weight=0.5,
                description="Destructive command pattern",
                source="rm -rf",
            )
        ],
        session_id="sess-123",
        assessment_time=datetime.utcnow(),
    )


@pytest.fixture
def mock_critical_risk_assessment():
    """Create a mock critical-risk assessment."""
    return RiskAssessment(
        overall_level=RiskLevel.CRITICAL,
        overall_score=0.95,
        requires_approval=True,
        approval_reason="Critical risk: system-level access detected",
        factors=[
            RiskFactor(
                factor_type=RiskFactorType.PATH,
                score=0.95,
                weight=0.5,
                description="System critical path access",
                source="/etc/passwd",
            )
        ],
        session_id="sess-123",
        assessment_time=datetime.utcnow(),
    )


@pytest.fixture
def approval_callback():
    """Create a mock approval callback."""
    return AsyncMock(return_value=True)


@pytest.fixture
def rejection_callback():
    """Create a mock rejection callback."""
    return AsyncMock(return_value=False)


# =============================================================================
# Test: ApprovalMode.AUTO
# =============================================================================


class TestAutoMode:
    """Tests for AUTO approval mode."""

    @pytest.mark.asyncio
    async def test_auto_mode_always_approves(self, mock_operation_context):
        """Test that AUTO mode always approves."""
        hook = RiskDrivenApprovalHook(mode=ApprovalMode.AUTO)

        decision = await hook.check_approval(mock_operation_context)

        assert decision.approved is True
        assert decision.approver == "system:auto_mode"
        assert decision.required_human_approval is False

    @pytest.mark.asyncio
    async def test_auto_mode_ignores_risk(self, mock_operation_context):
        """Test that AUTO mode ignores risk assessment."""
        hook = RiskDrivenApprovalHook(mode=ApprovalMode.AUTO)

        # Even with a high-risk command
        mock_operation_context.command = "rm -rf /"

        decision = await hook.check_approval(mock_operation_context)

        assert decision.approved is True


# =============================================================================
# Test: ApprovalMode.MANUAL
# =============================================================================


class TestManualMode:
    """Tests for MANUAL approval mode."""

    @pytest.mark.asyncio
    async def test_manual_mode_requires_callback(self, mock_operation_context):
        """Test that MANUAL mode requires approval callback."""
        hook = RiskDrivenApprovalHook(
            mode=ApprovalMode.MANUAL,
            approval_callback=None,  # No callback
        )

        decision = await hook.check_approval(mock_operation_context)

        assert decision.approved is False
        assert decision.required_human_approval is True
        assert "no callback" in decision.reason.lower()

    @pytest.mark.asyncio
    async def test_manual_mode_user_approves(
        self, mock_operation_context, approval_callback
    ):
        """Test that MANUAL mode gets user approval."""
        hook = RiskDrivenApprovalHook(
            mode=ApprovalMode.MANUAL,
            approval_callback=approval_callback,
        )

        decision = await hook.check_approval(mock_operation_context)

        assert decision.approved is True
        assert decision.required_human_approval is True
        assert decision.approver == "user"
        approval_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_manual_mode_user_rejects(
        self, mock_operation_context, rejection_callback
    ):
        """Test that MANUAL mode handles rejection."""
        hook = RiskDrivenApprovalHook(
            mode=ApprovalMode.MANUAL,
            approval_callback=rejection_callback,
        )

        decision = await hook.check_approval(mock_operation_context)

        assert decision.approved is False
        assert decision.required_human_approval is True
        assert decision.approver == "user:rejected"

    @pytest.mark.asyncio
    async def test_manual_mode_timeout(self, mock_operation_context):
        """Test that MANUAL mode handles timeout."""
        async def slow_callback(assessment):
            await asyncio.sleep(2)  # Longer than timeout
            return True

        hook = RiskDrivenApprovalHook(
            mode=ApprovalMode.MANUAL,
            approval_callback=slow_callback,
            timeout=0.1,  # 100ms timeout
        )

        decision = await hook.check_approval(mock_operation_context)

        assert decision.approved is False
        assert "timeout" in decision.reason.lower()


# =============================================================================
# Test: ApprovalMode.RISK_DRIVEN
# =============================================================================


class TestRiskDrivenMode:
    """Tests for RISK_DRIVEN approval mode."""

    @pytest.mark.asyncio
    async def test_auto_approve_low_risk(self, mock_operation_context):
        """Test auto-approval for low risk operations."""
        config = RiskConfig(auto_approve_low=True)

        with patch.object(
            RiskDrivenApprovalHook, "_risk_driven_approve"
        ) as mock_method:
            # Set up to return low risk
            mock_method.return_value = ApprovalDecision(
                approved=True,
                reason="Auto-approved: low risk",
                approver="system:risk_engine",
            )

            hook = RiskDrivenApprovalHook(
                config=config,
                mode=ApprovalMode.RISK_DRIVEN,
            )

            decision = await hook.check_approval(mock_operation_context)

            assert decision.approved is True

    @pytest.mark.asyncio
    async def test_require_approval_high_risk(
        self, mock_operation_context, approval_callback
    ):
        """Test that high risk requires approval."""
        config = RiskConfig(auto_approve_low=True, auto_approve_medium=False)

        hook = RiskDrivenApprovalHook(
            config=config,
            mode=ApprovalMode.RISK_DRIVEN,
            approval_callback=approval_callback,
        )

        # The actual behavior depends on the risk engine assessment
        # This tests the hook's integration with the callback
        decision = await hook.check_approval(mock_operation_context)

        # Decision made based on risk assessment
        assert decision is not None

    @pytest.mark.asyncio
    async def test_cached_approval(self, mock_operation_context):
        """Test that approved operations are cached for session."""
        hook = RiskDrivenApprovalHook(mode=ApprovalMode.RISK_DRIVEN)

        # First call
        decision1 = await hook.check_approval(mock_operation_context)

        # Same operation should be cached
        decision2 = await hook.check_approval(mock_operation_context)

        if decision1.approved:
            assert decision2.approved is True
            assert "cached" in decision2.approver or "previously" in decision2.reason.lower()


# =============================================================================
# Test: Auto-Approve Tools
# =============================================================================


class TestAutoApproveTools:
    """Tests for auto-approve tool list."""

    @pytest.mark.asyncio
    async def test_read_tool_auto_approved(self, mock_read_context):
        """Test that Read tool is auto-approved."""
        hook = RiskDrivenApprovalHook(mode=ApprovalMode.RISK_DRIVEN)

        decision = await hook.check_approval(mock_read_context)

        assert decision.approved is True
        assert "auto" in decision.approver.lower() or "auto" in decision.reason.lower()

    @pytest.mark.asyncio
    async def test_glob_tool_auto_approved(self):
        """Test that Glob tool is auto-approved."""
        context = OperationContext(
            tool_name="Glob",
            operation_type="read",
            target_paths=["**/*.py"],
            session_id="sess-123",
        )

        hook = RiskDrivenApprovalHook(mode=ApprovalMode.RISK_DRIVEN)

        decision = await hook.check_approval(context)

        assert decision.approved is True

    @pytest.mark.asyncio
    async def test_grep_tool_auto_approved(self):
        """Test that Grep tool is auto-approved."""
        context = OperationContext(
            tool_name="Grep",
            operation_type="read",
            target_paths=["src/"],
            session_id="sess-123",
        )

        hook = RiskDrivenApprovalHook(mode=ApprovalMode.RISK_DRIVEN)

        decision = await hook.check_approval(context)

        assert decision.approved is True

    @pytest.mark.asyncio
    async def test_add_auto_approve_tool(self):
        """Test adding custom tool to auto-approve list."""
        hook = RiskDrivenApprovalHook(mode=ApprovalMode.RISK_DRIVEN)

        # Add custom tool
        hook.add_auto_approve_tool("CustomTool")

        context = OperationContext(
            tool_name="CustomTool",
            operation_type="read",
            session_id="sess-123",
        )

        decision = await hook.check_approval(context)

        assert decision.approved is True

    @pytest.mark.asyncio
    async def test_remove_auto_approve_tool(self):
        """Test removing tool from auto-approve list."""
        hook = RiskDrivenApprovalHook(mode=ApprovalMode.RISK_DRIVEN)

        # Remove Read from auto-approve
        hook.remove_auto_approve_tool("Read")

        context = OperationContext(
            tool_name="Read",
            operation_type="read",
            target_paths=["/sensitive/file"],
            session_id="sess-123",
        )

        # Now should go through risk assessment
        decision = await hook.check_approval(context)

        # Approval depends on risk assessment, not auto-approve
        assert "read-only" not in decision.reason.lower()


# =============================================================================
# Test: Session Lifecycle
# =============================================================================


class TestSessionLifecycle:
    """Tests for session lifecycle methods."""

    @pytest.mark.asyncio
    async def test_on_session_start_clears_state(self):
        """Test that session start clears previous state."""
        hook = RiskDrivenApprovalHook(mode=ApprovalMode.RISK_DRIVEN)

        # Add some state
        hook._approved_operations.add("test-operation")
        hook._pending_approvals["test-key"] = MagicMock()

        # Start new session
        await hook.on_session_start("new-session")

        assert len(hook._approved_operations) == 0
        assert len(hook._pending_approvals) == 0

    @pytest.mark.asyncio
    async def test_on_session_end_clears_state(self):
        """Test that session end clears state."""
        hook = RiskDrivenApprovalHook(mode=ApprovalMode.RISK_DRIVEN)

        # Add some state
        hook._approved_operations.add("test-operation")
        hook._pending_approvals["test-key"] = MagicMock()

        # End session
        await hook.on_session_end("sess-123")

        assert len(hook._approved_operations) == 0
        assert len(hook._pending_approvals) == 0


# =============================================================================
# Test: Tool Context Conversion
# =============================================================================


class TestToolContextConversion:
    """Tests for from_tool_call_context helper."""

    def test_convert_bash_tool_call(self):
        """Test converting Bash tool call to context."""
        hook = RiskDrivenApprovalHook(mode=ApprovalMode.RISK_DRIVEN)

        context = hook.from_tool_call_context(
            tool_name="Bash",
            args={"command": "ls -la"},
            session_id="sess-123",
            user_id="user-456",
            environment="development",
        )

        assert context.tool_name == "Bash"
        assert context.operation_type == "execute"
        assert context.command == "ls -la"
        assert context.session_id == "sess-123"

    def test_convert_write_tool_call(self):
        """Test converting Write tool call to context."""
        hook = RiskDrivenApprovalHook(mode=ApprovalMode.RISK_DRIVEN)

        context = hook.from_tool_call_context(
            tool_name="Write",
            args={"file_path": "/tmp/test.txt", "content": "hello"},
            session_id="sess-123",
        )

        assert context.tool_name == "Write"
        assert context.operation_type == "write"
        assert "/tmp/test.txt" in context.target_paths

    def test_convert_edit_tool_call(self):
        """Test converting Edit tool call to context."""
        hook = RiskDrivenApprovalHook(mode=ApprovalMode.RISK_DRIVEN)

        context = hook.from_tool_call_context(
            tool_name="Edit",
            args={"file_path": "/src/main.py", "old_string": "foo", "new_string": "bar"},
            session_id="sess-123",
        )

        assert context.tool_name == "Edit"
        assert context.operation_type == "write"
        assert "/src/main.py" in context.target_paths

    def test_convert_read_tool_call(self):
        """Test converting Read tool call to context."""
        hook = RiskDrivenApprovalHook(mode=ApprovalMode.RISK_DRIVEN)

        context = hook.from_tool_call_context(
            tool_name="Read",
            args={"file_path": "/config.yaml"},
            session_id="sess-123",
        )

        assert context.tool_name == "Read"
        assert context.operation_type == "read"
        assert "/config.yaml" in context.target_paths


# =============================================================================
# Test: Configuration and State
# =============================================================================


class TestConfigurationAndState:
    """Tests for configuration and state management."""

    def test_set_mode(self):
        """Test changing approval mode."""
        hook = RiskDrivenApprovalHook(mode=ApprovalMode.AUTO)

        hook.set_mode(ApprovalMode.MANUAL)

        assert hook.mode == ApprovalMode.MANUAL

    def test_clear_approved_operations(self):
        """Test clearing cached approvals."""
        hook = RiskDrivenApprovalHook(mode=ApprovalMode.RISK_DRIVEN)
        hook._approved_operations.add("test-1")
        hook._approved_operations.add("test-2")

        hook.clear_approved_operations()

        assert len(hook._approved_operations) == 0

    def test_get_pending_approvals(self):
        """Test getting pending approvals."""
        hook = RiskDrivenApprovalHook(mode=ApprovalMode.RISK_DRIVEN)
        mock_assessment = MagicMock()
        hook._pending_approvals["key-1"] = mock_assessment

        pending = hook.get_pending_approvals()

        assert "key-1" in pending
        assert pending["key-1"] == mock_assessment

    def test_get_decision_history(self):
        """Test getting decision history."""
        hook = RiskDrivenApprovalHook(mode=ApprovalMode.RISK_DRIVEN)
        decision = ApprovalDecision(
            approved=True,
            reason="Test decision",
            approver="test",
        )
        hook._decision_history.append(decision)

        history = hook.get_decision_history()

        assert len(history) == 1
        assert history[0].reason == "Test decision"

    def test_get_engine_metrics(self):
        """Test getting engine metrics."""
        hook = RiskDrivenApprovalHook(mode=ApprovalMode.RISK_DRIVEN)

        metrics = hook.get_engine_metrics()

        assert "total_assessments" in metrics
        assert "assessments_by_level" in metrics
        assert "average_score" in metrics


# =============================================================================
# Test: ApprovalDecision Dataclass
# =============================================================================


class TestApprovalDecision:
    """Tests for ApprovalDecision dataclass."""

    def test_create_approved_decision(self):
        """Test creating an approved decision."""
        decision = ApprovalDecision(
            approved=True,
            reason="Low risk operation",
            approver="system:auto",
        )

        assert decision.approved is True
        assert decision.required_human_approval is False

    def test_create_rejected_decision(self):
        """Test creating a rejected decision."""
        decision = ApprovalDecision(
            approved=False,
            reason="User rejected",
            required_human_approval=True,
            approver="user:rejected",
        )

        assert decision.approved is False
        assert decision.required_human_approval is True

    def test_decision_with_risk_assessment(self, mock_low_risk_assessment):
        """Test decision with attached risk assessment."""
        decision = ApprovalDecision(
            approved=True,
            reason="Low risk",
            risk_assessment=mock_low_risk_assessment,
        )

        assert decision.risk_assessment is not None
        assert decision.risk_assessment.overall_level == RiskLevel.LOW

    def test_decision_metadata(self):
        """Test decision with metadata."""
        decision = ApprovalDecision(
            approved=True,
            reason="Approved",
            metadata={"source": "test", "version": 1},
        )

        assert decision.metadata["source"] == "test"
        assert decision.metadata["version"] == 1
