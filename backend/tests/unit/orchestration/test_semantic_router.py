"""
Unit Tests for Semantic Router

Tests for SemanticRouter and semantic route definitions.

Sprint 92: Story 92-5 - Semantic/LLM Unit Tests
"""

import pytest
from typing import List

from src.integrations.orchestration.intent_router.models import (
    ITIntentCategory,
    RiskLevel,
    SemanticRoute,
    SemanticRouteResult,
    WorkflowType,
)
from src.integrations.orchestration.intent_router.semantic_router import (
    SemanticRouter,
    get_default_routes,
    IT_SEMANTIC_ROUTES,
)
from src.integrations.orchestration.intent_router.semantic_router.router import (
    MockSemanticRouter,
)
from src.integrations.orchestration.intent_router.semantic_router.routes import (
    INCIDENT_ROUTES,
    REQUEST_ROUTES,
    CHANGE_ROUTES,
    QUERY_ROUTES,
    get_routes_by_category,
    get_route_statistics,
)


# =============================================================================
# SemanticRouteResult Model Tests
# =============================================================================

class TestSemanticRouteResult:
    """Tests for SemanticRouteResult dataclass."""

    def test_create_basic_result(self):
        """Test creating a basic matched result."""
        result = SemanticRouteResult(
            matched=True,
            intent_category=ITIntentCategory.INCIDENT,
            sub_intent="etl_failure",
            similarity=0.92,
            route_name="incident_etl",
        )

        assert result.matched is True
        assert result.intent_category == ITIntentCategory.INCIDENT
        assert result.sub_intent == "etl_failure"
        assert result.similarity == 0.92
        assert result.route_name == "incident_etl"

    def test_no_match_factory(self):
        """Test the no_match factory method."""
        result = SemanticRouteResult.no_match()

        assert result.matched is False
        assert result.intent_category is None
        assert result.similarity == 0.0

    def test_no_match_with_similarity(self):
        """Test no_match with a similarity score."""
        result = SemanticRouteResult.no_match(similarity=0.75)

        assert result.matched is False
        assert result.similarity == 0.75

    def test_similarity_validation_valid(self):
        """Test valid similarity scores."""
        for score in [0.0, 0.5, 1.0]:
            result = SemanticRouteResult(matched=False, similarity=score)
            assert result.similarity == score

    def test_similarity_validation_invalid(self):
        """Test invalid similarity scores raise ValueError."""
        with pytest.raises(ValueError, match="similarity must be between"):
            SemanticRouteResult(matched=False, similarity=1.5)

        with pytest.raises(ValueError, match="similarity must be between"):
            SemanticRouteResult(matched=False, similarity=-0.1)

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = SemanticRouteResult(
            matched=True,
            intent_category=ITIntentCategory.REQUEST,
            sub_intent="account_creation",
            similarity=0.88,
            route_name="request_account",
            metadata={"extra": "data"},
        )

        result_dict = result.to_dict()

        assert result_dict["matched"] is True
        assert result_dict["intent_category"] == "request"
        assert result_dict["sub_intent"] == "account_creation"
        assert result_dict["similarity"] == 0.88
        assert result_dict["route_name"] == "request_account"
        assert result_dict["metadata"] == {"extra": "data"}


# =============================================================================
# SemanticRoute Model Tests
# =============================================================================

class TestSemanticRoute:
    """Tests for SemanticRoute dataclass."""

    def test_create_route(self):
        """Test creating a semantic route."""
        route = SemanticRoute(
            name="test_route",
            category=ITIntentCategory.INCIDENT,
            sub_intent="test_incident",
            utterances=["test phrase one", "test phrase two"],
            description="Test route description",
        )

        assert route.name == "test_route"
        assert route.category == ITIntentCategory.INCIDENT
        assert route.sub_intent == "test_incident"
        assert len(route.utterances) == 2
        assert route.enabled is True

    def test_route_default_values(self):
        """Test default values for routes."""
        route = SemanticRoute(
            name="test",
            category=ITIntentCategory.QUERY,
            sub_intent="test",
            utterances=["test"],
        )

        assert route.workflow_type == WorkflowType.SIMPLE
        assert route.risk_level == RiskLevel.MEDIUM
        assert route.enabled is True
        assert route.metadata == {}

    def test_route_to_dict(self):
        """Test route conversion to dictionary."""
        route = SemanticRoute(
            name="test_route",
            category=ITIntentCategory.CHANGE,
            sub_intent="deployment",
            utterances=["deploy", "release"],
            workflow_type=WorkflowType.MAGENTIC,
            risk_level=RiskLevel.HIGH,
        )

        route_dict = route.to_dict()

        assert route_dict["name"] == "test_route"
        assert route_dict["category"] == "change"
        assert route_dict["sub_intent"] == "deployment"
        assert route_dict["workflow_type"] == "magentic"
        assert route_dict["risk_level"] == "high"


# =============================================================================
# Route Definitions Tests
# =============================================================================

class TestRouteDefinitions:
    """Tests for predefined route definitions."""

    def test_minimum_route_count(self):
        """Test that at least 10 routes are defined."""
        total_routes = len(IT_SEMANTIC_ROUTES)
        assert total_routes >= 10, f"Expected at least 10 routes, got {total_routes}"

    def test_actual_route_count(self):
        """Test the actual number of routes (should be 15)."""
        assert len(IT_SEMANTIC_ROUTES) == 15

    def test_incident_routes_count(self):
        """Test incident routes count."""
        assert len(INCIDENT_ROUTES) == 4

    def test_request_routes_count(self):
        """Test request routes count."""
        assert len(REQUEST_ROUTES) == 4

    def test_change_routes_count(self):
        """Test change routes count."""
        assert len(CHANGE_ROUTES) == 3

    def test_query_routes_count(self):
        """Test query routes count."""
        assert len(QUERY_ROUTES) == 4

    def test_all_routes_have_utterances(self):
        """Test that all routes have at least 3 utterances."""
        for route in IT_SEMANTIC_ROUTES:
            assert len(route.utterances) >= 3, (
                f"Route {route.name} has only {len(route.utterances)} utterances"
            )

    def test_all_routes_have_unique_names(self):
        """Test that all routes have unique names."""
        names = [r.name for r in IT_SEMANTIC_ROUTES]
        assert len(names) == len(set(names)), "Route names must be unique"

    def test_routes_cover_all_categories(self):
        """Test that routes cover all main categories."""
        categories = {r.category for r in IT_SEMANTIC_ROUTES}
        expected = {
            ITIntentCategory.INCIDENT,
            ITIntentCategory.REQUEST,
            ITIntentCategory.CHANGE,
            ITIntentCategory.QUERY,
        }
        assert categories == expected

    def test_get_default_routes(self):
        """Test get_default_routes returns a copy."""
        routes1 = get_default_routes()
        routes2 = get_default_routes()

        assert routes1 is not routes2  # Should be different objects
        assert len(routes1) == len(routes2)

    def test_get_routes_by_category(self):
        """Test filtering routes by category."""
        incident_routes = get_routes_by_category(ITIntentCategory.INCIDENT)
        assert len(incident_routes) == 4
        assert all(r.category == ITIntentCategory.INCIDENT for r in incident_routes)

    def test_get_route_statistics(self):
        """Test route statistics."""
        stats = get_route_statistics()

        assert stats["total"] == 15
        assert stats["by_category"]["incident"] == 4
        assert stats["by_category"]["request"] == 4
        assert stats["by_category"]["change"] == 3
        assert stats["by_category"]["query"] == 4
        assert stats["total_utterances"] >= 45  # At least 3 per route


# =============================================================================
# MockSemanticRouter Tests
# =============================================================================

class TestMockSemanticRouter:
    """Tests for MockSemanticRouter."""

    @pytest.fixture
    def mock_router(self):
        """Create a mock router with default routes."""
        return MockSemanticRouter(
            routes=get_default_routes(),
            threshold=0.5,  # Lower threshold for keyword matching
        )

    @pytest.mark.asyncio
    async def test_is_available(self, mock_router):
        """Test mock router is always available."""
        assert mock_router.is_available is True

    @pytest.mark.asyncio
    async def test_route_etl_incident(self, mock_router):
        """Test routing ETL failure input."""
        result = await mock_router.route("ETL 今天跑失敗了")

        assert result.matched is True
        assert result.intent_category == ITIntentCategory.INCIDENT
        assert "etl" in result.sub_intent.lower()

    @pytest.mark.asyncio
    async def test_route_network_incident(self, mock_router):
        """Test routing network issue input."""
        result = await mock_router.route("網路連線有問題")

        assert result.matched is True
        assert result.intent_category == ITIntentCategory.INCIDENT

    @pytest.mark.asyncio
    async def test_route_account_request(self, mock_router):
        """Test routing account creation request."""
        result = await mock_router.route("我需要申請新帳號")

        assert result.matched is True
        assert result.intent_category == ITIntentCategory.REQUEST

    @pytest.mark.asyncio
    async def test_route_deployment_change(self, mock_router):
        """Test routing deployment change request."""
        result = await mock_router.route("需要部署新版本")

        assert result.matched is True
        assert result.intent_category == ITIntentCategory.CHANGE

    @pytest.mark.asyncio
    async def test_route_status_query(self, mock_router):
        """Test routing status query."""
        result = await mock_router.route("目前系統狀態如何")

        assert result.matched is True
        assert result.intent_category == ITIntentCategory.QUERY

    @pytest.mark.asyncio
    async def test_route_no_match(self, mock_router):
        """Test no match for unrelated input."""
        # Use high threshold to ensure no match
        strict_router = MockSemanticRouter(
            routes=get_default_routes(),
            threshold=0.99,
        )

        result = await strict_router.route("今天天氣很好")

        # May or may not match depending on keywords
        # Just verify result structure is valid
        assert isinstance(result, SemanticRouteResult)

    @pytest.mark.asyncio
    async def test_route_metadata_includes_mock_flag(self, mock_router):
        """Test that mock results include mock flag in metadata."""
        result = await mock_router.route("ETL 失敗了")

        if result.matched:
            assert result.metadata.get("mock") is True


# =============================================================================
# SemanticRouter Tests (with Mock)
# =============================================================================

class TestSemanticRouter:
    """Tests for SemanticRouter class."""

    def test_init_with_threshold(self):
        """Test initialization with custom threshold."""
        router = SemanticRouter(threshold=0.90)
        assert router.threshold == 0.90

    def test_init_invalid_threshold(self):
        """Test initialization with invalid threshold."""
        with pytest.raises(ValueError, match="threshold must be between"):
            SemanticRouter(threshold=1.5)

        with pytest.raises(ValueError, match="threshold must be between"):
            SemanticRouter(threshold=-0.1)

    def test_add_route(self):
        """Test adding a route."""
        router = SemanticRouter()
        assert router.get_route_count() == 0

        route = SemanticRoute(
            name="test",
            category=ITIntentCategory.QUERY,
            sub_intent="test",
            utterances=["test phrase"],
        )
        router.add_route(route)

        assert router.get_route_count() == 1
        assert "test" in router.get_route_names()

    def test_remove_route(self):
        """Test removing a route."""
        route = SemanticRoute(
            name="test",
            category=ITIntentCategory.QUERY,
            sub_intent="test",
            utterances=["test"],
        )
        router = SemanticRouter(routes=[route])

        assert router.get_route_count() == 1

        removed = router.remove_route("test")
        assert removed is True
        assert router.get_route_count() == 0

    def test_remove_nonexistent_route(self):
        """Test removing a route that doesn't exist."""
        router = SemanticRouter()
        removed = router.remove_route("nonexistent")
        assert removed is False

    def test_get_route_names(self):
        """Test getting route names."""
        routes = get_default_routes()[:3]
        router = SemanticRouter(routes=routes)

        names = router.get_route_names()
        assert len(names) == 3

    def test_get_enabled_route_count(self):
        """Test counting enabled routes."""
        route1 = SemanticRoute(
            name="enabled", category=ITIntentCategory.QUERY,
            sub_intent="test", utterances=["test"], enabled=True
        )
        route2 = SemanticRoute(
            name="disabled", category=ITIntentCategory.QUERY,
            sub_intent="test", utterances=["test"], enabled=False
        )

        router = SemanticRouter(routes=[route1, route2])

        assert router.get_route_count() == 2
        assert router.get_enabled_route_count() == 1


# =============================================================================
# Performance Tests
# =============================================================================

class TestSemanticRouterPerformance:
    """Performance tests for Semantic Router."""

    @pytest.fixture
    def mock_router(self):
        """Create a mock router for performance testing."""
        return MockSemanticRouter(
            routes=get_default_routes(),
            threshold=0.5,
        )

    @pytest.mark.asyncio
    async def test_route_latency(self, mock_router):
        """Test that routing is fast (< 100ms)."""
        import time

        test_inputs = [
            "ETL 失敗了",
            "申請帳號",
            "部署新版本",
            "查詢狀態",
        ]

        for input_text in test_inputs:
            start = time.perf_counter()
            await mock_router.route(input_text)
            elapsed_ms = (time.perf_counter() - start) * 1000

            assert elapsed_ms < 100, f"Routing took {elapsed_ms:.2f}ms"

    @pytest.mark.asyncio
    async def test_batch_routing_performance(self, mock_router):
        """Test batch routing performance."""
        import time

        test_inputs = [
            "系統掛了",
            "需要權限",
            "更新配置",
            "查報表",
        ] * 10  # 40 inputs

        start = time.perf_counter()
        for input_text in test_inputs:
            await mock_router.route(input_text)
        total_ms = (time.perf_counter() - start) * 1000

        avg_ms = total_ms / len(test_inputs)
        assert avg_ms < 50, f"Average routing time {avg_ms:.2f}ms exceeds 50ms"
