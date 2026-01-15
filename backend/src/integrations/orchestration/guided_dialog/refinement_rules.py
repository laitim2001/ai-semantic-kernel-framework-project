"""
Refinement Rules for Sub-Intent Refinement

Defines rules for refining sub_intent based on extracted information.
Key principle: No LLM re-classification, only rule-based refinement.

Sprint 94: Story 94-3 - Implement Incremental Update Logic (Phase 28)
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from ..intent_router.models import ITIntentCategory

logger = logging.getLogger(__name__)


@dataclass
class RefinementCondition:
    """
    Condition for sub_intent refinement.

    Attributes:
        field_name: Field to check (e.g., "affected_system")
        field_value: Expected value or pattern
        is_pattern: If True, field_value is treated as regex pattern
        match_any: If True, matches if any keyword in field_value list matches
    """
    field_name: str
    field_value: str
    is_pattern: bool = False
    match_any: bool = False

    def matches(self, info: Dict[str, Any]) -> bool:
        """
        Check if condition matches the given information.

        Args:
            info: Dictionary of extracted information

        Returns:
            True if condition matches
        """
        value = info.get(self.field_name)
        if value is None:
            return False

        str_value = str(value).lower()

        if self.is_pattern:
            try:
                return bool(re.search(self.field_value, str_value, re.IGNORECASE))
            except re.error:
                logger.warning(f"Invalid regex pattern: {self.field_value}")
                return False

        if self.match_any:
            # field_value is a pipe-separated list of keywords
            keywords = self.field_value.lower().split("|")
            return any(kw in str_value for kw in keywords)

        return self.field_value.lower() in str_value


@dataclass
class RefinementRule:
    """
    Rule for refining sub_intent based on conditions.

    Attributes:
        id: Unique rule identifier
        category: Intent category this rule applies to
        from_sub_intent: Original sub_intent to match
        to_sub_intent: Target sub_intent after refinement
        conditions: List of conditions that must all match
        description: Human-readable description
        priority: Rule priority (higher = checked first)
        enabled: Whether the rule is active
    """
    id: str
    category: ITIntentCategory
    from_sub_intent: str
    to_sub_intent: str
    conditions: List[RefinementCondition]
    description: str = ""
    priority: int = 100
    enabled: bool = True

    def matches(
        self,
        current_sub_intent: str,
        info: Dict[str, Any],
    ) -> bool:
        """
        Check if this rule matches the current state.

        Args:
            current_sub_intent: Current sub_intent
            info: Extracted information dictionary

        Returns:
            True if rule matches (all conditions met)
        """
        if not self.enabled:
            return False

        # Check if from_sub_intent matches (or is wildcard)
        if self.from_sub_intent != "*":
            if current_sub_intent != self.from_sub_intent:
                return False

        # All conditions must match
        return all(cond.matches(info) for cond in self.conditions)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "category": self.category.value,
            "from_sub_intent": self.from_sub_intent,
            "to_sub_intent": self.to_sub_intent,
            "conditions": [
                {
                    "field_name": c.field_name,
                    "field_value": c.field_value,
                    "is_pattern": c.is_pattern,
                    "match_any": c.match_any,
                }
                for c in self.conditions
            ],
            "description": self.description,
            "priority": self.priority,
            "enabled": self.enabled,
        }


# =============================================================================
# Default Refinement Rules
# =============================================================================

# -----------------------------------------------------------------------------
# Incident Refinement Rules (事件細化規則)
# -----------------------------------------------------------------------------

INCIDENT_REFINEMENT_RULES: List[RefinementRule] = [
    # ETL Failure
    RefinementRule(
        id="INC_REF_001",
        category=ITIntentCategory.INCIDENT,
        from_sub_intent="general_incident",
        to_sub_intent="etl_failure",
        conditions=[
            RefinementCondition(
                field_name="affected_system",
                field_value="ETL|Pipeline|批次|排程|資料管道",
                match_any=True,
            ),
            RefinementCondition(
                field_name="symptom_type",
                field_value="報錯|失敗|錯誤|error|fail",
                match_any=True,
            ),
        ],
        description="ETL 系統報錯 → etl_failure",
        priority=100,
    ),
    # Network Failure
    RefinementRule(
        id="INC_REF_002",
        category=ITIntentCategory.INCIDENT,
        from_sub_intent="general_incident",
        to_sub_intent="network_failure",
        conditions=[
            RefinementCondition(
                field_name="affected_system",
                field_value="網路|network|網絡|VPN|防火牆|Firewall",
                match_any=True,
            ),
            RefinementCondition(
                field_name="symptom_type",
                field_value="斷線|disconnect|無法連接|連不上|timeout",
                match_any=True,
            ),
        ],
        description="網路系統斷線 → network_failure",
        priority=100,
    ),
    # Database Performance
    RefinementRule(
        id="INC_REF_003",
        category=ITIntentCategory.INCIDENT,
        from_sub_intent="general_incident",
        to_sub_intent="database_performance",
        conditions=[
            RefinementCondition(
                field_name="affected_system",
                field_value="資料庫|database|DB|SQL|Oracle|PostgreSQL|MySQL|MongoDB",
                match_any=True,
            ),
            RefinementCondition(
                field_name="symptom_type",
                field_value="慢|延遲|效能|slow|performance|lag|卡",
                match_any=True,
            ),
        ],
        description="資料庫效能問題 → database_performance",
        priority=100,
    ),
    # System Down (高優先級)
    RefinementRule(
        id="INC_REF_004",
        category=ITIntentCategory.INCIDENT,
        from_sub_intent="general_incident",
        to_sub_intent="system_down",
        conditions=[
            RefinementCondition(
                field_name="symptom_type",
                field_value="當機|掛|down|unavailable|停止|無法使用|crash",
                match_any=True,
            ),
        ],
        description="系統當機 → system_down",
        priority=150,  # Higher priority
    ),
    # API Error
    RefinementRule(
        id="INC_REF_005",
        category=ITIntentCategory.INCIDENT,
        from_sub_intent="general_incident",
        to_sub_intent="api_error",
        conditions=[
            RefinementCondition(
                field_name="affected_system",
                field_value="API|接口|服務|Service|Gateway|端點",
                match_any=True,
            ),
            RefinementCondition(
                field_name="symptom_type",
                field_value="錯誤|error|500|503|400|fail|失敗",
                match_any=True,
            ),
        ],
        description="API 錯誤 → api_error",
        priority=90,
    ),
    # Login Issue
    RefinementRule(
        id="INC_REF_006",
        category=ITIntentCategory.INCIDENT,
        from_sub_intent="general_incident",
        to_sub_intent="login_issue",
        conditions=[
            RefinementCondition(
                field_name="symptom_type",
                field_value="登入|login|登錄|認證|authentication|無法進入",
                match_any=True,
            ),
        ],
        description="登入問題 → login_issue",
        priority=80,
    ),
]

# -----------------------------------------------------------------------------
# Request Refinement Rules (請求細化規則)
# -----------------------------------------------------------------------------

REQUEST_REFINEMENT_RULES: List[RefinementRule] = [
    # Account Request
    RefinementRule(
        id="REQ_REF_001",
        category=ITIntentCategory.REQUEST,
        from_sub_intent="general_request",
        to_sub_intent="account_request",
        conditions=[
            RefinementCondition(
                field_name="request_type",
                field_value="帳號|account|用戶|user|員工|新人|報到",
                match_any=True,
            ),
        ],
        description="帳號申請 → account_request",
        priority=100,
    ),
    # Access Request
    RefinementRule(
        id="REQ_REF_002",
        category=ITIntentCategory.REQUEST,
        from_sub_intent="general_request",
        to_sub_intent="access_request",
        conditions=[
            RefinementCondition(
                field_name="request_type",
                field_value="權限|access|存取|授權|permission|VPN",
                match_any=True,
            ),
        ],
        description="權限申請 → access_request",
        priority=100,
    ),
    # Software Request
    RefinementRule(
        id="REQ_REF_003",
        category=ITIntentCategory.REQUEST,
        from_sub_intent="general_request",
        to_sub_intent="software_request",
        conditions=[
            RefinementCondition(
                field_name="request_type",
                field_value="軟體|software|安裝|install|程式|application|app",
                match_any=True,
            ),
        ],
        description="軟體安裝 → software_request",
        priority=100,
    ),
    # Hardware Request
    RefinementRule(
        id="REQ_REF_004",
        category=ITIntentCategory.REQUEST,
        from_sub_intent="general_request",
        to_sub_intent="hardware_request",
        conditions=[
            RefinementCondition(
                field_name="request_type",
                field_value="設備|hardware|電腦|筆電|laptop|螢幕|monitor|鍵盤|滑鼠",
                match_any=True,
            ),
        ],
        description="設備申請 → hardware_request",
        priority=100,
    ),
    # Password Reset
    RefinementRule(
        id="REQ_REF_005",
        category=ITIntentCategory.REQUEST,
        from_sub_intent="general_request",
        to_sub_intent="password_reset",
        conditions=[
            RefinementCondition(
                field_name="request_type",
                field_value="密碼|password|重設|reset|忘記|forgot",
                match_any=True,
            ),
        ],
        description="密碼重設 → password_reset",
        priority=110,  # Higher priority
    ),
]

# -----------------------------------------------------------------------------
# Change Refinement Rules (變更細化規則)
# -----------------------------------------------------------------------------

CHANGE_REFINEMENT_RULES: List[RefinementRule] = [
    # Release Deployment
    RefinementRule(
        id="CHG_REF_001",
        category=ITIntentCategory.CHANGE,
        from_sub_intent="general_change",
        to_sub_intent="release_deployment",
        conditions=[
            RefinementCondition(
                field_name="change_type",
                field_value="部署|deploy|發布|release|上版|版本|上線",
                match_any=True,
            ),
        ],
        description="版本部署 → release_deployment",
        priority=100,
    ),
    # Configuration Update
    RefinementRule(
        id="CHG_REF_002",
        category=ITIntentCategory.CHANGE,
        from_sub_intent="general_change",
        to_sub_intent="configuration_update",
        conditions=[
            RefinementCondition(
                field_name="change_type",
                field_value="配置|config|設定|parameter|參數|環境變數",
                match_any=True,
            ),
        ],
        description="配置更新 → configuration_update",
        priority=100,
    ),
    # Database Change
    RefinementRule(
        id="CHG_REF_003",
        category=ITIntentCategory.CHANGE,
        from_sub_intent="general_change",
        to_sub_intent="database_change",
        conditions=[
            RefinementCondition(
                field_name="target_system",
                field_value="資料庫|database|DB|SQL|schema|table|表",
                match_any=True,
            ),
        ],
        description="資料庫變更 → database_change",
        priority=110,
    ),
    # Infrastructure Change
    RefinementRule(
        id="CHG_REF_004",
        category=ITIntentCategory.CHANGE,
        from_sub_intent="general_change",
        to_sub_intent="infrastructure_change",
        conditions=[
            RefinementCondition(
                field_name="change_type",
                field_value="升級|upgrade|遷移|migration|擴容|scale|伺服器|server",
                match_any=True,
            ),
        ],
        description="基礎設施變更 → infrastructure_change",
        priority=90,
    ),
]


# =============================================================================
# Rules Registry
# =============================================================================

class RefinementRules:
    """
    Registry for refinement rules organized by intent category.

    Provides rule lookup and matching for the ConversationContextManager.
    """

    def __init__(
        self,
        custom_rules: Optional[Dict[ITIntentCategory, List[RefinementRule]]] = None,
    ):
        """
        Initialize the refinement rules registry.

        Args:
            custom_rules: Custom rules to add/override defaults
        """
        self._rules: Dict[ITIntentCategory, List[RefinementRule]] = {
            ITIntentCategory.INCIDENT: list(INCIDENT_REFINEMENT_RULES),
            ITIntentCategory.REQUEST: list(REQUEST_REFINEMENT_RULES),
            ITIntentCategory.CHANGE: list(CHANGE_REFINEMENT_RULES),
            ITIntentCategory.QUERY: [],
            ITIntentCategory.UNKNOWN: [],
        }

        if custom_rules:
            for category, rules in custom_rules.items():
                if category in self._rules:
                    self._rules[category].extend(rules)
                else:
                    self._rules[category] = rules

        # Sort rules by priority (descending)
        for category in self._rules:
            self._rules[category].sort(key=lambda r: r.priority, reverse=True)

    def find_rule(
        self,
        category: ITIntentCategory,
        current_sub_intent: str,
        extracted_info: Dict[str, Any],
    ) -> Optional[RefinementRule]:
        """
        Find matching refinement rule.

        Args:
            category: Intent category
            current_sub_intent: Current sub_intent value
            extracted_info: Extracted information from user response

        Returns:
            Matching RefinementRule or None if no match
        """
        rules = self._rules.get(category, [])

        for rule in rules:
            if rule.matches(current_sub_intent, extracted_info):
                logger.debug(
                    f"Refinement rule matched: {rule.id} "
                    f"({current_sub_intent} → {rule.to_sub_intent})"
                )
                return rule

        return None

    def get_rules_for_category(
        self,
        category: ITIntentCategory,
    ) -> List[RefinementRule]:
        """Get all rules for a category."""
        return self._rules.get(category, [])

    def add_rule(self, rule: RefinementRule) -> None:
        """
        Add a new refinement rule.

        Args:
            rule: RefinementRule to add
        """
        if rule.category not in self._rules:
            self._rules[rule.category] = []

        self._rules[rule.category].append(rule)
        # Re-sort by priority
        self._rules[rule.category].sort(key=lambda r: r.priority, reverse=True)

    def remove_rule(self, rule_id: str) -> bool:
        """
        Remove a rule by ID.

        Args:
            rule_id: ID of rule to remove

        Returns:
            True if rule was found and removed
        """
        for category in self._rules:
            for i, rule in enumerate(self._rules[category]):
                if rule.id == rule_id:
                    self._rules[category].pop(i)
                    return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert all rules to dictionary for serialization."""
        return {
            category.value: [rule.to_dict() for rule in rules]
            for category, rules in self._rules.items()
        }

    def get_all_target_sub_intents(
        self,
        category: ITIntentCategory,
    ) -> Set[str]:
        """
        Get all possible target sub_intents for a category.

        Args:
            category: Intent category

        Returns:
            Set of all possible target sub_intent values
        """
        rules = self._rules.get(category, [])
        return {rule.to_sub_intent for rule in rules}


# =============================================================================
# Factory Functions
# =============================================================================

def get_default_refinement_rules() -> RefinementRules:
    """Get default refinement rules instance."""
    return RefinementRules()


def create_refinement_rule(
    rule_id: str,
    category: ITIntentCategory,
    from_sub: str,
    to_sub: str,
    conditions: List[Dict[str, Any]],
    **kwargs,
) -> RefinementRule:
    """
    Factory function to create a RefinementRule.

    Args:
        rule_id: Unique rule identifier
        category: Intent category
        from_sub: Source sub_intent
        to_sub: Target sub_intent
        conditions: List of condition dictionaries
        **kwargs: Additional rule attributes

    Returns:
        RefinementRule instance
    """
    cond_list = [
        RefinementCondition(
            field_name=c["field_name"],
            field_value=c["field_value"],
            is_pattern=c.get("is_pattern", False),
            match_any=c.get("match_any", False),
        )
        for c in conditions
    ]

    return RefinementRule(
        id=rule_id,
        category=category,
        from_sub_intent=from_sub,
        to_sub_intent=to_sub,
        conditions=cond_list,
        **kwargs,
    )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "RefinementCondition",
    "RefinementRule",
    "RefinementRules",
    # Rule collections
    "INCIDENT_REFINEMENT_RULES",
    "REQUEST_REFINEMENT_RULES",
    "CHANGE_REFINEMENT_RULES",
    # Factory functions
    "get_default_refinement_rules",
    "create_refinement_rule",
]
