"""
IT Incident Action Recommender — Remediation Suggestion Engine.

Sprint 126: Story 126-2 — ActionRecommender generates remediation actions
using rule-based templates and optional LLM enhancement.

Rule-based action templates per incident category provide immediate,
well-tested suggestions. LLM can augment with context-specific actions.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from .prompts import REMEDIATION_SUGGESTION_PROMPT
from .types import (
    IncidentAnalysis,
    IncidentCategory,
    IncidentContext,
    IncidentSeverity,
    RemediationAction,
    RemediationActionType,
    RemediationRisk,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Pre-defined Action Templates per Category
# =============================================================================

ACTION_TEMPLATES: Dict[IncidentCategory, List[Dict[str, Any]]] = {
    IncidentCategory.STORAGE: [
        {
            "action_type": RemediationActionType.CLEAR_DISK_SPACE,
            "title": "Clear temporary files and old logs",
            "description": (
                "Remove temporary files from /tmp and rotate/compress old log files "
                "to free disk space immediately."
            ),
            "confidence": 0.85,
            "risk": RemediationRisk.AUTO,
            "mcp_tool": "shell:run_command",
            "mcp_params": {
                "command": (
                    "find /tmp -type f -mtime +7 -delete && "
                    "find /var/log -name '*.log.*' -mtime +30 -delete"
                ),
            },
            "prerequisites": ["Verify disk usage > 85%"],
            "rollback_steps": ["No rollback needed for cleanup"],
            "estimated_duration_seconds": 30,
        },
    ],
    IncidentCategory.APPLICATION: [
        {
            "action_type": RemediationActionType.RESTART_SERVICE,
            "title": "Restart application service",
            "description": (
                "Restart the affected application service to recover from crash, "
                "hang, or resource exhaustion."
            ),
            "confidence": 0.75,
            "risk": RemediationRisk.LOW,
            "mcp_tool": "shell:run_command",
            "mcp_params": {"command": "systemctl restart {service_name}"},
            "prerequisites": [
                "Verify service is not actively processing critical transactions",
            ],
            "rollback_steps": [
                "systemctl stop {service_name}",
                "Restore previous configuration if config was changed",
                "systemctl start {service_name}",
            ],
            "estimated_duration_seconds": 60,
        },
    ],
    IncidentCategory.AUTHENTICATION: [
        {
            "action_type": RemediationActionType.AD_ACCOUNT_UNLOCK,
            "title": "Unlock Active Directory account",
            "description": (
                "Unlock the user's AD account that was locked due to "
                "too many failed login attempts."
            ),
            "confidence": 0.90,
            "risk": RemediationRisk.AUTO,
            "mcp_tool": "ldap:ad_operations",
            "mcp_params": {
                "operation": "account_unlock",
                "username": "{affected_user}",
            },
            "prerequisites": [
                "Verify the user identity through caller information",
            ],
            "rollback_steps": [
                "Re-lock account if unlock was unauthorized",
            ],
            "estimated_duration_seconds": 10,
        },
    ],
    IncidentCategory.SERVER: [
        {
            "action_type": RemediationActionType.SCALE_RESOURCE,
            "title": "Scale VM resources (CPU/Memory)",
            "description": (
                "Increase VM resources to handle increased load or "
                "resource exhaustion. Requires approval due to cost impact."
            ),
            "confidence": 0.70,
            "risk": RemediationRisk.MEDIUM,
            "mcp_tool": "",
            "mcp_params": {},
            "prerequisites": [
                "Verify resource utilization metrics confirm exhaustion",
                "Confirm budget approval for resource scaling",
            ],
            "rollback_steps": [
                "Scale resources back to original values",
                "Monitor for recurrence of resource exhaustion",
            ],
            "estimated_duration_seconds": 300,
        },
    ],
    IncidentCategory.NETWORK: [
        {
            "action_type": RemediationActionType.NETWORK_ACL_CHANGE,
            "title": "Update network ACL rules",
            "description": (
                "Modify network Access Control List rules to restore "
                "connectivity or block malicious traffic. High risk, "
                "requires manual approval."
            ),
            "confidence": 0.60,
            "risk": RemediationRisk.HIGH,
            "mcp_tool": "",
            "mcp_params": {},
            "prerequisites": [
                "Identify specific ACL rule causing the issue",
                "Document current ACL state for rollback",
                "Notify network team",
            ],
            "rollback_steps": [
                "Revert ACL to saved state",
                "Verify connectivity restored",
                "Notify affected teams",
            ],
            "estimated_duration_seconds": 600,
        },
    ],
    IncidentCategory.SECURITY: [
        {
            "action_type": RemediationActionType.FIREWALL_RULE_CHANGE,
            "title": "Update firewall rules",
            "description": (
                "Modify firewall rules to block attack vectors or "
                "restore legitimate access. Critical risk, requires "
                "multi-approver approval."
            ),
            "confidence": 0.55,
            "risk": RemediationRisk.CRITICAL,
            "mcp_tool": "",
            "mcp_params": {},
            "prerequisites": [
                "Identify specific attack vector or access requirement",
                "Document current firewall state",
                "Security team review required",
            ],
            "rollback_steps": [
                "Revert firewall to previous rule set",
                "Verify no new security exposure",
                "Run security scan on affected systems",
            ],
            "estimated_duration_seconds": 900,
        },
    ],
    IncidentCategory.DATABASE: [
        {
            "action_type": RemediationActionType.RESTART_DATABASE,
            "title": "Restart database service",
            "description": (
                "Restart the database service to recover from connection "
                "pool exhaustion, deadlocks, or corrupted state."
            ),
            "confidence": 0.65,
            "risk": RemediationRisk.MEDIUM,
            "mcp_tool": "shell:run_command",
            "mcp_params": {"command": "systemctl restart {db_service}"},
            "prerequisites": [
                "Verify no active long-running transactions",
                "Notify dependent application teams",
                "Ensure recent backup exists",
            ],
            "rollback_steps": [
                "Check database consistency after restart",
                "Restore from backup if data corruption detected",
            ],
            "estimated_duration_seconds": 120,
        },
    ],
    IncidentCategory.PERFORMANCE: [
        {
            "action_type": RemediationActionType.CLEAR_CACHE,
            "title": "Clear application cache",
            "description": (
                "Clear application/CDN cache to resolve stale data or "
                "cache corruption causing performance degradation."
            ),
            "confidence": 0.70,
            "risk": RemediationRisk.LOW,
            "mcp_tool": "shell:run_command",
            "mcp_params": {"command": "redis-cli FLUSHDB"},
            "prerequisites": [
                "Verify cache size and hit rate metrics",
                "Notify downstream services of potential cold-start",
            ],
            "rollback_steps": [
                "No direct rollback; cache will repopulate on next access",
                "Monitor response times after cache clear",
            ],
            "estimated_duration_seconds": 15,
        },
    ],
}


class ActionRecommender:
    """Generates remediation action recommendations for IT incidents.

    Uses a two-tier approach:
        1. Rule-based templates: Pre-defined actions per incident category
        2. LLM enhancement: Context-specific suggestions (optional)

    Actions are ranked by confidence (DESC) then risk (ASC).

    Example:
        >>> recommender = ActionRecommender()
        >>> actions = await recommender.recommend(analysis, context)
        >>> for action in actions:
        ...     print(f"{action.title} (confidence: {action.confidence:.0%})")
    """

    def __init__(self, llm_service: Optional[Any] = None) -> None:
        """Initialize ActionRecommender.

        Args:
            llm_service: Optional LLM service implementing LLMServiceProtocol
        """
        self._llm_service = llm_service

    async def recommend(
        self,
        analysis: IncidentAnalysis,
        context: IncidentContext,
    ) -> List[RemediationAction]:
        """Generate remediation action recommendations.

        Args:
            analysis: IncidentAnalysis from IncidentAnalyzer
            context: Original incident context

        Returns:
            List of RemediationAction sorted by confidence DESC, risk ASC
        """
        logger.info(
            f"Generating recommendations for {context.incident_number} "
            f"(category: {context.category.value})"
        )

        # Step 1: Rule-based actions from templates
        actions = self._generate_rule_based_actions(context)

        # Step 2: Include any actions from analysis
        for existing_action in analysis.recommended_actions:
            if not self._is_duplicate(existing_action, actions):
                actions.append(existing_action)

        # Step 3: LLM enhancement (optional)
        if self._llm_service is not None:
            try:
                llm_actions = await self._generate_llm_actions(analysis, context, actions)
                for llm_action in llm_actions:
                    if not self._is_duplicate(llm_action, actions):
                        actions.append(llm_action)
            except Exception as e:
                logger.warning(
                    f"LLM recommendation failed for {context.incident_number}, "
                    f"using rule-based only: {e}"
                )

        # Step 4: Adjust confidence based on severity
        actions = self._adjust_confidence_by_severity(actions, context.severity)

        # Step 5: Sort by confidence DESC, then risk ASC
        risk_order = {
            RemediationRisk.AUTO: 0,
            RemediationRisk.LOW: 1,
            RemediationRisk.MEDIUM: 2,
            RemediationRisk.HIGH: 3,
            RemediationRisk.CRITICAL: 4,
        }
        actions.sort(
            key=lambda a: (-a.confidence, risk_order.get(a.risk, 5))
        )

        logger.info(
            f"Generated {len(actions)} recommendations for {context.incident_number}"
        )

        return actions

    def _generate_rule_based_actions(
        self,
        context: IncidentContext,
    ) -> List[RemediationAction]:
        """Generate actions from pre-defined templates.

        Args:
            context: Incident context

        Returns:
            List of template-based RemediationAction objects
        """
        templates = ACTION_TEMPLATES.get(context.category, [])
        actions: List[RemediationAction] = []

        for template in templates:
            # Substitute placeholders in MCP params
            mcp_params = self._substitute_params(
                template.get("mcp_params", {}), context
            )

            action = RemediationAction(
                action_type=template["action_type"],
                title=template["title"],
                description=template["description"],
                confidence=template["confidence"],
                risk=template["risk"],
                mcp_tool=template.get("mcp_tool", ""),
                mcp_params=mcp_params,
                prerequisites=list(template.get("prerequisites", [])),
                rollback_steps=list(template.get("rollback_steps", [])),
                estimated_duration_seconds=template.get(
                    "estimated_duration_seconds", 60
                ),
                metadata={"source": "rule_template", "category": context.category.value},
            )
            actions.append(action)

        return actions

    def _substitute_params(
        self,
        params: Dict[str, Any],
        context: IncidentContext,
    ) -> Dict[str, Any]:
        """Substitute placeholders in MCP parameters.

        Supported placeholders:
            - {service_name}: from cmdb_ci or "unknown-service"
            - {affected_user}: from caller_id or "unknown"
            - {db_service}: from cmdb_ci or "database"
            - {incident_number}: from incident_number

        Args:
            params: Parameter dict with possible placeholders
            context: Incident context for substitution values

        Returns:
            Params with placeholders replaced
        """
        substitutions = {
            "{service_name}": context.cmdb_ci or "unknown-service",
            "{affected_user}": context.caller_id or "unknown",
            "{db_service}": context.cmdb_ci or "database",
            "{incident_number}": context.incident_number,
        }

        result: Dict[str, Any] = {}
        for key, value in params.items():
            if isinstance(value, str):
                for placeholder, replacement in substitutions.items():
                    value = value.replace(placeholder, replacement)
            result[key] = value

        return result

    def _is_duplicate(
        self,
        new_action: RemediationAction,
        existing_actions: List[RemediationAction],
    ) -> bool:
        """Check if an action is a duplicate of existing actions.

        Args:
            new_action: Action to check
            existing_actions: List of existing actions

        Returns:
            True if the action title matches an existing one
        """
        new_title = new_action.title.lower().strip()
        return any(
            a.title.lower().strip() == new_title for a in existing_actions
        )

    def _adjust_confidence_by_severity(
        self,
        actions: List[RemediationAction],
        severity: IncidentSeverity,
    ) -> List[RemediationAction]:
        """Adjust action confidence based on incident severity.

        Higher severity incidents get slightly boosted confidence for
        matching category actions.

        Args:
            actions: List of actions to adjust
            severity: Incident severity

        Returns:
            Actions with adjusted confidence (new list, original not mutated)
        """
        severity_boost = {
            IncidentSeverity.P1: 0.10,
            IncidentSeverity.P2: 0.05,
            IncidentSeverity.P3: 0.0,
            IncidentSeverity.P4: -0.05,
        }
        boost = severity_boost.get(severity, 0.0)

        adjusted: List[RemediationAction] = []
        for action in actions:
            new_confidence = min(1.0, max(0.0, action.confidence + boost))
            adjusted_action = RemediationAction(
                action_id=action.action_id,
                action_type=action.action_type,
                title=action.title,
                description=action.description,
                confidence=new_confidence,
                risk=action.risk,
                mcp_tool=action.mcp_tool,
                mcp_params=dict(action.mcp_params),
                prerequisites=list(action.prerequisites),
                rollback_steps=list(action.rollback_steps),
                estimated_duration_seconds=action.estimated_duration_seconds,
                metadata=dict(action.metadata),
            )
            adjusted.append(adjusted_action)

        return adjusted

    async def _generate_llm_actions(
        self,
        analysis: IncidentAnalysis,
        context: IncidentContext,
        existing_actions: List[RemediationAction],
    ) -> List[RemediationAction]:
        """Generate additional actions using LLM.

        Args:
            analysis: Current incident analysis
            context: Incident context
            existing_actions: Already generated actions

        Returns:
            List of LLM-suggested RemediationAction objects
        """
        if not self._llm_service:
            return []

        # Format existing suggestions
        existing_lines = []
        for a in existing_actions:
            existing_lines.append(
                f"- {a.title} (risk: {a.risk.value}, confidence: {a.confidence:.0%})"
            )
        existing_str = (
            "\n".join(existing_lines) if existing_lines else "No existing suggestions."
        )

        # Format contributing factors
        factors_str = "\n".join(
            f"- {f}" for f in analysis.contributing_factors
        ) or "None identified."

        prompt = REMEDIATION_SUGGESTION_PROMPT.format(
            incident_number=context.incident_number,
            severity=context.severity.value,
            category=context.category.value,
            short_description=context.short_description,
            root_cause_summary=analysis.root_cause_summary,
            contributing_factors=factors_str,
            existing_suggestions=existing_str,
        )

        response = await self._llm_service.generate_structured(
            prompt=prompt,
            output_schema={
                "suggestions": [
                    {
                        "title": "string",
                        "description": "string",
                        "confidence": "number",
                        "risk": "string",
                        "mcp_tool": "string",
                        "mcp_params": "object",
                        "prerequisites": ["string"],
                        "rollback_steps": ["string"],
                    }
                ]
            },
            max_tokens=1500,
            temperature=0.3,
        )

        # Parse LLM suggestions
        actions: List[RemediationAction] = []
        for suggestion in response.get("suggestions", []):
            try:
                risk_str = suggestion.get("risk", "medium").lower()
                risk_map = {
                    "auto": RemediationRisk.AUTO,
                    "low": RemediationRisk.LOW,
                    "medium": RemediationRisk.MEDIUM,
                    "high": RemediationRisk.HIGH,
                    "critical": RemediationRisk.CRITICAL,
                }
                risk = risk_map.get(risk_str, RemediationRisk.MEDIUM)

                action = RemediationAction(
                    action_type=RemediationActionType.CUSTOM,
                    title=suggestion.get("title", ""),
                    description=suggestion.get("description", ""),
                    confidence=min(1.0, max(0.0, float(suggestion.get("confidence", 0.5)))),
                    risk=risk,
                    mcp_tool=suggestion.get("mcp_tool", ""),
                    mcp_params=suggestion.get("mcp_params", {}),
                    prerequisites=suggestion.get("prerequisites", []),
                    rollback_steps=suggestion.get("rollback_steps", []),
                    metadata={"source": "llm_suggestion"},
                )
                actions.append(action)
            except (ValueError, TypeError) as e:
                logger.warning(f"Skipping invalid LLM suggestion: {e}")
                continue

        return actions
