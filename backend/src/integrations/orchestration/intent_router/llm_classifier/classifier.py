"""
LLM Classifier Implementation

Uses LLMServiceProtocol for intent classification with multi-task output.
Provides Layer 3 routing with confidence scoring and completeness assessment.

Sprint 92: Story 92-3 - Implement LLM Classifier
Sprint 128: Story 128-1 - Migrate from anthropic SDK to LLMServiceProtocol
"""

import json
import logging
import re
import time
from typing import Any, Dict, Optional, TYPE_CHECKING

from ..models import (
    CompletenessInfo,
    ITIntentCategory,
    LLMClassificationResult,
)
from .prompts import get_classification_prompt

if TYPE_CHECKING:
    from src.integrations.llm import LLMServiceProtocol
    from .cache import ClassificationCache

logger = logging.getLogger(__name__)


# Default model configuration
DEFAULT_MAX_TOKENS = 500
DEFAULT_TEMPERATURE = 0.0


class LLMClassifier:
    """
    LLM-based Intent Classifier using LLMServiceProtocol.

    Uses the platform's LLM service abstraction for intent classification,
    supporting Azure OpenAI, Claude, and mock implementations via the
    LLMServiceProtocol interface.

    When llm_service is None, returns UNKNOWN for all classifications
    (graceful degradation).

    Attributes:
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature (lower = more deterministic)

    Example:
        >>> from src.integrations.llm import LLMServiceFactory
        >>> llm_service = LLMServiceFactory.create()
        >>> classifier = LLMClassifier(llm_service=llm_service)
        >>> result = await classifier.classify("我需要申請一個新帳號")
        >>> print(result.intent_category)  # ITIntentCategory.REQUEST
    """

    def __init__(
        self,
        llm_service: Optional["LLMServiceProtocol"] = None,
        classification_cache: Optional["ClassificationCache"] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
    ):
        """
        Initialize the LLM Classifier.

        Args:
            llm_service: LLMServiceProtocol implementation for LLM calls.
                         If None, classifier returns UNKNOWN for all inputs.
            classification_cache: Optional cache for classification results.
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
        """
        self._llm_service = llm_service
        self._cache = classification_cache
        self.max_tokens = max_tokens
        self.temperature = temperature

    @property
    def is_available(self) -> bool:
        """Check if LLM service is available."""
        return self._llm_service is not None

    async def classify(
        self,
        user_input: str,
        include_completeness: bool = True,
        simplified: bool = False,
    ) -> LLMClassificationResult:
        """
        Classify user input using the LLM service.

        Args:
            user_input: The user's input text to classify
            include_completeness: Whether to include completeness assessment
            simplified: Use simplified prompt for faster response

        Returns:
            LLMClassificationResult with classification details
        """
        start_time = time.perf_counter()

        # Graceful degradation: no LLM service → UNKNOWN
        if self._llm_service is None:
            logger.warning("LLM classification unavailable: no LLM service configured")
            return LLMClassificationResult(
                intent_category=ITIntentCategory.UNKNOWN,
                confidence=0.0,
                reasoning="LLM classifier unavailable: no service configured",
            )

        # Check cache first
        if self._cache is not None:
            cached = await self._cache.get(user_input, include_completeness, simplified)
            if cached is not None:
                processing_time = (time.perf_counter() - start_time) * 1000
                logger.info(
                    f"LLM classification from cache: {cached.intent_category.value} "
                    f"(time: {processing_time:.0f}ms)"
                )
                return cached

        try:
            # Generate prompt
            prompt = get_classification_prompt(
                user_input=user_input,
                include_completeness=include_completeness,
                simplified=simplified,
            )

            # Call LLM service
            raw_response = await self._llm_service.generate(
                prompt=prompt,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )

            processing_time = (time.perf_counter() - start_time) * 1000

            # Parse JSON response
            result = self._parse_response(raw_response)

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

            classification_result = LLMClassificationResult(
                intent_category=ITIntentCategory.from_string(
                    result.get("intent_category", "unknown")
                ),
                sub_intent=result.get("sub_intent"),
                confidence=result.get("confidence", 0.0),
                completeness=completeness,
                reasoning=result.get("reasoning", ""),
                raw_response=raw_response,
                model=getattr(self._llm_service, "model", ""),
                usage={},
            )

            # Cache the result
            if self._cache is not None:
                await self._cache.set(
                    user_input, include_completeness, simplified, classification_result
                )

            return classification_result

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
        Parse the JSON response from the LLM.

        Handles various response formats including:
        - Pure JSON
        - JSON wrapped in markdown code blocks
        - Partial/malformed JSON

        Args:
            response_text: Raw response text from LLM

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
        Check if the classifier is healthy and can make LLM calls.

        Returns:
            True if healthy, False otherwise
        """
        if self._llm_service is None:
            return False

        try:
            response = await self._llm_service.generate(
                prompt="Hi",
                max_tokens=10,
                temperature=0.0,
            )
            return response is not None and len(response) > 0
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
