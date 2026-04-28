"""
Unit Tests for AD Account Management Pattern Rules

Sprint 114: AD 場景基礎建設 (Phase 32)
Tests pattern matching rules for AD account management operations.
"""

import os
from pathlib import Path

import pytest

from src.integrations.orchestration.intent_router.pattern_matcher.matcher import (
    PatternMatcher,
)
from src.integrations.orchestration.intent_router.models import (
    ITIntentCategory,
    RiskLevel,
    WorkflowType,
)


@pytest.fixture
def matcher() -> PatternMatcher:
    """Create a PatternMatcher loaded with production rules.yaml."""
    rules_path = str(
        Path(__file__).resolve().parents[5]
        / "src"
        / "integrations"
        / "orchestration"
        / "intent_router"
        / "pattern_matcher"
        / "rules.yaml"
    )
    return PatternMatcher(rules_path=rules_path)


class TestADAccountUnlock:
    """Tests for AD account unlock pattern matching."""

    def test_unlock_english(self, matcher: PatternMatcher) -> None:
        """Test English unlock patterns."""
        result = matcher.match("Please unlock account for john.doe")
        assert result.matched
        assert result.rule_id == "ad_account_unlock"
        assert result.sub_intent == "ad_account_unlock"
        assert result.intent_category == ITIntentCategory.REQUEST
        assert result.risk_level == RiskLevel.MEDIUM

    def test_unlock_english_locked_out(self, matcher: PatternMatcher) -> None:
        """Test English locked out pattern."""
        result = matcher.match("account locked out for user jane.smith")
        assert result.matched
        assert result.rule_id == "ad_account_unlock"

    def test_unlock_chinese(self, matcher: PatternMatcher) -> None:
        """Test Chinese unlock patterns."""
        result = matcher.match("請幫我帳號解鎖")
        assert result.matched
        assert result.rule_id == "ad_account_unlock"

    def test_unlock_chinese_ad_prefix(self, matcher: PatternMatcher) -> None:
        """Test Chinese AD prefix unlock pattern."""
        result = matcher.match("AD 帳號被鎖定了")
        assert result.matched
        assert result.rule_id == "ad_account_unlock"


class TestADPasswordReset:
    """Tests for AD password reset pattern matching."""

    def test_reset_english(self, matcher: PatternMatcher) -> None:
        """Test English reset patterns."""
        result = matcher.match("reset AD password for user john.doe")
        assert result.matched
        assert result.rule_id == "ad_password_reset"
        assert result.sub_intent == "ad_password_reset"
        assert result.risk_level == RiskLevel.MEDIUM

    def test_reset_english_expired(self, matcher: PatternMatcher) -> None:
        """Test English password expired pattern."""
        result = matcher.match("AD password expired for user jane")
        assert result.matched
        assert result.rule_id == "ad_password_reset"

    def test_reset_chinese(self, matcher: PatternMatcher) -> None:
        """Test Chinese reset patterns."""
        result = matcher.match("AD 密碼重設申請")
        assert result.matched
        assert result.rule_id == "ad_password_reset"

    def test_reset_chinese_variant(self, matcher: PatternMatcher) -> None:
        """Test Chinese reset variant (重置)."""
        result = matcher.match("AD 密碼重置")
        assert result.matched
        assert result.rule_id == "ad_password_reset"


class TestADGroupMembership:
    """Tests for AD group membership change pattern matching."""

    def test_add_to_group_english(self, matcher: PatternMatcher) -> None:
        """Test English add to group pattern."""
        result = matcher.match("add john.doe to group IT-Admins")
        assert result.matched
        assert result.rule_id == "ad_group_membership"
        assert result.sub_intent == "ad_group_modify"
        assert result.risk_level == RiskLevel.HIGH

    def test_remove_from_group_english(self, matcher: PatternMatcher) -> None:
        """Test English remove from group pattern."""
        result = matcher.match("remove user from group Finance-Team")
        assert result.matched
        assert result.rule_id == "ad_group_membership"

    def test_group_chinese(self, matcher: PatternMatcher) -> None:
        """Test Chinese group change patterns."""
        result = matcher.match("群組異動申請")
        assert result.matched
        assert result.rule_id == "ad_group_membership"

    def test_group_chinese_add_member(self, matcher: PatternMatcher) -> None:
        """Test Chinese add member pattern."""
        result = matcher.match("AD 群組新增成員 john")
        assert result.matched
        assert result.rule_id == "ad_group_membership"

    def test_group_chinese_remove_member(self, matcher: PatternMatcher) -> None:
        """Test Chinese remove member pattern."""
        result = matcher.match("群組移除成員 jane.smith")
        assert result.matched
        assert result.rule_id == "ad_group_membership"


class TestADAccountCreate:
    """Tests for AD account creation pattern matching."""

    def test_create_english(self, matcher: PatternMatcher) -> None:
        """Test English create patterns."""
        result = matcher.match("create AD account for new employee")
        assert result.matched
        assert result.rule_id == "ad_account_create"
        assert result.sub_intent == "ad_account_create"
        assert result.risk_level == RiskLevel.HIGH

    def test_create_english_new(self, matcher: PatternMatcher) -> None:
        """Test English new AD account pattern."""
        result = matcher.match("need a new AD account for contractor")
        assert result.matched
        assert result.rule_id == "ad_account_create"

    def test_create_chinese(self, matcher: PatternMatcher) -> None:
        """Test Chinese create patterns."""
        result = matcher.match("新建 AD 帳號給新進員工")
        assert result.matched
        assert result.rule_id == "ad_account_create"

    def test_create_chinese_variant(self, matcher: PatternMatcher) -> None:
        """Test Chinese create variant (建立)."""
        result = matcher.match("建立 AD 帳號")
        assert result.matched
        assert result.rule_id == "ad_account_create"


class TestADAccountDisable:
    """Tests for AD account disable pattern matching."""

    def test_disable_english(self, matcher: PatternMatcher) -> None:
        """Test English disable patterns."""
        result = matcher.match("disable AD account for terminated employee")
        assert result.matched
        assert result.rule_id == "ad_account_disable"
        assert result.sub_intent == "ad_account_disable"
        assert result.risk_level == RiskLevel.HIGH

    def test_deactivate_english(self, matcher: PatternMatcher) -> None:
        """Test English deactivate pattern."""
        result = matcher.match("deactivate AD user john.doe")
        assert result.matched
        assert result.rule_id == "ad_account_disable"

    def test_disable_chinese(self, matcher: PatternMatcher) -> None:
        """Test Chinese disable patterns."""
        result = matcher.match("停用 AD 帳號 john.doe")
        assert result.matched
        assert result.rule_id == "ad_account_disable"

    def test_disable_chinese_close(self, matcher: PatternMatcher) -> None:
        """Test Chinese close account pattern."""
        result = matcher.match("關閉 AD 帳號")
        assert result.matched
        assert result.rule_id == "ad_account_disable"


class TestADRulesNoFalsePositive:
    """Tests to ensure AD rules don't create false positives."""

    def test_general_password_reset_not_ad(self, matcher: PatternMatcher) -> None:
        """General password reset should NOT match AD-specific rules."""
        result = matcher.match("重設密碼")
        assert result.matched
        # Should match existing request_password_reset, NOT ad_password_reset
        assert result.rule_id == "request_password_reset"

    def test_general_account_creation_not_ad(self, matcher: PatternMatcher) -> None:
        """General account creation should NOT match AD-specific rules."""
        result = matcher.match("申請帳號")
        assert result.matched
        # Should match existing request_account_creation, NOT ad_account_create
        assert result.rule_id == "request_account_creation"

    def test_unrelated_input(self, matcher: PatternMatcher) -> None:
        """Completely unrelated input should not match AD rules."""
        result = matcher.match("今天天氣如何")
        # May or may not match other rules, but should not match AD rules
        if result.matched:
            assert not result.rule_id.startswith("ad_")


class TestADRulesMetadata:
    """Tests for AD rule metadata fields."""

    def test_all_ad_rules_have_sequential_workflow(
        self, matcher: PatternMatcher
    ) -> None:
        """All AD rules should use sequential workflow type."""
        ad_rules = [r for r in matcher.rules if r.id.startswith("ad_")]
        assert len(ad_rules) == 5, f"Expected 5 AD rules, found {len(ad_rules)}"
        for rule in ad_rules:
            assert rule.workflow_type == WorkflowType.SEQUENTIAL, (
                f"Rule {rule.id} should be SEQUENTIAL, got {rule.workflow_type}"
            )

    def test_all_ad_rules_in_request_category(
        self, matcher: PatternMatcher
    ) -> None:
        """All AD rules should be in REQUEST category."""
        ad_rules = [r for r in matcher.rules if r.id.startswith("ad_")]
        for rule in ad_rules:
            assert rule.category == ITIntentCategory.REQUEST, (
                f"Rule {rule.id} should be REQUEST, got {rule.category}"
            )

    def test_existing_rules_count_preserved(self, matcher: PatternMatcher) -> None:
        """Verify existing rules are not affected (was 34, now 34+5=39)."""
        non_ad_rules = [r for r in matcher.rules if not r.id.startswith("ad_")]
        assert len(non_ad_rules) >= 34, (
            f"Expected at least 34 non-AD rules, found {len(non_ad_rules)}"
        )

    def test_total_rules_count(self, matcher: PatternMatcher) -> None:
        """Verify total rules count (34 existing + 5 AD = 39)."""
        assert len(matcher.rules) >= 39, (
            f"Expected at least 39 total rules, found {len(matcher.rules)}"
        )


class TestExistingRulesRegression:
    """Regression tests to ensure existing rules are not broken by AD additions."""

    def test_incident_etl_failure(self, matcher: PatternMatcher) -> None:
        """Existing ETL failure rule should still work."""
        result = matcher.match("ETL Pipeline failed last night")
        assert result.matched
        assert result.rule_id == "incident_etl_failure"

    def test_incident_system_down(self, matcher: PatternMatcher) -> None:
        """Existing system down rule should still work."""
        result = matcher.match("系統當機了")
        assert result.matched
        assert result.rule_id == "incident_system_down"

    def test_request_vpn_setup(self, matcher: PatternMatcher) -> None:
        """Existing VPN setup rule should still work."""
        result = matcher.match("申請 VPN 連線")
        assert result.matched
        assert result.rule_id == "request_vpn_setup"

    def test_change_deployment(self, matcher: PatternMatcher) -> None:
        """Existing deployment rule should still work."""
        result = matcher.match("部署請求 v2.0")
        assert result.matched
        assert result.rule_id == "change_deployment"

    def test_query_ticket_status(self, matcher: PatternMatcher) -> None:
        """Existing ticket status rule should still work."""
        result = matcher.match("我的工單案件進度如何")
        assert result.matched
        assert result.rule_id == "query_ticket_status"
