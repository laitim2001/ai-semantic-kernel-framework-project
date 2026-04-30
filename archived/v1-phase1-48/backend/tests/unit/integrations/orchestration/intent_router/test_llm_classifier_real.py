"""
LLM Classifier with LLMServiceProtocol Tests

Tests the LLMClassifier using mocked LLMServiceProtocol,
verifying classification across all intent categories.

Sprint 128: Story 128-3
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.orchestration.intent_router.llm_classifier.classifier import (
    LLMClassifier,
)
from src.integrations.orchestration.intent_router.models import (
    CompletenessInfo,
    ITIntentCategory,
    LLMClassificationResult,
)


# =============================================================================
# Helpers
# =============================================================================


def _make_llm_response(
    intent_category: str,
    sub_intent: str = "",
    confidence: float = 0.95,
    reasoning: str = "Test reasoning",
) -> str:
    """Build a JSON response string mimicking LLM output."""
    data = {
        "intent_category": intent_category,
        "sub_intent": sub_intent,
        "confidence": confidence,
        "completeness": {
            "score": 0.8,
            "is_complete": True,
            "missing_fields": [],
            "suggestions": [],
        },
        "reasoning": reasoning,
    }
    return json.dumps(data, ensure_ascii=False)


def _make_mock_llm(response: str) -> MagicMock:
    """Create a mock LLMServiceProtocol that returns the given response."""
    mock = MagicMock()
    mock.generate = AsyncMock(return_value=response)
    return mock


# =============================================================================
# TestLLMClassifierWithService
# =============================================================================


class TestLLMClassifierWithService:
    """Tests for LLMClassifier with mocked LLMServiceProtocol."""

    @pytest.mark.asyncio
    async def test_classify_incident(self):
        """Classify incident input correctly."""
        response = _make_llm_response("incident", "etl_failure")
        mock_llm = _make_mock_llm(response)
        classifier = LLMClassifier(llm_service=mock_llm)

        result = await classifier.classify("ETL Pipeline 跑失敗了")

        assert result.intent_category == ITIntentCategory.INCIDENT
        assert result.sub_intent == "etl_failure"
        assert result.confidence == 0.95
        mock_llm.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_classify_request(self):
        """Classify request input correctly."""
        response = _make_llm_response("request", "account_creation")
        mock_llm = _make_mock_llm(response)
        classifier = LLMClassifier(llm_service=mock_llm)

        result = await classifier.classify("我需要申請一個新帳號")

        assert result.intent_category == ITIntentCategory.REQUEST
        assert result.sub_intent == "account_creation"

    @pytest.mark.asyncio
    async def test_classify_change(self):
        """Classify change input correctly."""
        response = _make_llm_response("change", "release_deployment")
        mock_llm = _make_mock_llm(response)
        classifier = LLMClassifier(llm_service=mock_llm)

        result = await classifier.classify("週五需要部署 v2.5.0 到生產環境")

        assert result.intent_category == ITIntentCategory.CHANGE
        assert result.sub_intent == "release_deployment"

    @pytest.mark.asyncio
    async def test_classify_query(self):
        """Classify query input correctly."""
        response = _make_llm_response("query", "status_inquiry")
        mock_llm = _make_mock_llm(response)
        classifier = LLMClassifier(llm_service=mock_llm)

        result = await classifier.classify("目前生產環境的 CPU 使用率是多少？")

        assert result.intent_category == ITIntentCategory.QUERY
        assert result.sub_intent == "status_inquiry"

    @pytest.mark.asyncio
    async def test_classify_passes_correct_params(self):
        """Verify LLM generate is called with correct parameters."""
        response = _make_llm_response("incident", "etl_failure")
        mock_llm = _make_mock_llm(response)
        classifier = LLMClassifier(
            llm_service=mock_llm, max_tokens=300, temperature=0.1
        )

        await classifier.classify("test input")

        mock_llm.generate.assert_called_once()
        call_kwargs = mock_llm.generate.call_args
        assert call_kwargs.kwargs["max_tokens"] == 300
        assert call_kwargs.kwargs["temperature"] == 0.1

    @pytest.mark.asyncio
    async def test_classify_with_completeness(self):
        """Verify completeness info is extracted from LLM response."""
        data = {
            "intent_category": "incident",
            "sub_intent": "etl_failure",
            "confidence": 0.9,
            "completeness": {
                "score": 0.6,
                "is_complete": False,
                "missing_fields": ["影響範圍", "發生時間"],
                "suggestions": ["請提供影響範圍"],
            },
            "reasoning": "ETL failure detected",
        }
        mock_llm = _make_mock_llm(json.dumps(data))
        classifier = LLMClassifier(llm_service=mock_llm)

        result = await classifier.classify("ETL 失敗了")

        assert not result.completeness.is_complete
        assert "影響範圍" in result.completeness.missing_fields
        assert result.completeness.completeness_score == 0.6


# =============================================================================
# TestLLMClassifierResponseParsing
# =============================================================================


class TestLLMClassifierResponseParsing:
    """Tests for response parsing (markdown-wrapped, malformed, etc.)."""

    @pytest.mark.asyncio
    async def test_parse_markdown_wrapped_json(self):
        """Parse JSON wrapped in markdown code blocks."""
        raw = '```json\n{"intent_category": "incident", "confidence": 0.9, "reasoning": "test"}\n```'
        mock_llm = _make_mock_llm(raw)
        classifier = LLMClassifier(llm_service=mock_llm)

        result = await classifier.classify("test")

        assert result.intent_category == ITIntentCategory.INCIDENT

    @pytest.mark.asyncio
    async def test_parse_plain_json(self):
        """Parse plain JSON response."""
        raw = '{"intent_category": "request", "confidence": 0.85, "reasoning": "test"}'
        mock_llm = _make_mock_llm(raw)
        classifier = LLMClassifier(llm_service=mock_llm)

        result = await classifier.classify("test")

        assert result.intent_category == ITIntentCategory.REQUEST

    @pytest.mark.asyncio
    async def test_parse_malformed_json_with_text(self):
        """Extract intent from text when JSON is malformed."""
        raw = "This is an incident report about a system failure"
        mock_llm = _make_mock_llm(raw)
        classifier = LLMClassifier(llm_service=mock_llm)

        result = await classifier.classify("test")

        assert result.intent_category == ITIntentCategory.INCIDENT

    @pytest.mark.asyncio
    async def test_parse_empty_response(self):
        """Handle empty response gracefully."""
        mock_llm = _make_mock_llm("")
        classifier = LLMClassifier(llm_service=mock_llm)

        result = await classifier.classify("test")

        assert result.intent_category == ITIntentCategory.UNKNOWN


# =============================================================================
# TestLLMClassifierIsAvailable
# =============================================================================


class TestLLMClassifierIsAvailable:
    """Tests for is_available property."""

    def test_is_available_with_service(self):
        """is_available is True when LLM service is provided."""
        mock_llm = MagicMock()
        classifier = LLMClassifier(llm_service=mock_llm)
        assert classifier.is_available is True

    def test_is_not_available_without_service(self):
        """is_available is False when no LLM service."""
        classifier = LLMClassifier(llm_service=None)
        assert classifier.is_available is False


# =============================================================================
# TestLLMClassifierHealthCheck
# =============================================================================


class TestLLMClassifierHealthCheck:
    """Tests for health check."""

    @pytest.mark.asyncio
    async def test_health_check_with_service(self):
        """Health check passes when LLM service responds."""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value="OK")
        classifier = LLMClassifier(llm_service=mock_llm)

        assert await classifier.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_without_service(self):
        """Health check fails when no LLM service."""
        classifier = LLMClassifier(llm_service=None)

        assert await classifier.health_check() is False

    @pytest.mark.asyncio
    async def test_health_check_on_error(self):
        """Health check fails when LLM raises exception."""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(side_effect=Exception("API down"))
        classifier = LLMClassifier(llm_service=mock_llm)

        assert await classifier.health_check() is False
