"""
Pattern Matcher Implementation

Provides rule-based pattern matching using pre-compiled regex patterns.
Designed for high performance (<10ms) with configurable rules via YAML.

Sprint 91: Pattern Matcher + Rule Definition (Phase 28)
"""

import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Pattern, Tuple

import yaml

from ..models import (
    ITIntentCategory,
    PatternMatchResult,
    PatternRule,
    RiskLevel,
    WorkflowType,
)

logger = logging.getLogger(__name__)


@dataclass
class CompiledRule:
    """
    A rule with pre-compiled regex patterns.

    Attributes:
        rule: The original pattern rule
        compiled_patterns: List of compiled regex patterns
    """
    rule: PatternRule
    compiled_patterns: List[Tuple[Pattern[str], str]]


class PatternMatcher:
    """
    Rule-based pattern matcher for IT intent classification.

    Uses pre-compiled regex patterns loaded from YAML configuration
    for high-performance pattern matching.

    Attributes:
        rules_path: Path to YAML rules file
        rules: List of pattern rules
        compiled_rules: Pre-compiled regex patterns
        default_confidence: Default confidence for pattern matches
    """

    DEFAULT_CONFIDENCE = 0.95
    MIN_CONFIDENCE_THRESHOLD = 0.5

    def __init__(
        self,
        rules_path: Optional[str] = None,
        rules_dict: Optional[Dict[str, Any]] = None,
        default_confidence: float = DEFAULT_CONFIDENCE,
    ):
        """
        Initialize the pattern matcher.

        Args:
            rules_path: Path to YAML rules file
            rules_dict: Dictionary of rules (alternative to file)
            default_confidence: Default confidence for matches
        """
        self.rules_path = rules_path
        self.default_confidence = default_confidence
        self.rules: List[PatternRule] = []
        self.compiled_rules: List[CompiledRule] = []
        self._load_time_ms: float = 0.0

        if rules_dict:
            self._load_from_dict(rules_dict)
        elif rules_path:
            self._load_from_file(rules_path)

    def _load_from_file(self, rules_path: str) -> None:
        """
        Load rules from YAML file.

        Args:
            rules_path: Path to YAML rules file
        """
        start_time = time.perf_counter()
        path = Path(rules_path)

        if not path.exists():
            logger.warning(f"Rules file not found: {rules_path}")
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if data:
                self._load_from_dict(data)

        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML rules: {e}")
            raise ValueError(f"Invalid YAML in rules file: {e}")
        except Exception as e:
            logger.error(f"Error loading rules file: {e}")
            raise

        self._load_time_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"Loaded {len(self.rules)} rules in {self._load_time_ms:.2f}ms"
        )

    def _load_from_dict(self, data: Dict[str, Any]) -> None:
        """
        Load rules from dictionary.

        Args:
            data: Dictionary containing rules
        """
        rules_data = data.get("rules", [])

        for rule_data in rules_data:
            try:
                rule = self._parse_rule(rule_data)
                if rule.enabled:
                    self.rules.append(rule)
                    self._compile_rule(rule)
            except Exception as e:
                logger.warning(f"Error parsing rule {rule_data.get('id')}: {e}")

        # Sort by priority (descending)
        self.compiled_rules.sort(key=lambda cr: cr.rule.priority, reverse=True)

    def _parse_rule(self, rule_data: Dict[str, Any]) -> PatternRule:
        """
        Parse a single rule from dictionary.

        Args:
            rule_data: Dictionary containing rule data

        Returns:
            PatternRule instance
        """
        return PatternRule(
            id=rule_data["id"],
            category=ITIntentCategory.from_string(rule_data["category"]),
            sub_intent=rule_data.get("sub_intent", ""),
            patterns=rule_data.get("patterns", []),
            priority=rule_data.get("priority", 100),
            workflow_type=WorkflowType.from_string(
                rule_data.get("workflow_type", "simple")
            ),
            risk_level=RiskLevel.from_string(
                rule_data.get("risk_level", "medium")
            ),
            description=rule_data.get("description", ""),
            enabled=rule_data.get("enabled", True),
        )

    def _compile_rule(self, rule: PatternRule) -> None:
        """
        Compile regex patterns for a rule.

        Args:
            rule: The rule to compile patterns for
        """
        compiled_patterns: List[Tuple[Pattern[str], str]] = []

        for pattern_str in rule.patterns:
            try:
                # Compile with case-insensitive flag
                compiled = re.compile(pattern_str, re.IGNORECASE | re.UNICODE)
                compiled_patterns.append((compiled, pattern_str))
            except re.error as e:
                logger.warning(
                    f"Invalid regex pattern '{pattern_str}' in rule {rule.id}: {e}"
                )

        if compiled_patterns:
            self.compiled_rules.append(CompiledRule(rule, compiled_patterns))

    def match(self, user_input: str) -> PatternMatchResult:
        """
        Match user input against all rules.

        Args:
            user_input: The user's input text

        Returns:
            PatternMatchResult indicating match status
        """
        if not user_input or not user_input.strip():
            return PatternMatchResult.no_match()

        # Normalize input
        normalized_input = user_input.strip()

        # Try each compiled rule in priority order
        for compiled_rule in self.compiled_rules:
            result = self._try_match_rule(compiled_rule, normalized_input)
            if result.matched:
                return result

        return PatternMatchResult.no_match()

    def _try_match_rule(
        self,
        compiled_rule: CompiledRule,
        user_input: str,
    ) -> PatternMatchResult:
        """
        Try to match input against a single rule.

        Args:
            compiled_rule: The compiled rule to match
            user_input: Normalized user input

        Returns:
            PatternMatchResult
        """
        rule = compiled_rule.rule

        for compiled_pattern, pattern_str in compiled_rule.compiled_patterns:
            match = compiled_pattern.search(user_input)
            if match:
                # Calculate confidence based on match quality
                confidence = self._calculate_confidence(
                    match, user_input, rule
                )

                return PatternMatchResult(
                    matched=True,
                    intent_category=rule.category,
                    sub_intent=rule.sub_intent,
                    confidence=confidence,
                    rule_id=rule.id,
                    workflow_type=rule.workflow_type,
                    risk_level=rule.risk_level,
                    matched_pattern=pattern_str,
                    match_position=match.start(),
                )

        return PatternMatchResult.no_match()

    def _calculate_confidence(
        self,
        match: re.Match[str],
        user_input: str,
        rule: PatternRule,
    ) -> float:
        """
        Calculate confidence score for a match.

        Factors:
        - Match coverage: How much of input is covered
        - Rule priority: Higher priority = higher confidence
        - Match position: Earlier matches may be more relevant

        Args:
            match: The regex match object
            user_input: The original user input
            rule: The matched rule

        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Base confidence
        base_confidence = self.default_confidence

        # Coverage factor: how much of input is matched
        match_length = match.end() - match.start()
        input_length = len(user_input)
        coverage_factor = min(match_length / max(input_length, 1), 1.0)

        # Priority factor: normalize priority (assume 0-200 range)
        priority_factor = min(rule.priority / 200.0, 1.0)

        # Position factor: earlier matches slightly preferred
        position_factor = 1.0 - (match.start() / max(input_length, 1)) * 0.1

        # Combine factors with weights
        confidence = base_confidence * (
            0.7 +  # Base weight
            0.1 * coverage_factor +
            0.1 * priority_factor +
            0.1 * position_factor
        )

        return min(max(confidence, 0.0), 1.0)

    def match_all(
        self,
        user_input: str,
        max_results: int = 5,
    ) -> List[PatternMatchResult]:
        """
        Find all matching rules for user input.

        Args:
            user_input: The user's input text
            max_results: Maximum number of results to return

        Returns:
            List of PatternMatchResult instances
        """
        if not user_input or not user_input.strip():
            return []

        normalized_input = user_input.strip()
        results: List[PatternMatchResult] = []

        for compiled_rule in self.compiled_rules:
            result = self._try_match_rule(compiled_rule, normalized_input)
            if result.matched:
                results.append(result)
                if len(results) >= max_results:
                    break

        return results

    def get_rules_count(self) -> int:
        """Get total number of loaded rules."""
        return len(self.rules)

    def get_rules_by_category(
        self,
        category: ITIntentCategory,
    ) -> List[PatternRule]:
        """
        Get all rules for a specific category.

        Args:
            category: The intent category to filter by

        Returns:
            List of PatternRule instances
        """
        return [rule for rule in self.rules if rule.category == category]

    def reload_rules(self, rules_path: Optional[str] = None) -> None:
        """
        Reload rules from file.

        Args:
            rules_path: Optional new path to load from
        """
        path = rules_path or self.rules_path
        if path:
            self.rules.clear()
            self.compiled_rules.clear()
            self._load_from_file(path)

    def add_rule(self, rule: PatternRule) -> None:
        """
        Add a new rule dynamically.

        Args:
            rule: The rule to add
        """
        if rule.enabled:
            self.rules.append(rule)
            self._compile_rule(rule)
            # Re-sort by priority
            self.compiled_rules.sort(
                key=lambda cr: cr.rule.priority, reverse=True
            )

    def remove_rule(self, rule_id: str) -> bool:
        """
        Remove a rule by ID.

        Args:
            rule_id: The ID of the rule to remove

        Returns:
            True if rule was removed, False if not found
        """
        self.rules = [r for r in self.rules if r.id != rule_id]
        original_count = len(self.compiled_rules)
        self.compiled_rules = [
            cr for cr in self.compiled_rules if cr.rule.id != rule_id
        ]
        return len(self.compiled_rules) < original_count

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get matcher statistics.

        Returns:
            Dictionary with statistics
        """
        category_counts: Dict[str, int] = {}
        for rule in self.rules:
            cat = rule.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1

        total_patterns = sum(len(r.patterns) for r in self.rules)

        return {
            "total_rules": len(self.rules),
            "total_patterns": total_patterns,
            "load_time_ms": self._load_time_ms,
            "category_distribution": category_counts,
            "enabled_rules": len([r for r in self.rules if r.enabled]),
        }
