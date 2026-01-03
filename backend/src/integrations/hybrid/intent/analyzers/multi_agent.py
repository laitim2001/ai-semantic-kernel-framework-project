# =============================================================================
# IPA Platform - Multi-Agent Detector
# =============================================================================
# Phase 13: Hybrid Core Architecture
# Sprint 52: Intent Router & Mode Detection
#
# Detects when a task requires multiple agents or agent collaboration.
# Multi-agent scenarios trigger workflow mode for proper orchestration.
#
# Detection Signals:
#   - Explicit multi-agent keywords
#   - Multiple distinct skill domains
#   - Collaboration/handoff indicators
#   - Agent role references
#
# Dependencies:
#   - models.py (MultiAgentSignal)
# =============================================================================

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Pattern, Set

from src.integrations.hybrid.intent.models import (
    Message,
    SessionContext,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Multi-Agent Indicators
# =============================================================================

# Explicit multi-agent keywords
MULTI_AGENT_KEYWORDS: List[str] = [
    # English
    "multiple agents",
    "multi-agent",
    "several agents",
    "team of agents",
    "agent team",
    "agents collaborate",
    "agent collaboration",
    "collaborative agents",
    "coordinated agents",
    "agent coordination",
    "agent handoff",
    "handoff",
    "hand off",
    "pass to another agent",
    "transfer to agent",
    "delegate to",
    "agent specialization",
    "specialized agents",
    "groupchat",
    "group chat",
    "agent conversation",
    "agents discuss",
    "round robin",
    "agent rotation",
    # Chinese
    "多個代理",
    "多代理",
    "多智能體",
    "代理團隊",
    "代理協作",
    "協作代理",
    "代理協調",
    "代理移交",
    "移交",
    "轉交給代理",
    "委派給",
    "專業代理",
    "群組聊天",
    "代理對話",
    "代理討論",
    "輪流",
]

# Keywords indicating distinct skill domains
SKILL_DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "coding": [
        "code", "program", "develop", "implement", "debug", "fix bug",
        "程式", "編程", "開發", "實現", "除錯", "修復",
    ],
    "analysis": [
        "analyze", "evaluate", "assess", "review", "examine", "investigate",
        "分析", "評估", "審查", "檢查", "調查",
    ],
    "design": [
        "design", "architect", "plan", "blueprint", "structure",
        "設計", "架構", "規劃", "藍圖", "結構",
    ],
    "testing": [
        "test", "verify", "validate", "qa", "quality",
        "測試", "驗證", "確認", "品質",
    ],
    "documentation": [
        "document", "write docs", "readme", "manual", "guide",
        "文檔", "文件", "說明", "手冊", "指南",
    ],
    "deployment": [
        "deploy", "release", "publish", "ship", "launch",
        "部署", "發布", "上線", "發行",
    ],
    "research": [
        "research", "explore", "study", "learn about", "find out",
        "研究", "探索", "學習", "了解",
    ],
    "communication": [
        "communicate", "present", "explain to", "report to", "summarize for",
        "溝通", "報告", "解釋", "總結",
    ],
}

# Agent role references
AGENT_ROLE_REFERENCES: List[str] = [
    # English
    "coder", "developer", "programmer",
    "analyst", "researcher",
    "designer", "architect",
    "tester", "qa engineer",
    "writer", "documenter",
    "reviewer", "critic",
    "manager", "coordinator",
    "expert", "specialist",
    # Chinese
    "開發者", "程式員",
    "分析師", "研究員",
    "設計師", "架構師",
    "測試員", "品管",
    "撰寫者", "文檔員",
    "審查者", "評論者",
    "管理者", "協調者",
    "專家", "專員",
]

# Patterns for agent collaboration
COLLABORATION_PATTERNS: List[str] = [
    r"(?:one|first)\s+agent.*(?:another|second|other)\s+agent",
    r"agent\s+\w+\s+(?:then|and)\s+agent\s+\w+",
    r"pass(?:es|ing)?\s+(?:it\s+)?to\s+(?:another|the\s+next)",
    r"(?:work|working)\s+together",
    r"collaborate\s+(?:on|to|with)",
    r"coordinate\s+(?:with|between)",
    r"hand\s*(?:off|over)\s+(?:to|between)",
    r"一個代理.*另一個代理",
    r"代理\s*\w+\s*(?:然後|接著)\s*代理",
    r"傳給(?:下一個|另一個)",
    r"一起(?:工作|合作)",
    r"協調(?:與|之間)",
]


@dataclass
class MultiAgentSignal:
    """
    Result of multi-agent detection analysis.

    Attributes:
        requires_multi_agent: Whether multi-agent execution is needed
        confidence: Confidence score (0.0-1.0)
        detected_domains: Set of skill domains detected
        agent_count_estimate: Estimated number of agents needed
        collaboration_type: Type of collaboration detected
        reasoning: Explanation of the detection result
        indicators_found: List of specific indicators that triggered detection
    """
    requires_multi_agent: bool = False
    confidence: float = 0.0
    detected_domains: Set[str] = field(default_factory=set)
    agent_count_estimate: int = 1
    collaboration_type: Optional[str] = None
    reasoning: str = ""
    indicators_found: List[str] = field(default_factory=list)


class MultiAgentDetector:
    """
    Detects when a task requires multiple agents or collaboration.

    Uses keyword matching, skill domain detection, and pattern recognition
    to identify tasks that need multi-agent orchestration.

    Detection Strategy:
        1. Check for explicit multi-agent keywords
        2. Count distinct skill domains mentioned
        3. Look for agent role references
        4. Match collaboration patterns
        5. Combine signals with weighted scoring

    Thresholds:
        - 2+ skill domains: Suggests multi-agent
        - 3+ skill domains: Strong multi-agent signal
        - Explicit keywords: High confidence indicator
        - Role references: Moderate indicator

    Example:
        >>> detector = MultiAgentDetector()
        >>> signal = await detector.detect("First the coder writes, then tester validates")
        >>> print(f"Multi-agent: {signal.requires_multi_agent}, Agents: {signal.agent_count_estimate}")
    """

    def __init__(
        self,
        domain_threshold: int = 2,
        keyword_weight: float = 0.4,
        domain_weight: float = 0.3,
        role_weight: float = 0.15,
        pattern_weight: float = 0.15,
    ):
        """
        Initialize the multi-agent detector.

        Args:
            domain_threshold: Minimum skill domains to suggest multi-agent
            keyword_weight: Weight for explicit keyword signals (0.0-1.0)
            domain_weight: Weight for skill domain signals (0.0-1.0)
            role_weight: Weight for agent role signals (0.0-1.0)
            pattern_weight: Weight for collaboration pattern signals (0.0-1.0)
        """
        self.domain_threshold = domain_threshold

        # Normalize weights
        total = keyword_weight + domain_weight + role_weight + pattern_weight
        self.keyword_weight = keyword_weight / total
        self.domain_weight = domain_weight / total
        self.role_weight = role_weight / total
        self.pattern_weight = pattern_weight / total

        # Build keyword sets
        self.multi_agent_keywords = {kw.lower() for kw in MULTI_AGENT_KEYWORDS}
        self.agent_roles = {role.lower() for role in AGENT_ROLE_REFERENCES}

        # Build domain keyword sets
        self.domain_keywords: Dict[str, Set[str]] = {}
        for domain, keywords in SKILL_DOMAIN_KEYWORDS.items():
            self.domain_keywords[domain] = {kw.lower() for kw in keywords}

        # Compile patterns
        self.collaboration_patterns: List[Pattern] = [
            re.compile(p, re.IGNORECASE) for p in COLLABORATION_PATTERNS
        ]

        logger.debug("MultiAgentDetector initialized")

    async def detect(
        self,
        input_text: str,
        context: Optional[SessionContext] = None,
        history: Optional[List[Message]] = None,
    ) -> MultiAgentSignal:
        """
        Detect if input requires multi-agent execution.

        Args:
            input_text: The user's input text to analyze
            context: Optional session context
            history: Optional conversation history

        Returns:
            MultiAgentSignal with detection results
        """
        if not input_text or not input_text.strip():
            return MultiAgentSignal(
                requires_multi_agent=False,
                confidence=0.0,
                reasoning="Empty input has no multi-agent signals",
            )

        text_lower = input_text.lower()
        indicators_found: List[str] = []

        # Detect explicit multi-agent keywords
        keyword_score, keyword_matches = self._detect_keywords(text_lower)
        if keyword_matches:
            indicators_found.extend([f"keyword:{kw}" for kw in keyword_matches])

        # Detect skill domains
        domain_score, detected_domains = self._detect_domains(text_lower)
        if detected_domains:
            indicators_found.extend([f"domain:{d}" for d in detected_domains])

        # Detect agent roles
        role_score, role_matches = self._detect_roles(text_lower)
        if role_matches:
            indicators_found.extend([f"role:{r}" for r in role_matches])

        # Detect collaboration patterns
        pattern_score, pattern_matches = self._detect_patterns(input_text)
        if pattern_matches:
            indicators_found.extend([f"pattern:{p}" for p in pattern_matches])

        # Calculate weighted confidence
        confidence = (
            keyword_score * self.keyword_weight +
            domain_score * self.domain_weight +
            role_score * self.role_weight +
            pattern_score * self.pattern_weight
        )

        # Clamp to [0, 1]
        confidence = min(1.0, max(0.0, confidence))

        # Determine if multi-agent is needed
        # Include pattern matches since explicit collaboration patterns indicate multi-agent needs
        requires_multi_agent = (
            confidence >= 0.5 or
            len(detected_domains) >= self.domain_threshold or
            len(keyword_matches) >= 1 or
            len(pattern_matches) >= 1  # Collaboration patterns indicate multi-agent
        )

        # Estimate agent count
        agent_count = self._estimate_agent_count(
            detected_domains, role_matches, keyword_matches
        )

        # Determine collaboration type
        collaboration_type = self._determine_collaboration_type(
            keyword_matches, pattern_matches, detected_domains
        )

        # Build reasoning
        reasoning = self._build_reasoning(
            keyword_matches, detected_domains, role_matches, pattern_matches
        )

        return MultiAgentSignal(
            requires_multi_agent=requires_multi_agent,
            confidence=confidence,
            detected_domains=detected_domains,
            agent_count_estimate=agent_count,
            collaboration_type=collaboration_type,
            reasoning=reasoning,
            indicators_found=indicators_found,
        )

    def _detect_keywords(self, text_lower: str) -> tuple[float, List[str]]:
        """
        Detect explicit multi-agent keywords.

        Returns:
            Tuple of (score, list of matched keywords)
        """
        matches = [
            kw for kw in self.multi_agent_keywords
            if kw in text_lower
        ]

        # Score: 1 match = 0.7, 2+ matches = 1.0
        if len(matches) >= 2:
            score = 1.0
        elif len(matches) == 1:
            score = 0.7
        else:
            score = 0.0

        return score, matches

    def _detect_domains(self, text_lower: str) -> tuple[float, Set[str]]:
        """
        Detect distinct skill domains.

        Returns:
            Tuple of (score, set of detected domains)
        """
        detected: Set[str] = set()

        for domain, keywords in self.domain_keywords.items():
            for kw in keywords:
                if kw in text_lower:
                    detected.add(domain)
                    break  # Only count each domain once

        # Score: 1 domain = 0.2, 2 domains = 0.5, 3+ domains = 1.0
        domain_count = len(detected)
        if domain_count >= 3:
            score = 1.0
        elif domain_count == 2:
            score = 0.5
        elif domain_count == 1:
            score = 0.2
        else:
            score = 0.0

        return score, detected

    def _detect_roles(self, text_lower: str) -> tuple[float, List[str]]:
        """
        Detect agent role references.

        Returns:
            Tuple of (score, list of matched roles)
        """
        matches = [
            role for role in self.agent_roles
            if role in text_lower
        ]

        # Deduplicate similar roles
        unique_matches = list(set(matches))

        # Score: 1 role = 0.3, 2 roles = 0.6, 3+ roles = 1.0
        if len(unique_matches) >= 3:
            score = 1.0
        elif len(unique_matches) == 2:
            score = 0.6
        elif len(unique_matches) == 1:
            score = 0.3
        else:
            score = 0.0

        return score, unique_matches

    def _detect_patterns(self, text: str) -> tuple[float, List[str]]:
        """
        Detect collaboration patterns.

        Returns:
            Tuple of (score, list of matched pattern descriptions)
        """
        matches = []

        for pattern in self.collaboration_patterns:
            match = pattern.search(text)
            if match:
                matches.append(match.group(0)[:30])  # Truncate long matches

        # Score: 1 pattern = 0.6, 2+ patterns = 1.0
        if len(matches) >= 2:
            score = 1.0
        elif len(matches) == 1:
            score = 0.6
        else:
            score = 0.0

        return score, matches

    def _estimate_agent_count(
        self,
        domains: Set[str],
        roles: List[str],
        keywords: List[str],
    ) -> int:
        """
        Estimate the number of agents needed.

        Args:
            domains: Detected skill domains
            roles: Detected agent roles
            keywords: Detected multi-agent keywords

        Returns:
            Estimated agent count (minimum 1)
        """
        # Base estimate on domains
        base_count = max(1, len(domains))

        # Adjust based on explicit role mentions
        if len(roles) >= 3:
            base_count = max(base_count, 3)
        elif len(roles) == 2:
            base_count = max(base_count, 2)

        # Check for explicit team size in keywords
        for kw in keywords:
            if "team" in kw or "multiple" in kw or "several" in kw:
                base_count = max(base_count, 2)
            if "group" in kw:
                base_count = max(base_count, 3)

        return base_count

    def _determine_collaboration_type(
        self,
        keywords: List[str],
        patterns: List[str],
        domains: Set[str],
    ) -> Optional[str]:
        """
        Determine the type of collaboration needed.

        Returns:
            Collaboration type string or None
        """
        keywords_str = " ".join(keywords).lower()
        patterns_str = " ".join(patterns).lower()

        # Check for specific collaboration types
        if "handoff" in keywords_str or "hand off" in keywords_str or "移交" in keywords_str:
            return "handoff"
        if "groupchat" in keywords_str or "group chat" in keywords_str or "群組" in keywords_str:
            return "groupchat"
        if "round robin" in keywords_str or "rotation" in keywords_str or "輪流" in keywords_str:
            return "round_robin"
        if "collaborate" in keywords_str or "協作" in keywords_str:
            return "collaboration"
        if "coordinate" in keywords_str or "協調" in keywords_str:
            return "coordination"

        # Infer from patterns
        if "work together" in patterns_str or "一起" in patterns_str:
            return "collaboration"
        if "pass" in patterns_str or "hand" in patterns_str:
            return "handoff"

        # Infer from domain count
        if len(domains) >= 3:
            return "multi_specialist"
        elif len(domains) == 2:
            return "dual_agent"

        return None

    def _build_reasoning(
        self,
        keywords: List[str],
        domains: Set[str],
        roles: List[str],
        patterns: List[str],
    ) -> str:
        """
        Build reasoning explanation.

        Returns:
            Human-readable reasoning string
        """
        parts = []

        if keywords:
            parts.append(f"multi-agent keywords: {', '.join(keywords[:3])}")
        if domains:
            parts.append(f"skill domains: {', '.join(sorted(domains))}")
        if roles:
            parts.append(f"agent roles: {', '.join(roles[:3])}")
        if patterns:
            parts.append(f"collaboration patterns found")

        if not parts:
            return "No multi-agent signals detected"

        return "; ".join(parts)

    def get_supported_domains(self) -> List[str]:
        """Get list of supported skill domains."""
        return list(self.domain_keywords.keys())

    def add_domain(self, domain: str, keywords: List[str]) -> None:
        """
        Add a custom skill domain.

        Args:
            domain: Domain name
            keywords: List of keywords for this domain
        """
        self.domain_keywords[domain] = {kw.lower() for kw in keywords}
        logger.debug(f"Added domain {domain} with {len(keywords)} keywords")

    def add_keyword(self, keyword: str) -> None:
        """Add a custom multi-agent keyword."""
        self.multi_agent_keywords.add(keyword.lower())
        logger.debug(f"Added multi-agent keyword: {keyword}")
