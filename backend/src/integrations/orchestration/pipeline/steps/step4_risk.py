"""
Step 4: Risk Assessment — Evaluate risk using V8 7-dimension + 40 ITIL policies.

Wraps V8's RiskAssessor and builds AssessmentContext from pipeline context
(memory_text, knowledge_text) for enriched risk evaluation.

Outputs:
    context.risk_assessment — V8 RiskAssessment (level, score, requires_approval, etc.)

Phase 45: Orchestration Core (Sprint 154)
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..context import PipelineContext
from .base import PipelineStep

logger = logging.getLogger(__name__)

# Keywords for AssessmentContext extraction from memory/knowledge text
_PRODUCTION_KEYWORDS = [
    "production", "prod", "生產環境", "正式環境", "live",
]
_STAGING_KEYWORDS = [
    "staging", "stag", "測試環境", "預備環境",
]
_URGENCY_KEYWORDS = [
    "urgent", "emergency", "critical", "asap", "immediately",
    "緊急", "立即", "馬上",
]


class RiskStep(PipelineStep):
    """Evaluate risk with V8 RiskAssessor + enriched AssessmentContext.

    The key improvement over PoC: instead of regex-based risk (matching
    "production"/"database" keywords), we build a proper AssessmentContext
    from memory and knowledge texts, then use V8's 7-dimension + 40 ITIL
    policy system for precise evaluation.

    AssessmentContext dimensions populated:
        - is_production: from memory/knowledge mentions
        - is_staging: from memory/knowledge mentions
        - is_weekend: from current datetime
        - is_business_hours: from current datetime (9-18 weekdays)
        - is_urgent: from task text urgency keywords
        - affected_systems: extracted from task + knowledge
    """

    def __init__(
        self,
        risk_assessor: Optional[object] = None,
    ):
        """Initialize RiskStep.

        Args:
            risk_assessor: Pre-built RiskAssessor instance.
                If None, creates one with default policies.
        """
        self._risk_assessor = risk_assessor

    @property
    def name(self) -> str:
        return "risk_assessment"

    @property
    def step_index(self) -> int:
        return 3

    async def _execute(self, context: PipelineContext) -> PipelineContext:
        """Assess risk using routing decision and enriched context.

        Args:
            context: PipelineContext with routing_decision set (from Step 3).

        Returns:
            PipelineContext with risk_assessment populated.
        """
        if context.routing_decision is None:
            logger.warning("RiskStep: no routing_decision, skipping risk assessment")
            return context

        assessor = self._get_assessor()
        assessment_context = self._build_assessment_context(context)

        risk_assessment = assessor.assess(
            routing_decision=context.routing_decision,
            context=assessment_context,
        )

        # Intent-based risk cap: QUERY and UNKNOWN intents are read-only,
        # so risk should never exceed MEDIUM and never require approval.
        # This prevents context adjustments (e.g., production env) from
        # escalating simple information queries to HIGH/CRITICAL.
        intent_str = (
            context.routing_decision.intent_category.value
            if hasattr(context.routing_decision.intent_category, "value")
            else str(context.routing_decision.intent_category)
        ).lower()

        non_actionable = {"query", "unknown", "request"}
        if intent_str in non_actionable:
            from src.integrations.orchestration.intent_router.models import RiskLevel as RL

            if risk_assessment.level in (RL.HIGH, RL.CRITICAL):
                logger.info(
                    "RiskStep: capping risk from %s to MEDIUM for non-actionable intent '%s'",
                    risk_assessment.level.value,
                    intent_str,
                )
                risk_assessment.level = RL.MEDIUM
                risk_assessment.score = min(risk_assessment.score, 0.5)
                risk_assessment.requires_approval = False
                risk_assessment.approval_type = "none"
                risk_assessment.adjustments_applied.append(
                    f"Risk capped: non-actionable intent '{intent_str}'"
                )

        context.risk_assessment = risk_assessment

        logger.info(
            "RiskStep: level=%s, score=%.2f, requires_approval=%s, policy=%s",
            risk_assessment.level.value
            if hasattr(risk_assessment.level, "value")
            else str(risk_assessment.level),
            risk_assessment.score,
            risk_assessment.requires_approval,
            risk_assessment.policy_id,
        )

        return context

    def _build_assessment_context(self, context: PipelineContext) -> object:
        """Build AssessmentContext from pipeline state.

        Extracts environmental factors from memory_text, knowledge_text,
        and the task itself to populate the V8 AssessmentContext.

        Args:
            context: PipelineContext with memory_text, knowledge_text, task.

        Returns:
            AssessmentContext populated with extracted factors.
        """
        from src.integrations.orchestration.risk_assessor.assessor import (
            AssessmentContext,
        )

        # Only extract environment factors from the USER TASK, not from
        # memory/knowledge (which may contain "production" etc. unrelated
        # to the user's actual request). This prevents simple greetings
        # from being escalated to CRITICAL just because memory mentions
        # production systems.
        task_text = context.task.lower()

        now = datetime.now()
        is_weekend = now.weekday() >= 5  # Saturday=5, Sunday=6
        is_business_hours = (
            not is_weekend and 9 <= now.hour < 18
        )

        return AssessmentContext(
            is_production=self._contains_keywords(task_text, _PRODUCTION_KEYWORDS),
            is_staging=self._contains_keywords(task_text, _STAGING_KEYWORDS),
            is_weekend=is_weekend,
            is_business_hours=is_business_hours,
            is_urgent=self._contains_keywords(task_text, _URGENCY_KEYWORDS),
            affected_systems=self._extract_systems(task_text),
            custom_factors={
                "memory_available": bool(context.memory_text),
                "knowledge_available": bool(context.knowledge_text),
            },
        )

    @staticmethod
    def _contains_keywords(text: str, keywords: List[str]) -> bool:
        """Check if text contains any of the given keywords."""
        return any(kw in text for kw in keywords)

    @staticmethod
    def _extract_systems(text: str) -> List[str]:
        """Extract system/service names from text.

        Simple heuristic: looks for common IT system patterns.
        """
        systems: List[str] = []
        patterns = [
            r"\b(etl|crm|erp|vpn|dns|ldap|sql|redis|kafka|rabbitmq)\b",
            r"\b(database|server|cluster|pipeline|service|api)\b",
            r"\b(postgresql|mysql|mongodb|elasticsearch|qdrant)\b",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            systems.extend(matches)

        return list(set(s.lower() for s in systems))[:10]

    def _get_assessor(self) -> object:
        """Get or create RiskAssessor with default policies."""
        if self._risk_assessor is None:
            from src.integrations.orchestration.risk_assessor.assessor import (
                RiskAssessor,
            )

            self._risk_assessor = RiskAssessor()
        return self._risk_assessor
