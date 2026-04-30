"""
Unit Tests for BusinessIntentRouter

Tests for:
- RouterConfig defaults and from_env()
- RoutingMetrics tracking and calculations
- BusinessIntentRouter three-layer cascade (Pattern -> Semantic -> LLM)
- Workflow type mapping
- Risk level assessment
- create_router() factory function

Sprint 123: Story 123-1 - Orchestration Module Tests (Phase 33)
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.orchestration.intent_router.models import (
    CompletenessInfo,
    ITIntentCategory,
    LLMClassificationResult,
    PatternMatchResult,
    RiskLevel,
    RoutingDecision,
    SemanticRouteResult,
    WorkflowType,
)
from src.integrations.orchestration.intent_router.router import (
    BusinessIntentRouter,
    RouterConfig,
    RoutingMetrics,
    create_router,
)


# =============================================================================
# RouterConfig Tests
# =============================================================================


class TestRouterConfig:
    """Tests for RouterConfig dataclass."""

    def test_default_values(self):
        """Default configuration should use standard thresholds."""
        config = RouterConfig()

        assert config.pattern_threshold == 0.90
        assert config.semantic_threshold == 0.70
        assert config.enable_llm_fallback is True
        assert config.enable_completeness is True
        assert config.track_latency is True

    def test_custom_values(self):
        """Should accept custom configuration values."""
        config = RouterConfig(
            pattern_threshold=0.80,
            semantic_threshold=0.70,
            enable_llm_fallback=False,
            enable_completeness=False,
            track_latency=False,
        )

        assert config.pattern_threshold == 0.80
        assert config.semantic_threshold == 0.70
        assert config.enable_llm_fallback is False
        assert config.enable_completeness is False
        assert config.track_latency is False

    def test_from_env_with_defaults(self):
        """from_env() should use defaults when env vars are not set."""
        with patch.dict(os.environ, {}, clear=True):
            config = RouterConfig.from_env()

        assert config.pattern_threshold == 0.90
        assert config.semantic_threshold == 0.70
        assert config.enable_llm_fallback is True
        assert config.enable_completeness is True
        assert config.track_latency is True

    def test_from_env_with_custom_values(self):
        """from_env() should read custom values from environment."""
        env_vars = {
            "PATTERN_CONFIDENCE_THRESHOLD": "0.75",
            "SEMANTIC_SIMILARITY_THRESHOLD": "0.60",
            "ENABLE_LLM_FALLBACK": "false",
            "ENABLE_COMPLETENESS": "false",
            "TRACK_LATENCY": "false",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = RouterConfig.from_env()

        assert config.pattern_threshold == 0.75
        assert config.semantic_threshold == 0.60
        assert config.enable_llm_fallback is False
        assert config.enable_completeness is False
        assert config.track_latency is False

    def test_from_env_llm_fallback_case_insensitive(self):
        """from_env() should handle case-insensitive boolean parsing."""
        with patch.dict(os.environ, {"ENABLE_LLM_FALLBACK": "True"}, clear=True):
            config = RouterConfig.from_env()
        assert config.enable_llm_fallback is True

        with patch.dict(os.environ, {"ENABLE_LLM_FALLBACK": "FALSE"}, clear=True):
            config = RouterConfig.from_env()
        assert config.enable_llm_fallback is False


# =============================================================================
# RoutingMetrics Tests
# =============================================================================


class TestRoutingMetrics:
    """Tests for RoutingMetrics dataclass."""

    def test_initial_state(self):
        """Initial metrics should be all zeros."""
        metrics = RoutingMetrics()

        assert metrics.total_requests == 0
        assert metrics.pattern_matches == 0
        assert metrics.semantic_matches == 0
        assert metrics.llm_fallbacks == 0
        assert metrics.latencies == []

    def test_avg_latency_ms_empty(self):
        """Average latency should be 0.0 when no measurements recorded."""
        metrics = RoutingMetrics()
        assert metrics.avg_latency_ms == 0.0

    def test_avg_latency_ms_with_data(self):
        """Average latency should be correctly calculated."""
        metrics = RoutingMetrics()
        metrics.latencies = [10.0, 20.0, 30.0]

        assert metrics.avg_latency_ms == 20.0

    def test_avg_latency_ms_single_value(self):
        """Average latency for a single measurement should equal that value."""
        metrics = RoutingMetrics()
        metrics.latencies = [42.5]

        assert metrics.avg_latency_ms == 42.5

    def test_p95_latency_ms_empty(self):
        """P95 latency should be 0.0 when no measurements recorded."""
        metrics = RoutingMetrics()
        assert metrics.p95_latency_ms == 0.0

    def test_p95_latency_ms_with_data(self):
        """P95 latency should return the 95th percentile value."""
        metrics = RoutingMetrics()
        # 20 values: 1 to 20
        metrics.latencies = list(range(1, 21))
        # idx = int(20 * 0.95) = 19, sorted[19] = 20
        assert metrics.p95_latency_ms == 20.0

    def test_p95_latency_ms_single_value(self):
        """P95 latency for a single measurement should equal that value."""
        metrics = RoutingMetrics()
        metrics.latencies = [50.0]
        # idx = int(1 * 0.95) = 0, sorted[0] = 50.0
        assert metrics.p95_latency_ms == 50.0

    def test_record_latency(self):
        """record_latency() should append to latencies list."""
        metrics = RoutingMetrics()
        metrics.record_latency(10.5)
        metrics.record_latency(20.3)

        assert len(metrics.latencies) == 2
        assert metrics.latencies[0] == 10.5
        assert metrics.latencies[1] == 20.3

    def test_record_latency_caps_at_1000(self):
        """record_latency() should keep only last 1000 measurements."""
        metrics = RoutingMetrics()

        # Record 1050 measurements
        for i in range(1050):
            metrics.record_latency(float(i))

        assert len(metrics.latencies) == 1000
        # Should keep the last 1000 (indices 50-1049)
        assert metrics.latencies[0] == 50.0
        assert metrics.latencies[-1] == 1049.0

    def test_to_dict(self):
        """to_dict() should return properly formatted dictionary."""
        metrics = RoutingMetrics()
        metrics.total_requests = 100
        metrics.pattern_matches = 60
        metrics.semantic_matches = 25
        metrics.llm_fallbacks = 10
        metrics.latencies = [10.0, 20.0, 30.0]

        result = metrics.to_dict()

        assert result["total_requests"] == 100
        assert result["pattern_matches"] == 60
        assert result["semantic_matches"] == 25
        assert result["llm_fallbacks"] == 10
        assert result["avg_latency_ms"] == 20.0
        assert isinstance(result["p95_latency_ms"], float)

    def test_to_dict_rounds_values(self):
        """to_dict() should round latency values to 2 decimal places."""
        metrics = RoutingMetrics()
        metrics.latencies = [10.123456, 20.789012, 30.456789]

        result = metrics.to_dict()

        assert result["avg_latency_ms"] == round(metrics.avg_latency_ms, 2)
        assert result["p95_latency_ms"] == round(metrics.p95_latency_ms, 2)


# =============================================================================
# BusinessIntentRouter Test Fixtures
# =============================================================================


@pytest.fixture
def mock_pattern_matcher():
    """Create a mock PatternMatcher."""
    matcher = MagicMock()
    matcher.match.return_value = PatternMatchResult.no_match()
    return matcher


@pytest.fixture
def mock_semantic_router():
    """Create a mock SemanticRouter."""
    router = MagicMock()
    router.route = AsyncMock(return_value=SemanticRouteResult.no_match())
    return router


@pytest.fixture
def mock_llm_classifier():
    """Create a mock LLMClassifier."""
    classifier = MagicMock()
    classifier.classify = AsyncMock(
        return_value=LLMClassificationResult(
            intent_category=ITIntentCategory.UNKNOWN,
            confidence=0.5,
            reasoning="LLM fallback",
        )
    )
    return classifier


@pytest.fixture
def mock_completeness_checker():
    """Create a mock CompletenessChecker."""
    checker = MagicMock()
    checker.check.return_value = CompletenessInfo(
        is_complete=False,
        completeness_score=0.5,
        missing_fields=["affected_system"],
    )
    return checker


@pytest.fixture
def router_config():
    """Create a default RouterConfig for testing."""
    return RouterConfig()


@pytest.fixture
def router(
    mock_pattern_matcher,
    mock_semantic_router,
    mock_llm_classifier,
    mock_completeness_checker,
    router_config,
):
    """Create a BusinessIntentRouter with all mocked dependencies."""
    return BusinessIntentRouter(
        pattern_matcher=mock_pattern_matcher,
        semantic_router=mock_semantic_router,
        llm_classifier=mock_llm_classifier,
        completeness_checker=mock_completeness_checker,
        config=router_config,
    )


# =============================================================================
# BusinessIntentRouter Tests
# =============================================================================


class TestBusinessIntentRouter:
    """Tests for BusinessIntentRouter three-layer cascade."""

    @pytest.mark.asyncio
    async def test_empty_input_returns_unknown(self, router):
        """Empty string input should return UNKNOWN intent."""
        decision = await router.route("")

        assert decision.intent_category == ITIntentCategory.UNKNOWN
        assert decision.confidence == 0.0
        assert decision.routing_layer == "none"
        assert decision.reasoning == "Empty or invalid input"

    @pytest.mark.asyncio
    async def test_whitespace_input_returns_unknown(self, router):
        """Whitespace-only input should return UNKNOWN intent."""
        decision = await router.route("   \t\n  ")

        assert decision.intent_category == ITIntentCategory.UNKNOWN
        assert decision.confidence == 0.0
        assert decision.routing_layer == "none"

    @pytest.mark.asyncio
    async def test_pattern_match_priority(
        self,
        mock_pattern_matcher,
        mock_semantic_router,
        mock_llm_classifier,
        mock_completeness_checker,
    ):
        """When pattern matches with high confidence, use pattern layer result."""
        mock_pattern_matcher.match.return_value = PatternMatchResult(
            matched=True,
            intent_category=ITIntentCategory.INCIDENT,
            sub_intent="etl_failure",
            confidence=0.95,
            rule_id="incident_etl_001",
            workflow_type=WorkflowType.MAGENTIC,
            risk_level=RiskLevel.HIGH,
            matched_pattern="ETL.*失敗",
        )

        router = BusinessIntentRouter(
            pattern_matcher=mock_pattern_matcher,
            semantic_router=mock_semantic_router,
            llm_classifier=mock_llm_classifier,
            completeness_checker=mock_completeness_checker,
        )

        decision = await router.route("ETL Pipeline 今天失敗了")

        assert decision.intent_category == ITIntentCategory.INCIDENT
        assert decision.routing_layer == "pattern"
        assert decision.confidence == 0.95
        assert decision.sub_intent == "etl_failure"
        assert decision.rule_id == "incident_etl_001"
        # Semantic and LLM should NOT be called
        mock_semantic_router.route.assert_not_awaited()
        mock_llm_classifier.classify.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_semantic_fallback_when_pattern_fails(
        self,
        mock_pattern_matcher,
        mock_semantic_router,
        mock_llm_classifier,
        mock_completeness_checker,
    ):
        """When pattern doesn't match, should fall through to semantic layer."""
        mock_pattern_matcher.match.return_value = PatternMatchResult.no_match()
        mock_semantic_router.route = AsyncMock(
            return_value=SemanticRouteResult(
                matched=True,
                intent_category=ITIntentCategory.CHANGE,
                sub_intent="release_deployment",
                similarity=0.92,
                route_name="change_release",
                metadata={
                    "workflow_type": "magentic",
                    "risk_level": "high",
                },
            )
        )

        router = BusinessIntentRouter(
            pattern_matcher=mock_pattern_matcher,
            semantic_router=mock_semantic_router,
            llm_classifier=mock_llm_classifier,
            completeness_checker=mock_completeness_checker,
        )

        decision = await router.route("Deploy new release to production")

        assert decision.intent_category == ITIntentCategory.CHANGE
        assert decision.routing_layer == "semantic"
        assert decision.confidence == 0.92
        # LLM should NOT be called
        mock_llm_classifier.classify.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_llm_fallback_when_semantic_fails(
        self,
        mock_pattern_matcher,
        mock_semantic_router,
        mock_llm_classifier,
        mock_completeness_checker,
    ):
        """When both pattern and semantic fail, should use LLM classifier."""
        mock_pattern_matcher.match.return_value = PatternMatchResult.no_match()
        mock_semantic_router.route = AsyncMock(
            return_value=SemanticRouteResult.no_match(similarity=0.3)
        )
        mock_llm_classifier.classify = AsyncMock(
            return_value=LLMClassificationResult(
                intent_category=ITIntentCategory.QUERY,
                sub_intent="status_check",
                confidence=0.88,
                reasoning="User is asking about system status",
                model="claude-haiku",
            )
        )

        router = BusinessIntentRouter(
            pattern_matcher=mock_pattern_matcher,
            semantic_router=mock_semantic_router,
            llm_classifier=mock_llm_classifier,
            completeness_checker=mock_completeness_checker,
        )

        decision = await router.route("What is the current status?")

        assert decision.intent_category == ITIntentCategory.QUERY
        assert decision.routing_layer == "llm"
        assert decision.confidence == 0.88

    @pytest.mark.asyncio
    async def test_unknown_when_all_fail_and_llm_disabled(
        self,
        mock_pattern_matcher,
        mock_semantic_router,
        mock_llm_classifier,
        mock_completeness_checker,
    ):
        """When all layers fail and LLM is disabled, should return UNKNOWN."""
        mock_pattern_matcher.match.return_value = PatternMatchResult.no_match()
        mock_semantic_router.route = AsyncMock(
            return_value=SemanticRouteResult.no_match()
        )

        config = RouterConfig(enable_llm_fallback=False)
        router = BusinessIntentRouter(
            pattern_matcher=mock_pattern_matcher,
            semantic_router=mock_semantic_router,
            llm_classifier=mock_llm_classifier,
            completeness_checker=mock_completeness_checker,
            config=config,
        )

        decision = await router.route("Some ambiguous input")

        assert decision.intent_category == ITIntentCategory.UNKNOWN
        assert decision.confidence == 0.0
        assert decision.routing_layer == "none"
        assert decision.workflow_type == WorkflowType.HANDOFF
        # LLM should NOT be called
        mock_llm_classifier.classify.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_pattern_below_threshold_falls_through(
        self,
        mock_pattern_matcher,
        mock_semantic_router,
        mock_llm_classifier,
        mock_completeness_checker,
    ):
        """Pattern match below threshold should fall through to semantic."""
        mock_pattern_matcher.match.return_value = PatternMatchResult(
            matched=True,
            intent_category=ITIntentCategory.INCIDENT,
            sub_intent="general",
            confidence=0.70,  # Below default threshold of 0.90
            rule_id="incident_general",
        )
        mock_semantic_router.route = AsyncMock(
            return_value=SemanticRouteResult(
                matched=True,
                intent_category=ITIntentCategory.INCIDENT,
                sub_intent="etl_failure",
                similarity=0.90,
                route_name="incident_etl",
            )
        )

        router = BusinessIntentRouter(
            pattern_matcher=mock_pattern_matcher,
            semantic_router=mock_semantic_router,
            llm_classifier=mock_llm_classifier,
            completeness_checker=mock_completeness_checker,
        )

        decision = await router.route("Something about ETL")

        assert decision.routing_layer == "semantic"
        assert decision.confidence == 0.90

    @pytest.mark.asyncio
    async def test_semantic_below_threshold_falls_through(
        self,
        mock_pattern_matcher,
        mock_semantic_router,
        mock_llm_classifier,
        mock_completeness_checker,
    ):
        """Semantic match below threshold should fall through to LLM."""
        mock_pattern_matcher.match.return_value = PatternMatchResult.no_match()
        mock_semantic_router.route = AsyncMock(
            return_value=SemanticRouteResult(
                matched=True,
                intent_category=ITIntentCategory.REQUEST,
                sub_intent="account_creation",
                similarity=0.60,  # Below default threshold of 0.85
                route_name="request_account",
            )
        )
        mock_llm_classifier.classify = AsyncMock(
            return_value=LLMClassificationResult(
                intent_category=ITIntentCategory.REQUEST,
                sub_intent="account_creation",
                confidence=0.90,
                reasoning="LLM classified as account request",
            )
        )

        router = BusinessIntentRouter(
            pattern_matcher=mock_pattern_matcher,
            semantic_router=mock_semantic_router,
            llm_classifier=mock_llm_classifier,
            completeness_checker=mock_completeness_checker,
        )

        decision = await router.route("I need something about accounts")

        assert decision.routing_layer == "llm"

    @pytest.mark.asyncio
    async def test_metrics_track_pattern_matches(
        self,
        mock_pattern_matcher,
        mock_semantic_router,
        mock_llm_classifier,
        mock_completeness_checker,
    ):
        """Metrics should track pattern match count."""
        mock_pattern_matcher.match.return_value = PatternMatchResult(
            matched=True,
            intent_category=ITIntentCategory.INCIDENT,
            sub_intent="etl_failure",
            confidence=0.95,
            rule_id="test_rule",
            matched_pattern="ETL.*失敗",
        )

        router = BusinessIntentRouter(
            pattern_matcher=mock_pattern_matcher,
            semantic_router=mock_semantic_router,
            llm_classifier=mock_llm_classifier,
            completeness_checker=mock_completeness_checker,
        )

        await router.route("ETL 失敗了")
        await router.route("ETL 又失敗了")

        metrics = router.get_metrics()
        assert metrics["total_requests"] == 2
        assert metrics["pattern_matches"] == 2

    @pytest.mark.asyncio
    async def test_metrics_track_semantic_matches(
        self,
        mock_pattern_matcher,
        mock_semantic_router,
        mock_llm_classifier,
        mock_completeness_checker,
    ):
        """Metrics should track semantic match count."""
        mock_pattern_matcher.match.return_value = PatternMatchResult.no_match()
        mock_semantic_router.route = AsyncMock(
            return_value=SemanticRouteResult(
                matched=True,
                intent_category=ITIntentCategory.QUERY,
                similarity=0.90,
                route_name="query_status",
            )
        )

        router = BusinessIntentRouter(
            pattern_matcher=mock_pattern_matcher,
            semantic_router=mock_semantic_router,
            llm_classifier=mock_llm_classifier,
            completeness_checker=mock_completeness_checker,
        )

        await router.route("Check system status")

        metrics = router.get_metrics()
        assert metrics["total_requests"] == 1
        assert metrics["semantic_matches"] == 1

    @pytest.mark.asyncio
    async def test_metrics_track_llm_fallbacks(
        self,
        mock_pattern_matcher,
        mock_semantic_router,
        mock_llm_classifier,
        mock_completeness_checker,
    ):
        """Metrics should track LLM fallback count."""
        mock_pattern_matcher.match.return_value = PatternMatchResult.no_match()
        mock_semantic_router.route = AsyncMock(
            return_value=SemanticRouteResult.no_match()
        )
        mock_llm_classifier.classify = AsyncMock(
            return_value=LLMClassificationResult(
                intent_category=ITIntentCategory.QUERY,
                confidence=0.80,
                reasoning="Classified by LLM",
            )
        )

        router = BusinessIntentRouter(
            pattern_matcher=mock_pattern_matcher,
            semantic_router=mock_semantic_router,
            llm_classifier=mock_llm_classifier,
            completeness_checker=mock_completeness_checker,
        )

        await router.route("Some ambiguous query")

        metrics = router.get_metrics()
        assert metrics["total_requests"] == 1
        assert metrics["llm_fallbacks"] == 1

    @pytest.mark.asyncio
    async def test_reset_metrics(
        self,
        mock_pattern_matcher,
        mock_semantic_router,
        mock_llm_classifier,
        mock_completeness_checker,
    ):
        """reset_metrics() should clear all counters."""
        mock_pattern_matcher.match.return_value = PatternMatchResult(
            matched=True,
            intent_category=ITIntentCategory.INCIDENT,
            confidence=0.95,
            rule_id="test",
            matched_pattern="test",
        )

        router = BusinessIntentRouter(
            pattern_matcher=mock_pattern_matcher,
            semantic_router=mock_semantic_router,
            llm_classifier=mock_llm_classifier,
            completeness_checker=mock_completeness_checker,
        )

        await router.route("test input")
        assert router.get_metrics()["total_requests"] == 1

        router.reset_metrics()

        metrics = router.get_metrics()
        assert metrics["total_requests"] == 0
        assert metrics["pattern_matches"] == 0
        assert metrics["semantic_matches"] == 0
        assert metrics["llm_fallbacks"] == 0
        assert metrics["avg_latency_ms"] == 0.0


# =============================================================================
# _get_workflow_type Tests
# =============================================================================


class TestGetWorkflowType:
    """Tests for BusinessIntentRouter._get_workflow_type mapping."""

    @pytest.fixture
    def router_instance(
        self,
        mock_pattern_matcher,
        mock_semantic_router,
        mock_llm_classifier,
    ):
        """Create a router instance for testing internal methods."""
        return BusinessIntentRouter(
            pattern_matcher=mock_pattern_matcher,
            semantic_router=mock_semantic_router,
            llm_classifier=mock_llm_classifier,
        )

    def test_incident_system_unavailable_returns_magentic(self, router_instance):
        """INCIDENT + system_unavailable should map to MAGENTIC."""
        result = router_instance._get_workflow_type(
            ITIntentCategory.INCIDENT, "system_unavailable"
        )
        assert result == WorkflowType.MAGENTIC

    def test_incident_system_down_returns_magentic(self, router_instance):
        """INCIDENT + system_down should map to MAGENTIC."""
        result = router_instance._get_workflow_type(
            ITIntentCategory.INCIDENT, "system_down"
        )
        assert result == WorkflowType.MAGENTIC

    def test_incident_etl_returns_sequential(self, router_instance):
        """INCIDENT + etl_failure should map to SEQUENTIAL."""
        result = router_instance._get_workflow_type(
            ITIntentCategory.INCIDENT, "etl_failure"
        )
        assert result == WorkflowType.SEQUENTIAL

    def test_incident_general_returns_sequential(self, router_instance):
        """INCIDENT + general sub_intent should map to SEQUENTIAL."""
        result = router_instance._get_workflow_type(
            ITIntentCategory.INCIDENT, "general"
        )
        assert result == WorkflowType.SEQUENTIAL

    def test_change_release_returns_magentic(self, router_instance):
        """CHANGE + release_deployment should map to MAGENTIC."""
        result = router_instance._get_workflow_type(
            ITIntentCategory.CHANGE, "release_deployment"
        )
        assert result == WorkflowType.MAGENTIC

    def test_change_database_change_returns_magentic(self, router_instance):
        """CHANGE + database_change should map to MAGENTIC."""
        result = router_instance._get_workflow_type(
            ITIntentCategory.CHANGE, "database_change"
        )
        assert result == WorkflowType.MAGENTIC

    def test_change_configuration_returns_sequential(self, router_instance):
        """CHANGE + configuration_update should map to SEQUENTIAL."""
        result = router_instance._get_workflow_type(
            ITIntentCategory.CHANGE, "configuration_update"
        )
        assert result == WorkflowType.SEQUENTIAL

    def test_request_returns_simple(self, router_instance):
        """REQUEST category should map to SIMPLE."""
        result = router_instance._get_workflow_type(ITIntentCategory.REQUEST)
        assert result == WorkflowType.SIMPLE

    def test_query_returns_simple(self, router_instance):
        """QUERY category should map to SIMPLE."""
        result = router_instance._get_workflow_type(ITIntentCategory.QUERY)
        assert result == WorkflowType.SIMPLE

    def test_unknown_returns_handoff(self, router_instance):
        """UNKNOWN category should map to HANDOFF."""
        result = router_instance._get_workflow_type(ITIntentCategory.UNKNOWN)
        assert result == WorkflowType.HANDOFF

    def test_none_returns_handoff(self, router_instance):
        """None category should map to HANDOFF."""
        result = router_instance._get_workflow_type(None)
        assert result == WorkflowType.HANDOFF


# =============================================================================
# _get_risk_level Tests
# =============================================================================


class TestGetRiskLevel:
    """Tests for BusinessIntentRouter._get_risk_level assessment."""

    @pytest.fixture
    def router_instance(
        self,
        mock_pattern_matcher,
        mock_semantic_router,
        mock_llm_classifier,
    ):
        """Create a router instance for testing internal methods."""
        return BusinessIntentRouter(
            pattern_matcher=mock_pattern_matcher,
            semantic_router=mock_semantic_router,
            llm_classifier=mock_llm_classifier,
        )

    def test_incident_with_critical_keyword_jinJi(self, router_instance):
        """INCIDENT with '緊急' keyword should return CRITICAL."""
        result = router_instance._get_risk_level(
            ITIntentCategory.INCIDENT, "ETL 緊急失敗"
        )
        assert result == RiskLevel.CRITICAL

    def test_incident_with_critical_keyword_yanzhong(self, router_instance):
        """INCIDENT with '嚴重' keyword should return CRITICAL."""
        result = router_instance._get_risk_level(
            ITIntentCategory.INCIDENT, "嚴重問題"
        )
        assert result == RiskLevel.CRITICAL

    def test_incident_with_critical_keyword_english(self, router_instance):
        """INCIDENT with 'critical' keyword should return CRITICAL."""
        result = router_instance._get_risk_level(
            ITIntentCategory.INCIDENT, "System critical failure"
        )
        assert result == RiskLevel.CRITICAL

    def test_incident_with_critical_keyword_urgent(self, router_instance):
        """INCIDENT with 'urgent' keyword should return CRITICAL."""
        result = router_instance._get_risk_level(
            ITIntentCategory.INCIDENT, "Urgent outage detected"
        )
        assert result == RiskLevel.CRITICAL

    def test_incident_with_high_keyword_yingXiang(self, router_instance):
        """INCIDENT with '影響' keyword should return HIGH."""
        result = router_instance._get_risk_level(
            ITIntentCategory.INCIDENT, "影響到業務了"
        )
        assert result == RiskLevel.HIGH

    def test_incident_with_high_keyword_shengchan(self, router_instance):
        """INCIDENT with '生產' keyword should return HIGH."""
        result = router_instance._get_risk_level(
            ITIntentCategory.INCIDENT, "生產環境出問題"
        )
        assert result == RiskLevel.HIGH

    def test_incident_default_medium(self, router_instance):
        """INCIDENT without special keywords should return MEDIUM."""
        result = router_instance._get_risk_level(
            ITIntentCategory.INCIDENT, "ETL 系統有些問題"
        )
        assert result == RiskLevel.MEDIUM

    def test_change_with_production_keyword(self, router_instance):
        """CHANGE with '生產' keyword should return HIGH."""
        result = router_instance._get_risk_level(
            ITIntentCategory.CHANGE, "需要更新生產環境配置"
        )
        assert result == RiskLevel.HIGH

    def test_change_with_database_keyword(self, router_instance):
        """CHANGE with '資料庫' keyword should return HIGH."""
        result = router_instance._get_risk_level(
            ITIntentCategory.CHANGE, "資料庫升級"
        )
        assert result == RiskLevel.HIGH

    def test_change_default_medium(self, router_instance):
        """CHANGE without special keywords should return MEDIUM."""
        result = router_instance._get_risk_level(
            ITIntentCategory.CHANGE, "更新測試環境"
        )
        assert result == RiskLevel.MEDIUM

    def test_query_returns_low(self, router_instance):
        """QUERY category should always return LOW."""
        result = router_instance._get_risk_level(
            ITIntentCategory.QUERY, "查詢系統狀態"
        )
        assert result == RiskLevel.LOW

    def test_query_returns_low_regardless_of_keywords(self, router_instance):
        """QUERY should return LOW even with critical keywords."""
        result = router_instance._get_risk_level(
            ITIntentCategory.QUERY, "查詢緊急事件狀態"
        )
        assert result == RiskLevel.LOW

    def test_request_returns_medium(self, router_instance):
        """REQUEST category should return MEDIUM (default fallthrough)."""
        result = router_instance._get_risk_level(
            ITIntentCategory.REQUEST, "申請帳號"
        )
        assert result == RiskLevel.MEDIUM

    def test_none_category_returns_medium(self, router_instance):
        """None category should return MEDIUM."""
        result = router_instance._get_risk_level(None, "some input")
        assert result == RiskLevel.MEDIUM


# =============================================================================
# create_router() Factory Tests
# =============================================================================


class TestCreateRouter:
    """Tests for create_router() factory function."""

    def test_creates_with_rules_dict(self):
        """Should create router with pattern rules dictionary."""
        rules = {
            "rules": [
                {
                    "id": "test_rule",
                    "category": "incident",
                    "sub_intent": "test",
                    "patterns": ["test.*pattern"],
                    "priority": 100,
                },
            ]
        }

        router = create_router(pattern_rules_dict=rules)

        assert isinstance(router, BusinessIntentRouter)
        assert router.pattern_matcher is not None
        assert router.semantic_router is not None
        assert router.llm_classifier is not None

    def test_creates_with_empty_rules(self):
        """Should create router with no rules (empty fallback)."""
        router = create_router()

        assert isinstance(router, BusinessIntentRouter)
        assert router.pattern_matcher is not None

    def test_creates_with_config(self):
        """Should create router with custom configuration."""
        config = RouterConfig(
            pattern_threshold=0.80,
            enable_llm_fallback=False,
        )

        router = create_router(config=config)

        assert isinstance(router, BusinessIntentRouter)
        assert router.config.pattern_threshold == 0.80
        assert router.config.enable_llm_fallback is False

    def test_creates_with_semantic_routes(self):
        """Should create router with semantic routes list."""
        router = create_router(semantic_routes=[])

        assert isinstance(router, BusinessIntentRouter)
        assert router.semantic_router is not None

    def test_creates_with_llm_api_key(self):
        """Should create router with LLM API key."""
        router = create_router(llm_api_key="test-key-123")

        assert isinstance(router, BusinessIntentRouter)
        assert router.llm_classifier is not None
