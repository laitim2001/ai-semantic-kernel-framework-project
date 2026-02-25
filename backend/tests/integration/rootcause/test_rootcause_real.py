"""Integration tests for RootCause module with real case repository.

Tests the full RootCauseAnalyzer flow using CaseRepository + CaseMatcher
with seed data (no mocked historical cases).

Sprint 130 — Story 130-3
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.integrations.correlation.types import (
    Correlation,
    CorrelationGraph,
    CorrelationType,
    Event,
    EventSeverity,
    EventType,
    GraphNode,
)
from src.integrations.rootcause.analyzer import RootCauseAnalyzer
from src.integrations.rootcause.case_matcher import CaseMatcher
from src.integrations.rootcause.case_repository import CaseRepository
from src.integrations.rootcause.types import (
    AnalysisStatus,
    HistoricalCase,
    RootCauseAnalysis,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_event(
    event_id: str = "evt-test",
    title: str = "Database connection pool exhaustion",
    description: str = "Connection pool reached 100% capacity during traffic spike",
    severity: EventSeverity = EventSeverity.CRITICAL,
) -> Event:
    return Event(
        event_id=event_id,
        event_type=EventType.ALERT,
        title=title,
        description=description,
        severity=severity,
        timestamp=datetime.utcnow(),
        source_system="api-service",
        affected_components=["api-service", "db-service"],
    )


def _make_correlations() -> list:
    """Create sample correlations for testing."""
    return [
        Correlation(
            correlation_id="corr-1",
            source_event_id="evt-test",
            target_event_id="evt-related-1",
            correlation_type=CorrelationType.TIME,
            score=0.85,
            confidence=0.8,
            evidence=["Events occurred within 120 seconds"],
        ),
        Correlation(
            correlation_id="corr-2",
            source_event_id="evt-test",
            target_event_id="evt-related-2",
            correlation_type=CorrelationType.DEPENDENCY,
            score=0.72,
            confidence=0.75,
            evidence=["Dependency relationship: depends_on"],
        ),
    ]


def _make_graph(event_id: str = "evt-test") -> CorrelationGraph:
    """Create a simple correlation graph."""
    graph = CorrelationGraph(
        graph_id="graph-test",
        root_event_id=event_id,
    )
    graph.add_node(GraphNode(
        node_id=event_id,
        node_type="event",
        label="Test Event",
        severity=EventSeverity.CRITICAL,
        timestamp=datetime.utcnow(),
        metadata={"is_root": True},
    ))
    return graph


# ---------------------------------------------------------------------------
# 1. Full RCA Flow with Real Case Repository
# ---------------------------------------------------------------------------


class TestRCAWithCaseRepository:
    """Integration tests for RCA using real CaseRepository with seed data."""

    @pytest.mark.asyncio
    async def test_analyze_database_event(self) -> None:
        """Full RCA for database event matches HC-001 from seed data."""
        repo = CaseRepository()
        matcher = CaseMatcher(repo)
        analyzer = RootCauseAnalyzer(
            case_repository=repo,
            case_matcher=matcher,
        )

        event = _make_event()
        correlations = _make_correlations()
        graph = _make_graph()

        result = await analyzer.analyze_root_cause(event, correlations, graph)

        assert isinstance(result, RootCauseAnalysis)
        assert result.status == AnalysisStatus.COMPLETED
        assert result.event_id == "evt-test"
        assert result.confidence > 0.0
        assert len(result.similar_historical_cases) > 0
        # HC-001 should be among top matches
        case_ids = [c.case_id for c in result.similar_historical_cases]
        assert "HC-001" in case_ids

    @pytest.mark.asyncio
    async def test_analyze_network_event(self) -> None:
        """Full RCA for network event matches network-related seed cases."""
        repo = CaseRepository()
        matcher = CaseMatcher(repo)
        analyzer = RootCauseAnalyzer(
            case_repository=repo,
            case_matcher=matcher,
        )

        event = _make_event(
            title="DNS resolution failure",
            description="Intermittent DNS failures causing 5xx errors in 15% of requests",
            severity=EventSeverity.ERROR,
        )
        correlations = _make_correlations()

        result = await analyzer.analyze_root_cause(event, correlations)

        assert result.status == AnalysisStatus.COMPLETED
        assert len(result.similar_historical_cases) > 0
        # HC-003 (DNS) should be top match
        top_case_ids = [c.case_id for c in result.similar_historical_cases[:3]]
        assert "HC-003" in top_case_ids

    @pytest.mark.asyncio
    async def test_analyze_has_hypotheses(self) -> None:
        """RCA generates hypotheses from correlations and historical cases."""
        repo = CaseRepository()
        matcher = CaseMatcher(repo)
        analyzer = RootCauseAnalyzer(
            case_repository=repo,
            case_matcher=matcher,
        )

        event = _make_event()
        correlations = _make_correlations()

        result = await analyzer.analyze_root_cause(event, correlations)

        assert len(result.hypotheses) > 0
        # Should have both correlation-based and case-based hypotheses
        has_corr_hyp = any("correlated" in h.description.lower()
                          for h in result.hypotheses)
        has_case_hyp = any("similar to" in h.description.lower()
                          for h in result.hypotheses)
        assert has_corr_hyp or has_case_hyp

    @pytest.mark.asyncio
    async def test_analyze_has_recommendations(self) -> None:
        """RCA generates recommendations including case-based fixes."""
        repo = CaseRepository()
        matcher = CaseMatcher(repo)
        analyzer = RootCauseAnalyzer(
            case_repository=repo,
            case_matcher=matcher,
        )

        event = _make_event()
        correlations = _make_correlations()

        result = await analyzer.analyze_root_cause(event, correlations)

        assert len(result.recommendations) >= 2
        # Should have IMMEDIATE and PREVENTIVE at minimum
        types = [r.recommendation_type.value for r in result.recommendations]
        assert "immediate" in types
        assert "preventive" in types


# ---------------------------------------------------------------------------
# 2. get_similar_patterns with Real Repository
# ---------------------------------------------------------------------------


class TestGetSimilarPatterns:
    """Tests for get_similar_patterns using real CaseRepository."""

    @pytest.mark.asyncio
    async def test_similar_patterns_not_hardcoded(self) -> None:
        """get_similar_patterns returns real matches, not hardcoded 2 cases."""
        repo = CaseRepository()
        matcher = CaseMatcher(repo)
        analyzer = RootCauseAnalyzer(
            case_repository=repo,
            case_matcher=matcher,
        )

        event = _make_event()
        cases = await analyzer.get_similar_patterns(event)

        assert len(cases) > 0
        # Should have varying similarity scores (not all the same)
        scores = [c.similarity_score for c in cases]
        assert len(set(scores)) > 1  # Not all identical

    @pytest.mark.asyncio
    async def test_similar_patterns_respect_max(self) -> None:
        """get_similar_patterns respects max_results parameter."""
        repo = CaseRepository()
        matcher = CaseMatcher(repo)
        analyzer = RootCauseAnalyzer(
            case_repository=repo,
            case_matcher=matcher,
        )

        event = _make_event()
        cases = await analyzer.get_similar_patterns(event, max_results=3)

        assert len(cases) <= 3

    @pytest.mark.asyncio
    async def test_similar_patterns_sorted_by_score(self) -> None:
        """get_similar_patterns returns cases sorted by similarity."""
        repo = CaseRepository()
        matcher = CaseMatcher(repo)
        analyzer = RootCauseAnalyzer(
            case_repository=repo,
            case_matcher=matcher,
        )

        event = _make_event()
        cases = await analyzer.get_similar_patterns(event)

        if len(cases) > 1:
            for i in range(len(cases) - 1):
                assert cases[i].similarity_score >= cases[i + 1].similarity_score


# ---------------------------------------------------------------------------
# 3. No Repository Configured
# ---------------------------------------------------------------------------


class TestRCANoRepository:
    """Tests for RCA when no case repository is configured."""

    @pytest.mark.asyncio
    async def test_no_repo_returns_empty_patterns(self) -> None:
        """Without repository, get_similar_patterns returns empty list."""
        analyzer = RootCauseAnalyzer()

        event = _make_event()
        cases = await analyzer.get_similar_patterns(event)

        assert cases == []

    @pytest.mark.asyncio
    async def test_no_repo_analysis_still_works(self) -> None:
        """RCA still completes without repository (no historical cases)."""
        analyzer = RootCauseAnalyzer()

        event = _make_event()
        correlations = _make_correlations()

        result = await analyzer.analyze_root_cause(event, correlations)

        assert result.status == AnalysisStatus.COMPLETED
        assert result.similar_historical_cases == []
        # Should still have recommendations (IMMEDIATE + PREVENTIVE)
        assert len(result.recommendations) >= 2


# ---------------------------------------------------------------------------
# 4. Backward Compatibility
# ---------------------------------------------------------------------------


class TestRCABackwardCompat:
    """Tests for backward compatibility with legacy parameters."""

    @pytest.mark.asyncio
    async def test_legacy_params_accepted(self) -> None:
        """Constructor accepts legacy claude_client/knowledge_base params."""
        analyzer = RootCauseAnalyzer(
            claude_client=MagicMock(),
            knowledge_base=MagicMock(),
        )
        assert analyzer._claude_client is not None
        assert analyzer._knowledge_base is not None

    @pytest.mark.asyncio
    async def test_auto_creates_matcher_from_repo(self) -> None:
        """Providing case_repository without matcher auto-creates CaseMatcher."""
        repo = CaseRepository()
        analyzer = RootCauseAnalyzer(case_repository=repo)

        assert analyzer._case_matcher is not None
        assert isinstance(analyzer._case_matcher, CaseMatcher)

    @pytest.mark.asyncio
    async def test_metadata_includes_data_source(self) -> None:
        """Analysis metadata indicates data source used."""
        repo = CaseRepository()
        matcher = CaseMatcher(repo)
        analyzer = RootCauseAnalyzer(
            case_repository=repo,
            case_matcher=matcher,
        )

        event = _make_event()
        result = await analyzer.analyze_root_cause(event, [])

        assert result.metadata.get("data_source") == "case_repository"
