"""
Completeness Module

Provides information completeness checking for IT intent routing.

Sprint 93: CompletenessChecker + Rules Definition (Phase 28)
"""

from .checker import (
    CompletenessChecker,
    MockCompletenessChecker,
    create_completeness_checker,
    create_mock_checker,
)
from .rules import (
    FieldDefinition,
    CompletenessRule,
    CompletenessRules,
    # Default rules
    INCIDENT_RULE,
    REQUEST_RULE,
    CHANGE_RULE,
    QUERY_RULE,
    UNKNOWN_RULE,
    # Field collections
    INCIDENT_FIELDS,
    REQUEST_FIELDS,
    CHANGE_FIELDS,
    QUERY_FIELDS,
    # Utility functions
    get_default_rules,
    get_required_fields,
    get_field_definition,
)

__all__ = [
    # Checker classes
    "CompletenessChecker",
    "MockCompletenessChecker",
    "create_completeness_checker",
    "create_mock_checker",
    # Rule classes
    "FieldDefinition",
    "CompletenessRule",
    "CompletenessRules",
    # Default rules
    "INCIDENT_RULE",
    "REQUEST_RULE",
    "CHANGE_RULE",
    "QUERY_RULE",
    "UNKNOWN_RULE",
    # Field collections
    "INCIDENT_FIELDS",
    "REQUEST_FIELDS",
    "CHANGE_FIELDS",
    "QUERY_FIELDS",
    # Utility functions
    "get_default_rules",
    "get_required_fields",
    "get_field_definition",
]
