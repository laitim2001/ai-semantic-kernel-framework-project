"""
Unit Tests for IncidentAnalyzer.

Sprint 126: Story 126-4 — IT Incident Processing (Phase 34)
Tests IncidentAnalyzer with mocked CorrelationAnalyzer, RootCauseAnalyzer, and LLM.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.integrations.incident.analyzer import IncidentAnalyzer
from src.integrations.incident.types import (
    IncidentAnalysis,
    IncidentCategory,
    IncidentContext,
    IncidentSeverity,
    RemediationAction,
)
from src.integrations.correlation.types import (
    Correlation,
    CorrelationType,
    Event,
    EventSeverity,
    EventType,
)
from src.integrations.rootcause.types import (
    AnalysisStatus,
    HistoricalCase,
    Recommendation,
    RecommendationType,
    RootCauseAnalysis,
    RootCauseHypothesis,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_context() -> IncidentContext:
    """Create a sample IncidentContext for testing."""
    return IncidentContext(
        incident_number="INC0012345",
        severity=IncidentSeverity.P2,
        category=IncidentCategory.NETWORK,
        short_description="Switch core-sw-01 port flapping",
        description="Port Gi0/1 is flapping causing VLAN 100 outage",
        affected_components=["core-sw-01", "VLAN-100"],
        business_service="ERP System",
        cmdb_ci="core-sw-01",
    )


@pytest.fixture
def mock_correlations() -> list:
    """Create mock correlations."""
    return [
        Correlation(
            correlation_id="corr_001",
            correlation_type=CorrelationType.TIME,
            source_event_id="evt_001",
            target_event_id="evt_002",
            score=0.85,
            confidence=0.85,
            evidence=["Events occurred within 5 minutes"],
        ),
        Correlation(
            correlation_id="corr_002",
            correlation_type=CorrelationType.DEPENDENCY,
            source_event_id="evt_001",
            target_event_id="evt_003",
            score=0.70,
            confidence=0.70,
            evidence=["Same network segment"],
        ),
    ]


@pytest.fixture
def mock_rca_result() -> RootCauseAnalysis:
    """Create a mock RootCauseAnalysis result."""
    return RootCauseAnalysis(
        analysis_id="rca_001",
        event_id="evt_inc_001",
        root_cause="Duplex mismatch on port Gi0/1",
        confidence=0.82,
        status=AnalysisStatus.COMPLETED,
        started_at=datetime(2026, 2, 25, 8, 0),
        completed_at=datetime(2026, 2, 25, 8, 5),
        contributing_factors=["duplex mismatch", "auto-negotiation failure"],
        hypotheses=[
            RootCauseHypothesis(
                hypothesis_id="hyp_001",
                description="Duplex mismatch",
                confidence=0.85,
                evidence=["Port error counters"],
            ),
        ],
        similar_historical_cases=[
            HistoricalCase(
                case_id="hist_001",
                title="Switch port flapping on dist-sw-02",
                description="Similar port flapping issue on distribution switch",
                root_cause="Cable issue",
                resolution="Replaced cable",
                occurred_at=datetime(2026, 1, 15, 8, 0),
                resolved_at=datetime(2026, 1, 15, 9, 0),
                similarity_score=0.75,
            ),
        ],
        recommendations=[
            Recommendation(
                recommendation_id="rec_001",
                recommendation_type=RecommendationType.IMMEDIATE,
                title="Force duplex settings",
                description="Set port to full-duplex manually",
                priority=1,
                estimated_effort="30 minutes",
                steps=["Verify current duplex", "Force full-duplex"],
            ),
        ],
    )


@pytest.fixture
def mock_correlation_analyzer(mock_correlations):
    """Create a mocked CorrelationAnalyzer."""
    analyzer = MagicMock()
    analyzer.find_correlations = AsyncMock(return_value=mock_correlations)
    return analyzer


@pytest.fixture
def mock_rootcause_analyzer(mock_rca_result):
    """Create a mocked RootCauseAnalyzer."""
    analyzer = MagicMock()
    analyzer.analyze_root_cause = AsyncMock(return_value=mock_rca_result)
    return analyzer


@pytest.fixture
def mock_llm_service():
    """Create a mock LLM service."""
    service = MagicMock()
    service.generate_structured = AsyncMock(return_value={
        "root_cause_summary": "LLM: Port flapping caused by duplex mismatch with connected device",
        "root_cause_confidence": 0.92,
        "contributing_factors": ["duplex mismatch", "NIC firmware version"],
        "analysis_notes": "Enhanced analysis with historical context",
        "suggested_category_correction": None,
    })
    return service


@pytest.fixture
def analyzer(mock_correlation_analyzer, mock_rootcause_analyzer):
    """Create IncidentAnalyzer with mocked dependencies (no LLM)."""
    return IncidentAnalyzer(
        correlation_analyzer=mock_correlation_analyzer,
        rootcause_analyzer=mock_rootcause_analyzer,
        llm_service=None,
    )


@pytest.fixture
def analyzer_with_llm(mock_correlation_analyzer, mock_rootcause_analyzer, mock_llm_service):
    """Create IncidentAnalyzer with mocked dependencies including LLM."""
    return IncidentAnalyzer(
        correlation_analyzer=mock_correlation_analyzer,
        rootcause_analyzer=mock_rootcause_analyzer,
        llm_service=mock_llm_service,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestIncidentAnalyzerInit:
    """Tests for IncidentAnalyzer initialization."""

    def test_init_with_defaults(self) -> None:
        """Test initialization with default dependencies."""
        analyzer = IncidentAnalyzer()
        assert analyzer._correlation_analyzer is not None
        assert analyzer._rootcause_analyzer is not None
        assert analyzer._llm_service is None

    def test_init_with_injected_deps(
        self, mock_correlation_analyzer, mock_rootcause_analyzer
    ) -> None:
        """Test initialization with injected dependencies."""
        analyzer = IncidentAnalyzer(
            correlation_analyzer=mock_correlation_analyzer,
            rootcause_analyzer=mock_rootcause_analyzer,
        )
        assert analyzer._correlation_analyzer is mock_correlation_analyzer
        assert analyzer._rootcause_analyzer is mock_rootcause_analyzer


class TestIncidentAnalyzerAnalyze:
    """Tests for IncidentAnalyzer.analyze()."""

    @pytest.mark.asyncio
    async def test_analyze_returns_analysis(
        self, analyzer: IncidentAnalyzer, sample_context: IncidentContext
    ) -> None:
        """Test analyze returns an IncidentAnalysis object."""
        result = await analyzer.analyze(sample_context)
        assert isinstance(result, IncidentAnalysis)
        assert result.incident_number == "INC0012345"

    @pytest.mark.asyncio
    async def test_analyze_includes_correlations(
        self, analyzer: IncidentAnalyzer, sample_context: IncidentContext
    ) -> None:
        """Test analysis includes correlation count."""
        result = await analyzer.analyze(sample_context)
        assert result.correlations_found == 2

    @pytest.mark.asyncio
    async def test_analyze_includes_historical_matches(
        self, analyzer: IncidentAnalyzer, sample_context: IncidentContext
    ) -> None:
        """Test analysis includes historical case matches."""
        result = await analyzer.analyze(sample_context)
        assert result.historical_matches == 1

    @pytest.mark.asyncio
    async def test_analyze_includes_root_cause(
        self, analyzer: IncidentAnalyzer, sample_context: IncidentContext
    ) -> None:
        """Test analysis includes root cause from RCA."""
        result = await analyzer.analyze(sample_context)
        assert "Duplex mismatch" in result.root_cause_summary
        assert result.root_cause_confidence == 0.82

    @pytest.mark.asyncio
    async def test_analyze_includes_contributing_factors(
        self, analyzer: IncidentAnalyzer, sample_context: IncidentContext
    ) -> None:
        """Test analysis includes contributing factors."""
        result = await analyzer.analyze(sample_context)
        assert "duplex mismatch" in result.contributing_factors

    @pytest.mark.asyncio
    async def test_analyze_includes_recommended_actions(
        self, analyzer: IncidentAnalyzer, sample_context: IncidentContext
    ) -> None:
        """Test analysis converts RCA recommendations to RemediationActions."""
        result = await analyzer.analyze(sample_context)
        assert len(result.recommended_actions) >= 1
        action = result.recommended_actions[0]
        assert action.title == "Force duplex settings"

    @pytest.mark.asyncio
    async def test_analyze_includes_metadata(
        self, analyzer: IncidentAnalyzer, sample_context: IncidentContext
    ) -> None:
        """Test analysis metadata includes correlation and RCA info."""
        result = await analyzer.analyze(sample_context)
        assert "correlation_types" in result.metadata
        assert "rca_status" in result.metadata
        assert result.metadata["rca_status"] == "completed"

    @pytest.mark.asyncio
    async def test_analyze_without_llm(
        self, analyzer: IncidentAnalyzer, sample_context: IncidentContext
    ) -> None:
        """Test analysis without LLM enhancement."""
        result = await analyzer.analyze(sample_context)
        assert result.llm_enhanced is False

    @pytest.mark.asyncio
    async def test_analyze_with_llm_enhanced(
        self, analyzer_with_llm: IncidentAnalyzer, sample_context: IncidentContext
    ) -> None:
        """Test analysis with LLM enhancement."""
        result = await analyzer_with_llm.analyze(sample_context)
        assert result.llm_enhanced is True
        assert "LLM:" in result.root_cause_summary
        # Confidence should be merged: 0.82 * 0.4 + 0.92 * 0.6 = 0.88
        expected = 0.82 * 0.4 + 0.92 * 0.6
        assert abs(result.root_cause_confidence - expected) < 0.01

    @pytest.mark.asyncio
    async def test_analyze_llm_failure_fallback(
        self,
        mock_correlation_analyzer,
        mock_rootcause_analyzer,
        sample_context: IncidentContext,
    ) -> None:
        """Test analysis falls back to rule-based when LLM fails."""
        failing_llm = MagicMock()
        failing_llm.generate_structured = AsyncMock(
            side_effect=Exception("LLM API unavailable")
        )
        analyzer = IncidentAnalyzer(
            correlation_analyzer=mock_correlation_analyzer,
            rootcause_analyzer=mock_rootcause_analyzer,
            llm_service=failing_llm,
        )
        result = await analyzer.analyze(sample_context)
        assert result.llm_enhanced is False
        assert "Duplex mismatch" in result.root_cause_summary

    @pytest.mark.asyncio
    async def test_analyze_handles_exception_gracefully(
        self, sample_context: IncidentContext
    ) -> None:
        """Test analysis handles unexpected errors gracefully."""
        failing_corr = MagicMock()
        failing_corr.find_correlations = AsyncMock(
            side_effect=RuntimeError("Correlation service down")
        )
        analyzer = IncidentAnalyzer(
            correlation_analyzer=failing_corr,
        )
        result = await analyzer.analyze(sample_context)
        assert "Analysis failed" in result.root_cause_summary
        assert result.root_cause_confidence == 0.0
        assert "error" in result.metadata


class TestIncidentAnalyzerHelpers:
    """Tests for IncidentAnalyzer helper methods."""

    def test_context_to_event(
        self, analyzer: IncidentAnalyzer, sample_context: IncidentContext
    ) -> None:
        """Test conversion from IncidentContext to Event."""
        event = analyzer._context_to_event(sample_context)
        assert event.event_type == EventType.INCIDENT
        assert event.title == sample_context.short_description
        assert event.severity == EventSeverity.ERROR  # P2 → ERROR
        assert "core-sw-01" in event.affected_components

    def test_merge_confidence_without_llm(
        self, analyzer: IncidentAnalyzer
    ) -> None:
        """Test confidence merge uses only RCA when no LLM."""
        result = analyzer._merge_confidence(0.82, 0.0, False)
        assert result == 0.82

    def test_merge_confidence_with_llm(
        self, analyzer: IncidentAnalyzer
    ) -> None:
        """Test confidence merge is weighted average with LLM."""
        result = analyzer._merge_confidence(0.80, 0.90, True)
        expected = 0.80 * 0.4 + 0.90 * 0.6
        assert abs(result - expected) < 0.001

    def test_merge_factors_deduplicates(
        self, analyzer: IncidentAnalyzer
    ) -> None:
        """Test factor merge deduplicates (case-insensitive)."""
        result = analyzer._merge_factors(
            ["Duplex Mismatch", "Cable Issue"],
            ["duplex mismatch", "NIC firmware"],
            True,
        )
        assert len(result) == 3  # "Duplex Mismatch", "Cable Issue", "NIC firmware"
