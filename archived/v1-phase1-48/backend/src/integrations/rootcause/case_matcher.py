"""
Case Matcher — 案例匹配引擎

Sprint 130 — Story 130-2: RootCause 真實案例庫

提供:
- CaseMatcher: 案例匹配 (文字相似度 + 類別匹配 + 可選 LLM 語義匹配)
- MatchResult: 匹配結果 (案例 + 分數明細)

設計:
- 多維度匹配: keyword overlap + category + severity + LLM (optional)
- 加權綜合評分
- 結果排序和過濾
"""

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..correlation.types import Event, EventSeverity
from .case_repository import CaseRepository
from .types import HistoricalCase

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Match Configuration
# ---------------------------------------------------------------------------

# Scoring weights
WEIGHT_TEXT_SIMILARITY = 0.45
WEIGHT_CATEGORY_MATCH = 0.25
WEIGHT_SEVERITY_MATCH = 0.15
WEIGHT_RECENCY = 0.15

# Minimum similarity threshold
MIN_SIMILARITY_THRESHOLD = 0.2

# Stop words for keyword extraction
_STOP_WORDS = frozenset({
    "the", "a", "an", "is", "was", "are", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "can", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "during",
    "before", "after", "above", "below", "between", "out", "off", "over",
    "under", "again", "then", "once", "here", "there", "when", "where",
    "why", "how", "all", "both", "each", "few", "more", "most", "other",
    "some", "such", "no", "nor", "not", "only", "own", "same", "so",
    "than", "too", "very", "and", "but", "or", "if", "while", "because",
    "until", "about", "this", "that", "it", "its",
})

# Category inference keywords
_CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "database": [
        "database", "sql", "connection pool", "query", "deadlock",
        "postgres", "mysql", "redis", "mongodb", "table", "migration",
        "schema", "index", "transaction",
    ],
    "network": [
        "network", "dns", "timeout", "latency", "bandwidth",
        "firewall", "proxy", "load balancer", "ssl", "tls",
        "tcp", "http", "socket", "connection",
    ],
    "application": [
        "memory", "cpu", "thread", "process", "crash", "exception",
        "error", "bug", "code", "heap", "stack", "garbage collection",
        "leak", "performance", "slow", "hang",
    ],
    "infrastructure": [
        "kubernetes", "docker", "container", "pod", "node",
        "disk", "storage", "volume", "cluster", "server",
        "vm", "instance", "cloud", "aws", "azure", "gcp",
    ],
    "security": [
        "certificate", "auth", "token", "jwt", "oauth",
        "permission", "access", "encryption", "key", "rotation",
        "vulnerability", "patch",
    ],
    "deployment": [
        "deploy", "rollback", "release", "pipeline", "ci", "cd",
        "helm", "terraform", "configuration", "config",
        "version", "upgrade", "migration",
    ],
    "messaging": [
        "queue", "message", "rabbitmq", "kafka", "consumer",
        "producer", "broker", "lag", "offset", "topic",
    ],
    "data": [
        "etl", "pipeline", "batch", "spark", "data",
        "partition", "skew", "processing", "ingestion",
    ],
    "observability": [
        "log", "metric", "trace", "monitoring", "alert",
        "dashboard", "prometheus", "grafana", "elasticsearch",
    ],
}


# ---------------------------------------------------------------------------
# MatchResult
# ---------------------------------------------------------------------------


@dataclass
class MatchResult:
    """Detailed match result with score breakdown."""

    case: HistoricalCase
    total_score: float
    text_similarity: float
    category_match: float
    severity_match: float
    recency_score: float
    matched_keywords: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# CaseMatcher
# ---------------------------------------------------------------------------


class CaseMatcher:
    """
    案例匹配引擎

    使用多維度匹配找出與事件最相似的歷史案例:
    1. 文字相似度 (keyword overlap / TF-IDF style) — 45%
    2. 類別匹配 (event category vs case category) — 25%
    3. 嚴重度匹配 (severity alignment) — 15%
    4. 時間近因性 (more recent cases score higher) — 15%
    5. (可選) LLM 語義匹配 — overrides text similarity when available
    """

    def __init__(
        self,
        case_repository: CaseRepository,
        llm_service: Optional[Any] = None,
    ):
        self._repository = case_repository
        self._llm_service = llm_service

    async def find_similar_cases(
        self,
        event: Event,
        max_results: int = 10,
        min_similarity: float = MIN_SIMILARITY_THRESHOLD,
    ) -> List[HistoricalCase]:
        """
        Find historical cases most similar to the given event.

        Args:
            event: The target event to match against.
            max_results: Maximum number of results.
            min_similarity: Minimum score threshold.

        Returns:
            List of HistoricalCase with similarity_score set, sorted by relevance.
        """
        # Get all cases from repository
        all_cases = await self._repository.get_all_cases()
        if not all_cases:
            return []

        # Calculate match scores
        match_results: List[MatchResult] = []
        event_text = f"{event.title} {event.description}"
        event_category = self._infer_category(event_text)

        for case in all_cases:
            result = self._score_case(event, case, event_text, event_category)
            if result.total_score >= min_similarity:
                match_results.append(result)

        # Optional: LLM semantic re-ranking for top candidates
        if self._llm_service and match_results:
            match_results = await self._llm_rerank(event, match_results[:20])

        # Sort by total score descending
        match_results.sort(key=lambda r: r.total_score, reverse=True)

        # Convert to HistoricalCase with similarity_score set
        results: List[HistoricalCase] = []
        for mr in match_results[:max_results]:
            case = HistoricalCase(
                case_id=mr.case.case_id,
                title=mr.case.title,
                description=mr.case.description,
                root_cause=mr.case.root_cause,
                resolution=mr.case.resolution,
                occurred_at=mr.case.occurred_at,
                resolved_at=mr.case.resolved_at,
                similarity_score=round(mr.total_score, 4),
                lessons_learned=mr.case.lessons_learned,
            )
            results.append(case)

        return results

    async def find_similar_cases_detailed(
        self,
        event: Event,
        max_results: int = 10,
        min_similarity: float = MIN_SIMILARITY_THRESHOLD,
    ) -> List[MatchResult]:
        """
        Find similar cases with detailed match breakdown.

        Returns MatchResult objects with score components.
        """
        all_cases = await self._repository.get_all_cases()
        if not all_cases:
            return []

        event_text = f"{event.title} {event.description}"
        event_category = self._infer_category(event_text)

        results: List[MatchResult] = []
        for case in all_cases:
            result = self._score_case(event, case, event_text, event_category)
            if result.total_score >= min_similarity:
                results.append(result)

        results.sort(key=lambda r: r.total_score, reverse=True)
        return results[:max_results]

    # ------------------------------------------------------------------
    # Scoring Methods
    # ------------------------------------------------------------------

    def _score_case(
        self,
        event: Event,
        case: HistoricalCase,
        event_text: str,
        event_category: Optional[str],
    ) -> MatchResult:
        """Score a single case against the event."""
        # 1. Text similarity
        case_text = f"{case.title} {case.description} {case.root_cause}"
        text_sim, matched_kw = self._text_similarity(event_text, case_text)

        # 2. Category match
        case_category = self._infer_category(case_text)
        cat_match = self._category_match_score(event_category, case_category)

        # 3. Severity match
        sev_match = self._severity_match_score(event, case)

        # 4. Recency score
        recency = self._recency_score(case)

        # Weighted total
        total = (
            text_sim * WEIGHT_TEXT_SIMILARITY
            + cat_match * WEIGHT_CATEGORY_MATCH
            + sev_match * WEIGHT_SEVERITY_MATCH
            + recency * WEIGHT_RECENCY
        )

        return MatchResult(
            case=case,
            total_score=round(min(1.0, total), 4),
            text_similarity=round(text_sim, 4),
            category_match=round(cat_match, 4),
            severity_match=round(sev_match, 4),
            recency_score=round(recency, 4),
            matched_keywords=matched_kw,
        )

    def _text_similarity(
        self, text1: str, text2: str
    ) -> Tuple[float, List[str]]:
        """
        Calculate keyword-based text similarity.

        Uses token overlap with TF-IDF-like weighting:
        - Common words (appear in many cases) get lower weight
        - Specific technical terms get higher weight

        Returns:
            Tuple of (similarity_score, list_of_matched_keywords)
        """
        tokens1 = _tokenize(text1)
        tokens2 = _tokenize(text2)

        if not tokens1 or not tokens2:
            return 0.0, []

        # Count term frequencies
        tf1 = Counter(tokens1)
        tf2 = Counter(tokens2)

        # Find matching terms
        common = set(tf1.keys()) & set(tf2.keys())
        if not common:
            return 0.0, []

        # Weighted overlap (longer/rarer terms count more)
        weighted_match = sum(
            min(tf1[t], tf2[t]) * len(t) / 5.0 for t in common
        )
        weighted_total = sum(
            tf1[t] * len(t) / 5.0 for t in tf1
        ) + sum(
            tf2[t] * len(t) / 5.0 for t in tf2
        )

        if weighted_total == 0:
            return 0.0, []

        # Dice coefficient variant
        similarity = 2.0 * weighted_match / weighted_total
        similarity = min(1.0, similarity)

        matched_kw = sorted(common, key=lambda t: len(t), reverse=True)[:10]
        return similarity, matched_kw

    def _category_match_score(
        self,
        event_category: Optional[str],
        case_category: Optional[str],
    ) -> float:
        """Score category alignment (1.0 = exact match, 0.5 = related, 0.0 = different)."""
        if not event_category or not case_category:
            return 0.3  # Neutral when category unknown

        if event_category == case_category:
            return 1.0

        # Related categories get partial credit
        related_pairs = {
            frozenset({"database", "application"}),
            frozenset({"network", "infrastructure"}),
            frozenset({"security", "application"}),
            frozenset({"deployment", "infrastructure"}),
            frozenset({"messaging", "application"}),
            frozenset({"data", "database"}),
            frozenset({"observability", "infrastructure"}),
        }

        if frozenset({event_category, case_category}) in related_pairs:
            return 0.5

        return 0.0

    def _severity_match_score(
        self, event: Event, case: HistoricalCase
    ) -> float:
        """Score severity alignment between event and case."""
        sev_order = {
            "info": 0,
            "warning": 1,
            "error": 2,
            "critical": 3,
        }

        event_level = sev_order.get(event.severity.value, 1)

        # Infer case severity from seed data
        case_sev = _infer_case_severity(case)
        case_level = sev_order.get(case_sev, 1)

        diff = abs(event_level - case_level)
        if diff == 0:
            return 1.0
        elif diff == 1:
            return 0.6
        elif diff == 2:
            return 0.3
        return 0.1

    def _recency_score(self, case: HistoricalCase) -> float:
        """Score case recency (more recent = higher score)."""
        if not case.occurred_at:
            return 0.5

        days_ago = (datetime.utcnow() - case.occurred_at).days
        if days_ago <= 30:
            return 1.0
        elif days_ago <= 90:
            return 0.8
        elif days_ago <= 180:
            return 0.6
        elif days_ago <= 365:
            return 0.4
        return 0.2

    def _infer_category(self, text: str) -> Optional[str]:
        """Infer category from text using keyword matching."""
        text_lower = text.lower()
        scores: Dict[str, int] = {}

        for category, keywords in _CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[category] = score

        if not scores:
            return None
        return max(scores, key=scores.get)

    # ------------------------------------------------------------------
    # LLM Semantic Re-ranking (Optional)
    # ------------------------------------------------------------------

    async def _llm_rerank(
        self,
        event: Event,
        match_results: List[MatchResult],
    ) -> List[MatchResult]:
        """
        Use LLM to re-rank top match candidates.

        Falls back to original ranking if LLM is unavailable or fails.
        """
        if not self._llm_service:
            return match_results

        try:
            prompt = self._build_rerank_prompt(event, match_results)
            response = await self._llm_service.generate(
                prompt=prompt,
                max_tokens=500,
                temperature=0.1,
            )
            return self._parse_rerank_response(response, match_results)
        except Exception as e:
            logger.warning(f"LLM re-ranking failed, using keyword scores: {e}")
            return match_results

    def _build_rerank_prompt(
        self,
        event: Event,
        match_results: List[MatchResult],
    ) -> str:
        """Build prompt for LLM re-ranking."""
        cases_text = "\n".join(
            f"{i+1}. [{mr.case.case_id}] {mr.case.title} — {mr.case.root_cause[:100]}"
            for i, mr in enumerate(match_results[:10])
        )

        return (
            f"Given this incident:\n"
            f"Title: {event.title}\n"
            f"Description: {event.description}\n\n"
            f"Rank these historical cases by relevance (most relevant first):\n"
            f"{cases_text}\n\n"
            f"Return ONLY the case IDs in order, one per line."
        )

    def _parse_rerank_response(
        self,
        response: str,
        match_results: List[MatchResult],
    ) -> List[MatchResult]:
        """Parse LLM re-ranking response and reorder results."""
        case_map = {mr.case.case_id: mr for mr in match_results}
        reranked: List[MatchResult] = []

        for line in response.strip().split("\n"):
            line = line.strip()
            # Extract case ID from various formats
            for case_id in case_map:
                if case_id in line:
                    mr = case_map.pop(case_id)
                    # Boost score slightly based on LLM rank
                    boost = max(0.0, 0.1 * (1.0 - len(reranked) / 10.0))
                    mr = MatchResult(
                        case=mr.case,
                        total_score=min(1.0, mr.total_score + boost),
                        text_similarity=mr.text_similarity,
                        category_match=mr.category_match,
                        severity_match=mr.severity_match,
                        recency_score=mr.recency_score,
                        matched_keywords=mr.matched_keywords,
                    )
                    reranked.append(mr)
                    break

        # Add remaining unranked cases
        for mr in case_map.values():
            reranked.append(mr)

        return reranked


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _tokenize(text: str) -> List[str]:
    """Tokenize text into meaningful words."""
    # Split on non-alphanumeric characters
    tokens = re.findall(r"[a-zA-Z]{3,}", text.lower())
    return [t for t in tokens if t not in _STOP_WORDS]


def _infer_case_severity(case: HistoricalCase) -> str:
    """Infer severity from case content."""
    from .case_repository import _SEED_CASES

    for seed in _SEED_CASES:
        if seed["case_id"] == case.case_id:
            return seed.get("severity", "warning")

    # Heuristic from description
    desc = case.description.lower()
    if any(w in desc for w in ["100%", "complete", "outage", "all services"]):
        return "critical"
    if any(w in desc for w in ["degradation", "slow", "intermittent"]):
        return "error"
    return "warning"


from datetime import datetime
