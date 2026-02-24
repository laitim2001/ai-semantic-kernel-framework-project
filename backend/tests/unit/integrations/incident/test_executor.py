"""
Unit Tests for IncidentExecutor.

Sprint 126: Story 126-4 — IT Incident Processing (Phase 34)
Tests auto-execution, HITL approval, ServiceNow writeback, and error handling.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.incident.executor import (
    IncidentExecutor,
    SERVICENOW_STATE_IN_PROGRESS,
    SERVICENOW_STATE_RESOLVED,
)
from src.integrations.incident.types import (
    ExecutionResult,
    ExecutionStatus,
    IncidentAnalysis,
    IncidentCategory,
    IncidentContext,
    IncidentSeverity,
    RemediationAction,
    RemediationActionType,
    RemediationRisk,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_context() -> IncidentContext:
    """Create sample incident context."""
    return IncidentContext(
        incident_number="INC0099999",
        severity=IncidentSeverity.P3,
        category=IncidentCategory.STORAGE,
        short_description="Disk space critical on srv-prod-01",
        description="/dev/sda1 at 95% usage",
        affected_components=["srv-prod-01"],
        cmdb_ci="srv-prod-01",
    )


@pytest.fixture
def sample_analysis() -> IncidentAnalysis:
    """Create sample incident analysis."""
    return IncidentAnalysis(
        analysis_id="ana_test001",
        incident_number="INC0099999",
        root_cause_summary="Disk space exhausted by old log files",
        root_cause_confidence=0.85,
    )


@pytest.fixture
def auto_action() -> RemediationAction:
    """Create an auto-executable (LOW risk) action."""
    return RemediationAction(
        action_id="act-auto-001",
        action_type=RemediationActionType.CLEAR_DISK_SPACE,
        title="Clear temp files",
        description="Remove old temp files to free space",
        confidence=0.85,
        risk=RemediationRisk.AUTO,
        mcp_tool="shell:run_command",
        mcp_params={"command": "find /tmp -type f -mtime +7 -delete"},
    )


@pytest.fixture
def high_risk_action() -> RemediationAction:
    """Create a high-risk action requiring HITL approval."""
    return RemediationAction(
        action_id="act-high-001",
        action_type=RemediationActionType.FIREWALL_RULE_CHANGE,
        title="Update firewall rules",
        description="Block suspicious IP range in firewall",
        confidence=0.60,
        risk=RemediationRisk.HIGH,
        mcp_tool="",
        mcp_params={},
    )


@pytest.fixture
def mock_hitl_controller():
    """Create mock HITL controller."""
    controller = MagicMock()
    approval_request = MagicMock()
    approval_request.request_id = "approval-req-001"
    controller.request_approval = AsyncMock(return_value=approval_request)
    return controller


@pytest.fixture
def mock_shell_executor():
    """Create mock shell executor."""
    executor = MagicMock()
    executor.execute = AsyncMock(return_value="Files removed. 2GB freed.")
    return executor


@pytest.fixture
def mock_ldap_executor():
    """Create mock LDAP executor."""
    executor = MagicMock()
    executor.execute = AsyncMock(return_value="Account unlocked successfully")
    return executor


@pytest.fixture
def mock_servicenow_client():
    """Create mock ServiceNow client."""
    client = MagicMock()
    client.update_incident = AsyncMock(return_value=True)
    client.add_work_note = AsyncMock(return_value=True)
    return client


@pytest.fixture
def executor_no_clients(mock_hitl_controller):
    """Create executor with no external clients (simulation mode)."""
    return IncidentExecutor(
        hitl_controller=mock_hitl_controller,
        servicenow_client=None,
        shell_executor=None,
        ldap_executor=None,
    )


@pytest.fixture
def executor_with_clients(
    mock_hitl_controller,
    mock_shell_executor,
    mock_ldap_executor,
    mock_servicenow_client,
):
    """Create executor with all mock clients."""
    return IncidentExecutor(
        hitl_controller=mock_hitl_controller,
        servicenow_client=mock_servicenow_client,
        shell_executor=mock_shell_executor,
        ldap_executor=mock_ldap_executor,
    )


# ---------------------------------------------------------------------------
# Tests: Auto Execution
# ---------------------------------------------------------------------------


class TestAutoExecution:
    """Tests for auto-execution of low-risk actions."""

    @pytest.mark.asyncio
    async def test_auto_execute_low_risk_succeeds(
        self,
        executor_with_clients: IncidentExecutor,
        sample_context: IncidentContext,
        sample_analysis: IncidentAnalysis,
        auto_action: RemediationAction,
    ) -> None:
        """Test auto-execution of LOW/AUTO risk action succeeds."""
        results = await executor_with_clients.execute(
            sample_analysis, sample_context, [auto_action]
        )
        assert len(results) >= 1
        result = results[0]
        assert result.success is True
        assert result.status == ExecutionStatus.COMPLETED
        assert "2GB freed" in result.output

    @pytest.mark.asyncio
    async def test_auto_execute_simulation_mode(
        self,
        executor_no_clients: IncidentExecutor,
        sample_context: IncidentContext,
        sample_analysis: IncidentAnalysis,
        auto_action: RemediationAction,
    ) -> None:
        """Test auto-execution in simulation mode (no shell executor)."""
        results = await executor_no_clients.execute(
            sample_analysis, sample_context, [auto_action]
        )
        assert len(results) >= 1
        result = results[0]
        assert result.success is True
        assert "[Simulated]" in result.output

    @pytest.mark.asyncio
    async def test_auto_execute_shell_failure(
        self,
        mock_hitl_controller,
        sample_context: IncidentContext,
        sample_analysis: IncidentAnalysis,
        auto_action: RemediationAction,
    ) -> None:
        """Test auto-execution handles shell failure."""
        failing_shell = MagicMock()
        failing_shell.execute = AsyncMock(
            side_effect=RuntimeError("Permission denied")
        )
        executor = IncidentExecutor(
            hitl_controller=mock_hitl_controller,
            shell_executor=failing_shell,
        )
        results = await executor.execute(
            sample_analysis, sample_context, [auto_action]
        )
        result = results[0]
        assert result.success is False
        assert result.status == ExecutionStatus.FAILED
        assert "Permission denied" in result.error

    @pytest.mark.asyncio
    async def test_auto_execute_ldap_action(
        self,
        mock_hitl_controller,
        mock_ldap_executor,
        sample_context: IncidentContext,
        sample_analysis: IncidentAnalysis,
    ) -> None:
        """Test auto-execution of LDAP action (AD unlock)."""
        ldap_action = RemediationAction(
            action_id="act-ldap-001",
            action_type=RemediationActionType.AD_ACCOUNT_UNLOCK,
            title="Unlock AD account",
            confidence=0.90,
            risk=RemediationRisk.AUTO,
            mcp_tool="ldap:ad_operations",
            mcp_params={"operation": "account_unlock", "username": "john.doe"},
        )
        executor = IncidentExecutor(
            hitl_controller=mock_hitl_controller,
            ldap_executor=mock_ldap_executor,
        )
        results = await executor.execute(
            sample_analysis, sample_context, [ldap_action]
        )
        result = results[0]
        assert result.success is True
        mock_ldap_executor.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_successful_auto_execute_skips_remaining(
        self,
        executor_no_clients: IncidentExecutor,
        sample_context: IncidentContext,
        sample_analysis: IncidentAnalysis,
    ) -> None:
        """Test successful auto-execute skips remaining actions."""
        action1 = RemediationAction(
            action_id="act-first",
            action_type=RemediationActionType.CLEAR_DISK_SPACE,
            title="First action",
            confidence=0.90,
            risk=RemediationRisk.AUTO,
            mcp_tool="shell:run_command",
            mcp_params={"command": "echo test"},
        )
        action2 = RemediationAction(
            action_id="act-second",
            action_type=RemediationActionType.RESTART_SERVICE,
            title="Second action",
            confidence=0.70,
            risk=RemediationRisk.LOW,
            mcp_tool="shell:run_command",
            mcp_params={"command": "systemctl restart test"},
        )
        results = await executor_no_clients.execute(
            sample_analysis, sample_context, [action1, action2]
        )
        # action1 succeeds (simulated), action2 should be skipped
        assert len(results) == 2
        assert results[0].success is True
        assert results[1].status == ExecutionStatus.SKIPPED


# ---------------------------------------------------------------------------
# Tests: HITL Approval
# ---------------------------------------------------------------------------


class TestHITLApproval:
    """Tests for HITL approval workflow."""

    @pytest.mark.asyncio
    async def test_high_risk_requires_approval(
        self,
        executor_no_clients: IncidentExecutor,
        sample_context: IncidentContext,
        sample_analysis: IncidentAnalysis,
        high_risk_action: RemediationAction,
    ) -> None:
        """Test high-risk action triggers HITL approval request."""
        results = await executor_no_clients.execute(
            sample_analysis, sample_context, [high_risk_action]
        )
        result = results[0]
        assert result.status == ExecutionStatus.AWAITING_APPROVAL
        assert result.success is False
        assert result.approval_request_id == "approval-req-001"

    @pytest.mark.asyncio
    async def test_critical_risk_requires_multi_approval(
        self,
        mock_hitl_controller,
        sample_context: IncidentContext,
        sample_analysis: IncidentAnalysis,
    ) -> None:
        """Test CRITICAL risk uses multi-approver type."""
        critical_action = RemediationAction(
            action_id="act-critical",
            action_type=RemediationActionType.FIREWALL_RULE_CHANGE,
            title="Emergency firewall change",
            confidence=0.50,
            risk=RemediationRisk.CRITICAL,
        )
        executor = IncidentExecutor(hitl_controller=mock_hitl_controller)
        results = await executor.execute(
            sample_analysis, sample_context, [critical_action]
        )
        result = results[0]
        assert result.status == ExecutionStatus.AWAITING_APPROVAL
        # Verify HITL was called
        mock_hitl_controller.request_approval.assert_called_once()

    @pytest.mark.asyncio
    async def test_medium_risk_default_requires_approval(
        self,
        mock_hitl_controller,
        sample_context: IncidentContext,
        sample_analysis: IncidentAnalysis,
    ) -> None:
        """Test MEDIUM risk requires approval by default."""
        medium_action = RemediationAction(
            action_id="act-medium",
            action_type=RemediationActionType.SCALE_RESOURCE,
            title="Scale VM resources",
            confidence=0.70,
            risk=RemediationRisk.MEDIUM,
        )
        executor = IncidentExecutor(
            hitl_controller=mock_hitl_controller,
            auto_execute_medium=False,
        )
        results = await executor.execute(
            sample_analysis, sample_context, [medium_action]
        )
        assert results[0].status == ExecutionStatus.AWAITING_APPROVAL

    @pytest.mark.asyncio
    async def test_medium_risk_auto_execute_when_configured(
        self,
        mock_hitl_controller,
        sample_context: IncidentContext,
        sample_analysis: IncidentAnalysis,
    ) -> None:
        """Test MEDIUM risk auto-executes when auto_execute_medium=True."""
        medium_action = RemediationAction(
            action_id="act-medium",
            action_type=RemediationActionType.RESTART_DATABASE,
            title="Restart database",
            confidence=0.65,
            risk=RemediationRisk.MEDIUM,
            mcp_tool="shell:run_command",
            mcp_params={"command": "systemctl restart postgresql"},
        )
        executor = IncidentExecutor(
            hitl_controller=mock_hitl_controller,
            auto_execute_medium=True,
        )
        results = await executor.execute(
            sample_analysis, sample_context, [medium_action]
        )
        # Should be auto-executed (simulated), not awaiting approval
        assert results[0].status == ExecutionStatus.COMPLETED
        assert results[0].success is True

    @pytest.mark.asyncio
    async def test_hitl_approval_failure_handled(
        self,
        sample_context: IncidentContext,
        sample_analysis: IncidentAnalysis,
        high_risk_action: RemediationAction,
    ) -> None:
        """Test HITL approval request failure is handled gracefully."""
        failing_hitl = MagicMock()
        failing_hitl.request_approval = AsyncMock(
            side_effect=RuntimeError("HITL service unavailable")
        )
        executor = IncidentExecutor(hitl_controller=failing_hitl)
        results = await executor.execute(
            sample_analysis, sample_context, [high_risk_action]
        )
        result = results[0]
        assert result.status == ExecutionStatus.FAILED
        assert "HITL" in result.error


# ---------------------------------------------------------------------------
# Tests: ServiceNow Writeback
# ---------------------------------------------------------------------------


class TestServiceNowWriteback:
    """Tests for ServiceNow writeback integration."""

    @pytest.mark.asyncio
    async def test_writeback_on_success(
        self,
        executor_with_clients: IncidentExecutor,
        mock_servicenow_client,
        sample_context: IncidentContext,
        sample_analysis: IncidentAnalysis,
        auto_action: RemediationAction,
    ) -> None:
        """Test ServiceNow is updated after successful execution."""
        await executor_with_clients.execute(
            sample_analysis, sample_context, [auto_action]
        )
        # Should have called update_incident (in-progress + resolved)
        assert mock_servicenow_client.update_incident.call_count >= 1
        # Should have added work note
        assert mock_servicenow_client.add_work_note.call_count >= 1

    @pytest.mark.asyncio
    async def test_writeback_skipped_without_client(
        self,
        executor_no_clients: IncidentExecutor,
        sample_context: IncidentContext,
        sample_analysis: IncidentAnalysis,
        auto_action: RemediationAction,
    ) -> None:
        """Test ServiceNow writeback is skipped when no client configured."""
        results = await executor_no_clients.execute(
            sample_analysis, sample_context, [auto_action]
        )
        # Should still succeed, just without SN writeback
        assert results[0].success is True

    @pytest.mark.asyncio
    async def test_writeback_failure_does_not_affect_execution(
        self,
        mock_hitl_controller,
        mock_shell_executor,
        sample_context: IncidentContext,
        sample_analysis: IncidentAnalysis,
        auto_action: RemediationAction,
    ) -> None:
        """Test ServiceNow writeback failure doesn't break execution."""
        failing_sn = MagicMock()
        failing_sn.update_incident = AsyncMock(
            side_effect=Exception("SN API error")
        )
        failing_sn.add_work_note = AsyncMock(
            side_effect=Exception("SN API error")
        )
        executor = IncidentExecutor(
            hitl_controller=mock_hitl_controller,
            shell_executor=mock_shell_executor,
            servicenow_client=failing_sn,
        )
        results = await executor.execute(
            sample_analysis, sample_context, [auto_action]
        )
        # Execution should still succeed
        assert results[0].success is True
        assert results[0].servicenow_updated is False


# ---------------------------------------------------------------------------
# Tests: Helper Methods
# ---------------------------------------------------------------------------


class TestExecutorHelpers:
    """Tests for IncidentExecutor helper methods."""

    def test_should_auto_execute_auto_risk(
        self, executor_no_clients: IncidentExecutor
    ) -> None:
        """Test AUTO risk should auto-execute."""
        action = RemediationAction(
            risk=RemediationRisk.AUTO, confidence=0.9
        )
        assert executor_no_clients._should_auto_execute(action) is True

    def test_should_auto_execute_low_risk(
        self, executor_no_clients: IncidentExecutor
    ) -> None:
        """Test LOW risk should auto-execute."""
        action = RemediationAction(
            risk=RemediationRisk.LOW, confidence=0.9
        )
        assert executor_no_clients._should_auto_execute(action) is True

    def test_should_not_auto_execute_high_risk(
        self, executor_no_clients: IncidentExecutor
    ) -> None:
        """Test HIGH risk should NOT auto-execute."""
        action = RemediationAction(
            risk=RemediationRisk.HIGH, confidence=0.9
        )
        assert executor_no_clients._should_auto_execute(action) is False

    def test_risk_to_score(
        self, executor_no_clients: IncidentExecutor
    ) -> None:
        """Test risk to numerical score conversion."""
        assert executor_no_clients._risk_to_score(RemediationRisk.AUTO) == 0.1
        assert executor_no_clients._risk_to_score(RemediationRisk.LOW) == 0.25
        assert executor_no_clients._risk_to_score(RemediationRisk.MEDIUM) == 0.50
        assert executor_no_clients._risk_to_score(RemediationRisk.HIGH) == 0.75
        assert executor_no_clients._risk_to_score(RemediationRisk.CRITICAL) == 1.0

    def test_build_work_note(
        self, executor_no_clients: IncidentExecutor, auto_action: RemediationAction
    ) -> None:
        """Test work note building."""
        result = ExecutionResult(
            execution_id="exec-note-test",
            action=auto_action,
            status=ExecutionStatus.COMPLETED,
            success=True,
            output="Files cleaned up",
        )
        note = executor_no_clients._build_work_note(auto_action, result)
        assert "[SUCCESS]" in note
        assert auto_action.title in note
        assert "exec-note-test" in note

    def test_build_resolution_notes(
        self, executor_no_clients: IncidentExecutor, auto_action: RemediationAction
    ) -> None:
        """Test resolution notes building."""
        results = [
            ExecutionResult(
                action=auto_action,
                status=ExecutionStatus.COMPLETED,
                success=True,
            ),
        ]
        notes = executor_no_clients._build_resolution_notes(results)
        assert "IPA Auto-Remediation Summary" in notes
        assert "1/1 actions completed" in notes
