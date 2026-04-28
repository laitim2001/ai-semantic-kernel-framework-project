# =============================================================================
# IPA Platform - Autonomous Decision Engine
# =============================================================================
# Sprint 10: S10-3 AutonomousDecisionEngine (8 points)
#
# Intelligent decision-making engine that evaluates options, assesses risks,
# and makes explainable autonomous decisions.
#
# Features:
# - Multi-option evaluation with pros/cons analysis
# - Risk assessment and confidence calculation
# - Decision explainability
# - Custom decision rules support
# - Decision history tracking
# =============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple
from uuid import UUID, uuid4
import json


class DecisionType(str, Enum):
    """Types of decisions the engine can make."""
    ROUTING = "routing"              # Task routing decisions
    RESOURCE = "resource"            # Resource allocation
    ERROR_HANDLING = "error_handling"  # How to handle errors
    PRIORITY = "priority"            # Priority adjustments
    ESCALATION = "escalation"        # Escalation decisions
    OPTIMIZATION = "optimization"    # Optimization choices


class DecisionConfidence(str, Enum):
    """Decision confidence levels."""
    HIGH = "high"       # > 80% confidence, can auto-execute
    MEDIUM = "medium"   # 50-80% confidence, recommend human confirmation
    LOW = "low"         # < 50% confidence, requires human decision


class LLMServiceProtocol(Protocol):
    """Protocol for LLM service interface."""

    async def generate(self, prompt: str, max_tokens: int = 2000) -> str:
        """Generate text from a prompt."""
        ...


@dataclass
class DecisionOption:
    """
    Represents a decision option with its analysis.

    Contains pros, cons, risk assessment, and prerequisites.
    """
    id: str
    name: str
    description: str
    pros: List[str]
    cons: List[str]
    risk_level: float  # 0-1, where 1 is highest risk
    estimated_impact: float  # 0-1, where 1 is highest positive impact
    prerequisites: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert option to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "pros": self.pros,
            "cons": self.cons,
            "risk_level": self.risk_level,
            "estimated_impact": self.estimated_impact,
            "prerequisites": self.prerequisites,
            "metadata": self.metadata,
        }

    def get_score(self) -> float:
        """Calculate option score based on impact and risk."""
        return self.estimated_impact * (1 - self.risk_level)


@dataclass
class Decision:
    """
    Represents a decision made by the engine.

    Contains all context, options considered, and the decision reasoning.
    """
    id: UUID
    decision_type: DecisionType
    situation: str
    options_considered: List[DecisionOption]
    selected_option: str
    confidence: DecisionConfidence
    reasoning: str
    risk_assessment: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    human_approved: Optional[bool] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    execution_result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert decision to dictionary."""
        return {
            "id": str(self.id),
            "decision_type": self.decision_type.value,
            "situation": self.situation,
            "options_considered": [o.to_dict() for o in self.options_considered],
            "selected_option": self.selected_option,
            "confidence": self.confidence.value,
            "reasoning": self.reasoning,
            "risk_assessment": self.risk_assessment,
            "timestamp": self.timestamp.isoformat(),
            "human_approved": self.human_approved,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "execution_result": self.execution_result,
        }

    def approve(self, approver: str) -> None:
        """Approve this decision."""
        self.human_approved = True
        self.approved_by = approver
        self.approved_at = datetime.utcnow()

    def reject(self, approver: str, reason: str) -> None:
        """Reject this decision."""
        self.human_approved = False
        self.approved_by = approver
        self.approved_at = datetime.utcnow()
        self.execution_result = {"rejected": True, "reason": reason}


@dataclass
class DecisionRule:
    """
    A rule for automatic decision making.

    Rules are checked before LLM analysis for fast, deterministic decisions.
    """
    name: str
    condition: Callable[[str, List[str]], bool]
    action: str
    priority: int = 0
    description: str = ""

    def matches(self, situation: str, options: List[str]) -> bool:
        """Check if this rule matches the situation."""
        try:
            return self.condition(situation, options)
        except Exception:
            return False


class AutonomousDecisionEngine:
    """
    Autonomous Decision Engine.

    Makes intelligent decisions using:
    - Multi-option evaluation
    - Risk assessment
    - Confidence calculation
    - Explainability
    - Custom rules
    """

    def __init__(
        self,
        llm_service: Optional[LLMServiceProtocol] = None,
        risk_threshold: float = 0.7,
        auto_decision_confidence: float = 0.8
    ):
        """
        Initialize the decision engine.

        Args:
            llm_service: LLM service for intelligent analysis
            risk_threshold: Maximum acceptable risk level (0-1)
            auto_decision_confidence: Minimum confidence for auto-execution
        """
        self.llm_service = llm_service
        self.risk_threshold = risk_threshold
        self.auto_decision_confidence = auto_decision_confidence

        # Decision history
        self._decision_history: List[Decision] = []

        # Custom decision rules
        self._rules: List[DecisionRule] = []

        # Initialize default rules
        self._init_default_rules()

    def _init_default_rules(self) -> None:
        """Initialize default decision rules."""
        # Urgent situations
        self.add_rule(
            name="urgent_handling",
            condition=lambda s, o: "urgent" in s.lower() or "critical" in s.lower(),
            action="immediate_action",
            priority=100,
            description="Handle urgent situations immediately"
        )

        # Retry on transient errors
        self.add_rule(
            name="retry_transient",
            condition=lambda s, o: "timeout" in s.lower() or "temporary" in s.lower(),
            action="retry",
            priority=50,
            description="Retry on transient errors"
        )

        # Escalate on repeated failures
        self.add_rule(
            name="escalate_repeated",
            condition=lambda s, o: "repeated" in s.lower() and "fail" in s.lower(),
            action="escalate",
            priority=75,
            description="Escalate repeated failures"
        )

    async def make_decision(
        self,
        situation: str,
        options: List[str],
        context: Optional[Dict[str, Any]] = None,
        decision_type: DecisionType = DecisionType.ROUTING
    ) -> Dict[str, Any]:
        """
        Make a decision based on situation and options.

        Args:
            situation: Description of the situation
            options: Available options to choose from
            context: Additional context information
            decision_type: Type of decision being made

        Returns:
            Decision result with action, confidence, and reasoning
        """
        # 1. Check if any rules apply
        rule_action = await self.apply_rules(situation, options)
        if rule_action:
            # Create a simple decision based on rule
            decision = Decision(
                id=uuid4(),
                decision_type=decision_type,
                situation=situation,
                options_considered=[
                    DecisionOption(
                        id=rule_action,
                        name=rule_action,
                        description="Rule-based action",
                        pros=["Fast", "Deterministic"],
                        cons=[],
                        risk_level=0.2,
                        estimated_impact=0.8
                    )
                ],
                selected_option=rule_action,
                confidence=DecisionConfidence.HIGH,
                reasoning=f"Rule-based decision: {rule_action}",
                risk_assessment={"overall_risk": 0.2, "rule_based": True}
            )
            self._decision_history.append(decision)
            return self._format_decision_result(decision)

        # 2. Expand options with analysis
        expanded_options = await self._expand_options(options, situation, context)

        # 3. Evaluate each option
        evaluations = await self._evaluate_options(expanded_options, situation, context)

        # 4. Select best option
        selected, reasoning = await self._select_best_option(expanded_options, evaluations)

        # 5. Calculate confidence and risk
        confidence = self._calculate_confidence(evaluations, selected)
        risk_assessment = self._assess_risk(selected, evaluations)

        # 6. Create decision record
        decision = Decision(
            id=uuid4(),
            decision_type=decision_type,
            situation=situation,
            options_considered=expanded_options,
            selected_option=selected.id,
            confidence=confidence,
            reasoning=reasoning,
            risk_assessment=risk_assessment
        )

        self._decision_history.append(decision)

        return self._format_decision_result(decision)

    def _format_decision_result(self, decision: Decision) -> Dict[str, Any]:
        """Format decision for return."""
        return {
            "decision_id": str(decision.id),
            "action": decision.selected_option,
            "confidence": decision.confidence.value,
            "reasoning": decision.reasoning,
            "risk_level": decision.risk_assessment.get("overall_risk", 0),
            "requires_approval": decision.confidence != DecisionConfidence.HIGH,
            "options": [
                {
                    "id": opt.id,
                    "name": opt.name,
                    "score": opt.get_score()
                }
                for opt in decision.options_considered
            ]
        }

    async def _expand_options(
        self,
        options: List[str],
        situation: str,
        context: Optional[Dict[str, Any]]
    ) -> List[DecisionOption]:
        """Expand options with detailed analysis."""
        if self.llm_service:
            prompt = f"""
            Analyze each option for the following situation:

            Situation: {situation}
            Context: {context if context else "None"}

            Options:
            {json.dumps(options, ensure_ascii=False)}

            Return JSON analysis for each option:
            [
                {{
                    "id": "option_id",
                    "name": "Option Name",
                    "description": "Detailed description",
                    "pros": ["Advantage 1", "Advantage 2"],
                    "cons": ["Disadvantage 1", "Disadvantage 2"],
                    "risk_level": 0.3,
                    "estimated_impact": 0.7,
                    "prerequisites": ["Prerequisite condition"]
                }}
            ]
            """

            response = await self.llm_service.generate(
                prompt=prompt,
                max_tokens=1500
            )

            try:
                # Extract JSON from response
                json_start = response.find("[")
                json_end = response.rfind("]") + 1
                if json_start >= 0 and json_end > json_start:
                    options_data = json.loads(response[json_start:json_end])
                    return [
                        DecisionOption(
                            id=opt.get("id", str(i)),
                            name=opt.get("name", options[i] if i < len(options) else f"Option {i}"),
                            description=opt.get("description", ""),
                            pros=opt.get("pros", []),
                            cons=opt.get("cons", []),
                            risk_level=float(opt.get("risk_level", 0.5)),
                            estimated_impact=float(opt.get("estimated_impact", 0.5)),
                            prerequisites=opt.get("prerequisites", [])
                        )
                        for i, opt in enumerate(options_data)
                    ]
            except (json.JSONDecodeError, ValueError):
                pass

        # Fallback: create basic options
        return [
            DecisionOption(
                id=opt,
                name=opt,
                description=f"Option: {opt}",
                pros=["Available option"],
                cons=["Unknown risks"],
                risk_level=0.5,
                estimated_impact=0.5
            )
            for opt in options
        ]

    async def _evaluate_options(
        self,
        options: List[DecisionOption],
        situation: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Evaluate each option and calculate scores."""
        evaluations = {}

        for option in options:
            # Calculate composite score
            # Score = impact * (1 - risk) * prerequisites_met
            prerequisites_met = 1.0  # Assume all prerequisites are met

            score = (
                option.estimated_impact *
                (1 - option.risk_level) *
                prerequisites_met
            )

            # Adjust for pros/cons count
            pros_bonus = len(option.pros) * 0.05
            cons_penalty = len(option.cons) * 0.05
            score = score + pros_bonus - cons_penalty
            score = max(0, min(1, score))  # Clamp to 0-1

            evaluations[option.id] = {
                "score": score,
                "risk": option.risk_level,
                "impact": option.estimated_impact,
                "pros_count": len(option.pros),
                "cons_count": len(option.cons),
                "prerequisites_met": prerequisites_met,
            }

        return evaluations

    async def _select_best_option(
        self,
        options: List[DecisionOption],
        evaluations: Dict[str, Dict[str, Any]]
    ) -> Tuple[DecisionOption, str]:
        """Select the best option based on evaluations."""
        if not evaluations or not options:
            raise ValueError("No options to evaluate")

        # Create option index
        option_index = {opt.id: opt for opt in options}

        # Sort by score
        sorted_options = sorted(
            evaluations.items(),
            key=lambda x: x[1]["score"],
            reverse=True
        )

        best_id = sorted_options[0][0]
        best_score = sorted_options[0][1]["score"]
        best_option = option_index.get(best_id, options[0])

        # Generate reasoning
        reasoning = f"Selected '{best_option.name}' with score {best_score:.2f}."

        if len(sorted_options) > 1:
            second_id = sorted_options[1][0]
            second_score = sorted_options[1][1]["score"]
            second_option = option_index.get(second_id)
            if second_option:
                score_diff = best_score - second_score
                reasoning += f" This option scores {score_diff:.2f} higher than '{second_option.name}'."

        # Add risk consideration
        if best_option.risk_level > 0.5:
            reasoning += f" Note: This option has elevated risk ({best_option.risk_level:.0%})."
        elif best_option.risk_level < 0.3:
            reasoning += f" This option has low risk ({best_option.risk_level:.0%})."

        return best_option, reasoning

    def _calculate_confidence(
        self,
        evaluations: Dict[str, Dict[str, Any]],
        selected: DecisionOption
    ) -> DecisionConfidence:
        """Calculate decision confidence level."""
        if not evaluations:
            return DecisionConfidence.LOW

        scores = [e["score"] for e in evaluations.values()]
        max_score = max(scores)
        avg_score = sum(scores) / len(scores)

        # Calculate lead advantage
        lead = max_score - avg_score

        # Consider risk
        risk_factor = 1 - selected.risk_level

        # Calculate composite confidence score
        confidence_score = (
            max_score * 0.4 +
            lead * 0.3 +
            risk_factor * 0.3
        )

        if confidence_score >= self.auto_decision_confidence:
            return DecisionConfidence.HIGH
        elif confidence_score >= 0.5:
            return DecisionConfidence.MEDIUM
        else:
            return DecisionConfidence.LOW

    def _assess_risk(
        self,
        selected: DecisionOption,
        evaluations: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Assess risk of the selected option."""
        return {
            "overall_risk": selected.risk_level,
            "risk_category": self._categorize_risk(selected.risk_level),
            "potential_issues": selected.cons,
            "mitigation_suggestions": self._generate_mitigations(selected.cons),
            "reversible": selected.risk_level < 0.5,
            "requires_monitoring": selected.risk_level > 0.3,
        }

    def _categorize_risk(self, risk_level: float) -> str:
        """Categorize risk level."""
        if risk_level < 0.3:
            return "low"
        elif risk_level < 0.6:
            return "medium"
        else:
            return "high"

    def _generate_mitigations(self, cons: List[str]) -> List[str]:
        """Generate risk mitigation suggestions based on cons."""
        mitigations = []

        for con in cons:
            con_lower = con.lower()

            if "time" in con_lower or "slow" in con_lower or "delay" in con_lower:
                mitigations.append("Set timeout limits and have fallback ready")
            elif "cost" in con_lower or "expensive" in con_lower or "resource" in con_lower:
                mitigations.append("Set budget limits and monitor resource usage")
            elif "fail" in con_lower or "error" in con_lower or "risk" in con_lower:
                mitigations.append("Implement retry mechanism with fallback options")
            elif "complex" in con_lower or "difficult" in con_lower:
                mitigations.append("Break down into smaller steps with checkpoints")
            elif "depend" in con_lower or "require" in con_lower:
                mitigations.append("Verify prerequisites before proceeding")
            else:
                mitigations.append(f"Monitor and track: {con}")

        return mitigations

    async def explain_decision(self, decision_id: UUID) -> str:
        """
        Generate a detailed explanation of a decision.

        Args:
            decision_id: ID of the decision to explain

        Returns:
            Detailed explanation text
        """
        decision = next(
            (d for d in self._decision_history if d.id == decision_id),
            None
        )

        if not decision:
            return "Decision not found"

        explanation = f"""
Decision Explanation
====================

Situation: {decision.situation}

Options Considered:
"""

        for opt in decision.options_considered:
            explanation += f"""
- {opt.name}:
  Description: {opt.description}
  Pros: {', '.join(opt.pros) if opt.pros else 'None identified'}
  Cons: {', '.join(opt.cons) if opt.cons else 'None identified'}
  Risk Level: {opt.risk_level:.0%}
  Expected Impact: {opt.estimated_impact:.0%}
"""

        explanation += f"""
Selected Option: {decision.selected_option}

Reasoning: {decision.reasoning}

Confidence Level: {decision.confidence.value}

Risk Assessment:
- Overall Risk: {decision.risk_assessment.get('overall_risk', 0):.0%}
- Risk Category: {decision.risk_assessment.get('risk_category', 'unknown')}
- Reversible: {'Yes' if decision.risk_assessment.get('reversible') else 'No'}

Mitigation Suggestions:
{chr(10).join('- ' + s for s in decision.risk_assessment.get('mitigation_suggestions', []))}

Decision Time: {decision.timestamp.isoformat()}
"""

        if decision.human_approved is not None:
            approval_status = "Approved" if decision.human_approved else "Rejected"
            explanation += f"\nApproval Status: {approval_status} by {decision.approved_by}"

        return explanation

    def add_rule(
        self,
        name: str,
        condition: Callable[[str, List[str]], bool],
        action: str,
        priority: int = 0,
        description: str = ""
    ) -> None:
        """
        Add a custom decision rule.

        Args:
            name: Rule name
            condition: Function(situation, options) -> bool
            action: Action to take when rule matches
            priority: Rule priority (higher = checked first)
            description: Rule description
        """
        rule = DecisionRule(
            name=name,
            condition=condition,
            action=action,
            priority=priority,
            description=description
        )
        self._rules.append(rule)
        # Keep rules sorted by priority (descending)
        self._rules.sort(key=lambda r: r.priority, reverse=True)

    def remove_rule(self, name: str) -> bool:
        """Remove a rule by name."""
        original_count = len(self._rules)
        self._rules = [r for r in self._rules if r.name != name]
        return len(self._rules) < original_count

    async def apply_rules(
        self,
        situation: str,
        options: List[str]
    ) -> Optional[str]:
        """
        Apply decision rules to find a matching action.

        Returns action if a rule matches, None otherwise.
        """
        for rule in self._rules:
            if rule.matches(situation, options):
                return rule.action
        return None

    def get_decision_history(
        self,
        decision_type: Optional[DecisionType] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get decision history, optionally filtered by type."""
        decisions = self._decision_history

        if decision_type:
            decisions = [d for d in decisions if d.decision_type == decision_type]

        # Sort by timestamp descending
        decisions = sorted(decisions, key=lambda d: d.timestamp, reverse=True)

        return [d.to_dict() for d in decisions[:limit]]

    def get_decision(self, decision_id: UUID) -> Optional[Decision]:
        """Get a specific decision by ID."""
        return next(
            (d for d in self._decision_history if d.id == decision_id),
            None
        )

    async def approve_decision(
        self,
        decision_id: UUID,
        approver: str
    ) -> bool:
        """Approve a decision that requires human approval."""
        decision = self.get_decision(decision_id)
        if not decision:
            return False

        decision.approve(approver)
        return True

    async def reject_decision(
        self,
        decision_id: UUID,
        approver: str,
        reason: str
    ) -> bool:
        """Reject a decision."""
        decision = self.get_decision(decision_id)
        if not decision:
            return False

        decision.reject(approver, reason)
        return True

    def list_rules(self) -> List[Dict[str, Any]]:
        """List all registered rules."""
        return [
            {
                "name": r.name,
                "action": r.action,
                "priority": r.priority,
                "description": r.description,
            }
            for r in self._rules
        ]
