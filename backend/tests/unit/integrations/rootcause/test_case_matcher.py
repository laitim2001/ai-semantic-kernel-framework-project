"""Unit tests for CaseMatcher — historical case matching engine.

Tests cover:
    - Text similarity calculation (keyword overlap)
    - Category inference from text
    - Category match scoring
    - Severity match scoring
    - Recency scoring
    - Full case scoring (combined)
    - find_similar_cases end-to-end
    - Detailed match results
    - LLM re-ranking (mocked)
    - Edge cases (empty repo, no matches)

Sprint 130 — Story 130-3
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.integrations.correlation.types import Event, EventSeverity, EventType
from src.integrations.rootcause.case_matcher import (
    CaseMatcher,
    MatchResult,
    _tokenize,
)
from src.integrations.rootcause.case_repository import CaseRepository
from src.integrations.rootcause.types import HistoricalCase


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_event(
    title: str = "Database connection pool exhaustion",
    description: str = "Connection pool reached 100% causing timeouts",
    severity: EventSeverity = EventSeverity.CRITICAL,
) -> Event:
    return Event(
        event_id="evt-test",
        event_type=EventType.ALERT,
        title=title,
        description=description,
        severity=severity,
        timestamp=datetime.utcnow(),
        source_system="api-service",
        affected_components=["api-service", "db-service"],
    )


# ---------------------------------------------------------------------------
# Tokenization
# ---------------------------------------------------------------------------


class TestTokenize:
    """Tests for the _tokenize helper."""

    def test_basic_tokenization(self) -> None:
        """Tokenizes text into lowercase alpha words >= 3 chars."""
        tokens = _tokenize("The Database Connection Pool was exhausted")
        assert "database" in tokens
        assert "connection" in tokens
        assert "pool" in tokens
        assert "exhausted" in tokens
        assert "the" not in tokens  # stop word
        assert "was" not in tokens  # stop word

    def test_empty_text(self) -> None:
        """Empty text returns empty list."""
        assert _tokenize("") == []

    def test_short_words_excluded(self) -> None:
        """Words shorter than 3 characters are excluded."""
        tokens = _tokenize("I am OK")
        assert tokens == []


# ---------------------------------------------------------------------------
# Text Similarity
# ---------------------------------------------------------------------------


class TestTextSimilarity:
    """Tests for text similarity scoring."""

    def test_identical_text_high_similarity(self) -> None:
        """Identical texts produce high similarity."""
        repo = CaseRepository(seed=False)
        matcher = CaseMatcher(repo)

        sim, kw = matcher._text_similarity(
            "database connection pool exhaustion",
            "database connection pool exhaustion",
        )
        assert sim > 0.8
        assert "database" in kw

    def test_related_text_moderate_similarity(self) -> None:
        """Related but different texts produce moderate similarity."""
        repo = CaseRepository(seed=False)
        matcher = CaseMatcher(repo)

        sim, kw = matcher._text_similarity(
            "database connection pool exhaustion",
            "connection timeout in database service",
        )
        assert sim > 0.2
        assert any(k in kw for k in ["database", "connection"])

    def test_unrelated_text_low_similarity(self) -> None:
        """Unrelated texts produce low or zero similarity."""
        repo = CaseRepository(seed=False)
        matcher = CaseMatcher(repo)

        sim, _ = matcher._text_similarity(
            "database connection pool exhaustion",
            "frontend react component rendering issue",
        )
        assert sim < 0.2

    def test_empty_text_zero_similarity(self) -> None:
        """Empty text produces zero similarity."""
        repo = CaseRepository(seed=False)
        matcher = CaseMatcher(repo)

        sim, kw = matcher._text_similarity("", "some text")
        assert sim == 0.0
        assert kw == []


# ---------------------------------------------------------------------------
# Category Inference
# ---------------------------------------------------------------------------


class TestCategoryInference:
    """Tests for category inference from text."""

    def test_infer_database(self) -> None:
        """Database-related text infers 'database' category."""
        repo = CaseRepository(seed=False)
        matcher = CaseMatcher(repo)

        cat = matcher._infer_category("database connection pool SQL query deadlock")
        assert cat == "database"

    def test_infer_network(self) -> None:
        """Network-related text infers 'network' category."""
        repo = CaseRepository(seed=False)
        matcher = CaseMatcher(repo)

        cat = matcher._infer_category("DNS resolution timeout latency spike")
        assert cat == "network"

    def test_infer_security(self) -> None:
        """Security-related text infers 'security' category."""
        repo = CaseRepository(seed=False)
        matcher = CaseMatcher(repo)

        cat = matcher._infer_category("certificate expiry JWT token authentication")
        assert cat == "security"

    def test_infer_unknown(self) -> None:
        """Unrecognizable text returns None."""
        repo = CaseRepository(seed=False)
        matcher = CaseMatcher(repo)

        cat = matcher._infer_category("xyz abc qrs")
        assert cat is None


# ---------------------------------------------------------------------------
# Category Match Scoring
# ---------------------------------------------------------------------------


class TestCategoryMatchScore:
    """Tests for category match scoring."""

    def test_exact_match(self) -> None:
        """Same category scores 1.0."""
        repo = CaseRepository(seed=False)
        matcher = CaseMatcher(repo)

        assert matcher._category_match_score("database", "database") == 1.0

    def test_related_match(self) -> None:
        """Related categories score 0.5."""
        repo = CaseRepository(seed=False)
        matcher = CaseMatcher(repo)

        assert matcher._category_match_score("database", "application") == 0.5

    def test_unrelated_match(self) -> None:
        """Unrelated categories score 0.0."""
        repo = CaseRepository(seed=False)
        matcher = CaseMatcher(repo)

        assert matcher._category_match_score("database", "security") == 0.0

    def test_unknown_category(self) -> None:
        """Unknown category scores 0.3 (neutral)."""
        repo = CaseRepository(seed=False)
        matcher = CaseMatcher(repo)

        assert matcher._category_match_score(None, "database") == 0.3


# ---------------------------------------------------------------------------
# Severity Match Scoring
# ---------------------------------------------------------------------------


class TestSeverityMatchScore:
    """Tests for severity match scoring."""

    def test_exact_severity_match(self) -> None:
        """Same severity scores 1.0."""
        repo = CaseRepository()
        matcher = CaseMatcher(repo)

        event = _make_event(severity=EventSeverity.CRITICAL)
        case = HistoricalCase(
            case_id="HC-001",  # critical in seed data
            title="Database Connection Pool Exhaustion",
            description="", root_cause="", resolution="",
            occurred_at=datetime.utcnow(), resolved_at=None,
            similarity_score=0.0,
        )

        score = matcher._severity_match_score(event, case)
        assert score == 1.0

    def test_adjacent_severity(self) -> None:
        """Adjacent severity scores 0.6."""
        repo = CaseRepository()
        matcher = CaseMatcher(repo)

        event = _make_event(severity=EventSeverity.ERROR)
        case = HistoricalCase(
            case_id="HC-001",  # critical
            title="Database Connection Pool Exhaustion",
            description="", root_cause="", resolution="",
            occurred_at=datetime.utcnow(), resolved_at=None,
            similarity_score=0.0,
        )

        score = matcher._severity_match_score(event, case)
        assert score == 0.6


# ---------------------------------------------------------------------------
# Recency Scoring
# ---------------------------------------------------------------------------


class TestRecencyScore:
    """Tests for case recency scoring."""

    def test_recent_case_high_score(self) -> None:
        """Case from last 30 days scores 1.0."""
        repo = CaseRepository(seed=False)
        matcher = CaseMatcher(repo)

        case = HistoricalCase(
            case_id="recent", title="", description="",
            root_cause="", resolution="",
            occurred_at=datetime.utcnow() - timedelta(days=10),
            resolved_at=None, similarity_score=0.0,
        )
        assert matcher._recency_score(case) == 1.0

    def test_old_case_low_score(self) -> None:
        """Case from over a year ago scores 0.2."""
        repo = CaseRepository(seed=False)
        matcher = CaseMatcher(repo)

        case = HistoricalCase(
            case_id="old", title="", description="",
            root_cause="", resolution="",
            occurred_at=datetime.utcnow() - timedelta(days=400),
            resolved_at=None, similarity_score=0.0,
        )
        assert matcher._recency_score(case) == 0.2

    def test_no_timestamp(self) -> None:
        """Case with no occurred_at scores 0.5 (neutral)."""
        repo = CaseRepository(seed=False)
        matcher = CaseMatcher(repo)

        case = HistoricalCase(
            case_id="no-ts", title="", description="",
            root_cause="", resolution="",
            occurred_at=None, resolved_at=None,
            similarity_score=0.0,
        )
        assert matcher._recency_score(case) == 0.5


# ---------------------------------------------------------------------------
# Full Case Matching
# ---------------------------------------------------------------------------


class TestFindSimilarCases:
    """Tests for find_similar_cases end-to-end."""

    @pytest.mark.asyncio
    async def test_database_event_matches_database_cases(self) -> None:
        """Database-related event matches database-related cases."""
        repo = CaseRepository()
        matcher = CaseMatcher(repo)

        event = _make_event(
            title="Database connection pool exhaustion",
            description="Pool reached 100% capacity during traffic spike",
            severity=EventSeverity.CRITICAL,
        )

        results = await matcher.find_similar_cases(event, max_results=5)

        assert len(results) > 0
        # HC-001 should be top match (exact database connection pool case)
        assert results[0].case_id == "HC-001"
        assert results[0].similarity_score > 0.3

    @pytest.mark.asyncio
    async def test_network_event_matches_network_cases(self) -> None:
        """Network-related event matches network-related cases."""
        repo = CaseRepository()
        matcher = CaseMatcher(repo)

        event = _make_event(
            title="DNS resolution failure",
            description="Intermittent DNS failures causing 5xx errors",
            severity=EventSeverity.ERROR,
        )

        results = await matcher.find_similar_cases(event, max_results=5)

        assert len(results) > 0
        # HC-003 should be highly ranked
        top_ids = [r.case_id for r in results[:3]]
        assert "HC-003" in top_ids

    @pytest.mark.asyncio
    async def test_results_sorted_by_similarity(self) -> None:
        """Results are sorted by similarity score descending."""
        repo = CaseRepository()
        matcher = CaseMatcher(repo)

        event = _make_event()
        results = await matcher.find_similar_cases(event, max_results=10)

        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i].similarity_score >= results[i + 1].similarity_score

    @pytest.mark.asyncio
    async def test_min_similarity_filter(self) -> None:
        """Results below min_similarity are excluded."""
        repo = CaseRepository()
        matcher = CaseMatcher(repo)

        event = _make_event()
        results = await matcher.find_similar_cases(event, min_similarity=0.5)

        for r in results:
            assert r.similarity_score >= 0.5

    @pytest.mark.asyncio
    async def test_max_results_limit(self) -> None:
        """Results respect max_results limit."""
        repo = CaseRepository()
        matcher = CaseMatcher(repo)

        event = _make_event()
        results = await matcher.find_similar_cases(event, max_results=3)

        assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_empty_repository(self) -> None:
        """Empty repository returns empty results."""
        repo = CaseRepository(seed=False)
        matcher = CaseMatcher(repo)

        event = _make_event()
        results = await matcher.find_similar_cases(event)

        assert results == []


# ---------------------------------------------------------------------------
# Detailed Match Results
# ---------------------------------------------------------------------------


class TestDetailedMatchResults:
    """Tests for find_similar_cases_detailed."""

    @pytest.mark.asyncio
    async def test_detailed_results_have_breakdown(self) -> None:
        """Detailed results include score breakdown."""
        repo = CaseRepository()
        matcher = CaseMatcher(repo)

        event = _make_event()
        results = await matcher.find_similar_cases_detailed(event, max_results=3)

        assert len(results) > 0
        for r in results:
            assert isinstance(r, MatchResult)
            assert 0.0 <= r.text_similarity <= 1.0
            assert 0.0 <= r.category_match <= 1.0
            assert 0.0 <= r.severity_match <= 1.0
            assert 0.0 <= r.recency_score <= 1.0
            assert 0.0 <= r.total_score <= 1.0

    @pytest.mark.asyncio
    async def test_detailed_results_have_keywords(self) -> None:
        """Detailed results include matched keywords."""
        repo = CaseRepository()
        matcher = CaseMatcher(repo)

        event = _make_event(
            title="Database connection pool exhaustion",
            description="Connection pool reached capacity",
        )
        results = await matcher.find_similar_cases_detailed(event, max_results=1)

        if results:
            assert len(results[0].matched_keywords) > 0


# ---------------------------------------------------------------------------
# LLM Re-ranking
# ---------------------------------------------------------------------------


class TestLLMReranking:
    """Tests for optional LLM re-ranking."""

    @pytest.mark.asyncio
    async def test_llm_rerank_boosts_scores(self) -> None:
        """LLM re-ranking adjusts scores for top candidates."""
        repo = CaseRepository()
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value="HC-003\nHC-001\nHC-002")

        matcher = CaseMatcher(repo, llm_service=mock_llm)

        event = _make_event(
            title="DNS resolution failure",
            description="DNS timeout",
        )
        results = await matcher.find_similar_cases(event, max_results=5)

        assert len(results) > 0
        mock_llm.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_failure_falls_back(self) -> None:
        """LLM failure falls back to keyword-based scoring."""
        repo = CaseRepository()
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(side_effect=Exception("LLM unavailable"))

        matcher = CaseMatcher(repo, llm_service=mock_llm)

        event = _make_event()
        results = await matcher.find_similar_cases(event, max_results=5)

        # Should still return results (keyword-based)
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_no_llm_uses_keyword_scoring(self) -> None:
        """Without LLM, uses keyword-based scoring only."""
        repo = CaseRepository()
        matcher = CaseMatcher(repo, llm_service=None)

        event = _make_event()
        results = await matcher.find_similar_cases(event, max_results=5)

        assert len(results) > 0
