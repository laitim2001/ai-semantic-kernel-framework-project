"""
IT Incident Handling Types — Core Data Structures.

Sprint 126: Story 126-2 — IT Incident Processing Scenario (Phase 34)

Defines the core data types used across the incident handling pipeline:
    - IncidentContext: Normalized incident information
    - RemediationAction: Suggested/executed remediation action
    - IncidentAnalysis: Analysis result from IncidentAnalyzer
    - ExecutionResult: Result from IncidentExecutor
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


# =============================================================================
# Enums
# =============================================================================


class IncidentSeverity(str, Enum):
    """ServiceNow incident severity (Priority 1-4)."""

    P1 = "P1"  # Critical
    P2 = "P2"  # High
    P3 = "P3"  # Medium
    P4 = "P4"  # Low

    @classmethod
    def from_priority(cls, priority: str) -> "IncidentSeverity":
        """Convert ServiceNow priority string to IncidentSeverity.

        Args:
            priority: ServiceNow priority ("1", "2", "3", "4")

        Returns:
            Corresponding IncidentSeverity
        """
        mapping = {"1": cls.P1, "2": cls.P2, "3": cls.P3, "4": cls.P4}
        return mapping.get(str(priority).strip(), cls.P3)


class IncidentCategory(str, Enum):
    """Incident category classification."""

    NETWORK = "network"
    SERVER = "server"
    APPLICATION = "application"
    DATABASE = "database"
    SECURITY = "security"
    STORAGE = "storage"
    PERFORMANCE = "performance"
    AUTHENTICATION = "authentication"
    OTHER = "other"

    @classmethod
    def from_string(cls, value: str) -> "IncidentCategory":
        """Convert string to IncidentCategory.

        Args:
            value: Category string (case-insensitive)

        Returns:
            Corresponding IncidentCategory, defaults to OTHER
        """
        try:
            return cls(value.lower().strip())
        except ValueError:
            return cls.OTHER


class RemediationRisk(str, Enum):
    """Risk level for a remediation action."""

    AUTO = "auto"  # Fully automated, no approval needed
    LOW = "low"  # Low risk, auto-execute
    MEDIUM = "medium"  # Medium risk, may need approval
    HIGH = "high"  # High risk, requires HITL approval
    CRITICAL = "critical"  # Critical risk, requires multi-approver HITL


class RemediationActionType(str, Enum):
    """Pre-defined remediation action types."""

    RESTART_SERVICE = "restart_service"
    CLEAR_DISK_SPACE = "clear_disk_space"
    AD_ACCOUNT_UNLOCK = "ad_account_unlock"
    SCALE_RESOURCE = "scale_resource"
    NETWORK_ACL_CHANGE = "network_acl_change"
    FIREWALL_RULE_CHANGE = "firewall_rule_change"
    RESTART_DATABASE = "restart_database"
    CLEAR_CACHE = "clear_cache"
    ROTATE_CREDENTIALS = "rotate_credentials"
    CUSTOM = "custom"


class ExecutionStatus(str, Enum):
    """Status of a remediation action execution."""

    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    SKIPPED = "skipped"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class IncidentContext:
    """Normalized incident context for analysis.

    Attributes:
        incident_number: ServiceNow INC number (e.g., INC0012345)
        severity: Incident severity (P1-P4)
        category: Classified incident category
        short_description: Brief incident description
        description: Full incident description
        affected_components: List of affected CI/services
        business_service: Impacted business service
        cmdb_ci: Configuration item from CMDB
        assignment_group: Assignment group name
        caller_id: User who reported the incident
        raw_event: Original ServiceNow event data
        created_at: Incident creation timestamp
        metadata: Additional context metadata
    """

    incident_number: str
    severity: IncidentSeverity
    category: IncidentCategory
    short_description: str
    description: str = ""
    affected_components: List[str] = field(default_factory=list)
    business_service: str = ""
    cmdb_ci: str = ""
    assignment_group: str = ""
    caller_id: str = ""
    raw_event: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "incident_number": self.incident_number,
            "severity": self.severity.value,
            "category": self.category.value,
            "short_description": self.short_description,
            "description": self.description,
            "affected_components": self.affected_components,
            "business_service": self.business_service,
            "cmdb_ci": self.cmdb_ci,
            "assignment_group": self.assignment_group,
            "caller_id": self.caller_id,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class RemediationAction:
    """A single remediation action with risk assessment and MCP tool mapping.

    Attributes:
        action_id: Unique action identifier
        action_type: Pre-defined action type
        title: Human-readable action title
        description: Detailed action description
        confidence: Confidence score (0.0-1.0) that this action will resolve the incident
        risk: Risk level of this action
        mcp_tool: MCP tool identifier for execution (e.g., "shell:run_command")
        mcp_params: Parameters for the MCP tool call
        prerequisites: Conditions that must be met before execution
        rollback_steps: Steps to undo this action if it fails
        estimated_duration_seconds: Estimated time to complete
        metadata: Additional action metadata
    """

    action_id: str = field(default_factory=lambda: f"act_{uuid4().hex[:12]}")
    action_type: RemediationActionType = RemediationActionType.CUSTOM
    title: str = ""
    description: str = ""
    confidence: float = 0.0
    risk: RemediationRisk = RemediationRisk.MEDIUM
    mcp_tool: str = ""
    mcp_params: Dict[str, Any] = field(default_factory=dict)
    prerequisites: List[str] = field(default_factory=list)
    rollback_steps: List[str] = field(default_factory=list)
    estimated_duration_seconds: int = 60
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate confidence range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {self.confidence}")

    def should_auto_execute(self) -> bool:
        """Check if this action can be auto-executed without HITL approval.

        Returns:
            True if risk is AUTO or LOW
        """
        return self.risk in (RemediationRisk.AUTO, RemediationRisk.LOW)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "title": self.title,
            "description": self.description,
            "confidence": self.confidence,
            "risk": self.risk.value,
            "mcp_tool": self.mcp_tool,
            "mcp_params": self.mcp_params,
            "prerequisites": self.prerequisites,
            "rollback_steps": self.rollback_steps,
            "estimated_duration_seconds": self.estimated_duration_seconds,
            "metadata": self.metadata,
        }


@dataclass
class IncidentAnalysis:
    """Complete incident analysis result.

    Attributes:
        analysis_id: Unique analysis identifier
        incident_number: Related incident number
        root_cause_summary: Identified root cause description
        root_cause_confidence: Confidence in root cause identification (0.0-1.0)
        correlations_found: Number of correlated events found
        historical_matches: Number of similar historical incidents
        contributing_factors: List of contributing factor descriptions
        recommended_actions: Ranked list of remediation actions
        analysis_duration_ms: Time taken for analysis in milliseconds
        llm_enhanced: Whether LLM was used for enhanced analysis
        metadata: Additional analysis metadata
    """

    analysis_id: str = field(default_factory=lambda: f"ana_{uuid4().hex[:12]}")
    incident_number: str = ""
    root_cause_summary: str = ""
    root_cause_confidence: float = 0.0
    correlations_found: int = 0
    historical_matches: int = 0
    contributing_factors: List[str] = field(default_factory=list)
    recommended_actions: List[RemediationAction] = field(default_factory=list)
    analysis_duration_ms: int = 0
    llm_enhanced: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "analysis_id": self.analysis_id,
            "incident_number": self.incident_number,
            "root_cause_summary": self.root_cause_summary,
            "root_cause_confidence": self.root_cause_confidence,
            "correlations_found": self.correlations_found,
            "historical_matches": self.historical_matches,
            "contributing_factors": self.contributing_factors,
            "recommended_actions": [a.to_dict() for a in self.recommended_actions],
            "analysis_duration_ms": self.analysis_duration_ms,
            "llm_enhanced": self.llm_enhanced,
            "metadata": self.metadata,
        }


@dataclass
class ExecutionResult:
    """Result of executing a remediation action.

    Attributes:
        execution_id: Unique execution identifier
        action: The executed remediation action
        status: Current execution status
        success: Whether the action succeeded
        output: Command/action output text
        error: Error message if failed
        started_at: Execution start timestamp
        completed_at: Execution completion timestamp
        approval_request_id: HITL approval request ID (if applicable)
        servicenow_updated: Whether ServiceNow was updated with results
        metadata: Additional execution metadata
    """

    execution_id: str = field(default_factory=lambda: f"exec_{uuid4().hex[:12]}")
    action: Optional[RemediationAction] = None
    status: ExecutionStatus = ExecutionStatus.PENDING
    success: bool = False
    output: str = ""
    error: str = ""
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    approval_request_id: Optional[str] = None
    servicenow_updated: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "execution_id": self.execution_id,
            "action": self.action.to_dict() if self.action else None,
            "status": self.status.value,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "approval_request_id": self.approval_request_id,
            "servicenow_updated": self.servicenow_updated,
            "metadata": self.metadata,
        }
