"""
Event Collector — 事件收集器

Sprint 130 — Story 130-1: Correlation 真實資料連接

提供:
- EventCollector: 事件收集、去重、聚合
- CollectionConfig: 收集配置

功能:
- 時間窗口內事件收集
- 服務名稱關聯
- 事件去重（基於 event_id + 時間窗口）
- 事件聚合（按服務分組）
- 組件依賴解析
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from .data_source import EventDataSource
from .types import Event, EventSeverity

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CollectionConfig:
    """Event collection configuration."""

    default_time_window: timedelta = field(
        default_factory=lambda: timedelta(hours=1)
    )
    max_events_per_query: int = 200
    dedup_window_seconds: int = 60
    max_aggregation_groups: int = 50


DEFAULT_CONFIG = CollectionConfig()


# ---------------------------------------------------------------------------
# EventCollector
# ---------------------------------------------------------------------------


class EventCollector:
    """
    事件收集器

    從 EventDataSource 收集事件，進行去重和聚合處理。
    用於為 CorrelationAnalyzer 提供乾淨的事件資料。
    """

    def __init__(
        self,
        data_source: EventDataSource,
        config: Optional[CollectionConfig] = None,
    ):
        self._data_source = data_source
        self._config = config or DEFAULT_CONFIG
        self._dedup_cache: Dict[str, datetime] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def collect_events(
        self,
        start_time: datetime,
        end_time: datetime,
        service_name: Optional[str] = None,
        severity_min: Optional[EventSeverity] = None,
    ) -> List[Event]:
        """
        Collect events within a time window with optional filters.

        Args:
            start_time: Window start (UTC).
            end_time: Window end (UTC).
            service_name: Optional service/component filter.
            severity_min: Optional minimum severity.

        Returns:
            Deduplicated list of events sorted by timestamp.
        """
        events = await self._data_source.get_events_in_range(
            start_time=start_time,
            end_time=end_time,
            source_system=service_name,
            severity_min=severity_min,
            max_results=self._config.max_events_per_query,
        )

        # Deduplicate
        unique_events = self.deduplicate(events)

        # Sort by timestamp
        unique_events.sort(key=lambda e: e.timestamp)

        logger.debug(
            f"Collected {len(unique_events)} unique events "
            f"(from {len(events)} raw) in "
            f"[{start_time.isoformat()} - {end_time.isoformat()}]"
        )

        return unique_events

    async def collect_for_correlation(
        self,
        target_event: Event,
        time_window: Optional[timedelta] = None,
    ) -> List[Event]:
        """
        Collect events relevant for correlation analysis around a target event.

        Gets events within the time window on both sides of the target event.

        Args:
            target_event: The event to correlate against.
            time_window: Time window (default from config).

        Returns:
            Deduplicated list of correlated events (excludes target).
        """
        window = time_window or self._config.default_time_window
        start_time = target_event.timestamp - window
        end_time = target_event.timestamp + window

        events = await self.collect_events(
            start_time=start_time,
            end_time=end_time,
        )

        # Exclude the target event itself
        return [e for e in events if e.event_id != target_event.event_id]

    def deduplicate(self, events: List[Event]) -> List[Event]:
        """
        Remove duplicate events based on event_id and time proximity.

        Two events are considered duplicates if they share the same event_id,
        or if they have the same title + source within the dedup window.

        Args:
            events: List of events to deduplicate.

        Returns:
            Deduplicated list preserving first occurrence order.
        """
        seen_ids: Set[str] = set()
        seen_signatures: Dict[str, datetime] = {}
        unique: List[Event] = []

        dedup_window = timedelta(seconds=self._config.dedup_window_seconds)

        for event in events:
            # Check by event_id
            if event.event_id in seen_ids:
                continue

            # Check by signature (title + source) within time window
            signature = f"{event.title}|{event.source_system}"
            if signature in seen_signatures:
                prev_time = seen_signatures[signature]
                if abs((event.timestamp - prev_time).total_seconds()) < dedup_window.total_seconds():
                    continue

            seen_ids.add(event.event_id)
            seen_signatures[signature] = event.timestamp
            unique.append(event)

        return unique

    def aggregate_by_service(
        self, events: List[Event]
    ) -> Dict[str, List[Event]]:
        """
        Group events by source service/component.

        Args:
            events: List of events to aggregate.

        Returns:
            Dict mapping service name to list of events.
        """
        groups: Dict[str, List[Event]] = {}

        for event in events:
            service = event.source_system or "unknown"
            if service not in groups:
                groups[service] = []
            groups[service].append(event)

        # Sort each group by timestamp
        for service_events in groups.values():
            service_events.sort(key=lambda e: e.timestamp)

        return dict(
            sorted(
                groups.items(),
                key=lambda kv: len(kv[1]),
                reverse=True,
            )[: self._config.max_aggregation_groups]
        )

    def aggregate_by_severity(
        self, events: List[Event]
    ) -> Dict[str, List[Event]]:
        """
        Group events by severity level.

        Args:
            events: List of events to aggregate.

        Returns:
            Dict mapping severity name to list of events.
        """
        groups: Dict[str, List[Event]] = {}

        for event in events:
            sev = event.severity.value
            if sev not in groups:
                groups[sev] = []
            groups[sev].append(event)

        return groups

    async def get_dependencies(
        self,
        components: List[str],
        time_window: Optional[timedelta] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get component dependencies via the data source.

        Args:
            components: Component names to resolve dependencies for.
            time_window: How far back to look for dependency data.

        Returns:
            List of dependency dicts with component_id, relationship, type, distance.
        """
        return await self._data_source.get_dependencies(
            components=components,
            time_window=time_window or self._config.default_time_window,
        )

    async def search_similar(
        self,
        search_text: str,
        time_window: Optional[timedelta] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search for semantically similar events.

        Args:
            search_text: Text to search for.
            time_window: How far back to search.
            limit: Maximum results.

        Returns:
            List of dicts with 'event' and 'similarity' keys.
        """
        return await self._data_source.search_similar_events(
            search_text=search_text,
            time_window=time_window,
            limit=limit,
        )

    def get_event_statistics(
        self, events: List[Event]
    ) -> Dict[str, Any]:
        """
        Calculate statistics for a collection of events.

        Args:
            events: List of events.

        Returns:
            Statistics dict with counts, severity distribution, time span, etc.
        """
        if not events:
            return {
                "total": 0,
                "severity_distribution": {},
                "type_distribution": {},
                "services": [],
                "time_span_seconds": 0,
            }

        by_severity = self.aggregate_by_severity(events)
        by_service = self.aggregate_by_service(events)

        type_dist: Dict[str, int] = {}
        for event in events:
            t = event.event_type.value
            type_dist[t] = type_dist.get(t, 0) + 1

        timestamps = [e.timestamp for e in events]
        time_span = (max(timestamps) - min(timestamps)).total_seconds()

        return {
            "total": len(events),
            "severity_distribution": {
                k: len(v) for k, v in by_severity.items()
            },
            "type_distribution": type_dist,
            "services": list(by_service.keys()),
            "time_span_seconds": time_span,
            "earliest": min(timestamps).isoformat(),
            "latest": max(timestamps).isoformat(),
        }
