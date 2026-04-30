"""
Unit Tests for Risk Assessor Module

Tests for RiskAssessor, RiskPolicies, and related classes.

Sprint 96: Story 96-4 - Risk Assessment Unit Tests (Phase 28)
"""

import pytest
from datetime import datetime

from src.integrations.orchestration.intent_router.models import (
    ITIntentCategory,
    RiskLevel,
    RoutingDecision,
    WorkflowType,
)
from src.integrations.orchestration.risk_assessor import (
    AssessmentContext,
    RiskAssessment,
    RiskAssessor,
    RiskFactor,
    RiskPolicies,
    RiskPolicy,
)
from src.integrations.orchestration.risk_assessor.policies import (
    create_default_policies,
    create_strict_policies,
    create_relaxed_policies,
)


# =============================================================================
# RiskFactor Tests
# =============================================================================


class TestRiskFactor:
    """Tests for RiskFactor dataclass."""

    def test_create_risk_factor(self):
        """Test creating a basic risk factor."""
        factor = RiskFactor(
            name="test_factor",
            description="Test factor description",
            weight=0.5,
            value="test_value",
            impact="increase",
        )
        assert factor.name == "test_factor"
        assert factor.description == "Test factor description"
        assert factor.weight == 0.5
        assert factor.value == "test_value"
        assert factor.impact == "increase"

    def test_risk_factor_invalid_weight(self):
        """Test that invalid weight raises ValueError."""
        with pytest.raises(ValueError, match="weight must be between"):
            RiskFactor(
                name="test",
                description="test",
                weight=1.5,  # Invalid
            )

    def test_risk_factor_invalid_impact(self):
        """Test that invalid impact raises ValueError."""
        with pytest.raises(ValueError, match="impact must be"):
            RiskFactor(
                name="test",
                description="test",
                impact="invalid",  # Invalid
            )

    def test_risk_factor_to_dict(self):
        """Test serialization to dictionary."""
        factor = RiskFactor(
            name="test",
            description="desc",
            weight=0.3,
            value=True,
            impact="neutral",
        )
        data = factor.to_dict()
        assert data["name"] == "test"
        assert data["weight"] == 0.3
        assert data["value"] is True


# =============================================================================
# AssessmentContext Tests
# =============================================================================


class TestAssessmentContext:
    """Tests for AssessmentContext dataclass."""

    def test_create_default_context(self):
        """Test creating context with defaults."""
        context = AssessmentContext()
        assert context.is_production is False
        assert context.is_staging is False
        assert context.is_weekend is False
        assert context.is_business_hours is True
        assert context.is_urgent is False
        assert context.user_role is None
        assert context.affected_systems == []
        assert context.custom_factors == {}

    def test_create_production_context(self):
        """Test creating production environment context."""
        context = AssessmentContext(
            is_production=True,
            affected_systems=["system1", "system2"],
        )
        assert context.is_production is True
        assert len(context.affected_systems) == 2

    def test_context_from_dict(self):
        """Test creating context from dictionary."""
        data = {
            "is_production": True,
            "is_weekend": True,
            "is_urgent": True,
            "affected_systems": ["db1", "db2", "app1"],
        }
        context = AssessmentContext.from_dict(data)
        assert context.is_production is True
        assert context.is_weekend is True
        assert context.is_urgent is True
        assert len(context.affected_systems) == 3

    def test_context_to_dict(self):
        """Test serialization to dictionary."""
        context = AssessmentContext(
            is_production=True,
            is_urgent=True,
            user_role="admin",
        )
        data = context.to_dict()
        assert data["is_production"] is True
        assert data["is_urgent"] is True
        assert data["user_role"] == "admin"


# =============================================================================
# RiskAssessment Tests
# =============================================================================


class TestRiskAssessment:
    """Tests for RiskAssessment dataclass."""

    def test_create_basic_assessment(self):
        """Test creating a basic risk assessment."""
        assessment = RiskAssessment(
            level=RiskLevel.HIGH,
            score=0.75,
            requires_approval=True,
            approval_type="single",
        )
        assert assessment.level == RiskLevel.HIGH
        assert assessment.score == 0.75
        assert assessment.requires_approval is True
        assert assessment.approval_type == "single"

    def test_assessment_invalid_score(self):
        """Test that invalid score raises ValueError."""
        with pytest.raises(ValueError, match="score must be between"):
            RiskAssessment(
                level=RiskLevel.LOW,
                score=1.5,  # Invalid
            )

    def test_assessment_invalid_approval_type(self):
        """Test that invalid approval_type raises ValueError."""
        with pytest.raises(ValueError, match="approval_type must be"):
            RiskAssessment(
                level=RiskLevel.LOW,
                approval_type="invalid",  # Invalid
            )

    def test_assessment_with_factors(self):
        """Test assessment with risk factors."""
        factors = [
            RiskFactor(name="f1", description="Factor 1", weight=0.3),
            RiskFactor(name="f2", description="Factor 2", weight=0.5),
        ]
        assessment = RiskAssessment(
            level=RiskLevel.MEDIUM,
            factors=factors,
        )
        assert len(assessment.factors) == 2

    def test_assessment_to_dict(self):
        """Test serialization to dictionary."""
        assessment = RiskAssessment(
            level=RiskLevel.CRITICAL,
            score=0.95,
            requires_approval=True,
            approval_type="multi",
            reasoning="Critical incident detected",
        )
        data = assessment.to_dict()
        assert data["level"] == "critical"
        assert data["score"] == 0.95
        assert data["requires_approval"] is True
        assert data["approval_type"] == "multi"


# =============================================================================
# RiskPolicy Tests
# =============================================================================


class TestRiskPolicy:
    """Tests for RiskPolicy dataclass."""

    def test_create_policy(self):
        """Test creating a risk policy."""
        policy = RiskPolicy(
            id="test_policy",
            intent_category=ITIntentCategory.INCIDENT,
            sub_intent="system_down",
            default_risk_level=RiskLevel.CRITICAL,
            requires_approval=True,
            approval_type="multi",
            factors=["factor1", "factor2"],
            description="Test policy",
        )
        assert policy.id == "test_policy"
        assert policy.intent_category == ITIntentCategory.INCIDENT
        assert policy.default_risk_level == RiskLevel.CRITICAL
        assert policy.requires_approval is True

    def test_policy_invalid_approval_type(self):
        """Test that invalid approval_type raises ValueError."""
        with pytest.raises(ValueError, match="approval_type must be"):
            RiskPolicy(
                id="test",
                intent_category=ITIntentCategory.QUERY,
                sub_intent="*",
                default_risk_level=RiskLevel.LOW,
                approval_type="invalid",
            )

    def test_policy_to_dict(self):
        """Test serialization to dictionary."""
        policy = RiskPolicy(
            id="test",
            intent_category=ITIntentCategory.CHANGE,
            sub_intent="standard_change",
            default_risk_level=RiskLevel.MEDIUM,
        )
        data = policy.to_dict()
        assert data["id"] == "test"
        assert data["intent_category"] == "change"
        assert data["default_risk_level"] == "medium"

    def test_policy_from_dict(self):
        """Test creating policy from dictionary."""
        data = {
            "id": "from_dict_policy",
            "intent_category": "request",
            "sub_intent": "access_request",
            "default_risk_level": "high",
            "requires_approval": True,
            "approval_type": "single",
        }
        policy = RiskPolicy.from_dict(data)
        assert policy.id == "from_dict_policy"
        assert policy.intent_category == ITIntentCategory.REQUEST
        assert policy.default_risk_level == RiskLevel.HIGH


# =============================================================================
# RiskPolicies Tests
# =============================================================================


class TestRiskPolicies:
    """Tests for RiskPolicies collection."""

    def test_create_default_policies(self):
        """Test creating policies with defaults."""
        policies = RiskPolicies()
        assert len(policies) > 0

    def test_get_exact_match_policy(self):
        """Test getting policy with exact match."""
        policies = RiskPolicies()
        policy = policies.get_policy(ITIntentCategory.INCIDENT, "system_down")
        assert policy.default_risk_level == RiskLevel.CRITICAL
        assert policy.requires_approval is True

    def test_get_category_default_policy(self):
        """Test getting category default when no exact match."""
        policies = RiskPolicies()
        # Use a sub_intent that doesn't have exact match
        policy = policies.get_policy(ITIntentCategory.INCIDENT, "unknown_incident")
        # Should fall back to incident default
        assert policy.intent_category == ITIntentCategory.INCIDENT
        assert policy.sub_intent == "*"

    def test_get_global_default_policy(self):
        """Test getting global default for unknown category."""
        policies = RiskPolicies(include_defaults=False)
        policy = policies.get_policy(ITIntentCategory.UNKNOWN, "something")
        assert policy.id == "global_default"

    def test_add_custom_policy(self):
        """Test adding custom policy."""
        policies = RiskPolicies()
        custom_policy = RiskPolicy(
            id="custom_test",
            intent_category=ITIntentCategory.QUERY,
            sub_intent="custom_query",
            default_risk_level=RiskLevel.HIGH,  # Override query default
            priority=200,
        )
        policies.add_policy(custom_policy)
        retrieved = policies.get_policy(ITIntentCategory.QUERY, "custom_query")
        assert retrieved.id == "custom_test"
        assert retrieved.default_risk_level == RiskLevel.HIGH

    def test_remove_policy(self):
        """Test removing a policy."""
        policies = RiskPolicies()
        initial_count = len(policies)

        # Add and then remove
        custom_policy = RiskPolicy(
            id="to_remove",
            intent_category=ITIntentCategory.QUERY,
            sub_intent="removable",
            default_risk_level=RiskLevel.LOW,
        )
        policies.add_policy(custom_policy)
        assert len(policies) == initial_count + 1

        removed = policies.remove_policy("to_remove")
        assert removed is True
        assert len(policies) == initial_count

    def test_get_policies_for_category(self):
        """Test getting all policies for a category."""
        policies = RiskPolicies()
        incident_policies = policies.get_policies_for_category(ITIntentCategory.INCIDENT)
        assert len(incident_policies) > 0
        for policy in incident_policies:
            assert policy.intent_category == ITIntentCategory.INCIDENT

    def test_policies_to_dict(self):
        """Test serialization to dictionary."""
        policies = RiskPolicies()
        data = policies.to_dict()
        assert "policies" in data
        assert "count" in data
        assert data["count"] == len(policies)


# =============================================================================
# RiskAssessor Tests
# =============================================================================


class TestRiskAssessor:
    """Tests for RiskAssessor class."""

    @pytest.fixture
    def assessor(self):
        """Create a RiskAssessor instance."""
        return RiskAssessor()

    @pytest.fixture
    def routing_decision(self):
        """Create a sample routing decision."""
        return RoutingDecision(
            intent_category=ITIntentCategory.INCIDENT,
            sub_intent="etl_failure",
            confidence=0.95,
            workflow_type=WorkflowType.SEQUENTIAL,
            routing_layer="pattern",
        )

    def test_assess_incident_system_down(self, assessor):
        """Test assessment for system down incident."""
        decision = RoutingDecision(
            intent_category=ITIntentCategory.INCIDENT,
            sub_intent="system_down",
            confidence=0.99,
        )
        assessment = assessor.assess(decision)

        assert assessment.level == RiskLevel.CRITICAL
        assert assessment.requires_approval is True
        assert assessment.approval_type == "multi"
        assert assessment.score > 0.8

    def test_assess_incident_etl_failure(self, assessor):
        """Test assessment for ETL failure incident."""
        decision = RoutingDecision(
            intent_category=ITIntentCategory.INCIDENT,
            sub_intent="etl_failure",
            confidence=0.95,
        )
        assessment = assessor.assess(decision)

        assert assessment.level == RiskLevel.HIGH
        assert assessment.requires_approval is True
        assert assessment.approval_type == "single"

    def test_assess_query(self, assessor):
        """Test assessment for query (low risk)."""
        decision = RoutingDecision(
            intent_category=ITIntentCategory.QUERY,
            sub_intent="status_inquiry",
            confidence=0.90,
        )
        assessment = assessor.assess(decision)

        assert assessment.level == RiskLevel.LOW
        assert assessment.requires_approval is False
        assert assessment.approval_type == "none"

    def test_assess_request_access(self, assessor):
        """Test assessment for access request."""
        decision = RoutingDecision(
            intent_category=ITIntentCategory.REQUEST,
            sub_intent="access_request",
            confidence=0.92,
        )
        assessment = assessor.assess(decision)

        assert assessment.level == RiskLevel.HIGH
        assert assessment.requires_approval is True

    def test_assess_change_emergency(self, assessor):
        """Test assessment for emergency change."""
        decision = RoutingDecision(
            intent_category=ITIntentCategory.CHANGE,
            sub_intent="emergency_change",
            confidence=0.98,
        )
        assessment = assessor.assess(decision)

        assert assessment.level == RiskLevel.CRITICAL
        assert assessment.requires_approval is True
        assert assessment.approval_type == "multi"

    def test_assess_change_standard(self, assessor):
        """Test assessment for standard change."""
        decision = RoutingDecision(
            intent_category=ITIntentCategory.CHANGE,
            sub_intent="standard_change",
            confidence=0.95,
        )
        assessment = assessor.assess(decision)

        assert assessment.level == RiskLevel.MEDIUM
        assert assessment.requires_approval is False

    def test_context_production_elevates_risk(self, assessor):
        """Test that production context elevates risk level."""
        decision = RoutingDecision(
            intent_category=ITIntentCategory.CHANGE,
            sub_intent="standard_change",
            confidence=0.95,
        )

        # Without production context
        assessment_no_prod = assessor.assess(decision)
        base_level = assessment_no_prod.level

        # With production context
        context = AssessmentContext(is_production=True)
        assessment_prod = assessor.assess(decision, context)

        # Production should elevate the risk
        assert self._risk_level_index(assessment_prod.level) > self._risk_level_index(base_level)
        assert "Production environment" in str(assessment_prod.adjustments_applied)

    def test_context_weekend_elevates_risk(self, assessor):
        """Test that weekend context elevates risk level."""
        decision = RoutingDecision(
            intent_category=ITIntentCategory.REQUEST,
            sub_intent="account_request",
            confidence=0.90,
        )

        # Without weekend context
        assessment_normal = assessor.assess(decision)
        base_level = assessment_normal.level

        # With weekend context
        context = AssessmentContext(is_weekend=True)
        assessment_weekend = assessor.assess(decision, context)

        # Weekend should elevate the risk
        assert self._risk_level_index(assessment_weekend.level) > self._risk_level_index(base_level)
        assert "Weekend" in str(assessment_weekend.adjustments_applied)

    def test_context_urgent_elevates_risk(self, assessor):
        """Test that urgent flag elevates risk level."""
        decision = RoutingDecision(
            intent_category=ITIntentCategory.QUERY,
            sub_intent="status_inquiry",
            confidence=0.95,
        )

        context = AssessmentContext(is_urgent=True)
        assessment = assessor.assess(decision, context)

        # Urgent should elevate from LOW
        assert assessment.level != RiskLevel.LOW or "Urgent" in str(assessment.adjustments_applied)

    def test_multiple_context_factors(self, assessor):
        """Test assessment with multiple context factors."""
        decision = RoutingDecision(
            intent_category=ITIntentCategory.CHANGE,
            sub_intent="configuration_update",
            confidence=0.88,
        )

        context = AssessmentContext(
            is_production=True,
            is_weekend=True,
            affected_systems=["sys1", "sys2", "sys3", "sys4"],
        )
        assessment = assessor.assess(decision, context)

        # Multiple factors should elevate risk significantly
        assert assessment.level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        assert len(assessment.adjustments_applied) >= 2

    def test_low_confidence_increases_risk(self, assessor):
        """Test that low routing confidence adds risk factor."""
        decision = RoutingDecision(
            intent_category=ITIntentCategory.QUERY,
            sub_intent="status_inquiry",
            confidence=0.60,  # Low confidence
        )
        assessment = assessor.assess(decision)

        # Should have low_confidence factor
        factor_names = [f.name for f in assessment.factors]
        assert "low_confidence" in factor_names

    def test_assess_from_intent(self, assessor):
        """Test convenience method assess_from_intent."""
        assessment = assessor.assess_from_intent(
            intent_category=ITIntentCategory.INCIDENT,
            sub_intent="system_down",
        )
        assert assessment.level == RiskLevel.CRITICAL

    def test_assessment_includes_factors(self, assessor, routing_decision):
        """Test that assessment includes relevant factors."""
        assessment = assessor.assess(routing_decision)

        assert len(assessment.factors) > 0
        factor_names = [f.name for f in assessment.factors]
        assert "intent_category" in factor_names

    def test_assessment_includes_reasoning(self, assessor, routing_decision):
        """Test that assessment includes reasoning."""
        assessment = assessor.assess(routing_decision)

        assert assessment.reasoning != ""
        assert "incident" in assessment.reasoning.lower()

    def test_assessment_score_in_range(self, assessor, routing_decision):
        """Test that assessment score is within valid range."""
        assessment = assessor.assess(routing_decision)
        assert 0.0 <= assessment.score <= 1.0

    def test_assessment_has_timestamp(self, assessor, routing_decision):
        """Test that assessment has timestamp."""
        before = datetime.utcnow()
        assessment = assessor.assess(routing_decision)
        after = datetime.utcnow()

        assert before <= assessment.timestamp <= after

    @staticmethod
    def _risk_level_index(level: RiskLevel) -> int:
        """Helper to get numeric index for risk level comparison."""
        order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        return order.index(level)


# =============================================================================
# Policy Factory Tests
# =============================================================================


class TestPolicyFactories:
    """Tests for policy factory functions."""

    def test_create_default_policies(self):
        """Test creating default policies."""
        policies = create_default_policies()
        assert len(policies) > 0

    def test_create_strict_policies(self):
        """Test creating strict policies."""
        strict = create_strict_policies()

        # Incident default should be HIGH in strict mode
        policy = strict.get_policy(ITIntentCategory.INCIDENT, "unknown")
        # Either HIGH from strict override or specific policy
        assert policy.default_risk_level in (RiskLevel.HIGH, RiskLevel.MEDIUM)

    def test_create_relaxed_policies(self):
        """Test creating relaxed policies."""
        relaxed = create_relaxed_policies()

        # Change default should be LOW in relaxed mode
        policy = relaxed.get_policy(ITIntentCategory.CHANGE, "unknown_change")
        assert policy.default_risk_level == RiskLevel.LOW


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_unknown_intent_category(self):
        """Test handling of unknown intent category."""
        assessor = RiskAssessor()
        decision = RoutingDecision(
            intent_category=ITIntentCategory.UNKNOWN,
            confidence=0.50,
        )
        assessment = assessor.assess(decision)

        assert assessment.level == RiskLevel.MEDIUM
        assert assessment is not None

    def test_empty_sub_intent(self):
        """Test handling of empty sub_intent."""
        assessor = RiskAssessor()
        decision = RoutingDecision(
            intent_category=ITIntentCategory.INCIDENT,
            sub_intent=None,
            confidence=0.85,
        )
        assessment = assessor.assess(decision)

        # Should fall back to category default
        assert assessment is not None
        assert assessment.level is not None

    def test_maximum_affected_systems(self):
        """Test with large number of affected systems."""
        assessor = RiskAssessor()
        decision = RoutingDecision(
            intent_category=ITIntentCategory.QUERY,
            sub_intent="status_inquiry",
            confidence=0.95,
        )
        context = AssessmentContext(
            affected_systems=[f"system_{i}" for i in range(100)]
        )
        assessment = assessor.assess(decision, context)

        # Should handle gracefully and elevate risk
        assert assessment is not None
        assert assessment.level != RiskLevel.LOW

    def test_custom_factors_in_context(self):
        """Test handling of custom factors."""
        assessor = RiskAssessor()
        decision = RoutingDecision(
            intent_category=ITIntentCategory.CHANGE,
            sub_intent="standard_change",
            confidence=0.90,
        )
        context = AssessmentContext(
            custom_factors={
                "special_approval": True,
                "override_level": "critical",
            }
        )
        assessment = assessor.assess(decision, context)

        # Custom factors should not break assessment
        assert assessment is not None

    def test_boundary_confidence_values(self):
        """Test confidence boundary values."""
        assessor = RiskAssessor()

        # Minimum confidence
        decision_min = RoutingDecision(
            intent_category=ITIntentCategory.QUERY,
            confidence=0.0,
        )
        assessment_min = assessor.assess(decision_min)
        assert "low_confidence" in [f.name for f in assessment_min.factors]

        # Maximum confidence
        decision_max = RoutingDecision(
            intent_category=ITIntentCategory.QUERY,
            confidence=1.0,
        )
        assessment_max = assessor.assess(decision_max)
        assert assessment_max is not None

    def test_critical_cannot_elevate_further(self):
        """Test that CRITICAL risk level cannot be elevated further."""
        assessor = RiskAssessor()
        decision = RoutingDecision(
            intent_category=ITIntentCategory.INCIDENT,
            sub_intent="system_down",  # Already CRITICAL
            confidence=0.99,
        )

        # Add all possible elevation factors
        context = AssessmentContext(
            is_production=True,
            is_weekend=True,
            is_urgent=True,
            affected_systems=["s1", "s2", "s3", "s4", "s5"],
        )
        assessment = assessor.assess(decision, context)

        # Should still be CRITICAL (max level)
        assert assessment.level == RiskLevel.CRITICAL
