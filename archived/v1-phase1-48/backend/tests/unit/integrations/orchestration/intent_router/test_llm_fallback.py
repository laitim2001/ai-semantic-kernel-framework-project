"""
LLM Classifier Fallback Behavior Tests

Tests graceful degradation when LLM service is unavailable,
throws exceptions, or returns invalid responses.

Sprint 128: Story 128-3
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.integrations.orchestration.intent_router.llm_classifier.classifier import (
    LLMClassifier,
)
from src.integrations.orchestration.intent_router.models import (
    ITIntentCategory,
)


class TestNoLLMService:
    """Tests when no LLM service is provided."""

    @pytest.mark.asyncio
    async def test_no_service_returns_unknown(self):
        """No LLM service → UNKNOWN with zero confidence."""
        classifier = LLMClassifier(llm_service=None)

        result = await classifier.classify("ETL failed")

        assert result.intent_category == ITIntentCategory.UNKNOWN
        assert result.confidence == 0.0
        assert "unavailable" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_no_service_default_constructor(self):
        """Default constructor (no args) → UNKNOWN."""
        classifier = LLMClassifier()

        result = await classifier.classify("test input")

        assert result.intent_category == ITIntentCategory.UNKNOWN

    def test_no_service_is_not_available(self):
        """is_available is False when no service."""
        classifier = LLMClassifier()
        assert classifier.is_available is False


class TestLLMExceptionHandling:
    """Tests when LLM service raises exceptions."""

    @pytest.mark.asyncio
    async def test_llm_exception_returns_unknown(self):
        """LLM exception → UNKNOWN with error reasoning."""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(side_effect=Exception("API rate limit exceeded"))
        classifier = LLMClassifier(llm_service=mock_llm)

        result = await classifier.classify("test")

        assert result.intent_category == ITIntentCategory.UNKNOWN
        assert result.confidence == 0.0
        assert "rate limit" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_llm_timeout_returns_unknown(self):
        """LLM timeout → UNKNOWN with timeout info."""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(side_effect=TimeoutError("Request timed out"))
        classifier = LLMClassifier(llm_service=mock_llm)

        result = await classifier.classify("test")

        assert result.intent_category == ITIntentCategory.UNKNOWN
        assert "timed out" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_llm_connection_error_returns_unknown(self):
        """Connection error → UNKNOWN."""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(side_effect=ConnectionError("Server unreachable"))
        classifier = LLMClassifier(llm_service=mock_llm)

        result = await classifier.classify("test")

        assert result.intent_category == ITIntentCategory.UNKNOWN


class TestInvalidLLMResponse:
    """Tests when LLM returns invalid or unexpected responses."""

    @pytest.mark.asyncio
    async def test_invalid_json_fallback_to_text(self):
        """Invalid JSON → text extraction fallback."""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(
            return_value="This appears to be a service request for a new account"
        )
        classifier = LLMClassifier(llm_service=mock_llm)

        result = await classifier.classify("test")

        assert result.intent_category == ITIntentCategory.REQUEST

    @pytest.mark.asyncio
    async def test_empty_response_returns_unknown(self):
        """Empty LLM response → UNKNOWN."""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value="")
        classifier = LLMClassifier(llm_service=mock_llm)

        result = await classifier.classify("test")

        assert result.intent_category == ITIntentCategory.UNKNOWN

    @pytest.mark.asyncio
    async def test_json_missing_category_returns_unknown(self):
        """JSON without intent_category → UNKNOWN."""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(
            return_value='{"confidence": 0.5, "reasoning": "test"}'
        )
        classifier = LLMClassifier(llm_service=mock_llm)

        result = await classifier.classify("test")

        assert result.intent_category == ITIntentCategory.UNKNOWN

    @pytest.mark.asyncio
    async def test_json_invalid_category_returns_unknown(self):
        """JSON with invalid category string → UNKNOWN."""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(
            return_value='{"intent_category": "nonexistent", "confidence": 0.5}'
        )
        classifier = LLMClassifier(llm_service=mock_llm)

        result = await classifier.classify("test")

        assert result.intent_category == ITIntentCategory.UNKNOWN
