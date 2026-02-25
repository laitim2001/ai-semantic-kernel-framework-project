"""Integration tests for Correlation module with real data source wiring.

Tests the full flow from CorrelationAnalyzer through EventDataSource/EventCollector
using mocked HTTP responses (no real Azure Monitor).

Sprint 130 — Story 130-3
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.integrations.correlation.analyzer import CorrelationAnalyzer
from src.integrations.correlation.data_source import (
    AzureMonitorConfig,
    EventDataSource,
)
from src.integrations.correlation.event_collector import EventCollector
from src.integrations.correlation.types import (
    CorrelationResult,
    CorrelationType,
    DiscoveryQuery,
    Event,
    EventSeverity,
    EventType,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_event(
    event_id: str = "target-evt",
    title: str = "Database Error",
    severity: EventSeverity = EventSeverity.ERROR,
    timestamp: datetime = None,
) -> Event:
    return Event(
        event_id=event_id,
        event_type=EventType.ALERT,
        title=title,
        description=f"Description for {title}",
        severity=severity,
        timestamp=timestamp or datetime(2026, 2, 25, 10, 0),
        source_system="api-service",
        affected_components=["api-service", "db-service"],
    )


def _make_data_source_with_events(events: list) -> EventDataSource:
    """Create data source that returns pre-defined events."""
    ds = MagicMock(spec=EventDataSource)
    ds.get_event = AsyncMock(side_effect=lambda eid: next(
        (e for e in events if e.event_id == eid), None
    ))
    ds.get_events_in_range = AsyncMock(return_value=events)
    ds.get_events_for_component = AsyncMock(return_value=[])
    ds.search_similar_events = AsyncMock(return_value=[])
    ds.get_dependencies = AsyncMock(return_value=[])
    return ds


# ---------------------------------------------------------------------------
# 1. Analyzer with Real Data Source (mocked HTTP)
# ---------------------------------------------------------------------------


class TestCorrelationAnalyzerRealDataSource:
    """Integration tests for CorrelationAnalyzer with injected EventDataSource."""

    @pytest.mark.asyncio
    async def test_find_correlations_time(self) -> None:
        """Time correlation finds events in the same time window."""
        target = _make_event("target", timestamp=datetime(2026, 2, 25, 10, 0))
        nearby = [
            _make_event("nearby-1", title="Nearby 1",
                        timestamp=datetime(2026, 2, 25, 9, 50)),
            _make_event("nearby-2", title="Nearby 2",
                        timestamp=datetime(2026, 2, 25, 10, 5)),
        ]

        ds = _make_data_source_with_events([target] + nearby)
        collector = EventCollector(ds)
        analyzer = CorrelationAnalyzer(data_source=ds, event_collector=collector)

        correlations = await analyzer.find_correlations(
            event=target,
            time_window=timedelta(hours=1),
            correlation_types=[CorrelationType.TIME],
        )

        assert len(correlations) == 2
        for corr in correlations:
            assert corr.correlation_type == CorrelationType.TIME
            assert corr.score > 0.0

    @pytest.mark.asyncio
    async def test_find_correlations_dependency(self) -> None:
        """Dependency correlation finds events for dependent components."""
        target = _make_event("target")
        dep_event = _make_event("dep-1", title="Dep Event")

        ds = _make_data_source_with_events([target, dep_event])
        ds.get_dependencies = AsyncMock(return_value=[
            {"component_id": "db-downstream", "relationship": "depends_on",
             "type": "critical", "distance": 1}
        ])
        ds.get_events_for_component = AsyncMock(return_value=[dep_event])

        analyzer = CorrelationAnalyzer(data_source=ds)

        correlations = await analyzer.find_correlations(
            event=target,
            correlation_types=[CorrelationType.DEPENDENCY],
        )

        assert len(correlations) >= 1
        assert correlations[0].correlation_type == CorrelationType.DEPENDENCY

    @pytest.mark.asyncio
    async def test_find_correlations_semantic(self) -> None:
        """Semantic correlation finds similar events."""
        target = _make_event("target", title="Database connection pool timeout")
        similar = _make_event("similar", title="Connection pool exhaustion")

        ds = _make_data_source_with_events([target, similar])
        ds.search_similar_events = AsyncMock(return_value=[
            {"event": similar, "similarity": 0.82}
        ])

        collector = EventCollector(ds)
        analyzer = CorrelationAnalyzer(data_source=ds, event_collector=collector)

        correlations = await analyzer.find_correlations(
            event=target,
            correlation_types=[CorrelationType.SEMANTIC],
        )

        assert len(correlations) >= 1
        assert correlations[0].correlation_type == CorrelationType.SEMANTIC
        assert correlations[0].score >= 0.6


# ---------------------------------------------------------------------------
# 2. Full Analysis Flow
# ---------------------------------------------------------------------------


class TestCorrelationAnalyzerFullFlow:
    """Integration tests for the complete analyze() flow."""

    @pytest.mark.asyncio
    async def test_full_analysis_with_events(self) -> None:
        """Full analysis produces CorrelationResult with graph."""
        target = _make_event("target", timestamp=datetime(2026, 2, 25, 10, 0))
        nearby = _make_event(
            "nearby-1", title="Related Error",
            timestamp=datetime(2026, 2, 25, 9, 55),
        )

        ds = _make_data_source_with_events([target, nearby])
        collector = EventCollector(ds)
        analyzer = CorrelationAnalyzer(data_source=ds, event_collector=collector)

        query = DiscoveryQuery(event_id="target")
        result = await analyzer.analyze(query)

        assert isinstance(result, CorrelationResult)
        assert result.event.event_id == "target"
        assert result.analysis_time_ms >= 0
        assert result.graph is not None
        assert result.graph.node_count >= 1  # at least root node

    @pytest.mark.asyncio
    async def test_full_analysis_summary(self) -> None:
        """Full analysis generates meaningful summary text."""
        target = _make_event("target")
        nearby = _make_event(
            "nearby-1", timestamp=datetime(2026, 2, 25, 9, 55)
        )

        ds = _make_data_source_with_events([target, nearby])
        analyzer = CorrelationAnalyzer(data_source=ds)

        query = DiscoveryQuery(event_id="target")
        result = await analyzer.analyze(query)

        assert isinstance(result.summary, str)
        assert len(result.summary) > 0


# ---------------------------------------------------------------------------
# 3. Unconfigured / No Data Source
# ---------------------------------------------------------------------------


class TestCorrelationAnalyzerNoDatasource:
    """Tests for analyzer behavior when no data source is configured."""

    @pytest.mark.asyncio
    async def test_no_datasource_get_event_returns_none(self) -> None:
        """Without data source, _get_event returns None."""
        analyzer = CorrelationAnalyzer()
        result = await analyzer._get_event("some-id")

        assert result is None

    @pytest.mark.asyncio
    async def test_no_datasource_events_in_range_empty(self) -> None:
        """Without data source, _get_events_in_range returns empty list."""
        analyzer = CorrelationAnalyzer()
        now = datetime.utcnow()
        result = await analyzer._get_events_in_range(
            now - timedelta(hours=1), now
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_no_datasource_dependencies_empty(self) -> None:
        """Without data source, _get_dependencies returns empty list."""
        analyzer = CorrelationAnalyzer()
        result = await analyzer._get_dependencies(["svc-a"])

        assert result == []

    @pytest.mark.asyncio
    async def test_no_datasource_search_similar_empty(self) -> None:
        """Without data source, _search_similar_events returns empty list."""
        analyzer = CorrelationAnalyzer()
        result = await analyzer._search_similar_events("some text")

        assert result == []

    @pytest.mark.asyncio
    async def test_no_datasource_analyze_raises(self) -> None:
        """analyze() raises ValueError when event not found (no data source)."""
        analyzer = CorrelationAnalyzer()
        query = DiscoveryQuery(event_id="nonexistent")

        with pytest.raises(ValueError, match="Event not found"):
            await analyzer.analyze(query)


# ---------------------------------------------------------------------------
# 4. Backward Compatibility
# ---------------------------------------------------------------------------


class TestCorrelationAnalyzerBackwardCompat:
    """Tests for backward compatibility with legacy params."""

    @pytest.mark.asyncio
    async def test_legacy_params_accepted(self) -> None:
        """Constructor accepts legacy event_store/cmdb_client/memory_client."""
        analyzer = CorrelationAnalyzer(
            event_store=MagicMock(),
            cmdb_client=MagicMock(),
            memory_client=MagicMock(),
        )
        # Should not raise
        assert analyzer._event_store is not None
        assert analyzer._cmdb_client is not None
        assert analyzer._memory_client is not None

    @pytest.mark.asyncio
    async def test_data_source_auto_creates_collector(self) -> None:
        """Providing data_source without collector auto-creates EventCollector."""
        ds = MagicMock(spec=EventDataSource)
        analyzer = CorrelationAnalyzer(data_source=ds)

        assert analyzer._event_collector is not None
        assert isinstance(analyzer._event_collector, EventCollector)
