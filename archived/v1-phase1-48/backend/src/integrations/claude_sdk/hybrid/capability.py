"""Capability matching for Hybrid Orchestrator.

Sprint 50: S50-3 - Hybrid Orchestrator (12 pts)

This module provides capability analysis and framework matching
for intelligent task routing between Microsoft Agent Framework
and Claude Agent SDK.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .types import TaskAnalysis, TaskCapability


@dataclass
class CapabilityScore:
    """Score for a specific capability match."""

    capability: TaskCapability
    score: float = 0.0
    matched_keywords: List[str] = field(default_factory=list)
    context_relevance: float = 1.0


class CapabilityMatcher:
    """Analyzes task prompts to identify required capabilities.

    Uses keyword matching and context analysis to determine
    which capabilities are needed for a given task.
    """

    # Keywords that indicate specific capabilities
    CAPABILITY_KEYWORDS: Dict[TaskCapability, List[str]] = {
        TaskCapability.MULTI_AGENT: [
            "agents",
            "team",
            "collaborate",
            "multiple agents",
            "agent group",
            "multi-agent",
            "coordination",
            "swarm",
            "ensemble",
        ],
        TaskCapability.HANDOFF: [
            "handoff",
            "transfer",
            "delegate",
            "pass to",
            "hand over",
            "escalate",
            "forward to",
            "route to",
        ],
        TaskCapability.FILE_OPERATIONS: [
            "file",
            "read",
            "write",
            "edit",
            "save",
            "create file",
            "modify file",
            "delete file",
            "open file",
            "directory",
            "folder",
        ],
        TaskCapability.CODE_EXECUTION: [
            "run",
            "execute",
            "code",
            "script",
            "python",
            "javascript",
            "shell",
            "command",
            "terminal",
            "compile",
            "interpret",
        ],
        TaskCapability.WEB_SEARCH: [
            "search",
            "browse",
            "web",
            "internet",
            "find online",
            "google",
            "lookup",
            "website",
            "url",
            "http",
        ],
        TaskCapability.DATABASE_ACCESS: [
            "database",
            "sql",
            "query",
            "data",
            "table",
            "record",
            "insert",
            "update",
            "select",
            "mongodb",
            "postgres",
            "redis",
        ],
        TaskCapability.PLANNING: [
            "plan",
            "schedule",
            "organize",
            "task breakdown",
            "roadmap",
            "strategy",
            "milestone",
            "timeline",
            "prioritize",
        ],
        TaskCapability.CONVERSATION: [
            "chat",
            "conversation",
            "discuss",
            "talk",
            "respond",
            "answer",
            "explain",
            "clarify",
            "dialogue",
        ],
        TaskCapability.API_INTEGRATION: [
            "api",
            "rest",
            "graphql",
            "endpoint",
            "request",
            "response",
            "webhook",
            "integration",
            "service",
        ],
        TaskCapability.DOCUMENT_PROCESSING: [
            "document",
            "pdf",
            "word",
            "excel",
            "parse",
            "extract",
            "analyze document",
            "report",
            "spreadsheet",
        ],
    }

    # Framework capabilities mapping
    FRAMEWORK_CAPABILITIES: Dict[str, Set[TaskCapability]] = {
        "microsoft_agent_framework": {
            TaskCapability.MULTI_AGENT,
            TaskCapability.HANDOFF,
            TaskCapability.PLANNING,
            TaskCapability.API_INTEGRATION,
        },
        "claude_sdk": {
            TaskCapability.FILE_OPERATIONS,
            TaskCapability.CODE_EXECUTION,
            TaskCapability.WEB_SEARCH,
            TaskCapability.CONVERSATION,
            TaskCapability.DOCUMENT_PROCESSING,
        },
        "both": {
            TaskCapability.DATABASE_ACCESS,
        },
    }

    # Complexity indicators
    COMPLEXITY_INDICATORS: Dict[str, float] = {
        "complex": 0.2,
        "advanced": 0.2,
        "sophisticated": 0.2,
        "multi-step": 0.15,
        "comprehensive": 0.15,
        "detailed": 0.1,
        "thorough": 0.1,
        "simple": -0.2,
        "basic": -0.15,
        "quick": -0.1,
        "straightforward": -0.1,
    }

    def __init__(
        self,
        *,
        case_sensitive: bool = False,
        min_keyword_length: int = 2,
        context_window: int = 50,
    ):
        """Initialize the capability matcher.

        Args:
            case_sensitive: Whether keyword matching is case-sensitive.
            min_keyword_length: Minimum keyword length to consider.
            context_window: Characters around match for context analysis.
        """
        self._case_sensitive = case_sensitive
        self._min_keyword_length = min_keyword_length
        self._context_window = context_window

        # Pre-compile regex patterns for efficiency
        self._keyword_patterns: Dict[TaskCapability, List[re.Pattern]] = {}
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Pre-compile regex patterns for all keywords."""
        flags = 0 if self._case_sensitive else re.IGNORECASE

        for capability, keywords in self.CAPABILITY_KEYWORDS.items():
            patterns = []
            for keyword in keywords:
                if len(keyword) >= self._min_keyword_length:
                    # Word boundary matching
                    pattern = re.compile(rf"\b{re.escape(keyword)}\b", flags)
                    patterns.append(pattern)
            self._keyword_patterns[capability] = patterns

    def analyze(self, prompt: str) -> TaskAnalysis:
        """Analyze a task prompt and identify required capabilities.

        Args:
            prompt: The task description or prompt to analyze.

        Returns:
            TaskAnalysis with identified capabilities and recommendations.
        """
        if not prompt or not prompt.strip():
            return TaskAnalysis()

        # Normalize prompt
        normalized = prompt.strip()

        # Analyze capabilities
        capability_scores = self._score_capabilities(normalized)

        # Filter to significant capabilities
        threshold = 0.3
        significant_capabilities = {
            score.capability
            for score in capability_scores.values()
            if score.score >= threshold
        }

        # Build matched keywords dict
        matched_keywords: Dict[TaskCapability, List[str]] = {}
        for cap, score in capability_scores.items():
            if score.matched_keywords:
                matched_keywords[cap] = score.matched_keywords

        # Calculate complexity
        complexity = self._calculate_complexity(normalized, significant_capabilities)

        # Determine recommended framework
        recommended, confidence = self.match_framework(significant_capabilities)

        return TaskAnalysis(
            capabilities=significant_capabilities,
            complexity=complexity,
            recommended_framework=recommended,
            confidence=confidence,
            matched_keywords=matched_keywords,
        )

    def _score_capabilities(
        self, text: str
    ) -> Dict[TaskCapability, CapabilityScore]:
        """Score each capability based on keyword matches.

        Args:
            text: The text to analyze.

        Returns:
            Dictionary mapping capabilities to their scores.
        """
        scores: Dict[TaskCapability, CapabilityScore] = {}

        for capability, patterns in self._keyword_patterns.items():
            matched = []
            total_score = 0.0

            for pattern in patterns:
                matches = pattern.findall(text)
                if matches:
                    # Each match contributes to score
                    for match in matches:
                        matched.append(match)
                        # Base score per match
                        match_score = 0.3
                        # Longer keywords are more specific
                        if len(match) > 5:
                            match_score += 0.1
                        if len(match) > 10:
                            match_score += 0.1
                        total_score += match_score

            # Normalize score (cap at 1.0)
            normalized_score = min(1.0, total_score)

            scores[capability] = CapabilityScore(
                capability=capability,
                score=normalized_score,
                matched_keywords=matched,
            )

        return scores

    def _calculate_complexity(
        self, text: str, capabilities: Set[TaskCapability]
    ) -> float:
        """Calculate task complexity score.

        Args:
            text: The task text.
            capabilities: Identified capabilities.

        Returns:
            Complexity score from 0.0 to 1.0.
        """
        complexity = 0.3  # Base complexity

        # More capabilities = more complex
        capability_factor = len(capabilities) * 0.1
        complexity += min(0.3, capability_factor)

        # Check complexity indicators
        text_lower = text.lower()
        for indicator, score in self.COMPLEXITY_INDICATORS.items():
            if indicator in text_lower:
                complexity += score

        # Length factor (longer = potentially more complex)
        if len(text) > 500:
            complexity += 0.1
        if len(text) > 1000:
            complexity += 0.1

        # Clamp to valid range
        return max(0.0, min(1.0, complexity))

    def match_framework(
        self, capabilities: Set[TaskCapability]
    ) -> Tuple[str, float]:
        """Match capabilities to the best framework.

        Args:
            capabilities: Set of required capabilities.

        Returns:
            Tuple of (framework_name, confidence_score).
        """
        if not capabilities:
            return ("claude_sdk", 0.5)  # Default to Claude SDK

        ms_caps = self.FRAMEWORK_CAPABILITIES["microsoft_agent_framework"]
        claude_caps = self.FRAMEWORK_CAPABILITIES["claude_sdk"]
        both_caps = self.FRAMEWORK_CAPABILITIES["both"]

        # Count matches for each framework
        ms_matches = len(capabilities & ms_caps)
        claude_matches = len(capabilities & claude_caps)
        both_matches = len(capabilities & both_caps)

        # Calculate total possible matches
        total_caps = len(capabilities)

        # Determine winner
        if ms_matches > claude_matches:
            framework = "microsoft_agent_framework"
            match_count = ms_matches + both_matches
        elif claude_matches > ms_matches:
            framework = "claude_sdk"
            match_count = claude_matches + both_matches
        elif ms_matches == claude_matches and ms_matches > 0:
            # Tie - check for multi-agent (strong MS indicator)
            if TaskCapability.MULTI_AGENT in capabilities:
                framework = "microsoft_agent_framework"
                match_count = ms_matches + both_matches
            else:
                # Default to Claude SDK for ties
                framework = "claude_sdk"
                match_count = claude_matches + both_matches
        else:
            # No strong matches - default to Claude SDK
            framework = "claude_sdk"
            match_count = both_matches

        # Calculate confidence
        if total_caps > 0:
            confidence = min(0.95, 0.5 + (match_count / total_caps) * 0.4)
        else:
            confidence = 0.5

        return (framework, confidence)

    def get_capability_for_keyword(
        self, keyword: str
    ) -> Optional[TaskCapability]:
        """Find which capability a keyword belongs to.

        Args:
            keyword: The keyword to look up.

        Returns:
            The capability if found, None otherwise.
        """
        keyword_lower = keyword.lower() if not self._case_sensitive else keyword

        for capability, keywords in self.CAPABILITY_KEYWORDS.items():
            for kw in keywords:
                kw_check = kw.lower() if not self._case_sensitive else kw
                if kw_check == keyword_lower:
                    return capability

        return None

    def get_keywords_for_capability(
        self, capability: TaskCapability
    ) -> List[str]:
        """Get all keywords for a specific capability.

        Args:
            capability: The capability to get keywords for.

        Returns:
            List of keywords for this capability.
        """
        return list(self.CAPABILITY_KEYWORDS.get(capability, []))

    def add_custom_keyword(
        self, capability: TaskCapability, keyword: str
    ) -> None:
        """Add a custom keyword for a capability.

        Args:
            capability: The capability to add keyword for.
            keyword: The keyword to add.
        """
        if capability not in self.CAPABILITY_KEYWORDS:
            self.CAPABILITY_KEYWORDS[capability] = []

        if keyword not in self.CAPABILITY_KEYWORDS[capability]:
            self.CAPABILITY_KEYWORDS[capability].append(keyword)
            # Recompile patterns
            self._compile_patterns()


def create_matcher(
    *,
    case_sensitive: bool = False,
    min_keyword_length: int = 2,
) -> CapabilityMatcher:
    """Factory function to create a CapabilityMatcher.

    Args:
        case_sensitive: Whether matching is case-sensitive.
        min_keyword_length: Minimum keyword length.

    Returns:
        Configured CapabilityMatcher instance.
    """
    return CapabilityMatcher(
        case_sensitive=case_sensitive,
        min_keyword_length=min_keyword_length,
    )
