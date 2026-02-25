"""Unit tests for EventCollector — event collection, deduplication, aggregation.

Tests cover:
    - Event collection with time window
    - Collection for correlation (around target event)
    - Event deduplication (by ID and signature)
    - Aggregation by service
    - Aggregation by severity
    - Dependency resolution delegation
    - Similar event search delegation
    - Event statistics calculation

Sprint 130 — Story 130-3
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.integrations.correlation.data_source import EventDataSource
from src.integrations.correlation.event_collector import (
    CollectionConfig,
    EventCollector,
)
from src.integrations.correlation.types import Event, EventSeverity, EventType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_event(
    event_id: str = "evt-1",
    title: str = "Test Event",
    source: str = "svc-a",
    severity: EventSeverity = EventSeverity.WARNING,
    timestamp: datetime = None,
) -> Event:
    return Event(
        event_id=event_id,
        event_type=EventType.ALERT,
        title=title,
        description=f"Description for {title}",
        severity=severity,
        timestamp=timestamp or datetime.utcnow(),
        source_system=source,
        affected_components=[source],
    )


def _make_mock_data_source(events=None) -> EventDataSource:
    """Create a mock data source that returns specified events."""
    ds = MagicMock(spec=EventDataSource)
    ds.get_events_in_range = AsyncMock(return_value=events or [])
    ds.get_events_for_component = AsyncMock(return_value=[])
    ds.search_similar_events = AsyncMock(return_value=[])
    ds.get_dependencies = AsyncMock(return_value=[])
    return ds


# ---------------------------------------------------------------------------
# CollectionConfig
# ---------------------------------------------------------------------------


class TestCollectionConfig:
    """Tests for CollectionConfig."""

    def test_default_values(self) -> None:
        """Default config has sensible values."""
        config = CollectionConfig()
        assert config.default_time_window == timedelta(hours=1)
        assert config.max_events_per_query == 200
        assert config.dedup_window_seconds == 60

    def test_config_is_frozen(self) -> None:
        """Config is immutable."""
        config = CollectionConfig()
        with pytest.raises(AttributeError):
            config.max_events_per_query = 500  # type: ignore


# ---------------------------------------------------------------------------
# EventCollector — Collection
# ---------------------------------------------------------------------------


class TestEventCollectorCollection:
    """Tests for event collection methods."""

    @pytest.mark.asyncio
    async def test_collect_events_basic(self) -> None:
        """collect_events returns events from data source."""
        events = [
            _make_event("e1", timestamp=datetime(2026, 2, 25, 10, 0)),
            _make_event("e2", timestamp=datetime(2026, 2, 25, 10, 5)),
        ]
        ds = _make_mock_data_source(events)
        collector = EventCollector(ds)

        now = datetime(2026, 2, 25, 11, 0)
        result = await collector.collect_events(
            start_time=now - timedelta(hours=2),
            end_time=now,
        )

        assert len(result) == 2
        ds.get_events_in_range.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_events_empty(self) -> None:
        """collect_events returns empty list when no events found."""
        ds = _make_mock_data_source([])
        collector = EventCollector(ds)

        now = datetime.utcnow()
        result = await collector.collect_events(
            start_time=now - timedelta(hours=1),
            end_time=now,
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_collect_for_correlation_excludes_target(self) -> None:
        """collect_for_correlation excludes the target event."""
        target = _make_event("target", timestamp=datetime(2026, 2, 25, 10, 0))
        events = [
            target,
            _make_event("other-1", timestamp=datetime(2026, 2, 25, 9, 55)),
            _make_event("other-2", timestamp=datetime(2026, 2, 25, 10, 3)),
        ]
        ds = _make_mock_data_source(events)
        collector = EventCollector(ds)

        result = await collector.collect_for_correlation(target)

        assert len(result) == 2
        assert all(e.event_id != "target" for e in result)

    @pytest.mark.asyncio
    async def test_collect_for_correlation_custom_window(self) -> None:
        """collect_for_correlation respects custom time window."""
        target = _make_event("target", timestamp=datetime(2026, 2, 25, 10, 0))
        ds = _make_mock_data_source([])
        collector = EventCollector(ds)

        await collector.collect_for_correlation(
            target, time_window=timedelta(hours=2)
        )

        call_args = ds.get_events_in_range.call_args
        start = call_args.kwargs.get("start_time") or call_args[1].get("start_time")
        end = call_args.kwargs.get("end_time") or call_args[1].get("end_time")
        assert (end - start).total_seconds() == pytest.approx(4 * 3600, abs=1)


# ---------------------------------------------------------------------------
# EventCollector — Deduplication
# ---------------------------------------------------------------------------


class TestEventCollectorDedup:
    """Tests for event deduplication."""

    def test_dedup_by_id(self) -> None:
        """Duplicate event IDs are removed."""
        ts = datetime(2026, 2, 25, 10, 0)
        events = [
            _make_event("e1", title="Error A", timestamp=ts),
            _make_event("e1", title="Error A", timestamp=ts),  # duplicate
            _make_event("e2", title="Error B", timestamp=ts),
        ]
        collector = EventCollector(_make_mock_data_source())
        result = collector.deduplicate(events)

        assert len(result) == 2
        ids = [e.event_id for e in result]
        assert "e1" in ids
        assert "e2" in ids

    def test_dedup_by_signature_within_window(self) -> None:
        """Events with same title+source within dedup window are removed."""
        base = datetime(2026, 2, 25, 10, 0)
        events = [
            _make_event("e1", title="Same Error", source="svc-a", timestamp=base),
            _make_event(
                "e2", title="Same Error", source="svc-a",
                timestamp=base + timedelta(seconds=30),
            ),  # within 60s window
        ]
        collector = EventCollector(_make_mock_data_source())
        result = collector.deduplicate(events)

        assert len(result) == 1

    def test_dedup_by_signature_outside_window(self) -> None:
        """Events with same title+source outside dedup window are kept."""
        base = datetime(2026, 2, 25, 10, 0)
        events = [
            _make_event("e1", title="Same Error", source="svc-a", timestamp=base),
            _make_event(
                "e2", title="Same Error", source="svc-a",
                timestamp=base + timedelta(seconds=120),
            ),  # outside 60s window
        ]
        collector = EventCollector(_make_mock_data_source())
        result = collector.deduplicate(events)

        assert len(result) == 2

    def test_dedup_empty_list(self) -> None:
        """Empty list returns empty."""
        collector = EventCollector(_make_mock_data_source())
        assert collector.deduplicate([]) == []


# ---------------------------------------------------------------------------
# EventCollector — Aggregation
# ---------------------------------------------------------------------------


class TestEventCollectorAggregation:
    """Tests for event aggregation methods."""

    def test_aggregate_by_service(self) -> None:
        """Events grouped by source service."""
        events = [
            _make_event("e1", source="svc-a"),
            _make_event("e2", source="svc-b"),
            _make_event("e3", source="svc-a"),
        ]
        collector = EventCollector(_make_mock_data_source())
        groups = collector.aggregate_by_service(events)

        assert "svc-a" in groups
        assert "svc-b" in groups
        assert len(groups["svc-a"]) == 2
        assert len(groups["svc-b"]) == 1

    def test_aggregate_by_service_sorted_by_count(self) -> None:
        """Service groups sorted by event count (descending)."""
        events = [
            _make_event("e1", source="svc-a"),
            _make_event("e2", source="svc-b"),
            _make_event("e3", source="svc-b"),
            _make_event("e4", source="svc-b"),
        ]
        collector = EventCollector(_make_mock_data_source())
        groups = collector.aggregate_by_service(events)

        keys = list(groups.keys())
        assert keys[0] == "svc-b"  # most events first

    def test_aggregate_by_severity(self) -> None:
        """Events grouped by severity level."""
        events = [
            _make_event("e1", severity=EventSeverity.WARNING),
            _make_event("e2", severity=EventSeverity.ERROR),
            _make_event("e3", severity=EventSeverity.WARNING),
        ]
        collector = EventCollector(_make_mock_data_source())
        groups = collector.aggregate_by_severity(events)

        assert len(groups["warning"]) == 2
        assert len(groups["error"]) == 1

    def test_aggregate_empty(self) -> None:
        """Empty events produce empty groups."""
        collector = EventCollector(_make_mock_data_source())
        assert collector.aggregate_by_service([]) == {}
        assert collector.aggregate_by_severity([]) == {}


# ---------------------------------------------------------------------------
# EventCollector — Delegation
# ---------------------------------------------------------------------------


class TestEventCollectorDelegation:
    """Tests for methods that delegate to data source."""

    @pytest.mark.asyncio
    async def test_get_dependencies_delegates(self) -> None:
        """get_dependencies delegates to data source."""
        ds = _make_mock_data_source()
        ds.get_dependencies = AsyncMock(return_value=[
            {"component_id": "db", "relationship": "depends_on", "type": "critical", "distance": 1}
        ])
        collector = EventCollector(ds)

        deps = await collector.get_dependencies(["svc-a"])
        assert len(deps) == 1
        assert deps[0]["component_id"] == "db"

    @pytest.mark.asyncio
    async def test_search_similar_delegates(self) -> None:
        """search_similar delegates to data source."""
        ds = _make_mock_data_source()
        ds.search_similar_events = AsyncMock(return_value=[
            {"event": _make_event("sim-1"), "similarity": 0.8}
        ])
        collector = EventCollector(ds)

        results = await collector.search_similar("database error")
        assert len(results) == 1
        assert results[0]["similarity"] == 0.8


# ---------------------------------------------------------------------------
# EventCollector — Statistics
# ---------------------------------------------------------------------------


class TestEventCollectorStatistics:
    """Tests for event statistics calculation."""

    def test_statistics_basic(self) -> None:
        """Statistics calculated correctly for a set of events."""
        base = datetime(2026, 2, 25, 10, 0)
        events = [
            _make_event("e1", source="svc-a", severity=EventSeverity.WARNING, timestamp=base),
            _make_event("e2", source="svc-b", severity=EventSeverity.ERROR,
                        timestamp=base + timedelta(minutes=10)),
            _make_event("e3", source="svc-a", severity=EventSeverity.WARNING,
                        timestamp=base + timedelta(minutes=20)),
        ]
        collector = EventCollector(_make_mock_data_source())
        stats = collector.get_event_statistics(events)

        assert stats["total"] == 3
        assert stats["severity_distribution"]["warning"] == 2
        assert stats["severity_distribution"]["error"] == 1
        assert "svc-a" in stats["services"]
        assert "svc-b" in stats["services"]
        assert stats["time_span_seconds"] == pytest.approx(1200, abs=1)

    def test_statistics_empty(self) -> None:
        """Empty events produce zero statistics."""
        collector = EventCollector(_make_mock_data_source())
        stats = collector.get_event_statistics([])

        assert stats["total"] == 0
        assert stats["severity_distribution"] == {}
        assert stats["time_span_seconds"] == 0
