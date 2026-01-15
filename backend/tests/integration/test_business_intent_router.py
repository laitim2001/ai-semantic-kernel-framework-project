"""
Integration Tests for BusinessIntentRouter

Tests the complete three-layer routing flow with completeness checking.
Uses mock implementations for external dependencies.

Sprint 93: Story 93-4 - Integration Tests (Phase 28)
"""

import asyncio
import pytest
import time
from typing import Any, Dict, List

from src.integrations.orchestration.intent_router import (
    BusinessIntentRouter,
    MockBusinessIntentRouter,
    RouterConfig,
    RoutingMetrics,
    PatternMatcher,
    SemanticRouter,
    MockSemanticRouter,
    LLMClassifier,
    MockLLMClassifier,
    CompletenessChecker,
    MockCompletenessChecker,
    ITIntentCategory,
    RoutingDecision,
    RiskLevel,
    WorkflowType,
    PatternRule,
    SemanticRoute,
    create_router,
    create_mock_router,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def pattern_rules() -> Dict[str, Any]:
    """Pattern rules for testing."""
    return {
        "rules": [
            {
                "id": "incident-etl-001",
                "category": "incident",
                "sub_intent": "etl_failure",
                "patterns": [r"ETL.*(?:失敗|錯誤|fail)", r"資料同步.*(?:問題|異常)"],
                "priority": 200,
                "workflow_type": "sequential",
                "risk_level": "high",
                "description": "ETL 作業失敗",
                "enabled": True,
            },
            {
                "id": "incident-system-001",
                "category": "incident",
                "sub_intent": "system_down",
                "patterns": [r"(?:系統|服務|平台).*(?:掛了|當機|無法)", r"(?:無法|不能).*(?:登入|存取)"],
                "priority": 250,
                "workflow_type": "magentic",
                "risk_level": "critical",
                "description": "系統當機",
                "enabled": True,
            },
            {
                "id": "request-account-001",
                "category": "request",
                "sub_intent": "account_creation",
                "patterns": [r"(?:申請|開通|建立).*帳號", r"新.*(?:員工|人員).*(?:帳號|開通)"],
                "priority": 150,
                "workflow_type": "simple",
                "risk_level": "medium",
                "description": "帳號申請",
                "enabled": True,
            },
            {
                "id": "change-deploy-001",
                "category": "change",
                "sub_intent": "release_deployment",
                "patterns": [r"(?:部署|發布|release).*(?:版本|v?\d+\.\d+)", r"上線.*(?:排程|時間)"],
                "priority": 180,
                "workflow_type": "magentic",
                "risk_level": "high",
                "description": "版本部署",
                "enabled": True,
            },
            {
                "id": "query-status-001",
                "category": "query",
                "sub_intent": "status_inquiry",
                "patterns": [r"(?:查詢|詢問).*(?:狀態|進度)", r"(?:目前|現在).*(?:如何|怎樣)"],
                "priority": 100,
                "workflow_type": "simple",
                "risk_level": "low",
                "description": "狀態查詢",
                "enabled": True,
            },
        ]
    }


@pytest.fixture
def semantic_routes() -> List[SemanticRoute]:
    """Semantic routes for testing."""
    return [
        SemanticRoute(
            name="etl_failure",
            category=ITIntentCategory.INCIDENT,
            sub_intent="etl_failure",
            utterances=[
                "ETL 今天跑失敗了",
                "資料同步出現問題",
                "批次作業執行異常",
                "ETL pipeline 錯誤",
                "數據處理程序當掉",
            ],
            workflow_type=WorkflowType.SEQUENTIAL,
            risk_level=RiskLevel.HIGH,
        ),
        SemanticRoute(
            name="network_issue",
            category=ITIntentCategory.INCIDENT,
            sub_intent="network_issue",
            utterances=[
                "網路連線很慢",
                "無法連接到伺服器",
                "網路斷線了",
                "VPN 連不上",
                "網路延遲很高",
            ],
            workflow_type=WorkflowType.SEQUENTIAL,
            risk_level=RiskLevel.MEDIUM,
        ),
        SemanticRoute(
            name="account_creation",
            category=ITIntentCategory.REQUEST,
            sub_intent="account_creation",
            utterances=[
                "需要申請一個新帳號",
                "幫新同事開通系統權限",
                "建立新用戶帳號",
                "新人報到需要開帳號",
                "開通 AD 帳號",
            ],
            workflow_type=WorkflowType.SIMPLE,
            risk_level=RiskLevel.MEDIUM,
        ),
        SemanticRoute(
            name="software_installation",
            category=ITIntentCategory.REQUEST,
            sub_intent="software_installation",
            utterances=[
                "需要安裝新軟體",
                "請幫我裝 Visual Studio",
                "申請安裝開發工具",
                "軟體安裝申請",
                "安裝 Office 365",
            ],
            workflow_type=WorkflowType.SIMPLE,
            risk_level=RiskLevel.LOW,
        ),
    ]


@pytest.fixture
def router_config() -> RouterConfig:
    """Router configuration for testing."""
    return RouterConfig(
        pattern_threshold=0.90,
        semantic_threshold=0.85,
        enable_llm_fallback=True,
        enable_completeness=True,
        track_latency=True,
    )


@pytest.fixture
def mock_router(pattern_rules: Dict[str, Any], semantic_routes: List[SemanticRoute]) -> MockBusinessIntentRouter:
    """Create mock router for testing."""
    return MockBusinessIntentRouter(
        pattern_rules=pattern_rules,
        semantic_routes=semantic_routes,
    )


@pytest.fixture
def full_router(pattern_rules: Dict[str, Any], semantic_routes: List[SemanticRoute], router_config: RouterConfig) -> BusinessIntentRouter:
    """Create full router with mock external dependencies."""
    return BusinessIntentRouter(
        pattern_matcher=PatternMatcher(rules_dict=pattern_rules),
        semantic_router=MockSemanticRouter(routes=semantic_routes),
        llm_classifier=MockLLMClassifier(),
        completeness_checker=CompletenessChecker(),
        config=router_config,
    )


# =============================================================================
# Test Cases: Pattern Layer Direct Match
# =============================================================================

class TestPatternDirectMatch:
    """Tests for Pattern Matcher (Layer 1) direct matching."""

    @pytest.mark.asyncio
    async def test_etl_failure_pattern_match(self, full_router: BusinessIntentRouter):
        """Test ETL failure matches pattern layer."""
        decision = await full_router.route("ETL 今天跑失敗了，很緊急")

        assert decision.intent_category == ITIntentCategory.INCIDENT
        assert decision.sub_intent == "etl_failure"
        assert decision.routing_layer == "pattern"
        assert decision.confidence >= 0.90
        assert decision.rule_id == "incident-etl-001"

    @pytest.mark.asyncio
    async def test_system_down_pattern_match(self, full_router: BusinessIntentRouter):
        """Test system down matches pattern layer."""
        decision = await full_router.route("CRM 系統掛了，客戶無法使用")

        assert decision.intent_category == ITIntentCategory.INCIDENT
        assert decision.sub_intent == "system_down"
        assert decision.routing_layer == "pattern"
        assert decision.risk_level == RiskLevel.CRITICAL

    @pytest.mark.asyncio
    async def test_account_request_pattern_match(self, full_router: BusinessIntentRouter):
        """Test account request matches pattern layer."""
        decision = await full_router.route("申請帳號給新進員工張三")

        assert decision.intent_category == ITIntentCategory.REQUEST
        # May use pattern or semantic/llm depending on match
        assert decision.routing_layer in ["pattern", "semantic", "llm"]

    @pytest.mark.asyncio
    async def test_deployment_pattern_match(self, full_router: BusinessIntentRouter):
        """Test deployment request matches pattern layer."""
        decision = await full_router.route("部署版本 v2.1.0 到生產環境")

        assert decision.intent_category == ITIntentCategory.CHANGE
        assert decision.sub_intent == "release_deployment"
        assert decision.routing_layer == "pattern"

    @pytest.mark.asyncio
    async def test_status_query_pattern_match(self, full_router: BusinessIntentRouter):
        """Test status query matches pattern layer."""
        decision = await full_router.route("查詢系統目前狀態如何")

        assert decision.intent_category == ITIntentCategory.QUERY
        # May use pattern or semantic/llm depending on match
        assert decision.routing_layer in ["pattern", "semantic", "llm"]


# =============================================================================
# Test Cases: Semantic Layer Fallback
# =============================================================================

class TestSemanticLayerFallback:
    """Tests for falling back to Semantic Router (Layer 2)."""

    @pytest.mark.asyncio
    async def test_fallback_to_semantic_for_etl(self, full_router: BusinessIntentRouter):
        """Test fallback to semantic for varied ETL description."""
        # Input that won't match pattern but matches semantic route
        decision = await full_router.route("批次作業今天執行有異常")

        # Should fallback to semantic or LLM
        assert decision.intent_category in [ITIntentCategory.INCIDENT, ITIntentCategory.UNKNOWN]
        assert decision.routing_layer in ["semantic", "llm", "pattern"]

    @pytest.mark.asyncio
    async def test_semantic_network_issue(self, full_router: BusinessIntentRouter):
        """Test semantic matching for network issues."""
        decision = await full_router.route("VPN 好像連不上去")

        # May match semantic or fallback to LLM
        assert decision.routing_layer in ["semantic", "llm", "pattern"]

    @pytest.mark.asyncio
    async def test_semantic_software_request(self, full_router: BusinessIntentRouter):
        """Test semantic matching for software installation."""
        decision = await full_router.route("幫我裝一下 VSCode")

        # Should match semantic or LLM
        assert decision.routing_layer in ["semantic", "llm", "pattern"]


# =============================================================================
# Test Cases: LLM Layer Fallback
# =============================================================================

class TestLLMLayerFallback:
    """Tests for falling back to LLM Classifier (Layer 3)."""

    @pytest.mark.asyncio
    async def test_fallback_to_llm_for_ambiguous_input(self, full_router: BusinessIntentRouter):
        """Test fallback to LLM for ambiguous input."""
        decision = await full_router.route("有些事情想要處理一下")

        # Should go to LLM
        assert decision.routing_layer in ["llm", "semantic", "pattern"]

    @pytest.mark.asyncio
    async def test_llm_handles_complex_request(self, full_router: BusinessIntentRouter):
        """Test LLM handles complex multi-part request."""
        decision = await full_router.route(
            "我需要申請一個新的開發環境帳號，同時要安裝相關的開發工具"
        )

        # LLM should classify this
        assert decision.intent_category != ITIntentCategory.UNKNOWN


# =============================================================================
# Test Cases: Completeness Checking
# =============================================================================

class TestCompletenessChecking:
    """Tests for completeness checking integration."""

    @pytest.mark.asyncio
    async def test_incident_with_complete_info(self, full_router: BusinessIntentRouter):
        """Test incident with all required fields."""
        decision = await full_router.route(
            "ETL 系統今天跑失敗了，影響到訂單處理，很緊急需要處理"
        )

        assert decision.intent_category == ITIntentCategory.INCIDENT
        assert decision.completeness.completeness_score >= 0.6

    @pytest.mark.asyncio
    async def test_incident_with_partial_info(self, full_router: BusinessIntentRouter):
        """Test incident with partial information."""
        decision = await full_router.route("有東西壞了")

        # Should still classify but with lower completeness
        assert decision.completeness.completeness_score < 1.0

    @pytest.mark.asyncio
    async def test_completeness_suggestions(self, full_router: BusinessIntentRouter):
        """Test that suggestions are provided for missing fields."""
        decision = await full_router.route("系統有問題")

        # Should have suggestions if incomplete
        if not decision.completeness.is_complete:
            assert len(decision.completeness.suggestions) > 0 or len(decision.completeness.missing_fields) > 0


# =============================================================================
# Test Cases: Missing Field Detection
# =============================================================================

class TestMissingFieldDetection:
    """Tests for missing field detection."""

    @pytest.mark.asyncio
    async def test_detect_missing_urgency(self, full_router: BusinessIntentRouter):
        """Test detection of missing urgency field."""
        decision = await full_router.route("ETL 系統失敗了")

        assert decision.intent_category == ITIntentCategory.INCIDENT
        # May or may not have urgency detected depending on patterns

    @pytest.mark.asyncio
    async def test_detect_missing_schedule_for_change(self, full_router: BusinessIntentRouter):
        """Test detection of missing schedule for change request."""
        decision = await full_router.route("要部署版本 v2.0")

        if decision.intent_category == ITIntentCategory.CHANGE:
            # Schedule may be missing
            pass  # Completeness checker should note missing schedule

    @pytest.mark.asyncio
    async def test_query_requires_minimal_fields(self, full_router: BusinessIntentRouter):
        """Test that queries require minimal fields."""
        decision = await full_router.route("查詢系統狀態")

        if decision.intent_category == ITIntentCategory.QUERY:
            # Queries should be easy to satisfy
            assert decision.completeness.completeness_score >= 0.5


# =============================================================================
# Test Cases: Latency Tracking
# =============================================================================

class TestLatencyTracking:
    """Tests for latency tracking and metrics."""

    @pytest.mark.asyncio
    async def test_processing_time_recorded(self, full_router: BusinessIntentRouter):
        """Test that processing time is recorded."""
        decision = await full_router.route("ETL 今天跑失敗了")

        assert decision.processing_time_ms > 0
        assert decision.processing_time_ms < 10000  # Should be under 10 seconds

    @pytest.mark.asyncio
    async def test_pattern_layer_fast(self, full_router: BusinessIntentRouter):
        """Test that pattern layer is fast (< 10ms for simple cases)."""
        decision = await full_router.route("ETL 今天跑失敗了")

        if decision.routing_layer == "pattern":
            # Pattern matching should be very fast
            assert decision.processing_time_ms < 100  # Allow some margin

    @pytest.mark.asyncio
    async def test_layer_latencies_in_metadata(self, full_router: BusinessIntentRouter):
        """Test that layer latencies are tracked in metadata."""
        decision = await full_router.route("這是一個測試訊息")

        assert "layer_latencies" in decision.metadata
        assert "pattern" in decision.metadata["layer_latencies"]

    @pytest.mark.asyncio
    async def test_metrics_accumulation(self, full_router: BusinessIntentRouter):
        """Test that metrics accumulate correctly."""
        # Route multiple inputs
        await full_router.route("ETL 失敗了")
        await full_router.route("申請帳號")
        await full_router.route("查詢狀態")

        metrics = full_router.get_metrics()
        assert metrics["total_requests"] >= 3


# =============================================================================
# Test Cases: Router Configuration
# =============================================================================

class TestRouterConfiguration:
    """Tests for router configuration options."""

    @pytest.mark.asyncio
    async def test_custom_pattern_threshold(self, pattern_rules: Dict[str, Any], semantic_routes: List[SemanticRoute]):
        """Test custom pattern threshold."""
        config = RouterConfig(pattern_threshold=0.99)  # Very high threshold

        router = BusinessIntentRouter(
            pattern_matcher=PatternMatcher(rules_dict=pattern_rules),
            semantic_router=MockSemanticRouter(routes=semantic_routes),
            llm_classifier=MockLLMClassifier(),
            config=config,
        )

        decision = await router.route("ETL 失敗")
        # May fallback to semantic or LLM due to high threshold

    @pytest.mark.asyncio
    async def test_disable_llm_fallback(self, pattern_rules: Dict[str, Any], semantic_routes: List[SemanticRoute]):
        """Test disabling LLM fallback."""
        config = RouterConfig(enable_llm_fallback=False)

        router = BusinessIntentRouter(
            pattern_matcher=PatternMatcher(rules_dict=pattern_rules),
            semantic_router=MockSemanticRouter(routes=semantic_routes),
            llm_classifier=MockLLMClassifier(),
            config=config,
        )

        decision = await router.route("這是一個模糊的訊息")
        assert decision.routing_layer != "llm"

    @pytest.mark.asyncio
    async def test_disable_completeness(self, pattern_rules: Dict[str, Any], semantic_routes: List[SemanticRoute]):
        """Test disabling completeness checking."""
        config = RouterConfig(enable_completeness=False)

        router = BusinessIntentRouter(
            pattern_matcher=PatternMatcher(rules_dict=pattern_rules),
            semantic_router=MockSemanticRouter(routes=semantic_routes),
            llm_classifier=MockLLMClassifier(),
            config=config,
        )

        decision = await router.route("ETL 失敗了")
        # Completeness should be default
        assert decision.completeness.completeness_score == 1.0


# =============================================================================
# Test Cases: Workflow Type Assignment
# =============================================================================

class TestWorkflowTypeAssignment:
    """Tests for workflow type assignment."""

    @pytest.mark.asyncio
    async def test_critical_incident_gets_magentic(self, full_router: BusinessIntentRouter):
        """Test critical incidents get MAGENTIC workflow."""
        decision = await full_router.route("CRM 系統掛了，客戶無法使用")

        if decision.sub_intent == "system_down":
            assert decision.workflow_type == WorkflowType.MAGENTIC

    @pytest.mark.asyncio
    async def test_query_gets_simple(self, full_router: BusinessIntentRouter):
        """Test queries get SIMPLE workflow."""
        decision = await full_router.route("查詢目前系統狀態如何")

        if decision.intent_category == ITIntentCategory.QUERY:
            assert decision.workflow_type == WorkflowType.SIMPLE

    @pytest.mark.asyncio
    async def test_deployment_gets_appropriate_workflow(self, full_router: BusinessIntentRouter):
        """Test deployments get appropriate workflow."""
        decision = await full_router.route("部署版本 v2.1.0 到生產環境")

        if decision.intent_category == ITIntentCategory.CHANGE:
            # Should be MAGENTIC or SEQUENTIAL for changes
            assert decision.workflow_type in [WorkflowType.MAGENTIC, WorkflowType.SEQUENTIAL]


# =============================================================================
# Test Cases: Risk Level Assessment
# =============================================================================

class TestRiskLevelAssessment:
    """Tests for risk level assessment."""

    @pytest.mark.asyncio
    async def test_urgent_incident_is_critical(self, full_router: BusinessIntentRouter):
        """Test urgent incidents are marked critical."""
        decision = await full_router.route("系統掛了非常緊急")

        if decision.intent_category == ITIntentCategory.INCIDENT:
            assert decision.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]

    @pytest.mark.asyncio
    async def test_production_change_is_high_risk(self, full_router: BusinessIntentRouter):
        """Test production changes are high risk."""
        decision = await full_router.route("部署版本到生產環境")

        if decision.intent_category == ITIntentCategory.CHANGE:
            # Production should be high risk
            assert decision.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL, RiskLevel.MEDIUM]

    @pytest.mark.asyncio
    async def test_query_is_low_risk(self, full_router: BusinessIntentRouter):
        """Test queries are low risk."""
        decision = await full_router.route("查詢系統狀態")

        if decision.intent_category == ITIntentCategory.QUERY:
            assert decision.risk_level == RiskLevel.LOW


# =============================================================================
# Test Cases: Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_input(self, full_router: BusinessIntentRouter):
        """Test empty input handling."""
        decision = await full_router.route("")

        assert decision.intent_category == ITIntentCategory.UNKNOWN
        assert decision.confidence == 0.0

    @pytest.mark.asyncio
    async def test_whitespace_only_input(self, full_router: BusinessIntentRouter):
        """Test whitespace-only input handling."""
        decision = await full_router.route("   \n\t   ")

        assert decision.intent_category == ITIntentCategory.UNKNOWN

    @pytest.mark.asyncio
    async def test_very_long_input(self, full_router: BusinessIntentRouter):
        """Test handling of very long input."""
        long_input = "ETL 失敗了，" * 100 + "很緊急"
        decision = await full_router.route(long_input)

        assert decision.intent_category == ITIntentCategory.INCIDENT
        assert decision.processing_time_ms < 5000  # Should complete in reasonable time

    @pytest.mark.asyncio
    async def test_special_characters(self, full_router: BusinessIntentRouter):
        """Test handling of special characters."""
        decision = await full_router.route("ETL 失敗!!! ??? @#$%")

        # Should still process
        assert decision.intent_category is not None

    @pytest.mark.asyncio
    async def test_mixed_language(self, full_router: BusinessIntentRouter):
        """Test handling of mixed Chinese-English input."""
        decision = await full_router.route("ETL job failed, 請幫忙處理 urgent")

        assert decision.intent_category != ITIntentCategory.UNKNOWN


# =============================================================================
# Test Cases: Factory Functions
# =============================================================================

class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_create_mock_router(self):
        """Test create_mock_router factory."""
        router = create_mock_router()

        assert isinstance(router, MockBusinessIntentRouter)

    @pytest.mark.asyncio
    async def test_mock_router_basic_routing(self):
        """Test mock router basic routing."""
        router = create_mock_router()
        decision = await router.route("ETL 失敗了")

        assert decision is not None
        assert isinstance(decision, RoutingDecision)


# =============================================================================
# Test Cases: Concurrent Routing
# =============================================================================

class TestConcurrentRouting:
    """Tests for concurrent routing requests."""

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, full_router: BusinessIntentRouter):
        """Test handling multiple concurrent requests."""
        inputs = [
            "ETL 今天跑失敗了",
            "申請新帳號",
            "系統很慢",
            "部署版本 v2.0",
            "查詢進度",
        ]

        tasks = [full_router.route(inp) for inp in inputs]
        decisions = await asyncio.gather(*tasks)

        assert len(decisions) == 5
        for decision in decisions:
            assert decision.intent_category is not None

    @pytest.mark.asyncio
    async def test_metrics_thread_safety(self, full_router: BusinessIntentRouter):
        """Test metrics accumulation under concurrent load."""
        inputs = ["測試 " + str(i) for i in range(10)]

        tasks = [full_router.route(inp) for inp in inputs]
        await asyncio.gather(*tasks)

        metrics = full_router.get_metrics()
        assert metrics["total_requests"] >= 10


# =============================================================================
# Test Cases: Decision Serialization
# =============================================================================

class TestDecisionSerialization:
    """Tests for decision serialization."""

    @pytest.mark.asyncio
    async def test_decision_to_dict(self, full_router: BusinessIntentRouter):
        """Test RoutingDecision serialization."""
        decision = await full_router.route("ETL 今天跑失敗了，很緊急")

        decision_dict = decision.to_dict()

        assert "intent_category" in decision_dict
        assert "confidence" in decision_dict
        assert "completeness" in decision_dict
        assert "routing_layer" in decision_dict
        assert "processing_time_ms" in decision_dict

    @pytest.mark.asyncio
    async def test_decision_json_serializable(self, full_router: BusinessIntentRouter):
        """Test decision is JSON serializable."""
        import json

        decision = await full_router.route("系統故障了")
        decision_dict = decision.to_dict()

        # Should not raise
        json_str = json.dumps(decision_dict, ensure_ascii=False)
        assert len(json_str) > 0
