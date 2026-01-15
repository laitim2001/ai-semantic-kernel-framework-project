"""
LLM Classifier Implementation

Uses Claude Haiku for intent classification with multi-task output.
Provides Layer 3 routing with confidence scoring and completeness assessment.

Sprint 92: Story 92-3 - Implement LLM Classifier
"""

import json
import logging
import re
import time
from typing import Any, Dict, Optional

from ..models import (
    CompletenessInfo,
    ITIntentCategory,
    LLMClassificationResult,
)
from .prompts import get_classification_prompt

logger = logging.getLogger(__name__)


# Flag to track if anthropic is available
_ANTHROPIC_AVAILABLE = False
_AsyncAnthropic = None

try:
    from anthropic import AsyncAnthropic

    _AsyncAnthropic = AsyncAnthropic
    _ANTHROPIC_AVAILABLE = True
    logger.info("Anthropic SDK loaded successfully")
except ImportError:
    logger.warning(
        "anthropic library not installed. "
        "Install with: pip install anthropic"
    )


class LLMClassifier:
    """
    LLM-based Intent Classifier using Claude Haiku.

    Uses Claude's language understanding to classify intents when
    pattern matching and semantic routing are insufficient.

    Attributes:
        model: Claude model to use (default: claude-3-haiku-20240307)
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature (lower = more deterministic)

    Example:
        >>> classifier = LLMClassifier(api_key="...")
        >>> result = await classifier.classify("我需要申請一個新帳號")
        >>> print(result.intent_category)  # ITIntentCategory.REQUEST
    """

    # Default model configuration
    DEFAULT_MODEL = "claude-3-haiku-20240307"
    DEFAULT_MAX_TOKENS = 500
    DEFAULT_TEMPERATURE = 0.0

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        client: Optional[Any] = None,
    ):
        """
        Initialize the LLM Classifier.

        Args:
            api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)
            model: Claude model to use
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            client: Pre-configured AsyncAnthropic client (optional)
        """
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._api_key = api_key
        self._client = client
        self._initialized = False

    @property
    def is_available(self) -> bool:
        """Check if Anthropic SDK is available."""
        return _ANTHROPIC_AVAILABLE

    def _get_client(self) -> Any:
        """
        Get or create the Anthropic client.

        Returns:
            AsyncAnthropic client instance
        """
        if self._client is not None:
            return self._client

        if not _ANTHROPIC_AVAILABLE:
            raise RuntimeError("Anthropic SDK not installed")

        client_kwargs = {}
        if self._api_key:
            client_kwargs["api_key"] = self._api_key

        self._client = _AsyncAnthropic(**client_kwargs)
        return self._client

    async def classify(
        self,
        user_input: str,
        include_completeness: bool = True,
        simplified: bool = False,
    ) -> LLMClassificationResult:
        """
        Classify user input using Claude Haiku.

        Args:
            user_input: The user's input text to classify
            include_completeness: Whether to include completeness assessment
            simplified: Use simplified prompt for faster response

        Returns:
            LLMClassificationResult with classification details

        Raises:
            RuntimeError: If Anthropic SDK is not available
        """
        start_time = time.perf_counter()

        if not _ANTHROPIC_AVAILABLE:
            logger.error("LLM classification unavailable: SDK not installed")
            return LLMClassificationResult(
                intent_category=ITIntentCategory.UNKNOWN,
                confidence=0.0,
                reasoning="LLM classifier unavailable",
            )

        try:
            client = self._get_client()

            # Generate prompt
            prompt = get_classification_prompt(
                user_input=user_input,
                include_completeness=include_completeness,
                simplified=simplified,
            )

            # Call Claude API
            response = await client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ],
            )

            processing_time = (time.perf_counter() - start_time) * 1000

            # Extract response text
            raw_response = response.content[0].text

            # Parse JSON response
            result = self._parse_response(raw_response)

            # Build usage stats
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }

            # Build completeness info
            completeness = CompletenessInfo()
            if "completeness" in result:
                comp_data = result["completeness"]
                completeness = CompletenessInfo(
                    is_complete=comp_data.get("is_complete", True),
                    missing_fields=comp_data.get("missing_fields", []),
                    completeness_score=comp_data.get("score", 1.0),
                    suggestions=comp_data.get("suggestions", []),
                )

            logger.info(
                f"LLM classification completed: {result.get('intent_category')} "
                f"(confidence: {result.get('confidence', 0):.2f}, "
                f"time: {processing_time:.0f}ms)"
            )

            return LLMClassificationResult(
                intent_category=ITIntentCategory.from_string(
                    result.get("intent_category", "unknown")
                ),
                sub_intent=result.get("sub_intent"),
                confidence=result.get("confidence", 0.0),
                completeness=completeness,
                reasoning=result.get("reasoning", ""),
                raw_response=raw_response,
                model=self.model,
                usage=usage,
            )

        except Exception as e:
            processing_time = (time.perf_counter() - start_time) * 1000
            logger.error(f"LLM classification error: {e}")

            return LLMClassificationResult(
                intent_category=ITIntentCategory.UNKNOWN,
                confidence=0.0,
                reasoning=f"Classification failed: {str(e)}",
                usage={"error": True},
            )

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse the JSON response from Claude.

        Handles various response formats including:
        - Pure JSON
        - JSON wrapped in markdown code blocks
        - Partial/malformed JSON

        Args:
            response_text: Raw response text from Claude

        Returns:
            Parsed dictionary with classification results
        """
        # Try to extract JSON from response
        text = response_text.strip()

        # Remove markdown code block markers if present
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]

        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        # Try to parse as JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON object in text
        json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Fallback: extract key information from text
        logger.warning(f"Failed to parse JSON response: {text[:100]}...")
        return self._extract_from_text(text)

    def _extract_from_text(self, text: str) -> Dict[str, Any]:
        """
        Extract classification information from unstructured text.

        Fallback method when JSON parsing fails.

        Args:
            text: Response text to extract from

        Returns:
            Dictionary with extracted information
        """
        result: Dict[str, Any] = {
            "intent_category": "unknown",
            "sub_intent": None,
            "confidence": 0.5,
            "reasoning": "Extracted from unstructured response",
        }

        text_lower = text.lower()

        # Try to detect intent category from keywords
        if "incident" in text_lower or "故障" in text_lower or "問題" in text_lower:
            result["intent_category"] = "incident"
        elif "request" in text_lower or "請求" in text_lower or "申請" in text_lower:
            result["intent_category"] = "request"
        elif "change" in text_lower or "變更" in text_lower or "部署" in text_lower:
            result["intent_category"] = "change"
        elif "query" in text_lower or "查詢" in text_lower or "詢問" in text_lower:
            result["intent_category"] = "query"

        return result

    async def health_check(self) -> bool:
        """
        Check if the classifier is healthy and can make API calls.

        Returns:
            True if healthy, False otherwise
        """
        if not _ANTHROPIC_AVAILABLE:
            return False

        try:
            client = self._get_client()
            # Make a minimal API call
            response = await client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return response is not None
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


class MockLLMClassifier(LLMClassifier):
    """
    Mock LLM Classifier for testing without API calls.

    Uses rule-based classification for deterministic testing.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def is_available(self) -> bool:
        """Mock classifier is always available."""
        return True

    async def classify(
        self,
        user_input: str,
        include_completeness: bool = True,
        simplified: bool = False,
    ) -> LLMClassificationResult:
        """
        Mock classification using keyword matching.

        Args:
            user_input: The user's input text to classify
            include_completeness: Whether to include completeness assessment
            simplified: Use simplified prompt (ignored in mock)

        Returns:
            LLMClassificationResult based on keywords
        """
        start_time = time.perf_counter()
        text_lower = user_input.lower()

        # Default values
        intent_category = ITIntentCategory.UNKNOWN
        sub_intent = None
        confidence = 0.7
        reasoning = "Mock classification based on keywords"

        # Keyword-based classification
        if any(kw in text_lower for kw in ["etl", "失敗", "錯誤", "故障", "掛", "問題", "慢"]):
            intent_category = ITIntentCategory.INCIDENT
            if "etl" in text_lower:
                sub_intent = "etl_failure"
            elif "慢" in text_lower or "效能" in text_lower:
                sub_intent = "performance_degradation"
            elif "網路" in text_lower:
                sub_intent = "network_issue"
            else:
                sub_intent = "general_incident"
            confidence = 0.85

        elif any(kw in text_lower for kw in ["申請", "帳號", "權限", "安裝", "密碼"]):
            intent_category = ITIntentCategory.REQUEST
            if "帳號" in text_lower:
                sub_intent = "account_creation"
            elif "權限" in text_lower:
                sub_intent = "permission_change"
            elif "安裝" in text_lower:
                sub_intent = "software_installation"
            elif "密碼" in text_lower:
                sub_intent = "password_reset"
            else:
                sub_intent = "general_request"
            confidence = 0.85

        elif any(kw in text_lower for kw in ["部署", "變更", "更新", "config", "設定"]):
            intent_category = ITIntentCategory.CHANGE
            if "部署" in text_lower:
                sub_intent = "release_deployment"
            elif "設定" in text_lower or "config" in text_lower:
                sub_intent = "configuration_update"
            else:
                sub_intent = "general_change"
            confidence = 0.80

        elif any(kw in text_lower for kw in ["查詢", "狀態", "報表", "進度", "如何"]):
            intent_category = ITIntentCategory.QUERY
            if "狀態" in text_lower:
                sub_intent = "status_inquiry"
            elif "報表" in text_lower:
                sub_intent = "report_request"
            elif "進度" in text_lower:
                sub_intent = "ticket_status"
            else:
                sub_intent = "general_query"
            confidence = 0.75

        # Build completeness assessment
        completeness = CompletenessInfo(
            is_complete=len(user_input) > 20,
            completeness_score=min(len(user_input) / 50, 1.0),
            missing_fields=[] if len(user_input) > 20 else ["詳細描述"],
            suggestions=[] if len(user_input) > 20 else ["請提供更多細節"],
        )

        processing_time = (time.perf_counter() - start_time) * 1000

        return LLMClassificationResult(
            intent_category=intent_category,
            sub_intent=sub_intent,
            confidence=confidence,
            completeness=completeness,
            reasoning=reasoning,
            raw_response=f"Mock response for: {user_input[:50]}...",
            model="mock-classifier",
            usage={"mock": True, "processing_time_ms": processing_time},
        )

    async def health_check(self) -> bool:
        """Mock classifier is always healthy."""
        return True
