"""
Unit Tests for Pattern Matcher

Tests for:
- Core models (ITIntentCategory, CompletenessInfo, RoutingDecision)
- PatternMatcher matching logic
- Rule loading and parsing
- Confidence calculation
- Performance requirements

Sprint 91: Pattern Matcher + Rule Definition (Phase 28)
"""

import time
from pathlib import Path

import pytest

from src.integrations.orchestration.intent_router.models import (
    CompletenessInfo,
    ITIntentCategory,
    PatternMatchResult,
    PatternRule,
    RiskLevel,
    RoutingDecision,
    WorkflowType,
)
from src.integrations.orchestration.intent_router.pattern_matcher import (
    PatternMatcher,
)


class TestITIntentCategory:
    """Tests for ITIntentCategory enum."""

    def test_all_categories_exist(self):
        """All ITIL categories should be defined."""
        assert ITIntentCategory.INCIDENT.value == "incident"
        assert ITIntentCategory.REQUEST.value == "request"
        assert ITIntentCategory.CHANGE.value == "change"
        assert ITIntentCategory.QUERY.value == "query"
        assert ITIntentCategory.UNKNOWN.value == "unknown"

    def test_from_string_valid(self):
        """Should convert valid strings to enum."""
        assert ITIntentCategory.from_string("incident") == ITIntentCategory.INCIDENT
        assert ITIntentCategory.from_string("INCIDENT") == ITIntentCategory.INCIDENT
        assert ITIntentCategory.from_string("Request") == ITIntentCategory.REQUEST

    def test_from_string_invalid(self):
        """Should return UNKNOWN for invalid strings."""
        assert ITIntentCategory.from_string("invalid") == ITIntentCategory.UNKNOWN
        assert ITIntentCategory.from_string("") == ITIntentCategory.UNKNOWN


class TestRiskLevel:
    """Tests for RiskLevel enum."""

    def test_all_levels_exist(self):
        """All risk levels should be defined."""
        assert RiskLevel.CRITICAL.value == "critical"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.LOW.value == "low"

    def test_from_string_valid(self):
        """Should convert valid strings to enum."""
        assert RiskLevel.from_string("critical") == RiskLevel.CRITICAL
        assert RiskLevel.from_string("HIGH") == RiskLevel.HIGH

    def test_from_string_invalid(self):
        """Should return MEDIUM for invalid strings."""
        assert RiskLevel.from_string("invalid") == RiskLevel.MEDIUM


class TestWorkflowType:
    """Tests for WorkflowType enum."""

    def test_all_types_exist(self):
        """All workflow types should be defined."""
        assert WorkflowType.MAGENTIC.value == "magentic"
        assert WorkflowType.HANDOFF.value == "handoff"
        assert WorkflowType.CONCURRENT.value == "concurrent"
        assert WorkflowType.SEQUENTIAL.value == "sequential"
        assert WorkflowType.SIMPLE.value == "simple"

    def test_from_string_valid(self):
        """Should convert valid strings to enum."""
        assert WorkflowType.from_string("magentic") == WorkflowType.MAGENTIC

    def test_from_string_invalid(self):
        """Should return SIMPLE for invalid strings."""
        assert WorkflowType.from_string("invalid") == WorkflowType.SIMPLE


class TestCompletenessInfo:
    """Tests for CompletenessInfo dataclass."""

    def test_default_values(self):
        """Default values should indicate complete information."""
        info = CompletenessInfo()
        assert info.is_complete is True
        assert info.missing_fields == []
        assert info.completeness_score == 1.0

    def test_with_missing_fields(self):
        """Should track missing fields."""
        info = CompletenessInfo(
            is_complete=False,
            missing_fields=["field1", "field2"],
            completeness_score=0.5,
        )
        assert info.is_complete is False
        assert len(info.missing_fields) == 2
        assert info.completeness_score == 0.5

    def test_invalid_completeness_score(self):
        """Should raise error for invalid score."""
        with pytest.raises(ValueError):
            CompletenessInfo(completeness_score=1.5)
        with pytest.raises(ValueError):
            CompletenessInfo(completeness_score=-0.1)


class TestPatternMatchResult:
    """Tests for PatternMatchResult dataclass."""

    def test_no_match_factory(self):
        """No match factory should create valid result."""
        result = PatternMatchResult.no_match()
        assert result.matched is False
        assert result.confidence == 0.0
        assert result.intent_category is None

    def test_matched_result(self):
        """Matched result should have all fields."""
        result = PatternMatchResult(
            matched=True,
            intent_category=ITIntentCategory.INCIDENT,
            sub_intent="etl_failure",
            confidence=0.95,
            rule_id="incident_etl_failure",
            workflow_type=WorkflowType.MAGENTIC,
            risk_level=RiskLevel.HIGH,
        )
        assert result.matched is True
        assert result.intent_category == ITIntentCategory.INCIDENT
        assert result.confidence == 0.95

    def test_invalid_confidence(self):
        """Should raise error for invalid confidence."""
        with pytest.raises(ValueError):
            PatternMatchResult(matched=True, confidence=1.5)


class TestRoutingDecision:
    """Tests for RoutingDecision dataclass."""

    def test_default_values(self):
        """Default values should be sensible."""
        decision = RoutingDecision(intent_category=ITIntentCategory.INCIDENT)
        assert decision.intent_category == ITIntentCategory.INCIDENT
        assert decision.confidence == 0.0
        assert decision.workflow_type == WorkflowType.SIMPLE
        assert decision.routing_layer == "pattern"

    def test_to_dict(self):
        """Should convert to dictionary correctly."""
        decision = RoutingDecision(
            intent_category=ITIntentCategory.INCIDENT,
            sub_intent="etl_failure",
            confidence=0.95,
        )
        d = decision.to_dict()
        assert d["intent_category"] == "incident"
        assert d["sub_intent"] == "etl_failure"
        assert d["confidence"] == 0.95

    def test_from_pattern_match_success(self):
        """Should create from successful pattern match."""
        match_result = PatternMatchResult(
            matched=True,
            intent_category=ITIntentCategory.INCIDENT,
            sub_intent="etl_failure",
            confidence=0.95,
            rule_id="incident_etl_failure",
            workflow_type=WorkflowType.MAGENTIC,
            risk_level=RiskLevel.HIGH,
            matched_pattern="ETL.*失敗",
        )
        decision = RoutingDecision.from_pattern_match(match_result, 5.0)
        assert decision.intent_category == ITIntentCategory.INCIDENT
        assert decision.confidence == 0.95
        assert decision.processing_time_ms == 5.0

    def test_from_pattern_match_no_match(self):
        """Should create from no match result."""
        match_result = PatternMatchResult.no_match()
        decision = RoutingDecision.from_pattern_match(match_result, 1.0)
        assert decision.intent_category == ITIntentCategory.UNKNOWN
        assert decision.confidence == 0.0


class TestPatternMatcher:
    """Tests for PatternMatcher class."""

    @pytest.fixture
    def sample_rules(self):
        """Sample rules for testing."""
        return {
            "rules": [
                {
                    "id": "incident_etl_failure",
                    "category": "incident",
                    "sub_intent": "etl_failure",
                    "patterns": ["ETL.*失敗", "ETL.*fail", "pipeline.*error"],
                    "priority": 100,
                    "workflow_type": "magentic",
                    "risk_level": "high",
                },
                {
                    "id": "request_account",
                    "category": "request",
                    "sub_intent": "account_creation",
                    "patterns": ["申請.*帳號", "create.*account"],
                    "priority": 80,
                    "workflow_type": "sequential",
                    "risk_level": "medium",
                },
                {
                    "id": "query_status",
                    "category": "query",
                    "sub_intent": "status_check",
                    "patterns": ["狀態.*查詢", "status.*check"],
                    "priority": 60,
                    "workflow_type": "simple",
                    "risk_level": "low",
                },
            ]
        }

    @pytest.fixture
    def matcher(self, sample_rules):
        """Create a matcher with sample rules."""
        return PatternMatcher(rules_dict=sample_rules)

    def test_init_from_dict(self, matcher):
        """Should initialize from dictionary."""
        assert matcher.get_rules_count() == 3

    def test_match_incident_chinese(self, matcher):
        """Should match Chinese incident patterns."""
        result = matcher.match("ETL job 今天又失敗了")
        assert result.matched is True
        assert result.intent_category == ITIntentCategory.INCIDENT
        assert result.sub_intent == "etl_failure"
        assert result.confidence > 0.8

    def test_match_incident_english(self, matcher):
        """Should match English incident patterns."""
        result = matcher.match("The ETL pipeline failed this morning")
        assert result.matched is True
        assert result.intent_category == ITIntentCategory.INCIDENT

    def test_match_request(self, matcher):
        """Should match request patterns."""
        result = matcher.match("我想申請一個新帳號")
        assert result.matched is True
        assert result.intent_category == ITIntentCategory.REQUEST

    def test_match_query(self, matcher):
        """Should match query patterns."""
        # Sample rules pattern is "狀態.*查詢"
        result = matcher.match("系統狀態查詢")
        assert result.matched is True
        assert result.intent_category == ITIntentCategory.QUERY

    def test_no_match(self, matcher):
        """Should return no match for unmatched input."""
        result = matcher.match("今天天氣真好")
        assert result.matched is False
        assert result.confidence == 0.0

    def test_empty_input(self, matcher):
        """Should handle empty input."""
        result = matcher.match("")
        assert result.matched is False
        result = matcher.match("   ")
        assert result.matched is False

    def test_priority_ordering(self, sample_rules):
        """Higher priority rules should be checked first."""
        # Add overlapping rules
        rules = sample_rules.copy()
        rules["rules"].append({
            "id": "low_priority",
            "category": "query",
            "sub_intent": "general",
            "patterns": ["ETL"],  # Would also match ETL
            "priority": 10,
            "workflow_type": "simple",
            "risk_level": "low",
        })
        matcher = PatternMatcher(rules_dict=rules)
        result = matcher.match("ETL 失敗")
        # Higher priority incident rule should win
        assert result.rule_id == "incident_etl_failure"

    def test_match_all(self, matcher):
        """Should return multiple matches."""
        # Add a pattern that could match multiple rules
        matcher.add_rule(PatternRule(
            id="incident_general",
            category=ITIntentCategory.INCIDENT,
            sub_intent="general",
            patterns=["失敗"],
            priority=50,
            workflow_type=WorkflowType.SIMPLE,
            risk_level=RiskLevel.MEDIUM,
        ))
        results = matcher.match_all("ETL 失敗", max_results=5)
        assert len(results) >= 1

    def test_confidence_calculation(self, matcher):
        """Confidence should be calculated reasonably."""
        result = matcher.match("ETL失敗")
        assert 0.8 <= result.confidence <= 1.0

    def test_get_rules_by_category(self, matcher):
        """Should filter rules by category."""
        incident_rules = matcher.get_rules_by_category(ITIntentCategory.INCIDENT)
        assert len(incident_rules) == 1
        assert incident_rules[0].category == ITIntentCategory.INCIDENT

    def test_add_rule(self, matcher):
        """Should add rules dynamically."""
        initial_count = matcher.get_rules_count()
        matcher.add_rule(PatternRule(
            id="new_rule",
            category=ITIntentCategory.CHANGE,
            sub_intent="test",
            patterns=["test.*pattern"],
            priority=100,
            workflow_type=WorkflowType.SIMPLE,
            risk_level=RiskLevel.LOW,
        ))
        assert matcher.get_rules_count() == initial_count + 1

    def test_remove_rule(self, matcher):
        """Should remove rules by ID."""
        initial_count = matcher.get_rules_count()
        removed = matcher.remove_rule("incident_etl_failure")
        assert removed is True
        assert matcher.get_rules_count() == initial_count - 1

    def test_remove_nonexistent_rule(self, matcher):
        """Should handle removing nonexistent rules."""
        removed = matcher.remove_rule("nonexistent_rule")
        assert removed is False

    def test_get_statistics(self, matcher):
        """Should return valid statistics."""
        stats = matcher.get_statistics()
        assert stats["total_rules"] == 3
        assert stats["total_patterns"] > 0
        assert "category_distribution" in stats

    def test_disabled_rule_not_loaded(self):
        """Disabled rules should not be loaded."""
        rules = {
            "rules": [
                {
                    "id": "enabled_rule",
                    "category": "incident",
                    "sub_intent": "test",
                    "patterns": ["test"],
                    "enabled": True,
                },
                {
                    "id": "disabled_rule",
                    "category": "incident",
                    "sub_intent": "test",
                    "patterns": ["disabled"],
                    "enabled": False,
                },
            ]
        }
        matcher = PatternMatcher(rules_dict=rules)
        assert matcher.get_rules_count() == 1


class TestPatternMatcherPerformance:
    """Performance tests for Pattern Matcher."""

    @pytest.fixture
    def production_matcher(self):
        """Load production rules for performance testing."""
        rules_path = Path(__file__).parent.parent.parent.parent / (
            "src/integrations/orchestration/intent_router/"
            "pattern_matcher/rules.yaml"
        )
        if rules_path.exists():
            return PatternMatcher(rules_path=str(rules_path))
        # Fallback to sample rules
        return PatternMatcher(rules_dict={
            "rules": [
                {
                    "id": f"rule_{i}",
                    "category": "incident",
                    "sub_intent": "test",
                    "patterns": [f"pattern{i}.*test"],
                    "priority": 100 - i,
                }
                for i in range(30)
            ]
        })

    def test_match_latency_under_10ms(self, production_matcher):
        """Match operation should complete under 10ms average."""
        test_inputs = [
            "ETL job 失敗了",
            "系統當機無法連接",
            "申請新帳號",
            "查詢狀態",
            "random text that won't match",
        ]

        total_time = 0.0
        iterations = 1000

        for _ in range(iterations):
            for input_text in test_inputs:
                start = time.perf_counter()
                production_matcher.match(input_text)
                total_time += (time.perf_counter() - start) * 1000

        avg_time = total_time / (iterations * len(test_inputs))
        assert avg_time < 10.0, f"Average match time {avg_time:.2f}ms exceeds 10ms"

    def test_rules_count_minimum(self, production_matcher):
        """Should have at least 30 rules loaded."""
        assert production_matcher.get_rules_count() >= 30


class TestPatternMatcherRulesFile:
    """Tests for loading rules from YAML file."""

    @pytest.fixture
    def rules_path(self):
        """Path to production rules file."""
        return Path(__file__).parent.parent.parent.parent / (
            "src/integrations/orchestration/intent_router/"
            "pattern_matcher/rules.yaml"
        )

    def test_load_from_file(self, rules_path):
        """Should load rules from YAML file."""
        if not rules_path.exists():
            pytest.skip("Rules file not found")

        matcher = PatternMatcher(rules_path=str(rules_path))
        assert matcher.get_rules_count() >= 30

    def test_category_distribution(self, rules_path):
        """Rules should cover all categories."""
        if not rules_path.exists():
            pytest.skip("Rules file not found")

        matcher = PatternMatcher(rules_path=str(rules_path))
        stats = matcher.get_statistics()
        dist = stats["category_distribution"]

        # Each category should have rules
        assert dist.get("incident", 0) >= 6
        assert dist.get("request", 0) >= 6
        assert dist.get("change", 0) >= 6
        assert dist.get("query", 0) >= 6

    def test_chinese_pattern_matching(self, rules_path):
        """Chinese patterns should work correctly."""
        if not rules_path.exists():
            pytest.skip("Rules file not found")

        matcher = PatternMatcher(rules_path=str(rules_path))

        # Test various Chinese inputs
        test_cases = [
            ("ETL今天又失敗了", ITIntentCategory.INCIDENT),
            ("系統當機了怎麼辦", ITIntentCategory.INCIDENT),
            ("我想申請一個新帳號", ITIntentCategory.REQUEST),
            ("請幫我重設密碼", ITIntentCategory.REQUEST),
            ("系統升級申請", ITIntentCategory.CHANGE),
            ("查詢工單狀態", ITIntentCategory.QUERY),
        ]

        for input_text, expected_category in test_cases:
            result = matcher.match(input_text)
            assert result.matched, f"Should match: {input_text}"
            assert result.intent_category == expected_category, (
                f"Input '{input_text}' expected {expected_category}, "
                f"got {result.intent_category}"
            )
