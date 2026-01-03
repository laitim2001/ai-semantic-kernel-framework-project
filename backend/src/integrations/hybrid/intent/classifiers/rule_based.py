# =============================================================================
# IPA Platform - Rule-Based Intent Classifier
# =============================================================================
# Phase 13: Hybrid Core Architecture
# Sprint 52: Intent Router & Mode Detection
#
# Rule-based classifier using keyword patterns and heuristics.
# Fast and deterministic, runs before LLM-based classification.
#
# Keywords are organized by language (English + Traditional Chinese)
# to support the primary target markets (Taiwan/Hong Kong).
#
# Dependencies:
#   - base.py (BaseClassifier)
#   - models.py (ClassificationResult, ExecutionMode)
# =============================================================================

import logging
import re
from typing import Dict, List, Optional, Pattern, Set

from src.integrations.hybrid.intent.classifiers.base import BaseClassifier
from src.integrations.hybrid.intent.models import (
    ClassificationResult,
    ExecutionMode,
    Message,
    SessionContext,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Keyword Patterns (English + Traditional Chinese)
# =============================================================================

# Keywords strongly indicating workflow/multi-step execution
WORKFLOW_KEYWORDS: List[str] = [
    # English workflow indicators
    "workflow",
    "pipeline",
    "multi-step",
    "automate",
    "automation",
    "orchestrate",
    "orchestration",
    "schedule",
    "batch",
    "process",
    "execute",
    "run task",
    "create task",
    "start workflow",
    # Multi-agent indicators
    "multiple agents",
    "multi-agent",
    "agent collaboration",
    "agent handoff",
    "handoff",
    "group chat",
    "groupchat",
    "team of agents",
    # Chinese workflow indicators (Traditional)
    "工作流程",
    "流程",
    "步驟",
    "自動化",
    "排程",
    "批次",
    "執行任務",
    "建立任務",
    "多個 agent",
    "多代理",
    "代理協作",
    "代理移交",
    "群組聊天",
]

# Keywords strongly indicating simple chat/Q&A
CHAT_KEYWORDS: List[str] = [
    # English chat indicators
    "explain",
    "describe",
    "what is",
    "what are",
    "why",
    "how does",
    "tell me about",
    "help me understand",
    "can you explain",
    "definition of",
    "meaning of",
    "summarize",
    "summary",
    "analyze this",
    "review",
    "feedback",
    "opinion",
    "suggest",
    "advice",
    "recommend",
    # Chinese chat indicators (Traditional)
    "解釋",
    "說明",
    "什麼是",
    "為什麼",
    "怎麼",
    "幫我理解",
    "定義",
    "意思",
    "總結",
    "摘要",
    "分析",
    "建議",
    "推薦",
    "意見",
    "評論",
]

# Keywords that might indicate hybrid mode (both chat and workflow elements)
HYBRID_INDICATORS: List[str] = [
    # English hybrid indicators
    "first explain then",
    "after understanding",
    "once you understand",
    "then execute",
    "then run",
    "step by step guide then",
    # Chinese hybrid indicators
    "先解釋再",
    "理解後",
    "了解之後",
    "然後執行",
    "逐步指導然後",
]

# Phrase patterns that strongly indicate workflow mode
WORKFLOW_PHRASE_PATTERNS: List[str] = [
    r"create\s+(?:a\s+)?(?:new\s+)?workflow",
    r"set\s+up\s+(?:a\s+)?(?:new\s+)?automation",
    r"schedule\s+(?:a\s+)?(?:new\s+)?task",
    r"run\s+(?:the\s+)?pipeline",
    r"execute\s+(?:the\s+)?(?:following\s+)?steps",
    r"coordinate\s+(?:multiple\s+)?agents",
    r"hand\s*off\s+to\s+(?:another\s+)?agent",
    r"建立(?:新的)?(?:工作)?流程",
    r"設定(?:新的)?自動化",
    r"排程(?:新的)?任務",
    r"執行(?:以下)?步驟",
    r"協調(?:多個)?代理",
]

# Phrase patterns that strongly indicate chat mode
CHAT_PHRASE_PATTERNS: List[str] = [
    r"what\s+(?:is|are)\s+(?:the\s+)?",
    r"can\s+you\s+(?:explain|describe|tell)",
    r"help\s+me\s+understand",
    r"I\s+(?:don't|do\s+not)\s+understand",
    r"please\s+(?:explain|clarify)",
    r"什麼是",
    r"請(?:解釋|說明)",
    r"幫我(?:理解|了解)",
    r"我不(?:理解|了解|懂)",
]


class RuleBasedClassifier(BaseClassifier):
    """
    Rule-based intent classifier using keyword patterns.

    Uses keyword matching and regex patterns to quickly classify user intent
    without requiring LLM calls. Suitable as a fast first-pass classifier.

    Attributes:
        workflow_keywords: Set of keywords indicating workflow mode
        chat_keywords: Set of keywords indicating chat mode
        workflow_patterns: Compiled regex patterns for workflow detection
        chat_patterns: Compiled regex patterns for chat detection

    Example:
        >>> classifier = RuleBasedClassifier()
        >>> result = await classifier.classify("Create a new workflow")
        >>> print(result.mode)  # ExecutionMode.WORKFLOW_MODE
    """

    def __init__(
        self,
        name: str = "rule_based",
        weight: float = 1.0,
        enabled: bool = True,
        custom_workflow_keywords: Optional[List[str]] = None,
        custom_chat_keywords: Optional[List[str]] = None,
    ):
        """
        Initialize the rule-based classifier.

        Args:
            name: Classifier name for identification
            weight: Weight for voting (0.0 to 1.0)
            enabled: Whether classifier is enabled
            custom_workflow_keywords: Additional workflow keywords
            custom_chat_keywords: Additional chat keywords
        """
        super().__init__(name=name, weight=weight, enabled=enabled)

        # Build keyword sets (lowercase for case-insensitive matching)
        self.workflow_keywords: Set[str] = {
            kw.lower() for kw in WORKFLOW_KEYWORDS
        }
        self.chat_keywords: Set[str] = {kw.lower() for kw in CHAT_KEYWORDS}
        self.hybrid_keywords: Set[str] = {kw.lower() for kw in HYBRID_INDICATORS}

        # Add custom keywords if provided
        if custom_workflow_keywords:
            self.workflow_keywords.update(kw.lower() for kw in custom_workflow_keywords)
        if custom_chat_keywords:
            self.chat_keywords.update(kw.lower() for kw in custom_chat_keywords)

        # Compile regex patterns
        self.workflow_patterns: List[Pattern] = [
            re.compile(pattern, re.IGNORECASE) for pattern in WORKFLOW_PHRASE_PATTERNS
        ]
        self.chat_patterns: List[Pattern] = [
            re.compile(pattern, re.IGNORECASE) for pattern in CHAT_PHRASE_PATTERNS
        ]

        logger.debug(
            f"RuleBasedClassifier initialized with "
            f"{len(self.workflow_keywords)} workflow keywords, "
            f"{len(self.chat_keywords)} chat keywords"
        )

    async def classify(
        self,
        input_text: str,
        context: Optional[SessionContext] = None,
        history: Optional[List[Message]] = None,
    ) -> ClassificationResult:
        """
        Classify user input using rule-based pattern matching.

        Args:
            input_text: The user's input text to analyze
            context: Optional session context
            history: Optional conversation history

        Returns:
            ClassificationResult with detected mode and confidence
        """
        if not input_text or not input_text.strip():
            return ClassificationResult(
                mode=ExecutionMode.CHAT_MODE,
                confidence=0.5,
                reasoning="Empty input defaults to chat mode",
                classifier_name=self.name,
            )

        text_lower = input_text.lower()

        # Count keyword matches
        workflow_matches = self._count_keyword_matches(text_lower, self.workflow_keywords)
        chat_matches = self._count_keyword_matches(text_lower, self.chat_keywords)
        hybrid_matches = self._count_keyword_matches(text_lower, self.hybrid_keywords)

        # Check phrase patterns
        workflow_pattern_matches = self._count_pattern_matches(input_text, self.workflow_patterns)
        chat_pattern_matches = self._count_pattern_matches(input_text, self.chat_patterns)

        # Combine scores (patterns weigh more than keywords)
        workflow_score = workflow_matches + (workflow_pattern_matches * 2)
        chat_score = chat_matches + (chat_pattern_matches * 2)
        hybrid_score = hybrid_matches * 2  # Hybrid indicators are strong signals

        # Consider context
        context_boost = self._get_context_boost(context)

        # Build metadata for debugging
        metadata: Dict = {
            "workflow_keyword_matches": workflow_matches,
            "chat_keyword_matches": chat_matches,
            "hybrid_keyword_matches": hybrid_matches,
            "workflow_pattern_matches": workflow_pattern_matches,
            "chat_pattern_matches": chat_pattern_matches,
            "workflow_score": workflow_score,
            "chat_score": chat_score,
            "hybrid_score": hybrid_score,
            "context_boost": context_boost,
        }

        # Determine mode based on scores
        if hybrid_score > 0 and workflow_score > 0 and chat_score > 0:
            # Clear hybrid indication
            mode = ExecutionMode.HYBRID_MODE
            confidence = min(0.85, 0.6 + (hybrid_score * 0.1))
            reasoning = (
                f"Hybrid indicators detected: {hybrid_score} hybrid matches, "
                f"{workflow_score} workflow signals, {chat_score} chat signals"
            )
        elif workflow_score > chat_score:
            mode = ExecutionMode.WORKFLOW_MODE
            # Apply context boost if currently in workflow
            if context_boost == "workflow":
                workflow_score += 2
            confidence = self._calculate_confidence(workflow_score, chat_score)
            reasoning = (
                f"Workflow mode detected: {workflow_score} workflow signals "
                f"vs {chat_score} chat signals"
            )
        elif chat_score > workflow_score:
            mode = ExecutionMode.CHAT_MODE
            # Apply context boost if currently in chat
            if context_boost == "chat":
                chat_score += 1
            confidence = self._calculate_confidence(chat_score, workflow_score)
            reasoning = (
                f"Chat mode detected: {chat_score} chat signals "
                f"vs {workflow_score} workflow signals"
            )
        else:
            # Tie or no matches - default to chat
            mode = ExecutionMode.CHAT_MODE
            confidence = 0.5
            reasoning = "No clear indicators, defaulting to chat mode"

        return ClassificationResult(
            mode=mode,
            confidence=confidence,
            reasoning=reasoning,
            classifier_name=self.name,
            metadata=metadata,
        )

    def _count_keyword_matches(self, text: str, keywords: Set[str]) -> int:
        """Count how many keywords appear in the text."""
        count = 0
        for keyword in keywords:
            if keyword in text:
                count += 1
        return count

    def _count_pattern_matches(self, text: str, patterns: List[Pattern]) -> int:
        """Count how many regex patterns match the text."""
        count = 0
        for pattern in patterns:
            if pattern.search(text):
                count += 1
        return count

    def _calculate_confidence(self, winner_score: int, loser_score: int) -> float:
        """
        Calculate confidence based on score difference.

        Args:
            winner_score: Score of the winning mode
            loser_score: Score of the losing mode

        Returns:
            Confidence value between 0.5 and 0.95
        """
        if winner_score == 0:
            return 0.5

        diff = winner_score - loser_score
        total = winner_score + loser_score

        # Base confidence from score difference
        if diff >= 5:
            confidence = 0.95
        elif diff >= 3:
            confidence = 0.85
        elif diff >= 2:
            confidence = 0.75
        elif diff >= 1:
            confidence = 0.65
        else:
            confidence = 0.55

        # Adjust based on total signals (more signals = more confident)
        if total >= 5:
            confidence = min(0.95, confidence + 0.05)

        return confidence

    def _get_context_boost(self, context: Optional[SessionContext]) -> Optional[str]:
        """
        Determine context-based boost for mode detection.

        Args:
            context: Session context

        Returns:
            "workflow", "chat", or None based on context
        """
        if not context:
            return None

        if context.workflow_active and context.pending_steps > 0:
            return "workflow"
        elif context.current_mode == ExecutionMode.CHAT_MODE:
            return "chat"

        return None

    def add_workflow_keyword(self, keyword: str) -> None:
        """Add a custom workflow keyword."""
        self.workflow_keywords.add(keyword.lower())
        logger.debug(f"Added workflow keyword: {keyword}")

    def add_chat_keyword(self, keyword: str) -> None:
        """Add a custom chat keyword."""
        self.chat_keywords.add(keyword.lower())
        logger.debug(f"Added chat keyword: {keyword}")

    def get_keyword_stats(self) -> Dict[str, int]:
        """Get statistics about loaded keywords."""
        return {
            "workflow_keywords": len(self.workflow_keywords),
            "chat_keywords": len(self.chat_keywords),
            "hybrid_keywords": len(self.hybrid_keywords),
            "workflow_patterns": len(self.workflow_patterns),
            "chat_patterns": len(self.chat_patterns),
        }
