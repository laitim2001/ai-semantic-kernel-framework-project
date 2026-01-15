"""
Completeness Checker Implementation

Checks information completeness for routing decisions based on intent category.
Extracts fields from user input and calculates completeness score.

Sprint 93: Story 93-2 - Implement CompletenessChecker (Phase 28)
"""

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from ..models import CompletenessInfo, ITIntentCategory
from .rules import (
    CompletenessRule,
    CompletenessRules,
    FieldDefinition,
    get_default_rules,
)

logger = logging.getLogger(__name__)


class CompletenessChecker:
    """
    Completeness checker for IT intent information.

    Analyzes user input to determine if sufficient information is provided
    for the detected intent category. Uses rule-based field extraction
    with keyword matching and regex patterns.

    Attributes:
        rules: CompletenessRules registry
        strict_mode: If True, requires all required fields (default: False)

    Example:
        >>> checker = CompletenessChecker()
        >>> result = checker.check(
        ...     intent_category=ITIntentCategory.INCIDENT,
        ...     user_input="ETL 今天跑失敗了，很緊急",
        ... )
        >>> print(result.completeness_score)  # 1.0
        >>> print(result.is_complete)  # True
    """

    def __init__(
        self,
        rules: Optional[CompletenessRules] = None,
        strict_mode: bool = False,
    ):
        """
        Initialize the completeness checker.

        Args:
            rules: Custom completeness rules (optional, uses defaults if not provided)
            strict_mode: Require all required fields if True
        """
        self.rules = rules or get_default_rules()
        self.strict_mode = strict_mode

    def check(
        self,
        intent_category: ITIntentCategory,
        user_input: str,
        collected_info: Optional[Dict[str, Any]] = None,
    ) -> CompletenessInfo:
        """
        Check information completeness for the given intent.

        Args:
            intent_category: The detected intent category
            user_input: The user's input text
            collected_info: Previously collected information (optional)

        Returns:
            CompletenessInfo with completeness assessment
        """
        # Get rule for this category
        rule = self.rules.get_rule(intent_category)

        # If no required fields, consider complete
        if not rule.required_fields:
            return CompletenessInfo(
                is_complete=True,
                completeness_score=1.0,
                missing_fields=[],
                optional_missing=[],
                suggestions=[],
            )

        # Merge collected info with extracted info
        merged_info = collected_info.copy() if collected_info else {}
        extracted_info = self._extract_fields(user_input, rule)
        merged_info.update(extracted_info)

        # Calculate completeness
        present_required = []
        missing_required = []

        for field in rule.required_fields:
            if self._field_present(field.name, merged_info, user_input, field):
                present_required.append(field.name)
            else:
                missing_required.append(field.name)

        # Check optional fields
        missing_optional = []
        for field in rule.optional_fields:
            if not self._field_present(field.name, merged_info, user_input, field):
                missing_optional.append(field.name)

        # Calculate score
        total_required = len(rule.required_fields)
        present_count = len(present_required)
        score = present_count / total_required if total_required > 0 else 1.0

        # Determine if complete (score >= threshold)
        is_complete = score >= rule.threshold

        # In strict mode, require all fields
        if self.strict_mode and missing_required:
            is_complete = False

        # Generate suggestions for missing fields
        suggestions = self._generate_suggestions(
            missing_required, rule
        )

        logger.debug(
            f"Completeness check for {intent_category.value}: "
            f"score={score:.2f}, threshold={rule.threshold}, "
            f"missing={missing_required}"
        )

        return CompletenessInfo(
            is_complete=is_complete,
            completeness_score=score,
            missing_fields=missing_required,
            optional_missing=missing_optional,
            suggestions=suggestions,
        )

    def _extract_fields(
        self,
        user_input: str,
        rule: CompletenessRule,
    ) -> Dict[str, Any]:
        """
        Extract field values from user input using patterns and keywords.

        Args:
            user_input: The user's input text
            rule: The completeness rule with field definitions

        Returns:
            Dictionary of extracted field values
        """
        extracted: Dict[str, Any] = {}
        all_fields = rule.required_fields + rule.optional_fields

        for field in all_fields:
            value = self._extract_field_value(user_input, field)
            if value is not None:
                extracted[field.name] = value

        return extracted

    def _extract_field_value(
        self,
        user_input: str,
        field: FieldDefinition,
    ) -> Optional[str]:
        """
        Extract a single field value from user input.

        Args:
            user_input: The user's input text
            field: The field definition

        Returns:
            Extracted value or None if not found
        """
        # Try patterns first
        for pattern in field.patterns:
            try:
                match = re.search(pattern, user_input, re.IGNORECASE | re.UNICODE)
                if match:
                    # Return the first captured group or the whole match
                    if match.groups():
                        value = match.group(1)
                        if value:
                            return value.strip()
                    else:
                        return match.group(0).strip()
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{pattern}': {e}")

        return None

    def _field_present(
        self,
        field_name: str,
        info: Dict[str, Any],
        user_input: str,
        field: FieldDefinition,
    ) -> bool:
        """
        Check if a field is present in collected info or user input.

        Args:
            field_name: Name of the field to check
            info: Collected information dictionary
            user_input: The user's input text
            field: The field definition

        Returns:
            True if field is present, False otherwise
        """
        # Check if explicitly provided in info
        if field_name in info and info[field_name]:
            return True

        # Check keywords in user input
        user_input_lower = user_input.lower()
        for keyword in field.keywords:
            if keyword.lower() in user_input_lower:
                return True

        # Check patterns
        for pattern in field.patterns:
            try:
                if re.search(pattern, user_input, re.IGNORECASE | re.UNICODE):
                    return True
            except re.error:
                pass

        return False

    def _generate_suggestions(
        self,
        missing_fields: List[str],
        rule: CompletenessRule,
    ) -> List[str]:
        """
        Generate suggestions for missing required fields.

        Args:
            missing_fields: List of missing field names
            rule: The completeness rule

        Returns:
            List of suggestion strings
        """
        suggestions = []
        field_map = {f.name: f for f in rule.required_fields}

        for field_name in missing_fields:
            field = field_map.get(field_name)
            if field:
                suggestion = rule.suggestions_template.format(
                    field_name=field.display_name
                )
                suggestions.append(suggestion)

        return suggestions

    def extract_all_fields(
        self,
        intent_category: ITIntentCategory,
        user_input: str,
    ) -> Dict[str, Any]:
        """
        Extract all fields from user input for a given intent.

        Args:
            intent_category: The intent category
            user_input: The user's input text

        Returns:
            Dictionary of all extracted fields
        """
        rule = self.rules.get_rule(intent_category)
        return self._extract_fields(user_input, rule)

    def get_required_fields(
        self,
        intent_category: ITIntentCategory,
    ) -> List[str]:
        """
        Get list of required fields for an intent category.

        Args:
            intent_category: The intent category

        Returns:
            List of required field names
        """
        rule = self.rules.get_rule(intent_category)
        return [f.name for f in rule.required_fields]

    def get_threshold(
        self,
        intent_category: ITIntentCategory,
    ) -> float:
        """
        Get completeness threshold for an intent category.

        Args:
            intent_category: The intent category

        Returns:
            Completeness threshold (0.0 to 1.0)
        """
        rule = self.rules.get_rule(intent_category)
        return rule.threshold

    def validate_info(
        self,
        intent_category: ITIntentCategory,
        info: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """
        Validate if provided info is complete for an intent.

        Args:
            intent_category: The intent category
            info: Information dictionary to validate

        Returns:
            Tuple of (is_valid, missing_fields)
        """
        rule = self.rules.get_rule(intent_category)
        missing = []

        for field in rule.required_fields:
            if field.name not in info or not info[field.name]:
                missing.append(field.name)

        is_valid = len(missing) == 0 or (
            len(rule.required_fields) - len(missing)
        ) / len(rule.required_fields) >= rule.threshold

        return is_valid, missing


class MockCompletenessChecker(CompletenessChecker):
    """
    Mock completeness checker for testing.

    Always returns a deterministic result based on input length.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def check(
        self,
        intent_category: ITIntentCategory,
        user_input: str,
        collected_info: Optional[Dict[str, Any]] = None,
    ) -> CompletenessInfo:
        """
        Mock completeness check based on input length.

        Args:
            intent_category: The intent category
            user_input: The user's input text
            collected_info: Previously collected info (optional)

        Returns:
            CompletenessInfo with mock assessment
        """
        # Simple heuristic based on input length
        input_length = len(user_input)

        if input_length >= 50:
            score = 1.0
            is_complete = True
            missing = []
        elif input_length >= 30:
            score = 0.8
            is_complete = True
            missing = []
        elif input_length >= 15:
            score = 0.6
            is_complete = True
            missing = ["additional_details"]
        else:
            score = 0.3
            is_complete = False
            missing = ["description", "context"]

        return CompletenessInfo(
            is_complete=is_complete,
            completeness_score=score,
            missing_fields=missing,
            optional_missing=[],
            suggestions=[f"請提供更多詳細資訊"] if not is_complete else [],
        )


# =============================================================================
# Factory Functions
# =============================================================================

def create_completeness_checker(
    rules: Optional[CompletenessRules] = None,
    strict_mode: bool = False,
) -> CompletenessChecker:
    """
    Factory function to create a CompletenessChecker instance.

    Args:
        rules: Custom rules (optional)
        strict_mode: Require all fields if True

    Returns:
        CompletenessChecker instance
    """
    return CompletenessChecker(rules=rules, strict_mode=strict_mode)


def create_mock_checker() -> MockCompletenessChecker:
    """
    Factory function to create a mock checker for testing.

    Returns:
        MockCompletenessChecker instance
    """
    return MockCompletenessChecker()


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "CompletenessChecker",
    "MockCompletenessChecker",
    "create_completeness_checker",
    "create_mock_checker",
]
