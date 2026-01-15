"""
Unit Tests for LLM Classifier

Tests for LLMClassifier and classification prompts.

Sprint 92: Story 92-5 - Semantic/LLM Unit Tests
"""

import json
import pytest
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.orchestration.intent_router.models import (
    CompletenessInfo,
    ITIntentCategory,
    LLMClassificationResult,
)
from src.integrations.orchestration.intent_router.llm_classifier import (
    LLMClassifier,
    CLASSIFICATION_PROMPT,
)
from src.integrations.orchestration.intent_router.llm_classifier.classifier import (
    MockLLMClassifier,
)
from src.integrations.orchestration.intent_router.llm_classifier.prompts import (
    get_classification_prompt,
    get_completeness_prompt,
    get_required_fields,
    get_sub_intent_examples,
    SIMPLE_CLASSIFICATION_PROMPT,
)


# =============================================================================
# LLMClassificationResult Model Tests
# =============================================================================

class TestLLMClassificationResult:
    """Tests for LLMClassificationResult dataclass."""

    def test_create_basic_result(self):
        """Test creating a basic classification result."""
        result = LLMClassificationResult(
            intent_category=ITIntentCategory.INCIDENT,
            sub_intent="etl_failure",
            confidence=0.92,
            reasoning="User reported ETL job failure",
        )

        assert result.intent_category == ITIntentCategory.INCIDENT
        assert result.sub_intent == "etl_failure"
        assert result.confidence == 0.92
        assert "ETL" in result.reasoning

    def test_result_with_completeness(self):
        """Test result with completeness information."""
        completeness = CompletenessInfo(
            is_complete=False,
            missing_fields=["影響範圍", "發生時間"],
            completeness_score=0.6,
            suggestions=["請提供影響範圍", "請說明何時開始發生"],
        )

        result = LLMClassificationResult(
            intent_category=ITIntentCategory.INCIDENT,
            confidence=0.85,
            completeness=completeness,
        )

        assert result.completeness.is_complete is False
        assert len(result.completeness.missing_fields) == 2
        assert result.completeness.completeness_score == 0.6

    def test_confidence_validation_valid(self):
        """Test valid confidence scores."""
        for score in [0.0, 0.5, 1.0]:
            result = LLMClassificationResult(
                intent_category=ITIntentCategory.QUERY,
                confidence=score,
            )
            assert result.confidence == score

    def test_confidence_validation_invalid(self):
        """Test invalid confidence scores raise ValueError."""
        with pytest.raises(ValueError, match="confidence must be between"):
            LLMClassificationResult(
                intent_category=ITIntentCategory.QUERY,
                confidence=1.5,
            )

    def test_to_dict(self):
        """Test conversion to dictionary."""
        completeness = CompletenessInfo(
            is_complete=True,
            completeness_score=0.9,
        )

        result = LLMClassificationResult(
            intent_category=ITIntentCategory.REQUEST,
            sub_intent="account_creation",
            confidence=0.88,
            completeness=completeness,
            reasoning="Account request detected",
            model="claude-3-haiku",
            usage={"input_tokens": 100, "output_tokens": 50},
        )

        result_dict = result.to_dict()

        assert result_dict["intent_category"] == "request"
        assert result_dict["sub_intent"] == "account_creation"
        assert result_dict["confidence"] == 0.88
        assert result_dict["completeness"]["is_complete"] is True
        assert result_dict["model"] == "claude-3-haiku"

    def test_from_pattern_fallback(self):
        """Test creating from pattern match result."""
        from src.integrations.orchestration.intent_router.models import PatternMatchResult

        pattern_result = PatternMatchResult(
            matched=True,
            intent_category=ITIntentCategory.CHANGE,
            sub_intent="deployment",
            confidence=0.95,
            matched_pattern="部署.*版本",
        )

        llm_result = LLMClassificationResult.from_pattern_fallback(pattern_result)

        assert llm_result.intent_category == ITIntentCategory.CHANGE
        assert llm_result.sub_intent == "deployment"
        assert llm_result.confidence == 0.95
        assert "pattern match" in llm_result.reasoning.lower()


# =============================================================================
# Prompt Tests
# =============================================================================

class TestPrompts:
    """Tests for classification prompts."""

    def test_classification_prompt_has_all_categories(self):
        """Test that classification prompt mentions all categories."""
        assert "incident" in CLASSIFICATION_PROMPT.lower()
        assert "request" in CLASSIFICATION_PROMPT.lower()
        assert "change" in CLASSIFICATION_PROMPT.lower()
        assert "query" in CLASSIFICATION_PROMPT.lower()

    def test_classification_prompt_has_json_format(self):
        """Test that prompt specifies JSON output format."""
        assert "json" in CLASSIFICATION_PROMPT.lower()
        assert "intent_category" in CLASSIFICATION_PROMPT
        assert "confidence" in CLASSIFICATION_PROMPT

    def test_get_classification_prompt(self):
        """Test generating classification prompt."""
        user_input = "ETL 失敗了"
        prompt = get_classification_prompt(user_input)

        assert user_input in prompt
        assert "intent_category" in prompt

    def test_get_classification_prompt_simplified(self):
        """Test simplified prompt generation."""
        user_input = "測試輸入"
        prompt = get_classification_prompt(user_input, simplified=True)

        assert user_input in prompt
        # Simplified prompt should be shorter
        assert len(prompt) < len(get_classification_prompt(user_input))

    def test_get_completeness_prompt(self):
        """Test completeness prompt generation."""
        prompt = get_completeness_prompt("ETL 失敗", "incident")

        assert "incident" in prompt
        assert "ETL 失敗" in prompt

    def test_get_required_fields(self):
        """Test getting required fields for each category."""
        incident_fields = get_required_fields("incident")
        assert len(incident_fields) >= 2

        request_fields = get_required_fields("request")
        assert len(request_fields) >= 2

        change_fields = get_required_fields("change")
        assert len(change_fields) >= 2

        query_fields = get_required_fields("query")
        assert len(query_fields) >= 1

    def test_get_sub_intent_examples(self):
        """Test getting sub-intent examples."""
        incident_examples = get_sub_intent_examples("incident")
        assert "etl_failure" in incident_examples

        request_examples = get_sub_intent_examples("request")
        assert "account_creation" in request_examples


# =============================================================================
# MockLLMClassifier Tests
# =============================================================================

class TestMockLLMClassifier:
    """Tests for MockLLMClassifier."""

    @pytest.fixture
    def mock_classifier(self):
        """Create a mock classifier."""
        return MockLLMClassifier()

    @pytest.mark.asyncio
    async def test_is_available(self, mock_classifier):
        """Test mock classifier is always available."""
        assert mock_classifier.is_available is True

    @pytest.mark.asyncio
    async def test_classify_incident_etl(self, mock_classifier):
        """Test classifying ETL incident."""
        result = await mock_classifier.classify("ETL 今天跑失敗了")

        assert result.intent_category == ITIntentCategory.INCIDENT
        assert "etl" in result.sub_intent.lower()
        assert result.confidence > 0.7

    @pytest.mark.asyncio
    async def test_classify_incident_performance(self, mock_classifier):
        """Test classifying performance incident."""
        result = await mock_classifier.classify("系統跑得很慢")

        assert result.intent_category == ITIntentCategory.INCIDENT
        assert "performance" in result.sub_intent.lower()

    @pytest.mark.asyncio
    async def test_classify_request_account(self, mock_classifier):
        """Test classifying account request."""
        result = await mock_classifier.classify("我需要申請新帳號")

        assert result.intent_category == ITIntentCategory.REQUEST
        assert "account" in result.sub_intent.lower()

    @pytest.mark.asyncio
    async def test_classify_request_permission(self, mock_classifier):
        """Test classifying permission request."""
        result = await mock_classifier.classify("請幫我開通權限")

        assert result.intent_category == ITIntentCategory.REQUEST
        assert "permission" in result.sub_intent.lower()

    @pytest.mark.asyncio
    async def test_classify_change_deployment(self, mock_classifier):
        """Test classifying deployment change."""
        result = await mock_classifier.classify("需要部署新版本")

        assert result.intent_category == ITIntentCategory.CHANGE
        assert "deployment" in result.sub_intent.lower()

    @pytest.mark.asyncio
    async def test_classify_query_status(self, mock_classifier):
        """Test classifying status query."""
        result = await mock_classifier.classify("目前系統狀態如何")

        assert result.intent_category == ITIntentCategory.QUERY
        assert "status" in result.sub_intent.lower()

    @pytest.mark.asyncio
    async def test_classify_completeness_assessment(self, mock_classifier):
        """Test completeness assessment."""
        # Short input should be marked incomplete
        result = await mock_classifier.classify("問題")
        assert result.completeness.is_complete is False
        assert result.completeness.completeness_score < 1.0

        # Longer input should have higher completeness
        result = await mock_classifier.classify(
            "ETL 任務在今天早上 8 點開始失敗，影響所有報表系統"
        )
        assert result.completeness.completeness_score > 0.5

    @pytest.mark.asyncio
    async def test_classify_unknown_input(self, mock_classifier):
        """Test classifying unrelated input."""
        result = await mock_classifier.classify("今天天氣很好")

        # May classify as UNKNOWN or match some keyword
        assert isinstance(result.intent_category, ITIntentCategory)
        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_health_check(self, mock_classifier):
        """Test health check."""
        is_healthy = await mock_classifier.health_check()
        assert is_healthy is True


# =============================================================================
# LLMClassifier Tests (with Mocked API)
# =============================================================================

class TestLLMClassifier:
    """Tests for LLMClassifier class."""

    def test_init_default_values(self):
        """Test initialization with default values."""
        classifier = LLMClassifier()

        assert classifier.model == LLMClassifier.DEFAULT_MODEL
        assert classifier.max_tokens == LLMClassifier.DEFAULT_MAX_TOKENS
        assert classifier.temperature == LLMClassifier.DEFAULT_TEMPERATURE

    def test_init_custom_values(self):
        """Test initialization with custom values."""
        classifier = LLMClassifier(
            model="claude-3-sonnet",
            max_tokens=1000,
            temperature=0.5,
        )

        assert classifier.model == "claude-3-sonnet"
        assert classifier.max_tokens == 1000
        assert classifier.temperature == 0.5

    def test_parse_response_valid_json(self):
        """Test parsing valid JSON response."""
        classifier = LLMClassifier()

        response = json.dumps({
            "intent_category": "incident",
            "sub_intent": "etl_failure",
            "confidence": 0.9,
            "reasoning": "ETL failure detected",
        })

        result = classifier._parse_response(response)

        assert result["intent_category"] == "incident"
        assert result["confidence"] == 0.9

    def test_parse_response_json_with_markdown(self):
        """Test parsing JSON wrapped in markdown code block."""
        classifier = LLMClassifier()

        response = """```json
{
  "intent_category": "request",
  "confidence": 0.85
}
```"""

        result = classifier._parse_response(response)
        assert result["intent_category"] == "request"

    def test_parse_response_invalid_json(self):
        """Test parsing invalid JSON falls back to text extraction."""
        classifier = LLMClassifier()

        response = "The intent is clearly an incident related to system failure"

        result = classifier._parse_response(response)

        # Should extract something or return unknown
        assert "intent_category" in result

    def test_extract_from_text_incident(self):
        """Test extracting intent from text - incident."""
        classifier = LLMClassifier()

        result = classifier._extract_from_text("這是一個系統故障問題")
        assert result["intent_category"] == "incident"

    def test_extract_from_text_request(self):
        """Test extracting intent from text - request."""
        classifier = LLMClassifier()

        result = classifier._extract_from_text("用戶申請了新帳號")
        assert result["intent_category"] == "request"


# =============================================================================
# Integration Tests (with Mock Client)
# =============================================================================

class TestLLMClassifierIntegration:
    """Integration tests with mocked Anthropic client."""

    @pytest.fixture
    def mock_response(self):
        """Create a mock API response."""
        response = MagicMock()
        response.content = [MagicMock()]
        response.content[0].text = json.dumps({
            "intent_category": "incident",
            "sub_intent": "system_down",
            "confidence": 0.92,
            "completeness": {
                "score": 0.8,
                "is_complete": True,
                "missing_fields": [],
                "suggestions": [],
            },
            "reasoning": "System unavailability reported",
        })
        response.usage = MagicMock()
        response.usage.input_tokens = 150
        response.usage.output_tokens = 80
        return response

    @pytest.mark.asyncio
    async def test_classify_with_mock_client(self, mock_response):
        """Test classification with mocked client."""
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        classifier = LLMClassifier(client=mock_client)

        result = await classifier.classify("系統掛掉了")

        assert result.intent_category == ITIntentCategory.INCIDENT
        assert result.sub_intent == "system_down"
        assert result.confidence == 0.92
        assert result.completeness.is_complete is True

    @pytest.mark.asyncio
    async def test_classify_handles_api_error(self):
        """Test graceful handling of API errors."""
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            side_effect=Exception("API Error")
        )

        classifier = LLMClassifier(client=mock_client)

        result = await classifier.classify("測試輸入")

        # Should return UNKNOWN with error info
        assert result.intent_category == ITIntentCategory.UNKNOWN
        assert result.confidence == 0.0
        assert "failed" in result.reasoning.lower()


# =============================================================================
# Performance Tests
# =============================================================================

class TestLLMClassifierPerformance:
    """Performance tests for LLM Classifier."""

    @pytest.fixture
    def mock_classifier(self):
        """Create a mock classifier for performance testing."""
        return MockLLMClassifier()

    @pytest.mark.asyncio
    async def test_classify_latency(self, mock_classifier):
        """Test classification latency."""
        import time

        test_inputs = [
            "ETL 失敗了",
            "申請帳號",
            "部署新版本",
            "查詢狀態",
        ]

        for input_text in test_inputs:
            start = time.perf_counter()
            await mock_classifier.classify(input_text)
            elapsed_ms = (time.perf_counter() - start) * 1000

            # Mock classifier should be very fast
            assert elapsed_ms < 100, f"Classification took {elapsed_ms:.2f}ms"

    @pytest.mark.asyncio
    async def test_batch_classification(self, mock_classifier):
        """Test batch classification performance."""
        import time

        test_inputs = [
            "系統故障", "申請權限", "更新配置", "查報表",
            "網路問題", "安裝軟體", "部署更新", "檢查狀態",
        ] * 5  # 40 inputs

        start = time.perf_counter()
        results = []
        for input_text in test_inputs:
            result = await mock_classifier.classify(input_text)
            results.append(result)

        total_ms = (time.perf_counter() - start) * 1000

        assert len(results) == 40
        avg_ms = total_ms / len(results)
        assert avg_ms < 50, f"Average classification time {avg_ms:.2f}ms exceeds 50ms"


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestLLMClassifierErrorHandling:
    """Tests for error handling in LLM Classifier."""

    def test_parse_empty_response(self):
        """Test parsing empty response."""
        classifier = LLMClassifier()

        result = classifier._parse_response("")
        assert result["intent_category"] == "unknown"

    def test_parse_null_json_values(self):
        """Test parsing JSON with null values."""
        classifier = LLMClassifier()

        response = json.dumps({
            "intent_category": "incident",
            "sub_intent": None,
            "confidence": 0.8,
        })

        result = classifier._parse_response(response)
        assert result["intent_category"] == "incident"
        assert result["sub_intent"] is None

    def test_parse_partial_json(self):
        """Test parsing partial/truncated JSON."""
        classifier = LLMClassifier()

        # Truncated JSON
        response = '{"intent_category": "request", "confidence": 0.'

        result = classifier._parse_response(response)
        # Should handle gracefully
        assert "intent_category" in result
