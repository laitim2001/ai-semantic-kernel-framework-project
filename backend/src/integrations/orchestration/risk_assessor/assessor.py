"""
Risk Assessor Implementation

Core risk assessment engine that evaluates IT intents and returns risk assessments
based on configurable policies and contextual factors.

Sprint 96: Story 96-1 - Implement RiskAssessor Core (Phase 28)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..intent_router.models import ITIntentCategory, RiskLevel, RoutingDecision

logger = logging.getLogger(__name__)


@dataclass
class RiskFactor:
    """
    Individual risk factor contributing to overall risk assessment.

    Attributes:
        name: Factor identifier (e.g., 'intent_category', 'is_production')
        description: Human-readable description of the factor
        weight: Contribution weight to overall score (0.0 - 1.0)
        value: Current value of the factor
        impact: Impact direction ('increase', 'decrease', 'neutral')
    """

    name: str
    description: str
    weight: float = 0.0
    value: Any = None
    impact: str = "neutral"  # 'increase', 'decrease', 'neutral'

    def __post_init__(self) -> None:
        """Validate weight range."""
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError(f"weight must be between 0.0 and 1.0, got {self.weight}")
        if self.impact not in ("increase", "decrease", "neutral"):
            raise ValueError(f"impact must be 'increase', 'decrease', or 'neutral'")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "weight": self.weight,
            "value": self.value,
            "impact": self.impact,
        }


@dataclass
class AssessmentContext:
    """
    Contextual information for risk assessment adjustments.

    Attributes:
        is_production: Whether this affects production environment
        is_staging: Whether this affects staging environment
        is_weekend: Whether current time is weekend
        is_business_hours: Whether current time is business hours
        is_urgent: Whether marked as urgent
        user_role: Role of the requesting user
        affected_systems: List of affected system identifiers
        custom_factors: Additional custom factors as key-value pairs
    """

    is_production: bool = False
    is_staging: bool = False
    is_weekend: bool = False
    is_business_hours: bool = True
    is_urgent: bool = False
    user_role: Optional[str] = None
    affected_systems: List[str] = field(default_factory=list)
    custom_factors: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AssessmentContext":
        """Create AssessmentContext from dictionary."""
        return cls(
            is_production=data.get("is_production", False),
            is_staging=data.get("is_staging", False),
            is_weekend=data.get("is_weekend", False),
            is_business_hours=data.get("is_business_hours", True),
            is_urgent=data.get("is_urgent", False),
            user_role=data.get("user_role"),
            affected_systems=data.get("affected_systems", []),
            custom_factors=data.get("custom_factors", {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "is_production": self.is_production,
            "is_staging": self.is_staging,
            "is_weekend": self.is_weekend,
            "is_business_hours": self.is_business_hours,
            "is_urgent": self.is_urgent,
            "user_role": self.user_role,
            "affected_systems": self.affected_systems,
            "custom_factors": self.custom_factors,
        }


@dataclass
class RiskAssessment:
    """
    Complete risk assessment result.

    Attributes:
        level: Final risk level (low/medium/high/critical)
        score: Numerical risk score (0.0 - 1.0)
        requires_approval: Whether approval workflow is required
        approval_type: Type of approval needed ('none', 'single', 'multi')
        factors: List of contributing risk factors
        reasoning: Human-readable explanation of assessment
        policy_id: ID of the policy used for assessment
        adjustments_applied: List of context adjustments applied
        timestamp: When the assessment was made
    """

    level: RiskLevel
    score: float = 0.0
    requires_approval: bool = False
    approval_type: str = "none"  # 'none', 'single', 'multi'
    factors: List[RiskFactor] = field(default_factory=list)
    reasoning: str = ""
    policy_id: Optional[str] = None
    adjustments_applied: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Validate score range and approval type."""
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be between 0.0 and 1.0, got {self.score}")
        if self.approval_type not in ("none", "single", "multi"):
            raise ValueError(f"approval_type must be 'none', 'single', or 'multi'")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "level": self.level.value,
            "score": self.score,
            "requires_approval": self.requires_approval,
            "approval_type": self.approval_type,
            "factors": [f.to_dict() for f in self.factors],
            "reasoning": self.reasoning,
            "policy_id": self.policy_id,
            "adjustments_applied": self.adjustments_applied,
            "timestamp": self.timestamp.isoformat(),
        }


class RiskAssessor:
    """
    Risk assessment engine for IT service management.

    Evaluates routing decisions and returns comprehensive risk assessments
    based on configurable policies and contextual factors.

    Assessment Dimensions:
    1. Intent Category (incident > change > request > query)
    2. Sub Intent (system_down > etl_failure > general)
    3. Context Factors (production, weekend, urgent)

    Example:
        >>> from .policies import RiskPolicies
        >>> policies = RiskPolicies()
        >>> assessor = RiskAssessor(policies)
        >>> assessment = assessor.assess(routing_decision)
        >>> print(assessment.level)  # RiskLevel.HIGH
        >>> print(assessment.requires_approval)  # True
    """

    # Risk level score mappings
    RISK_LEVEL_SCORES: Dict[RiskLevel, float] = {
        RiskLevel.LOW: 0.25,
        RiskLevel.MEDIUM: 0.50,
        RiskLevel.HIGH: 0.75,
        RiskLevel.CRITICAL: 1.0,
    }

    # Risk level ordering for elevation/reduction
    RISK_LEVEL_ORDER: List[RiskLevel] = [
        RiskLevel.LOW,
        RiskLevel.MEDIUM,
        RiskLevel.HIGH,
        RiskLevel.CRITICAL,
    ]

    def __init__(self, policies: Optional["RiskPolicies"] = None) -> None:
        """
        Initialize RiskAssessor with policies.

        Args:
            policies: Risk policy collection. If None, default policies are used.
        """
        # Import here to avoid circular import
        from .policies import RiskPolicies

        self.policies = policies or RiskPolicies()

    def assess(
        self,
        routing_decision: RoutingDecision,
        context: Optional[AssessmentContext] = None,
    ) -> RiskAssessment:
        """
        Assess risk for a routing decision.

        Args:
            routing_decision: The routing decision to assess
            context: Optional contextual information for adjustments

        Returns:
            RiskAssessment with complete risk evaluation
        """
        logger.debug(
            f"Assessing risk for {routing_decision.intent_category.value}/"
            f"{routing_decision.sub_intent}"
        )

        # Initialize context if not provided
        context = context or AssessmentContext()

        # 1. Get base policy
        policy = self.policies.get_policy(
            routing_decision.intent_category,
            routing_decision.sub_intent or "*",
        )

        # 2. Calculate base risk level
        base_level = policy.default_risk_level

        # 3. Collect risk factors
        factors = self._collect_factors(routing_decision, context, policy)

        # 4. Apply context adjustments
        final_level, adjustments = self._apply_context_adjustments(
            base_level, context
        )

        # 5. Calculate risk score
        score = self._calculate_score(final_level, factors, context)

        # 6. Determine approval requirements
        requires_approval = self._requires_approval(final_level)
        approval_type = self._get_approval_type(final_level)

        # 7. Generate reasoning
        reasoning = self._generate_reasoning(
            routing_decision, policy, final_level, adjustments
        )

        logger.info(
            f"Risk assessment: {final_level.value} "
            f"(score: {score:.2f}, approval: {approval_type})"
        )

        return RiskAssessment(
            level=final_level,
            score=score,
            requires_approval=requires_approval,
            approval_type=approval_type,
            factors=factors,
            reasoning=reasoning,
            policy_id=policy.id if hasattr(policy, "id") else None,
            adjustments_applied=adjustments,
        )

    def assess_from_intent(
        self,
        intent_category: ITIntentCategory,
        sub_intent: Optional[str] = None,
        context: Optional[AssessmentContext] = None,
    ) -> RiskAssessment:
        """
        Assess risk directly from intent category and sub-intent.

        Convenience method when a full RoutingDecision is not available.

        Args:
            intent_category: The IT intent category
            sub_intent: Optional sub-intent specification
            context: Optional contextual information

        Returns:
            RiskAssessment with complete risk evaluation
        """
        # Create a minimal routing decision
        routing_decision = RoutingDecision(
            intent_category=intent_category,
            sub_intent=sub_intent,
            confidence=1.0,
            routing_layer="direct",
        )
        return self.assess(routing_decision, context)

    def _collect_factors(
        self,
        routing_decision: RoutingDecision,
        context: AssessmentContext,
        policy: "RiskPolicy",
    ) -> List[RiskFactor]:
        """
        Collect all risk factors for the assessment.

        Args:
            routing_decision: The routing decision
            context: Assessment context
            policy: Applicable policy

        Returns:
            List of RiskFactor objects
        """
        factors = []

        # Factor 1: Intent Category
        category_weight = self._get_category_weight(routing_decision.intent_category)
        factors.append(
            RiskFactor(
                name="intent_category",
                description=f"Intent category: {routing_decision.intent_category.value}",
                weight=category_weight,
                value=routing_decision.intent_category.value,
                impact="increase" if category_weight > 0.5 else "neutral",
            )
        )

        # Factor 2: Sub Intent
        if routing_decision.sub_intent:
            sub_intent_weight = self._get_sub_intent_weight(
                routing_decision.intent_category, routing_decision.sub_intent
            )
            factors.append(
                RiskFactor(
                    name="sub_intent",
                    description=f"Sub-intent: {routing_decision.sub_intent}",
                    weight=sub_intent_weight,
                    value=routing_decision.sub_intent,
                    impact="increase" if sub_intent_weight > 0.3 else "neutral",
                )
            )

        # Factor 3: Production Environment
        if context.is_production:
            factors.append(
                RiskFactor(
                    name="is_production",
                    description="Affects production environment",
                    weight=0.3,
                    value=True,
                    impact="increase",
                )
            )

        # Factor 4: Weekend
        if context.is_weekend:
            factors.append(
                RiskFactor(
                    name="is_weekend",
                    description="Executed during weekend",
                    weight=0.2,
                    value=True,
                    impact="increase",
                )
            )

        # Factor 5: Urgent
        if context.is_urgent:
            factors.append(
                RiskFactor(
                    name="is_urgent",
                    description="Marked as urgent",
                    weight=0.15,
                    value=True,
                    impact="increase",
                )
            )

        # Factor 6: Affected Systems Count
        system_count = len(context.affected_systems)
        if system_count > 0:
            weight = min(0.1 * system_count, 0.3)  # Cap at 0.3
            factors.append(
                RiskFactor(
                    name="affected_systems",
                    description=f"Number of affected systems: {system_count}",
                    weight=weight,
                    value=system_count,
                    impact="increase" if system_count > 2 else "neutral",
                )
            )

        # Factor 7: Confidence Score
        if routing_decision.confidence < 0.8:
            confidence_penalty = 0.2 * (1 - routing_decision.confidence)
            factors.append(
                RiskFactor(
                    name="low_confidence",
                    description=f"Low routing confidence: {routing_decision.confidence:.2f}",
                    weight=confidence_penalty,
                    value=routing_decision.confidence,
                    impact="increase",
                )
            )

        return factors

    def _get_category_weight(self, category: ITIntentCategory) -> float:
        """Get base weight for intent category."""
        weights = {
            ITIntentCategory.INCIDENT: 0.8,
            ITIntentCategory.CHANGE: 0.6,
            ITIntentCategory.REQUEST: 0.4,
            ITIntentCategory.QUERY: 0.2,
            ITIntentCategory.UNKNOWN: 0.5,
        }
        return weights.get(category, 0.5)

    def _get_sub_intent_weight(
        self, category: ITIntentCategory, sub_intent: str
    ) -> float:
        """Get additional weight for sub-intent."""
        high_risk_sub_intents = {
            "system_down": 0.5,
            "system_unavailable": 0.5,
            "etl_failure": 0.4,
            "emergency_change": 0.5,
            "database_change": 0.4,
            "access_request": 0.3,
            "security_incident": 0.5,
        }
        return high_risk_sub_intents.get(sub_intent, 0.1)

    def _apply_context_adjustments(
        self,
        base_level: RiskLevel,
        context: AssessmentContext,
    ) -> tuple[RiskLevel, List[str]]:
        """
        Apply context-based adjustments to risk level.

        Args:
            base_level: Base risk level from policy
            context: Assessment context

        Returns:
            Tuple of (adjusted_level, list of adjustments applied)
        """
        adjusted_level = base_level
        adjustments: List[str] = []

        # Production environment adjustment
        if context.is_production:
            new_level = self._elevate_risk(adjusted_level)
            if new_level != adjusted_level:
                adjustments.append(
                    f"Production environment: {adjusted_level.value} → {new_level.value}"
                )
                adjusted_level = new_level

        # Weekend adjustment
        if context.is_weekend:
            new_level = self._elevate_risk(adjusted_level)
            if new_level != adjusted_level:
                adjustments.append(
                    f"Weekend execution: {adjusted_level.value} → {new_level.value}"
                )
                adjusted_level = new_level

        # Urgent adjustment (elevate if not already critical)
        if context.is_urgent:
            new_level = self._elevate_risk(adjusted_level)
            if new_level != adjusted_level:
                adjustments.append(
                    f"Urgent flag: {adjusted_level.value} → {new_level.value}"
                )
                adjusted_level = new_level

        # Multiple systems adjustment
        if len(context.affected_systems) > 3:
            new_level = self._elevate_risk(adjusted_level)
            if new_level != adjusted_level:
                adjustments.append(
                    f"Multiple systems ({len(context.affected_systems)}): "
                    f"{adjusted_level.value} → {new_level.value}"
                )
                adjusted_level = new_level

        return adjusted_level, adjustments

    def _elevate_risk(self, level: RiskLevel) -> RiskLevel:
        """
        Elevate risk level by one step.

        Args:
            level: Current risk level

        Returns:
            Elevated risk level (or same if already CRITICAL)
        """
        try:
            current_idx = self.RISK_LEVEL_ORDER.index(level)
            if current_idx < len(self.RISK_LEVEL_ORDER) - 1:
                return self.RISK_LEVEL_ORDER[current_idx + 1]
        except ValueError:
            pass
        return level

    def _reduce_risk(self, level: RiskLevel) -> RiskLevel:
        """
        Reduce risk level by one step.

        Args:
            level: Current risk level

        Returns:
            Reduced risk level (or same if already LOW)
        """
        try:
            current_idx = self.RISK_LEVEL_ORDER.index(level)
            if current_idx > 0:
                return self.RISK_LEVEL_ORDER[current_idx - 1]
        except ValueError:
            pass
        return level

    def _calculate_score(
        self,
        level: RiskLevel,
        factors: List[RiskFactor],
        context: AssessmentContext,
    ) -> float:
        """
        Calculate numerical risk score.

        Combines base level score with factor weights.

        Args:
            level: Final risk level
            factors: List of risk factors
            context: Assessment context

        Returns:
            Risk score between 0.0 and 1.0
        """
        # Base score from level
        base_score = self.RISK_LEVEL_SCORES.get(level, 0.5)

        # Adjust based on factors
        factor_adjustment = 0.0
        for factor in factors:
            if factor.impact == "increase":
                factor_adjustment += factor.weight * 0.1
            elif factor.impact == "decrease":
                factor_adjustment -= factor.weight * 0.1

        # Combine and clamp
        final_score = base_score + factor_adjustment
        return max(0.0, min(1.0, final_score))

    def _requires_approval(self, level: RiskLevel) -> bool:
        """
        Determine if approval is required for risk level.

        Args:
            level: Risk level

        Returns:
            True if approval workflow is required
        """
        return level in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    def _get_approval_type(self, level: RiskLevel) -> str:
        """
        Determine approval type for risk level.

        Args:
            level: Risk level

        Returns:
            Approval type ('none', 'single', 'multi')
        """
        if level == RiskLevel.CRITICAL:
            return "multi"
        elif level == RiskLevel.HIGH:
            return "single"
        return "none"

    def _generate_reasoning(
        self,
        routing_decision: RoutingDecision,
        policy: "RiskPolicy",
        final_level: RiskLevel,
        adjustments: List[str],
    ) -> str:
        """
        Generate human-readable reasoning for the assessment.

        Args:
            routing_decision: The routing decision
            policy: Applied policy
            final_level: Final risk level
            adjustments: List of adjustments applied

        Returns:
            Reasoning string
        """
        parts = []

        # Base assessment
        parts.append(
            f"Intent '{routing_decision.intent_category.value}'"
            + (f"/{routing_decision.sub_intent}" if routing_decision.sub_intent else "")
            + f" assessed as {final_level.value} risk."
        )

        # Policy reference
        if hasattr(policy, "id") and policy.id:
            parts.append(f"Policy: {policy.id}")

        # Adjustments
        if adjustments:
            parts.append("Adjustments: " + "; ".join(adjustments))

        return " ".join(parts)


# Type hint for forward reference
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .policies import RiskPolicy, RiskPolicies
