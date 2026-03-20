"""
RoutingDecisionClassifier — Bridges three-tier RoutingDecision to ExecutionMode.

Converts the IT intent classification from BusinessIntentRouter
(Pattern -> Semantic -> LLM) into FrameworkSelector's ExecutionMode,
enabling intelligent mode dispatch based on intent category, risk level,
and workflow complexity indicators.

Sprint 144 — Phase 42 Deep Integration.
"""

import logging
from typing import Dict, List, Optional

from src.integrations.hybrid.intent.classifiers.base import BaseClassifier
from src.integrations.hybrid.intent.models import (
    ClassificationResult,
    ExecutionMode,
    Message,
    SessionContext,
)

logger = logging.getLogger(__name__)


class RoutingDecisionClassifier(BaseClassifier):
    """Classifier that uses RoutingDecision from three-tier routing.

    Before calling classify(), the caller must set ``routing_decision``
    with the result from BusinessIntentRouter.route().  If no
    routing_decision is set, the classifier abstains (returns CHAT_MODE
    with low confidence so other classifiers dominate).

    Mapping rules:
        QUERY  + LOW risk      -> CHAT_MODE   (0.90)
        QUERY  + MEDIUM+ risk  -> CHAT_MODE   (0.75)
        REQUEST                -> WORKFLOW_MODE (0.85)
        CHANGE                 -> WORKFLOW_MODE (0.85)
        INCIDENT + CRITICAL    -> SWARM_MODE   (0.90)
        INCIDENT + HIGH        -> WORKFLOW_MODE (0.85)
        INCIDENT + MEDIUM/LOW  -> WORKFLOW_MODE (0.75)
        UNKNOWN                -> CHAT_MODE   (0.50)
    """

    def __init__(
        self,
        name: str = "routing_decision",
        weight: float = 1.5,
        enabled: bool = True,
    ) -> None:
        super().__init__(name=name, weight=weight, enabled=enabled)
        self.routing_decision: Optional[object] = None

    def set_routing_decision(self, routing_decision: object) -> None:
        """Inject the RoutingDecision before classify() is called."""
        self.routing_decision = routing_decision

    async def classify(
        self,
        input_text: str,
        context: Optional[SessionContext] = None,
        history: Optional[List[Message]] = None,
    ) -> ClassificationResult:
        """Classify based on the injected RoutingDecision."""
        if self.routing_decision is None:
            return ClassificationResult(
                mode=ExecutionMode.CHAT_MODE,
                confidence=0.3,
                reasoning="No routing decision available, abstaining",
                classifier_name=self.name,
            )

        rd = self.routing_decision
        intent = self._get_field(rd, "intent_category", "unknown")
        risk = self._get_field(rd, "risk_level", "low")
        confidence_from_router = float(self._get_field(rd, "confidence", 0.5))
        sub_intent = self._get_field(rd, "sub_intent", "")
        workflow_type = self._get_field(rd, "workflow_type", "")

        # Normalise to lowercase strings for comparison
        intent_str = str(intent).lower().replace("intintentcategory.", "")
        risk_str = str(risk).lower().replace("risklevel.", "")

        mode, conf, reasoning = self._map_intent_to_mode(
            intent_str, risk_str, confidence_from_router, sub_intent, workflow_type,
        )

        metadata: Dict = {
            "intent_category": intent_str,
            "risk_level": risk_str,
            "router_confidence": confidence_from_router,
            "sub_intent": sub_intent,
            "workflow_type": str(workflow_type),
        }

        return ClassificationResult(
            mode=mode,
            confidence=conf,
            reasoning=reasoning,
            classifier_name=self.name,
            metadata=metadata,
        )

    def _map_intent_to_mode(
        self,
        intent: str,
        risk: str,
        router_confidence: float,
        sub_intent: str,
        workflow_type: str,
    ) -> tuple:
        """Map IT intent + risk to ExecutionMode.

        Returns (mode, confidence, reasoning).
        """
        # --- QUERY / greeting => CHAT_MODE ---
        if intent in ("query", "greeting", "unknown_query"):
            if risk in ("low", "none"):
                return (
                    ExecutionMode.CHAT_MODE,
                    0.90,
                    f"Query/greeting intent with low risk -> CHAT_MODE",
                )
            return (
                ExecutionMode.CHAT_MODE,
                0.75,
                f"Query intent with {risk} risk -> CHAT_MODE (elevated risk noted)",
            )

        # --- INCIDENT => SWARM or WORKFLOW ---
        if intent == "incident":
            if risk in ("critical",):
                return (
                    ExecutionMode.SWARM_MODE,
                    0.90,
                    "Critical incident -> SWARM_MODE (multi-agent collaboration needed)",
                )
            if risk in ("high",):
                return (
                    ExecutionMode.WORKFLOW_MODE,
                    0.85,
                    "High-risk incident -> WORKFLOW_MODE (structured remediation)",
                )
            return (
                ExecutionMode.WORKFLOW_MODE,
                0.75,
                f"Incident with {risk} risk -> WORKFLOW_MODE",
            )

        # --- REQUEST => WORKFLOW ---
        if intent == "request":
            return (
                ExecutionMode.WORKFLOW_MODE,
                0.85,
                "Service request -> WORKFLOW_MODE (task orchestration)",
            )

        # --- CHANGE => WORKFLOW ---
        if intent == "change":
            if risk in ("critical", "high"):
                return (
                    ExecutionMode.WORKFLOW_MODE,
                    0.90,
                    f"Change request with {risk} risk -> WORKFLOW_MODE (approval required)",
                )
            return (
                ExecutionMode.WORKFLOW_MODE,
                0.80,
                "Change request -> WORKFLOW_MODE",
            )

        # --- UNKNOWN => CHAT_MODE (low confidence) ---
        return (
            ExecutionMode.CHAT_MODE,
            max(0.50, router_confidence * 0.6),
            f"Unknown intent '{intent}' -> CHAT_MODE fallback",
        )

    @staticmethod
    def _get_field(obj: object, field: str, default: object = None) -> object:
        """Get a field from an object or dict."""
        if isinstance(obj, dict):
            return obj.get(field, default)
        return getattr(obj, field, default)
