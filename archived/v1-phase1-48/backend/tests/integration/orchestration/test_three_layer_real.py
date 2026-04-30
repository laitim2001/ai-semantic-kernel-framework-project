"""
Three-Layer Routing Integration Tests

Tests the full three-layer routing pipeline (Pattern → Semantic → LLM)
using mocked LLM service to verify end-to-end routing behavior.

Sprint 128: Story 128-3
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.integrations.orchestration.intent_router.models import (
    ITIntentCategory,
    RiskLevel,
    WorkflowType,
)
from src.integrations.orchestration.intent_router.router import (
    BusinessIntentRouter,
    RouterConfig,
    create_router,
)
from src.integrations.orchestration.intent_router.pattern_matcher import PatternMatcher
from src.integrations.orchestration.intent_router.semantic_router import SemanticRouter
from src.integrations.orchestration.intent_router.llm_classifier import LLMClassifier


# =============================================================================
# Fixtures
# =============================================================================


def _make_pattern_rules() -> dict:
    """Create pattern rules that match common IT incidents."""
    return {
        "rules": [
            {
                "id": "incident_etl",
                "category": "incident",
                "sub_intent": "etl_failure",
                "patterns": [r"ETL.*失敗", r"ETL.*fail", r"pipeline.*fail"],
                "priority": 100,
                "workflow_type": "sequential",
                "risk_level": "high",
            },
            {
                "id": "request_account",
                "category": "request",
                "sub_intent": "account_creation",
                "patterns": [r"申請.*帳號", r"新.*帳號", r"create.*account"],
                "priority": 100,
                "workflow_type": "simple",
                "risk_level": "low",
            },
        ]
    }


def _make_llm_response(category: str, sub_intent: str, confidence: float) -> str:
    """Build a mock LLM JSON response."""
    return json.dumps({
        "intent_category": category,
        "sub_intent": sub_intent,
        "confidence": confidence,
        "reasoning": f"Classified as {category}",
    })


def _make_router_with_llm(
    llm_response: str,
    pattern_rules: dict = None,
) -> BusinessIntentRouter:
    """Create a router with mocked LLM service and real pattern matcher."""
    mock_llm_service = MagicMock()
    mock_llm_service.generate = AsyncMock(return_value=llm_response)

    return create_router(
        pattern_rules_dict=pattern_rules or _make_pattern_rules(),
        llm_service=mock_llm_service,
        config=RouterConfig(
            pattern_threshold=0.85,
            semantic_threshold=0.85,
            enable_llm_fallback=True,
        ),
    )


# =============================================================================
# Tests
# =============================================================================


class TestPatternLayerMatch:
    """Tests where pattern matcher provides the classification."""

    @pytest.mark.asyncio
    async def test_pattern_match_etl_no_llm_called(self):
        """Pattern match for ETL failure — LLM should NOT be called."""
        mock_llm_service = MagicMock()
        mock_llm_service.generate = AsyncMock(return_value="should not be called")

        router = create_router(
            pattern_rules_dict=_make_pattern_rules(),
            llm_service=mock_llm_service,
            config=RouterConfig(pattern_threshold=0.85, enable_llm_fallback=True),
        )

        decision = await router.route("ETL Pipeline 失敗了")

        assert decision.intent_category == ITIntentCategory.INCIDENT
        assert decision.routing_layer == "pattern"
        mock_llm_service.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_pattern_match_account_request(self):
        """Pattern match for account request."""
        router = _make_router_with_llm("unused")

        decision = await router.route("我需要申請一個新帳號")

        assert decision.intent_category == ITIntentCategory.REQUEST
        assert decision.routing_layer == "pattern"


class TestLLMFallback:
    """Tests where LLM fallback provides the classification."""

    @pytest.mark.asyncio
    async def test_llm_fallback_for_unmatched_input(self):
        """Input not matching any pattern falls through to LLM."""
        llm_response = _make_llm_response("change", "configuration_update", 0.88)
        router = _make_router_with_llm(llm_response)

        decision = await router.route("需要修改防火牆規則，開放 8443 端口")

        assert decision.intent_category == ITIntentCategory.CHANGE
        assert decision.routing_layer == "llm"
        assert decision.confidence == 0.88

    @pytest.mark.asyncio
    async def test_llm_fallback_query(self):
        """Query input not matched by patterns falls through to LLM."""
        llm_response = _make_llm_response("query", "status_inquiry", 0.92)
        router = _make_router_with_llm(llm_response)

        decision = await router.route("請問目前伺服器的運行狀況如何？")

        assert decision.intent_category == ITIntentCategory.QUERY
        assert decision.routing_layer == "llm"


class TestLLMFallbackDisabled:
    """Tests when LLM fallback is disabled."""

    @pytest.mark.asyncio
    async def test_no_llm_fallback_returns_unknown(self):
        """Unmatched input with LLM disabled → UNKNOWN."""
        router = create_router(
            pattern_rules_dict=_make_pattern_rules(),
            llm_service=None,
            config=RouterConfig(
                pattern_threshold=0.90,
                enable_llm_fallback=False,
            ),
        )

        decision = await router.route("這是一段無法分類的輸入")

        assert decision.intent_category == ITIntentCategory.UNKNOWN
        assert decision.routing_layer == "none"


class TestConcurrentRouting:
    """Tests for concurrent routing requests."""

    @pytest.mark.asyncio
    async def test_concurrent_classify_calls(self):
        """3 parallel classify calls all return correct results."""
        # Create mock LLM that returns different results based on call order
        call_count = 0

        async def mock_generate(prompt, **kwargs):
            nonlocal call_count
            call_count += 1
            # Use substrings unique to each user input (not in prompt template)
            if "Pipeline" in prompt:
                return _make_llm_response("incident", "etl_failure", 0.95)
            elif "新帳號" in prompt:
                return _make_llm_response("request", "account_creation", 0.90)
            elif "伺服器" in prompt:
                return _make_llm_response("query", "general_question", 0.80)
            else:
                return _make_llm_response("query", "general_question", 0.80)

        mock_llm_service = MagicMock()
        mock_llm_service.generate = AsyncMock(side_effect=mock_generate)

        router = create_router(
            pattern_rules_dict={"rules": []},  # No pattern rules — force LLM
            llm_service=mock_llm_service,
            config=RouterConfig(enable_llm_fallback=True),
        )

        # Run 3 classifications in parallel
        results = await asyncio.gather(
            router.route("ETL Pipeline 失敗"),
            router.route("申請新帳號"),
            router.route("伺服器狀態查詢"),
        )

        assert results[0].intent_category == ITIntentCategory.INCIDENT
        assert results[1].intent_category == ITIntentCategory.REQUEST
        assert results[2].intent_category == ITIntentCategory.QUERY


class TestEmptyInput:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_empty_input(self):
        """Empty input returns UNKNOWN immediately."""
        router = _make_router_with_llm("unused")

        decision = await router.route("")

        assert decision.intent_category == ITIntentCategory.UNKNOWN
        assert decision.routing_layer == "none"

    @pytest.mark.asyncio
    async def test_whitespace_input(self):
        """Whitespace-only input returns UNKNOWN."""
        router = _make_router_with_llm("unused")

        decision = await router.route("   ")

        assert decision.intent_category == ITIntentCategory.UNKNOWN
