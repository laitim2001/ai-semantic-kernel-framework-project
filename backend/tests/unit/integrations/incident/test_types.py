"""
Unit Tests for Incident Types and Data Models.

Sprint 126: Story 126-4 — IT Incident Processing (Phase 34)
Tests IncidentContext, IncidentAnalysis, RemediationAction, ExecutionResult,
and all enums (IncidentSeverity, IncidentCategory, RemediationRisk, etc.)
"""

import pytest

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
    """Create a sample IncidentContext."""
    return IncidentContext(
        incident_number="INC0012345",
        severity=IncidentSeverity.P2,
        category=IncidentCategory.NETWORK,
        short_description="Switch port flapping on core-sw-01",
        description="Port Gi0/1 on core-sw-01 is flapping, causing connectivity loss to VLAN 100",
        affected_components=["core-sw-01", "VLAN-100"],
        business_service="ERP System",
        cmdb_ci="core-sw-01",
        raw_event={
            "sys_id": "abc123",
            "number": "INC0012345",
            "priority": "2",
        },
    )


@pytest.fixture
def sample_action() -> RemediationAction:
    """Create a sample RemediationAction."""
    return RemediationAction(
        action_id="act-001",
        action_type=RemediationActionType.RESTART_SERVICE,
        title="Restart port on core-sw-01",
        description="Bounce the flapping port to restore connectivity",
        confidence=0.85,
        risk=RemediationRisk.LOW,
        mcp_tool="shell:run_command",
        mcp_params={"command": "restart_port core-sw-01 Gi0/1"},
        prerequisites=["Verify no active sessions on port"],
        rollback_steps=["Disable port if issue persists"],
    )


@pytest.fixture
def sample_analysis(sample_action: RemediationAction) -> IncidentAnalysis:
    """Create a sample IncidentAnalysis."""
    return IncidentAnalysis(
        analysis_id="analysis-001",
        incident_number="INC0012345",
        root_cause_summary="Port flapping due to duplex mismatch",
        root_cause_confidence=0.90,
        correlations_found=2,
        historical_matches=1,
        contributing_factors=["duplex mismatch", "cable quality"],
        recommended_actions=[sample_action],
        llm_enhanced=True,
    )


# ---------------------------------------------------------------------------
# Enum Tests
# ---------------------------------------------------------------------------


class TestIncidentSeverity:
    """Tests for IncidentSeverity enum."""

    def test_severity_values(self) -> None:
        """Test that all severity levels are defined."""
        assert IncidentSeverity.P1.value == "P1"
        assert IncidentSeverity.P2.value == "P2"
        assert IncidentSeverity.P3.value == "P3"
        assert IncidentSeverity.P4.value == "P4"

    def test_severity_from_string(self) -> None:
        """Test creating severity from string value."""
        sev = IncidentSeverity("P1")
        assert sev == IncidentSeverity.P1

    def test_from_priority_mapping(self) -> None:
        """Test from_priority class method mapping."""
        assert IncidentSeverity.from_priority("1") == IncidentSeverity.P1
        assert IncidentSeverity.from_priority("2") == IncidentSeverity.P2
        assert IncidentSeverity.from_priority("3") == IncidentSeverity.P3
        assert IncidentSeverity.from_priority("4") == IncidentSeverity.P4

    def test_from_priority_unknown_defaults_to_p3(self) -> None:
        """Test unknown priority defaults to P3."""
        assert IncidentSeverity.from_priority("5") == IncidentSeverity.P3
        assert IncidentSeverity.from_priority("unknown") == IncidentSeverity.P3


class TestIncidentCategory:
    """Tests for IncidentCategory enum."""

    def test_all_categories_defined(self) -> None:
        """Test that all expected categories exist."""
        expected = {
            "NETWORK", "SERVER", "APPLICATION", "DATABASE",
            "SECURITY", "STORAGE", "PERFORMANCE", "AUTHENTICATION", "OTHER",
        }
        actual = {cat.name for cat in IncidentCategory}
        assert expected == actual

    def test_category_string_values_lowercase(self) -> None:
        """Test category string values are lowercase."""
        for cat in IncidentCategory:
            assert cat.value == cat.value.lower()

    def test_from_string(self) -> None:
        """Test from_string class method."""
        assert IncidentCategory.from_string("network") == IncidentCategory.NETWORK
        assert IncidentCategory.from_string("SERVER") == IncidentCategory.SERVER

    def test_from_string_unknown_defaults_to_other(self) -> None:
        """Test unknown category defaults to OTHER."""
        assert IncidentCategory.from_string("xyz_unknown") == IncidentCategory.OTHER


class TestRemediationRisk:
    """Tests for RemediationRisk enum."""

    def test_risk_levels(self) -> None:
        """Test all risk levels exist with correct values."""
        assert RemediationRisk.AUTO.value == "auto"
        assert RemediationRisk.LOW.value == "low"
        assert RemediationRisk.MEDIUM.value == "medium"
        assert RemediationRisk.HIGH.value == "high"
        assert RemediationRisk.CRITICAL.value == "critical"


class TestRemediationActionType:
    """Tests for RemediationActionType enum."""

    def test_action_types_defined(self) -> None:
        """Test all action types are defined."""
        expected = {
            "RESTART_SERVICE", "CLEAR_DISK_SPACE", "AD_ACCOUNT_UNLOCK",
            "SCALE_RESOURCE", "NETWORK_ACL_CHANGE", "FIREWALL_RULE_CHANGE",
            "RESTART_DATABASE", "CLEAR_CACHE", "ROTATE_CREDENTIALS", "CUSTOM",
        }
        actual = {at.name for at in RemediationActionType}
        assert expected == actual


class TestExecutionStatus:
    """Tests for ExecutionStatus enum."""

    def test_all_statuses(self) -> None:
        """Test all execution statuses exist."""
        expected = {
            "pending", "executing", "completed", "failed",
            "awaiting_approval", "approved", "rejected", "skipped",
        }
        actual = {s.value for s in ExecutionStatus}
        assert expected == actual


# ---------------------------------------------------------------------------
# Dataclass Tests
# ---------------------------------------------------------------------------


class TestIncidentContext:
    """Tests for IncidentContext dataclass."""

    def test_construction(self, sample_context: IncidentContext) -> None:
        """Test basic construction with all fields."""
        assert sample_context.incident_number == "INC0012345"
        assert sample_context.severity == IncidentSeverity.P2
        assert sample_context.category == IncidentCategory.NETWORK
        assert sample_context.short_description == "Switch port flapping on core-sw-01"
        assert len(sample_context.affected_components) == 2
        assert sample_context.business_service == "ERP System"

    def test_raw_event_preserved(self, sample_context: IncidentContext) -> None:
        """Test raw event dict is preserved."""
        assert sample_context.raw_event["sys_id"] == "abc123"
        assert sample_context.raw_event["priority"] == "2"

    def test_default_values(self) -> None:
        """Test defaults for optional fields."""
        ctx = IncidentContext(
            incident_number="INC001",
            severity=IncidentSeverity.P4,
            category=IncidentCategory.OTHER,
            short_description="Minor issue",
        )
        assert ctx.description == ""
        assert ctx.affected_components == []
        assert ctx.business_service == ""
        assert ctx.cmdb_ci == ""
        assert ctx.assignment_group == ""
        assert ctx.caller_id == ""
        assert ctx.raw_event == {}
        assert ctx.metadata == {}

    def test_to_dict(self, sample_context: IncidentContext) -> None:
        """Test to_dict serialization."""
        d = sample_context.to_dict()
        assert d["incident_number"] == "INC0012345"
        assert d["severity"] == "P2"
        assert d["category"] == "network"
        assert d["short_description"] == "Switch port flapping on core-sw-01"
        assert len(d["affected_components"]) == 2
        assert "created_at" in d


class TestRemediationAction:
    """Tests for RemediationAction dataclass."""

    def test_construction(self, sample_action: RemediationAction) -> None:
        """Test basic construction."""
        assert sample_action.action_id == "act-001"
        assert sample_action.action_type == RemediationActionType.RESTART_SERVICE
        assert sample_action.confidence == 0.85
        assert sample_action.risk == RemediationRisk.LOW

    def test_mcp_tool_mapping(self, sample_action: RemediationAction) -> None:
        """Test MCP tool and params are correctly stored."""
        assert sample_action.mcp_tool == "shell:run_command"
        assert "command" in sample_action.mcp_params

    def test_should_auto_execute_low_risk(self) -> None:
        """Test should_auto_execute returns True for AUTO and LOW risk."""
        action_auto = RemediationAction(
            action_type=RemediationActionType.CLEAR_CACHE,
            risk=RemediationRisk.AUTO,
            confidence=0.9,
        )
        action_low = RemediationAction(
            action_type=RemediationActionType.RESTART_SERVICE,
            risk=RemediationRisk.LOW,
            confidence=0.8,
        )
        assert action_auto.should_auto_execute() is True
        assert action_low.should_auto_execute() is True

    def test_should_auto_execute_high_risk(self) -> None:
        """Test should_auto_execute returns False for MEDIUM+ risk."""
        for risk in [RemediationRisk.MEDIUM, RemediationRisk.HIGH, RemediationRisk.CRITICAL]:
            action = RemediationAction(risk=risk, confidence=0.9)
            assert action.should_auto_execute() is False

    def test_confidence_validation(self) -> None:
        """Test confidence must be between 0.0 and 1.0."""
        with pytest.raises(ValueError, match="confidence must be between"):
            RemediationAction(confidence=1.5)
        with pytest.raises(ValueError, match="confidence must be between"):
            RemediationAction(confidence=-0.1)

    def test_default_values(self) -> None:
        """Test default field values."""
        action = RemediationAction(confidence=0.5)
        assert action.action_type == RemediationActionType.CUSTOM
        assert action.title == ""
        assert action.description == ""
        assert action.mcp_tool == ""
        assert action.mcp_params == {}
        assert action.prerequisites == []
        assert action.rollback_steps == []
        assert action.estimated_duration_seconds == 60

    def test_to_dict(self, sample_action: RemediationAction) -> None:
        """Test to_dict serialization."""
        d = sample_action.to_dict()
        assert d["action_id"] == "act-001"
        assert d["action_type"] == "restart_service"
        assert d["confidence"] == 0.85
        assert d["risk"] == "low"
        assert d["mcp_tool"] == "shell:run_command"


class TestIncidentAnalysis:
    """Tests for IncidentAnalysis dataclass."""

    def test_construction(self, sample_analysis: IncidentAnalysis) -> None:
        """Test basic construction."""
        assert sample_analysis.analysis_id == "analysis-001"
        assert sample_analysis.incident_number == "INC0012345"
        assert sample_analysis.root_cause_confidence == 0.90
        assert sample_analysis.correlations_found == 2
        assert sample_analysis.historical_matches == 1
        assert sample_analysis.llm_enhanced is True

    def test_to_dict(self, sample_analysis: IncidentAnalysis) -> None:
        """Test to_dict serialization."""
        d = sample_analysis.to_dict()
        assert d["analysis_id"] == "analysis-001"
        assert d["root_cause_summary"] == "Port flapping due to duplex mismatch"
        assert d["root_cause_confidence"] == 0.90
        assert d["correlations_found"] == 2
        assert len(d["contributing_factors"]) == 2
        assert len(d["recommended_actions"]) == 1
        assert d["llm_enhanced"] is True

    def test_recommended_actions_serialized(self, sample_analysis: IncidentAnalysis) -> None:
        """Test recommended actions are serialized in to_dict."""
        d = sample_analysis.to_dict()
        action_dict = d["recommended_actions"][0]
        assert action_dict["action_type"] == "restart_service"
        assert action_dict["confidence"] == 0.85

    def test_default_empty_analysis(self) -> None:
        """Test analysis with minimal fields."""
        analysis = IncidentAnalysis(
            analysis_id="analysis-empty",
            root_cause_summary="Unknown",
        )
        assert analysis.root_cause_confidence == 0.0
        assert analysis.correlations_found == 0
        assert analysis.historical_matches == 0
        assert analysis.contributing_factors == []
        assert analysis.recommended_actions == []
        assert analysis.llm_enhanced is False


class TestExecutionResult:
    """Tests for ExecutionResult dataclass."""

    def test_successful_execution(self, sample_action: RemediationAction) -> None:
        """Test successful execution result."""
        result = ExecutionResult(
            execution_id="exec-001",
            action=sample_action,
            status=ExecutionStatus.COMPLETED,
            success=True,
            output="Port restarted successfully",
            servicenow_updated=True,
        )
        assert result.success is True
        assert result.status == ExecutionStatus.COMPLETED
        assert result.output == "Port restarted successfully"
        assert result.servicenow_updated is True

    def test_failed_execution(self, sample_action: RemediationAction) -> None:
        """Test failed execution result."""
        result = ExecutionResult(
            execution_id="exec-002",
            action=sample_action,
            status=ExecutionStatus.FAILED,
            success=False,
            error="Connection timeout to core-sw-01",
        )
        assert result.success is False
        assert result.error == "Connection timeout to core-sw-01"
        assert result.output == ""

    def test_awaiting_approval(self, sample_action: RemediationAction) -> None:
        """Test execution awaiting HITL approval."""
        result = ExecutionResult(
            execution_id="exec-003",
            action=sample_action,
            status=ExecutionStatus.AWAITING_APPROVAL,
            success=False,
            approval_request_id="approval-abc-123",
        )
        assert result.status == ExecutionStatus.AWAITING_APPROVAL
        assert result.approval_request_id == "approval-abc-123"
        assert result.servicenow_updated is False

    def test_to_dict(self, sample_action: RemediationAction) -> None:
        """Test to_dict serialization."""
        result = ExecutionResult(
            execution_id="exec-dict",
            action=sample_action,
            status=ExecutionStatus.COMPLETED,
            success=True,
            output="OK",
        )
        d = result.to_dict()
        assert d["execution_id"] == "exec-dict"
        assert d["status"] == "completed"
        assert d["success"] is True
        assert d["action"] is not None
        assert d["action"]["action_type"] == "restart_service"

    def test_to_dict_no_action(self) -> None:
        """Test to_dict with no action attached."""
        result = ExecutionResult(
            execution_id="exec-no-action",
            status=ExecutionStatus.SKIPPED,
        )
        d = result.to_dict()
        assert d["action"] is None
        assert d["status"] == "skipped"
