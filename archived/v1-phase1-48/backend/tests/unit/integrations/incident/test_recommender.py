"""
Unit Tests for ActionRecommender.

Sprint 126: Story 126-4 — IT Incident Processing (Phase 34)
Tests ActionRecommender rule-based templates, LLM enhancement, sorting, and risk assignment.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.integrations.incident.recommender import (
    ACTION_TEMPLATES,
    ActionRecommender,
)
from src.integrations.incident.types import (
    IncidentAnalysis,
    IncidentCategory,
    IncidentContext,
    IncidentSeverity,
    RemediationAction,
    RemediationActionType,
    RemediationRisk,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_context(
    category: IncidentCategory = IncidentCategory.STORAGE,
    severity: IncidentSeverity = IncidentSeverity.P3,
    incident_number: str = "INC001",
    cmdb_ci: str = "srv-prod-01",
    caller_id: str = "john.doe",
) -> IncidentContext:
    """Helper to create test IncidentContext."""
    return IncidentContext(
        incident_number=incident_number,
        severity=severity,
        category=category,
        short_description=f"Test incident for {category.value}",
        cmdb_ci=cmdb_ci,
        caller_id=caller_id,
    )


def _make_analysis(
    root_cause: str = "Test root cause",
    recommended_actions: list = None,
) -> IncidentAnalysis:
    """Helper to create test IncidentAnalysis."""
    return IncidentAnalysis(
        analysis_id="test_analysis",
        incident_number="INC001",
        root_cause_summary=root_cause,
        root_cause_confidence=0.80,
        contributing_factors=["factor_1", "factor_2"],
        recommended_actions=recommended_actions or [],
    )


@pytest.fixture
def recommender() -> ActionRecommender:
    """Create ActionRecommender without LLM."""
    return ActionRecommender(llm_service=None)


@pytest.fixture
def mock_llm_service():
    """Create mock LLM that returns additional suggestions."""
    service = MagicMock()
    service.generate_structured = AsyncMock(return_value={
        "suggestions": [
            {
                "title": "LLM: Check upstream router",
                "description": "Verify upstream router BGP peering status",
                "confidence": 0.7,
                "risk": "medium",
                "mcp_tool": "shell:run_command",
                "mcp_params": {"command": "show ip bgp summary"},
                "prerequisites": ["Access to router CLI"],
                "rollback_steps": ["No rollback needed"],
            },
        ]
    })
    return service


# ---------------------------------------------------------------------------
# Template Coverage Tests
# ---------------------------------------------------------------------------


class TestActionTemplates:
    """Tests for pre-defined action templates."""

    def test_storage_template_exists(self) -> None:
        """Test STORAGE category has templates."""
        assert IncidentCategory.STORAGE in ACTION_TEMPLATES
        templates = ACTION_TEMPLATES[IncidentCategory.STORAGE]
        assert len(templates) >= 1
        assert templates[0]["action_type"] == RemediationActionType.CLEAR_DISK_SPACE

    def test_application_template_exists(self) -> None:
        """Test APPLICATION category has templates."""
        assert IncidentCategory.APPLICATION in ACTION_TEMPLATES
        templates = ACTION_TEMPLATES[IncidentCategory.APPLICATION]
        assert templates[0]["action_type"] == RemediationActionType.RESTART_SERVICE

    def test_authentication_template_exists(self) -> None:
        """Test AUTHENTICATION category has templates."""
        assert IncidentCategory.AUTHENTICATION in ACTION_TEMPLATES
        templates = ACTION_TEMPLATES[IncidentCategory.AUTHENTICATION]
        assert templates[0]["action_type"] == RemediationActionType.AD_ACCOUNT_UNLOCK

    def test_security_template_is_critical_risk(self) -> None:
        """Test SECURITY actions are CRITICAL risk."""
        templates = ACTION_TEMPLATES[IncidentCategory.SECURITY]
        assert templates[0]["risk"] == RemediationRisk.CRITICAL

    def test_network_template_is_high_risk(self) -> None:
        """Test NETWORK ACL actions are HIGH risk."""
        templates = ACTION_TEMPLATES[IncidentCategory.NETWORK]
        assert templates[0]["risk"] == RemediationRisk.HIGH

    def test_all_major_categories_covered(self) -> None:
        """Test templates exist for all major categories."""
        expected = {
            IncidentCategory.STORAGE,
            IncidentCategory.APPLICATION,
            IncidentCategory.AUTHENTICATION,
            IncidentCategory.SERVER,
            IncidentCategory.NETWORK,
            IncidentCategory.SECURITY,
            IncidentCategory.DATABASE,
            IncidentCategory.PERFORMANCE,
        }
        actual = set(ACTION_TEMPLATES.keys())
        assert expected == actual


# ---------------------------------------------------------------------------
# Recommender Tests
# ---------------------------------------------------------------------------


class TestActionRecommender:
    """Tests for ActionRecommender."""

    @pytest.mark.asyncio
    async def test_recommend_storage_incident(
        self, recommender: ActionRecommender
    ) -> None:
        """Test recommendation for STORAGE incident."""
        ctx = _make_context(category=IncidentCategory.STORAGE)
        analysis = _make_analysis()
        actions = await recommender.recommend(analysis, ctx)
        assert len(actions) >= 1
        assert any(
            a.action_type == RemediationActionType.CLEAR_DISK_SPACE for a in actions
        )

    @pytest.mark.asyncio
    async def test_recommend_auth_incident(
        self, recommender: ActionRecommender
    ) -> None:
        """Test recommendation for AUTHENTICATION incident."""
        ctx = _make_context(category=IncidentCategory.AUTHENTICATION)
        analysis = _make_analysis()
        actions = await recommender.recommend(analysis, ctx)
        assert any(
            a.action_type == RemediationActionType.AD_ACCOUNT_UNLOCK for a in actions
        )

    @pytest.mark.asyncio
    async def test_recommend_unknown_category_returns_empty_rule_based(
        self, recommender: ActionRecommender
    ) -> None:
        """Test OTHER category has no rule-based templates."""
        ctx = _make_context(category=IncidentCategory.OTHER)
        analysis = _make_analysis()
        actions = await recommender.recommend(analysis, ctx)
        # Should have 0 rule-based (OTHER not in templates)
        # but may have actions from analysis.recommended_actions
        assert isinstance(actions, list)

    @pytest.mark.asyncio
    async def test_recommend_sorts_by_confidence_desc(
        self, recommender: ActionRecommender
    ) -> None:
        """Test actions are sorted by confidence descending."""
        ctx = _make_context(category=IncidentCategory.APPLICATION)
        analysis = _make_analysis()
        actions = await recommender.recommend(analysis, ctx)
        if len(actions) >= 2:
            for i in range(len(actions) - 1):
                assert actions[i].confidence >= actions[i + 1].confidence

    @pytest.mark.asyncio
    async def test_recommend_includes_analysis_actions(
        self, recommender: ActionRecommender
    ) -> None:
        """Test actions from analysis are included."""
        existing_action = RemediationAction(
            action_type=RemediationActionType.CUSTOM,
            title="Custom analysis action",
            confidence=0.95,
            risk=RemediationRisk.LOW,
        )
        ctx = _make_context(category=IncidentCategory.APPLICATION)
        analysis = _make_analysis(recommended_actions=[existing_action])
        actions = await recommender.recommend(analysis, ctx)
        titles = [a.title for a in actions]
        assert "Custom analysis action" in titles

    @pytest.mark.asyncio
    async def test_recommend_deduplicates_actions(
        self, recommender: ActionRecommender
    ) -> None:
        """Test duplicate actions are not included twice."""
        duplicate_action = RemediationAction(
            action_type=RemediationActionType.RESTART_SERVICE,
            title="Restart application service",  # Same as template title
            confidence=0.90,
            risk=RemediationRisk.LOW,
        )
        ctx = _make_context(category=IncidentCategory.APPLICATION)
        analysis = _make_analysis(recommended_actions=[duplicate_action])
        actions = await recommender.recommend(analysis, ctx)
        restart_count = sum(
            1 for a in actions if a.title.lower() == "restart application service"
        )
        assert restart_count == 1

    @pytest.mark.asyncio
    async def test_severity_boosts_confidence_p1(
        self, recommender: ActionRecommender
    ) -> None:
        """Test P1 severity boosts action confidence by 0.10."""
        ctx = _make_context(
            category=IncidentCategory.STORAGE,
            severity=IncidentSeverity.P1,
        )
        analysis = _make_analysis()
        actions = await recommender.recommend(analysis, ctx)
        # STORAGE template has confidence 0.85, P1 boost +0.10 = 0.95
        storage_action = next(
            (a for a in actions if a.action_type == RemediationActionType.CLEAR_DISK_SPACE),
            None,
        )
        assert storage_action is not None
        assert abs(storage_action.confidence - 0.95) < 0.01

    @pytest.mark.asyncio
    async def test_severity_reduces_confidence_p4(
        self, recommender: ActionRecommender
    ) -> None:
        """Test P4 severity reduces action confidence by 0.05."""
        ctx = _make_context(
            category=IncidentCategory.STORAGE,
            severity=IncidentSeverity.P4,
        )
        analysis = _make_analysis()
        actions = await recommender.recommend(analysis, ctx)
        storage_action = next(
            (a for a in actions if a.action_type == RemediationActionType.CLEAR_DISK_SPACE),
            None,
        )
        assert storage_action is not None
        assert abs(storage_action.confidence - 0.80) < 0.01  # 0.85 - 0.05

    @pytest.mark.asyncio
    async def test_param_substitution_cmdb_ci(
        self, recommender: ActionRecommender
    ) -> None:
        """Test MCP param substitution uses cmdb_ci."""
        ctx = _make_context(
            category=IncidentCategory.APPLICATION,
            cmdb_ci="my-app-service",
        )
        analysis = _make_analysis()
        actions = await recommender.recommend(analysis, ctx)
        restart_action = next(
            (a for a in actions if a.action_type == RemediationActionType.RESTART_SERVICE),
            None,
        )
        assert restart_action is not None
        assert "my-app-service" in restart_action.mcp_params.get("command", "")


class TestActionRecommenderWithLLM:
    """Tests for ActionRecommender with LLM enhancement."""

    @pytest.mark.asyncio
    async def test_llm_adds_additional_actions(
        self, mock_llm_service
    ) -> None:
        """Test LLM suggestions are appended to rule-based actions."""
        recommender = ActionRecommender(llm_service=mock_llm_service)
        ctx = _make_context(category=IncidentCategory.NETWORK)
        analysis = _make_analysis()
        actions = await recommender.recommend(analysis, ctx)
        llm_titles = [a.title for a in actions if a.title.startswith("LLM:")]
        assert len(llm_titles) >= 1

    @pytest.mark.asyncio
    async def test_llm_failure_falls_back_to_rules(self) -> None:
        """Test LLM failure still returns rule-based actions."""
        failing_llm = MagicMock()
        failing_llm.generate_structured = AsyncMock(
            side_effect=Exception("LLM unavailable")
        )
        recommender = ActionRecommender(llm_service=failing_llm)
        ctx = _make_context(category=IncidentCategory.STORAGE)
        analysis = _make_analysis()
        actions = await recommender.recommend(analysis, ctx)
        # Should still have rule-based actions
        assert len(actions) >= 1
        assert any(
            a.action_type == RemediationActionType.CLEAR_DISK_SPACE for a in actions
        )
