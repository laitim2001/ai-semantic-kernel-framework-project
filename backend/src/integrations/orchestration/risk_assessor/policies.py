"""
Risk Policies Definition

Defines risk policies for IT service management scenarios.
Maps intent categories and sub-intents to risk levels and approval requirements.

Sprint 96: Story 96-2 - Define Risk Assessment Policies (Phase 28)
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..intent_router.models import ITIntentCategory, RiskLevel

logger = logging.getLogger(__name__)


@dataclass
class RiskPolicy:
    """
    Risk policy definition for a specific intent type.

    Attributes:
        id: Unique policy identifier
        intent_category: IT intent category this policy applies to
        sub_intent: Specific sub-intent (use "*" for category-wide default)
        default_risk_level: Base risk level for this policy
        requires_approval: Whether approval is required by default
        approval_type: Type of approval needed ('none', 'single', 'multi')
        factors: List of factors that influence this policy
        description: Human-readable policy description
        enabled: Whether this policy is active
        priority: Policy priority (higher = checked first)
    """

    id: str
    intent_category: ITIntentCategory
    sub_intent: str
    default_risk_level: RiskLevel
    requires_approval: bool = False
    approval_type: str = "none"  # 'none', 'single', 'multi'
    factors: List[str] = field(default_factory=list)
    description: str = ""
    enabled: bool = True
    priority: int = 100

    def __post_init__(self) -> None:
        """Validate policy configuration."""
        if self.approval_type not in ("none", "single", "multi"):
            raise ValueError(f"approval_type must be 'none', 'single', or 'multi'")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "intent_category": self.intent_category.value,
            "sub_intent": self.sub_intent,
            "default_risk_level": self.default_risk_level.value,
            "requires_approval": self.requires_approval,
            "approval_type": self.approval_type,
            "factors": self.factors,
            "description": self.description,
            "enabled": self.enabled,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RiskPolicy":
        """Create RiskPolicy from dictionary."""
        return cls(
            id=data["id"],
            intent_category=ITIntentCategory.from_string(data["intent_category"]),
            sub_intent=data["sub_intent"],
            default_risk_level=RiskLevel.from_string(data["default_risk_level"]),
            requires_approval=data.get("requires_approval", False),
            approval_type=data.get("approval_type", "none"),
            factors=data.get("factors", []),
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
            priority=data.get("priority", 100),
        )


class RiskPolicies:
    """
    Collection of risk policies with lookup capabilities.

    Provides policy lookup based on intent category and sub-intent,
    with fallback to category defaults and global defaults.

    Policy Lookup Order:
    1. Exact match (category + sub_intent)
    2. Category default (category + "*")
    3. Global default

    Example:
        >>> policies = RiskPolicies()
        >>> policy = policies.get_policy(ITIntentCategory.INCIDENT, "system_down")
        >>> print(policy.default_risk_level)  # RiskLevel.CRITICAL
    """

    # Default policies based on ITIL risk framework
    DEFAULT_POLICIES: List[RiskPolicy] = [
        # =============================================================================
        # INCIDENT Policies
        # =============================================================================
        RiskPolicy(
            id="incident_system_down",
            intent_category=ITIntentCategory.INCIDENT,
            sub_intent="system_down",
            default_risk_level=RiskLevel.CRITICAL,
            requires_approval=True,
            approval_type="multi",
            factors=["system_criticality", "business_impact", "affected_users"],
            description="System unavailable - critical business impact",
            priority=200,
        ),
        RiskPolicy(
            id="incident_system_unavailable",
            intent_category=ITIntentCategory.INCIDENT,
            sub_intent="system_unavailable",
            default_risk_level=RiskLevel.CRITICAL,
            requires_approval=True,
            approval_type="multi",
            factors=["system_criticality", "business_impact"],
            description="System unavailable - critical business impact",
            priority=200,
        ),
        RiskPolicy(
            id="incident_etl_failure",
            intent_category=ITIntentCategory.INCIDENT,
            sub_intent="etl_failure",
            default_risk_level=RiskLevel.HIGH,
            requires_approval=True,
            approval_type="single",
            factors=["data_impact", "downstream_systems", "sla_breach"],
            description="ETL pipeline failure affecting data delivery",
            priority=180,
        ),
        RiskPolicy(
            id="incident_security_incident",
            intent_category=ITIntentCategory.INCIDENT,
            sub_intent="security_incident",
            default_risk_level=RiskLevel.CRITICAL,
            requires_approval=True,
            approval_type="multi",
            factors=["data_breach_risk", "compliance_impact", "attack_scope"],
            description="Security incident requiring immediate response",
            priority=200,
        ),
        RiskPolicy(
            id="incident_performance_issue",
            intent_category=ITIntentCategory.INCIDENT,
            sub_intent="performance_issue",
            default_risk_level=RiskLevel.MEDIUM,
            requires_approval=False,
            approval_type="none",
            factors=["response_time", "user_impact"],
            description="Performance degradation affecting user experience",
            priority=150,
        ),
        RiskPolicy(
            id="incident_database_issue",
            intent_category=ITIntentCategory.INCIDENT,
            sub_intent="database_issue",
            default_risk_level=RiskLevel.HIGH,
            requires_approval=True,
            approval_type="single",
            factors=["data_integrity", "replication_status"],
            description="Database issue affecting data availability",
            priority=170,
        ),
        RiskPolicy(
            id="incident_network_failure",
            intent_category=ITIntentCategory.INCIDENT,
            sub_intent="network_failure",
            default_risk_level=RiskLevel.HIGH,
            requires_approval=True,
            approval_type="single",
            factors=["affected_segments", "redundancy_status"],
            description="Network connectivity failure",
            priority=175,
        ),
        RiskPolicy(
            id="incident_hardware_failure",
            intent_category=ITIntentCategory.INCIDENT,
            sub_intent="hardware_failure",
            default_risk_level=RiskLevel.HIGH,
            requires_approval=True,
            approval_type="single",
            factors=["hardware_type", "redundancy_available"],
            description="Hardware failure requiring replacement",
            priority=165,
        ),
        RiskPolicy(
            id="incident_software_issue",
            intent_category=ITIntentCategory.INCIDENT,
            sub_intent="software_issue",
            default_risk_level=RiskLevel.MEDIUM,
            requires_approval=False,
            approval_type="none",
            factors=["affected_functionality", "workaround_available"],
            description="Software bug or malfunction",
            priority=140,
        ),
        # Incident category default
        RiskPolicy(
            id="incident_default",
            intent_category=ITIntentCategory.INCIDENT,
            sub_intent="*",
            default_risk_level=RiskLevel.MEDIUM,
            requires_approval=False,
            approval_type="none",
            factors=["general_impact"],
            description="Default policy for unclassified incidents",
            priority=100,
        ),
        # =============================================================================
        # REQUEST Policies
        # =============================================================================
        RiskPolicy(
            id="request_access_request",
            intent_category=ITIntentCategory.REQUEST,
            sub_intent="access_request",
            default_risk_level=RiskLevel.HIGH,
            requires_approval=True,
            approval_type="single",
            factors=["access_level", "data_sensitivity", "role_appropriateness"],
            description="Access request requiring authorization review",
            priority=160,
        ),
        RiskPolicy(
            id="request_account_request",
            intent_category=ITIntentCategory.REQUEST,
            sub_intent="account_request",
            default_risk_level=RiskLevel.MEDIUM,
            requires_approval=False,
            approval_type="none",
            factors=["account_type", "approval_workflow"],
            description="Account creation or modification request",
            priority=130,
        ),
        RiskPolicy(
            id="request_software_request",
            intent_category=ITIntentCategory.REQUEST,
            sub_intent="software_request",
            default_risk_level=RiskLevel.MEDIUM,
            requires_approval=False,
            approval_type="none",
            factors=["software_type", "licensing"],
            description="Software installation or upgrade request",
            priority=120,
        ),
        RiskPolicy(
            id="request_hardware_request",
            intent_category=ITIntentCategory.REQUEST,
            sub_intent="hardware_request",
            default_risk_level=RiskLevel.MEDIUM,
            requires_approval=False,
            approval_type="none",
            factors=["hardware_cost", "procurement_process"],
            description="Hardware procurement request",
            priority=120,
        ),
        # Request category default
        RiskPolicy(
            id="request_default",
            intent_category=ITIntentCategory.REQUEST,
            sub_intent="*",
            default_risk_level=RiskLevel.LOW,
            requires_approval=False,
            approval_type="none",
            factors=["service_catalog_item"],
            description="Default policy for standard service requests",
            priority=100,
        ),
        # =============================================================================
        # CHANGE Policies
        # =============================================================================
        RiskPolicy(
            id="change_emergency_change",
            intent_category=ITIntentCategory.CHANGE,
            sub_intent="emergency_change",
            default_risk_level=RiskLevel.CRITICAL,
            requires_approval=True,
            approval_type="multi",
            factors=["change_urgency", "rollback_plan", "test_status"],
            description="Emergency change requiring immediate implementation",
            priority=200,
        ),
        RiskPolicy(
            id="change_standard_change",
            intent_category=ITIntentCategory.CHANGE,
            sub_intent="standard_change",
            default_risk_level=RiskLevel.MEDIUM,
            requires_approval=False,
            approval_type="none",
            factors=["pre_approved", "documented_procedure"],
            description="Pre-approved standard change with documented procedure",
            priority=120,
        ),
        RiskPolicy(
            id="change_normal_change",
            intent_category=ITIntentCategory.CHANGE,
            sub_intent="normal_change",
            default_risk_level=RiskLevel.HIGH,
            requires_approval=True,
            approval_type="single",
            factors=["change_impact", "test_results", "rollback_plan"],
            description="Normal change requiring CAB approval",
            priority=150,
        ),
        RiskPolicy(
            id="change_release_deployment",
            intent_category=ITIntentCategory.CHANGE,
            sub_intent="release_deployment",
            default_risk_level=RiskLevel.HIGH,
            requires_approval=True,
            approval_type="single",
            factors=["release_type", "environment", "rollback_procedure"],
            description="Release deployment to production",
            priority=170,
        ),
        RiskPolicy(
            id="change_database_change",
            intent_category=ITIntentCategory.CHANGE,
            sub_intent="database_change",
            default_risk_level=RiskLevel.HIGH,
            requires_approval=True,
            approval_type="single",
            factors=["schema_change", "data_migration", "backup_status"],
            description="Database schema or data change",
            priority=175,
        ),
        RiskPolicy(
            id="change_configuration_update",
            intent_category=ITIntentCategory.CHANGE,
            sub_intent="configuration_update",
            default_risk_level=RiskLevel.MEDIUM,
            requires_approval=False,
            approval_type="none",
            factors=["config_scope", "validation_steps"],
            description="Configuration update to existing systems",
            priority=130,
        ),
        # Change category default
        RiskPolicy(
            id="change_default",
            intent_category=ITIntentCategory.CHANGE,
            sub_intent="*",
            default_risk_level=RiskLevel.MEDIUM,
            requires_approval=False,
            approval_type="none",
            factors=["change_type"],
            description="Default policy for unclassified changes",
            priority=100,
        ),
        # =============================================================================
        # QUERY Policies
        # =============================================================================
        RiskPolicy(
            id="query_default",
            intent_category=ITIntentCategory.QUERY,
            sub_intent="*",
            default_risk_level=RiskLevel.LOW,
            requires_approval=False,
            approval_type="none",
            factors=[],
            description="Information queries with no risk impact",
            priority=100,
        ),
        RiskPolicy(
            id="query_status_inquiry",
            intent_category=ITIntentCategory.QUERY,
            sub_intent="status_inquiry",
            default_risk_level=RiskLevel.LOW,
            requires_approval=False,
            approval_type="none",
            factors=[],
            description="Status inquiry for existing tickets or services",
            priority=110,
        ),
        RiskPolicy(
            id="query_documentation",
            intent_category=ITIntentCategory.QUERY,
            sub_intent="documentation",
            default_risk_level=RiskLevel.LOW,
            requires_approval=False,
            approval_type="none",
            factors=[],
            description="Documentation or knowledge base query",
            priority=110,
        ),
        # =============================================================================
        # UNKNOWN Policies
        # =============================================================================
        RiskPolicy(
            id="unknown_default",
            intent_category=ITIntentCategory.UNKNOWN,
            sub_intent="*",
            default_risk_level=RiskLevel.MEDIUM,
            requires_approval=False,
            approval_type="none",
            factors=["classification_confidence"],
            description="Unclassified intent requiring review",
            priority=50,
        ),
    ]

    # Global default policy
    GLOBAL_DEFAULT_POLICY = RiskPolicy(
        id="global_default",
        intent_category=ITIntentCategory.UNKNOWN,
        sub_intent="*",
        default_risk_level=RiskLevel.MEDIUM,
        requires_approval=False,
        approval_type="none",
        factors=[],
        description="Global fallback policy",
        priority=0,
    )

    def __init__(
        self,
        policies: Optional[List[RiskPolicy]] = None,
        include_defaults: bool = True,
    ) -> None:
        """
        Initialize RiskPolicies collection.

        Args:
            policies: Custom policies to add
            include_defaults: Whether to include default policies
        """
        self._policies: List[RiskPolicy] = []
        self._policy_index: Dict[str, RiskPolicy] = {}

        # Add default policies if requested
        if include_defaults:
            for policy in self.DEFAULT_POLICIES:
                self._add_policy(policy)

        # Add custom policies
        if policies:
            for policy in policies:
                self._add_policy(policy)

        # Build index for fast lookup
        self._rebuild_index()

    def _add_policy(self, policy: RiskPolicy) -> None:
        """Add a policy to the collection."""
        if not policy.enabled:
            return

        # Remove existing policy with same ID
        self._policies = [p for p in self._policies if p.id != policy.id]
        self._policies.append(policy)

    def _rebuild_index(self) -> None:
        """Rebuild policy lookup index."""
        # Sort by priority (highest first)
        self._policies.sort(key=lambda p: p.priority, reverse=True)

        # Build composite key index
        self._policy_index.clear()
        for policy in self._policies:
            key = f"{policy.intent_category.value}:{policy.sub_intent}"
            if key not in self._policy_index:
                self._policy_index[key] = policy

    def get_policy(
        self,
        intent_category: ITIntentCategory,
        sub_intent: str = "*",
    ) -> RiskPolicy:
        """
        Get the most appropriate policy for an intent.

        Lookup order:
        1. Exact match (category + sub_intent)
        2. Category default (category + "*")
        3. Global default

        Args:
            intent_category: The intent category
            sub_intent: The sub-intent (default "*" for category default)

        Returns:
            The matching RiskPolicy
        """
        # Try exact match
        exact_key = f"{intent_category.value}:{sub_intent}"
        if exact_key in self._policy_index:
            logger.debug(f"Policy exact match: {exact_key}")
            return self._policy_index[exact_key]

        # Try category default
        default_key = f"{intent_category.value}:*"
        if default_key in self._policy_index:
            logger.debug(f"Policy category default: {default_key}")
            return self._policy_index[default_key]

        # Return global default
        logger.debug("Policy global default")
        return self.GLOBAL_DEFAULT_POLICY

    def add_policy(self, policy: RiskPolicy) -> None:
        """
        Add or update a policy.

        Args:
            policy: The policy to add
        """
        self._add_policy(policy)
        self._rebuild_index()

    def remove_policy(self, policy_id: str) -> bool:
        """
        Remove a policy by ID.

        Args:
            policy_id: The policy ID to remove

        Returns:
            True if policy was removed, False if not found
        """
        original_count = len(self._policies)
        self._policies = [p for p in self._policies if p.id != policy_id]

        if len(self._policies) < original_count:
            self._rebuild_index()
            return True
        return False

    def get_all_policies(self) -> List[RiskPolicy]:
        """
        Get all policies.

        Returns:
            List of all policies
        """
        return list(self._policies)

    def get_policies_for_category(
        self, intent_category: ITIntentCategory
    ) -> List[RiskPolicy]:
        """
        Get all policies for a specific category.

        Args:
            intent_category: The intent category

        Returns:
            List of policies for the category
        """
        return [p for p in self._policies if p.intent_category == intent_category]

    def to_dict(self) -> Dict[str, Any]:
        """Convert all policies to dictionary."""
        return {
            "policies": [p.to_dict() for p in self._policies],
            "count": len(self._policies),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RiskPolicies":
        """
        Create RiskPolicies from dictionary.

        Args:
            data: Dictionary with 'policies' key

        Returns:
            RiskPolicies instance
        """
        policies = [
            RiskPolicy.from_dict(p_data) for p_data in data.get("policies", [])
        ]
        return cls(policies=policies, include_defaults=False)

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "RiskPolicies":
        """
        Load policies from YAML file.

        Args:
            yaml_path: Path to YAML file

        Returns:
            RiskPolicies instance
        """
        import yaml

        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return cls.from_dict(data)

    def __len__(self) -> int:
        """Return number of policies."""
        return len(self._policies)

    def __contains__(self, policy_id: str) -> bool:
        """Check if policy ID exists."""
        return any(p.id == policy_id for p in self._policies)


# =============================================================================
# Policy Factory Functions
# =============================================================================


def create_default_policies() -> RiskPolicies:
    """
    Create default risk policies.

    Returns:
        RiskPolicies with default configuration
    """
    return RiskPolicies()


def create_strict_policies() -> RiskPolicies:
    """
    Create strict risk policies with elevated approval requirements.

    All HIGH risk items require multi-approval.
    All MEDIUM risk items require single approval.

    Returns:
        RiskPolicies with strict configuration
    """
    policies = RiskPolicies()

    # Override with stricter policies
    strict_overrides = [
        RiskPolicy(
            id="strict_incident_default",
            intent_category=ITIntentCategory.INCIDENT,
            sub_intent="*",
            default_risk_level=RiskLevel.HIGH,
            requires_approval=True,
            approval_type="single",
            factors=["strict_mode"],
            description="Strict mode: all incidents require approval",
            priority=101,
        ),
        RiskPolicy(
            id="strict_change_default",
            intent_category=ITIntentCategory.CHANGE,
            sub_intent="*",
            default_risk_level=RiskLevel.HIGH,
            requires_approval=True,
            approval_type="single",
            factors=["strict_mode"],
            description="Strict mode: all changes require approval",
            priority=101,
        ),
    ]

    for policy in strict_overrides:
        policies.add_policy(policy)

    return policies


def create_relaxed_policies() -> RiskPolicies:
    """
    Create relaxed risk policies for development/testing environments.

    Reduces approval requirements across the board.

    Returns:
        RiskPolicies with relaxed configuration
    """
    policies = RiskPolicies()

    # Override with relaxed policies
    relaxed_overrides = [
        RiskPolicy(
            id="relaxed_change_default",
            intent_category=ITIntentCategory.CHANGE,
            sub_intent="*",
            default_risk_level=RiskLevel.LOW,
            requires_approval=False,
            approval_type="none",
            factors=["dev_environment"],
            description="Relaxed mode: changes auto-approved in dev",
            priority=101,
        ),
    ]

    for policy in relaxed_overrides:
        policies.add_policy(policy)

    return policies


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "RiskPolicy",
    "RiskPolicies",
    "create_default_policies",
    "create_strict_policies",
    "create_relaxed_policies",
]
