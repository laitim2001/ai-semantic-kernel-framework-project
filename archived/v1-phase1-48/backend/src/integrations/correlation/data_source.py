"""
Event Data Source — Azure Monitor / Application Insights 事件資料來源

Sprint 130 — Story 130-1: Correlation 真實資料連接

提供:
- AzureMonitorConfig: Azure Monitor 連線配置
- EventDataSource: 事件資料來源（App Insights + Log Analytics）

支援:
- Application Insights 的 KQL 查詢
- Log Analytics workspace 查詢
- OTel traces/metrics 提取
- 原始資料轉換為 Event 物件
"""

import hashlib
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

from .types import Event, EventSeverity, EventType

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AzureMonitorConfig:
    """Azure Monitor / Application Insights 連線配置 (immutable)."""

    workspace_id: str
    app_insights_app_id: str
    app_insights_api_key: str
    subscription_id: str = ""
    resource_group: str = ""
    log_analytics_endpoint: str = "https://api.loganalytics.io/v1"
    app_insights_endpoint: str = "https://api.applicationinsights.io/v1"

    @classmethod
    def from_env(cls) -> "AzureMonitorConfig":
        """Load configuration from environment variables."""
        return cls(
            workspace_id=os.environ.get("AZURE_MONITOR_WORKSPACE_ID", ""),
            app_insights_app_id=os.environ.get("APP_INSIGHTS_APP_ID", ""),
            app_insights_api_key=os.environ.get("APP_INSIGHTS_API_KEY", ""),
            subscription_id=os.environ.get("AZURE_SUBSCRIPTION_ID", ""),
            resource_group=os.environ.get("AZURE_RESOURCE_GROUP", ""),
        )

    @property
    def is_configured(self) -> bool:
        """Check if required fields are present."""
        return bool(self.app_insights_app_id and self.app_insights_api_key)


# ---------------------------------------------------------------------------
# Severity / Type Mapping
# ---------------------------------------------------------------------------

_SEVERITY_MAP: Dict[str, EventSeverity] = {
    "0": EventSeverity.INFO,
    "1": EventSeverity.INFO,
    "2": EventSeverity.WARNING,
    "3": EventSeverity.ERROR,
    "4": EventSeverity.CRITICAL,
    "verbose": EventSeverity.INFO,
    "information": EventSeverity.INFO,
    "warning": EventSeverity.WARNING,
    "error": EventSeverity.ERROR,
    "critical": EventSeverity.CRITICAL,
}

_TYPE_MAP: Dict[str, EventType] = {
    "exception": EventType.ALERT,
    "trace": EventType.LOG_PATTERN,
    "request": EventType.ALERT,
    "dependency": EventType.ALERT,
    "customEvent": EventType.ALERT,
    "availabilityResult": EventType.METRIC_ANOMALY,
    "performanceCounter": EventType.METRIC_ANOMALY,
    "customMetric": EventType.METRIC_ANOMALY,
    "alert": EventType.ALERT,
    "incident": EventType.INCIDENT,
    "change": EventType.CHANGE,
    "deployment": EventType.DEPLOYMENT,
    "security": EventType.SECURITY,
}


# ---------------------------------------------------------------------------
# EventDataSource
# ---------------------------------------------------------------------------


class EventDataSource:
    """
    真實事件資料來源 — Azure Monitor / Application Insights.

    連接 Application Insights REST API 查詢事件資料，
    將原始遙測資料轉換為 correlation Event 物件。

    當未配置 Azure 憑證時，優雅降級為空結果（不再返回偽造資料）。
    """

    def __init__(
        self,
        config: Optional[AzureMonitorConfig] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        self._config = config
        self._http_client = http_client
        self._owns_client = http_client is None

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Lazily create HTTP client if not injected."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
            self._owns_client = True
        return self._http_client

    async def close(self) -> None:
        """Close the HTTP client if we own it."""
        if self._owns_client and self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_event(self, event_id: str) -> Optional[Event]:
        """
        Get a single event by ID from Application Insights.

        Args:
            event_id: The event identifier (operation_Id or itemId).

        Returns:
            Event object or None if not found / not configured.
        """
        if not self._is_configured():
            logger.debug("EventDataSource not configured — returning None")
            return None

        query = (
            f"union exceptions, traces, requests, dependencies, customEvents "
            f"| where operation_Id == '{_sanitize_kql(event_id)}' "
            f"  or itemId == '{_sanitize_kql(event_id)}' "
            f"| take 1"
        )
        rows = await self._query_app_insights(query)
        if not rows:
            return None
        return self._convert_to_event(rows[0])

    async def get_events_in_range(
        self,
        start_time: datetime,
        end_time: datetime,
        source_system: Optional[str] = None,
        severity_min: Optional[EventSeverity] = None,
        max_results: int = 200,
    ) -> List[Event]:
        """
        Get events within a time range from Application Insights.

        Args:
            start_time: Range start (UTC).
            end_time: Range end (UTC).
            source_system: Optional filter by cloud_RoleName.
            severity_min: Optional minimum severity filter.
            max_results: Maximum events to return.

        Returns:
            List of Event objects sorted by timestamp.
        """
        if not self._is_configured():
            return []

        iso_start = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        iso_end = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")

        where_clauses = [
            f"timestamp between(datetime('{iso_start}') .. datetime('{iso_end}'))",
        ]

        if source_system:
            where_clauses.append(
                f"cloud_RoleName == '{_sanitize_kql(source_system)}'"
            )

        if severity_min:
            sev_level = _severity_to_level(severity_min)
            where_clauses.append(f"severityLevel >= {sev_level}")

        where = " and ".join(where_clauses)
        query = (
            f"union exceptions, traces, requests, dependencies "
            f"| where {where} "
            f"| order by timestamp asc "
            f"| take {max_results}"
        )

        rows = await self._query_app_insights(query)
        return [self._convert_to_event(r) for r in rows]

    async def get_events_for_component(
        self,
        component_id: str,
        time_window: Optional[timedelta] = None,
        max_results: int = 50,
    ) -> List[Event]:
        """
        Get events for a specific component (cloud_RoleName).

        Args:
            component_id: The component / service name.
            time_window: How far back to look (default 1 hour).
            max_results: Maximum events.

        Returns:
            List of Event objects for the component.
        """
        if not self._is_configured():
            return []

        window = time_window or timedelta(hours=1)
        ago_str = f"{int(window.total_seconds())}s"

        query = (
            f"union exceptions, traces, requests, dependencies "
            f"| where timestamp > ago({ago_str}) "
            f"  and cloud_RoleName == '{_sanitize_kql(component_id)}' "
            f"| order by timestamp desc "
            f"| take {max_results}"
        )

        rows = await self._query_app_insights(query)
        return [self._convert_to_event(r) for r in rows]

    async def search_similar_events(
        self,
        search_text: str,
        time_window: Optional[timedelta] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search for semantically similar events using text matching.

        Uses KQL `has_any` / `contains` for keyword overlap.
        Returns list of {event: Event, similarity: float}.

        Args:
            search_text: Text to search for.
            time_window: How far back to search (default 24 hours).
            limit: Maximum results.

        Returns:
            List of dicts with 'event' and 'similarity' keys.
        """
        if not self._is_configured():
            return []

        window = time_window or timedelta(hours=24)
        ago_str = f"{int(window.total_seconds())}s"

        # Extract keywords for KQL search (top 5 meaningful words)
        keywords = _extract_keywords(search_text)
        if not keywords:
            return []

        # Build KQL has_any filter
        kw_list = ", ".join(f"'{_sanitize_kql(w)}'" for w in keywords[:5])
        query = (
            f"union exceptions, traces, requests "
            f"| where timestamp > ago({ago_str}) "
            f"| where message has_any ({kw_list}) "
            f"  or name has_any ({kw_list}) "
            f"| project timestamp, itemId, operation_Id, name, message, "
            f"  severityLevel, cloud_RoleName, itemType "
            f"| take {limit * 2}"
        )

        rows = await self._query_app_insights(query)
        results = []
        for row in rows:
            event = self._convert_to_event(row)
            similarity = _calculate_keyword_similarity(
                search_text, f"{event.title} {event.description}"
            )
            if similarity >= 0.3:
                results.append({"event": event, "similarity": similarity})

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:limit]

    async def get_dependencies(
        self,
        components: List[str],
        time_window: Optional[timedelta] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get component dependencies from Application Insights dependency telemetry.

        Uses the dependency table to discover service-to-service relationships.

        Args:
            components: List of component names to find dependencies for.
            time_window: How far back to look (default 1 hour).

        Returns:
            List of dependency dicts with component_id, relationship, type, distance.
        """
        if not self._is_configured() or not components:
            return []

        window = time_window or timedelta(hours=1)
        ago_str = f"{int(window.total_seconds())}s"

        comp_list = ", ".join(
            f"'{_sanitize_kql(c)}'" for c in components
        )
        query = (
            f"dependencies "
            f"| where timestamp > ago({ago_str}) "
            f"  and cloud_RoleName in ({comp_list}) "
            f"| summarize call_count=count() by "
            f"  caller=cloud_RoleName, target=target, "
            f"  dep_type=type, success=tostring(success) "
            f"| order by call_count desc "
            f"| take 50"
        )

        rows = await self._query_app_insights(query)
        dependencies: List[Dict[str, Any]] = []
        seen: set = set()

        for row in rows:
            target = row.get("target", "")
            if not target or target in seen:
                continue
            seen.add(target)

            dep_type = "standard"
            if row.get("success") == "False":
                dep_type = "critical"

            dependencies.append({
                "component_id": target,
                "relationship": "depends_on",
                "type": dep_type,
                "distance": 1,
                "caller": row.get("caller", ""),
                "call_count": row.get("call_count", 0),
            })

        return dependencies

    # ------------------------------------------------------------------
    # Internal Methods
    # ------------------------------------------------------------------

    def _is_configured(self) -> bool:
        """Check if we have valid Azure configuration."""
        return self._config is not None and self._config.is_configured

    async def _query_app_insights(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute a KQL query against Application Insights REST API.

        Args:
            query: KQL query string.

        Returns:
            List of row dictionaries.
        """
        if not self._config:
            return []

        client = await self._ensure_client()
        url = (
            f"{self._config.app_insights_endpoint}/apps/"
            f"{self._config.app_insights_app_id}/query"
        )

        try:
            response = await client.post(
                url,
                headers={
                    "x-api-key": self._config.app_insights_api_key,
                    "Content-Type": "application/json",
                },
                json={"query": query},
            )
            response.raise_for_status()
            return self._parse_query_response(response.json())

        except httpx.HTTPStatusError as e:
            logger.error(
                f"App Insights query failed (HTTP {e.response.status_code}): "
                f"{e.response.text[:200]}"
            )
            return []
        except httpx.RequestError as e:
            logger.error(f"App Insights connection error: {e}")
            return []

    async def _query_log_analytics(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute a KQL query against Log Analytics workspace.

        Args:
            query: KQL query string.

        Returns:
            List of row dictionaries.
        """
        if not self._config or not self._config.workspace_id:
            return []

        client = await self._ensure_client()
        url = (
            f"{self._config.log_analytics_endpoint}/workspaces/"
            f"{self._config.workspace_id}/query"
        )

        try:
            response = await client.post(
                url,
                headers={
                    "x-api-key": self._config.app_insights_api_key,
                    "Content-Type": "application/json",
                },
                json={"query": query},
            )
            response.raise_for_status()
            return self._parse_query_response(response.json())

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Log Analytics query failed (HTTP {e.response.status_code}): "
                f"{e.response.text[:200]}"
            )
            return []
        except httpx.RequestError as e:
            logger.error(f"Log Analytics connection error: {e}")
            return []

    def _parse_query_response(
        self, data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Parse Application Insights / Log Analytics query response.

        Response format:
        {
            "tables": [{
                "columns": [{"name": "col1", "type": "string"}, ...],
                "rows": [["val1", "val2", ...], ...]
            }]
        }
        """
        rows: List[Dict[str, Any]] = []
        tables = data.get("tables", [])
        if not tables:
            return rows

        table = tables[0]
        columns = [col["name"] for col in table.get("columns", [])]
        for raw_row in table.get("rows", []):
            row_dict = dict(zip(columns, raw_row))
            rows.append(row_dict)

        return rows

    def _convert_to_event(self, row: Dict[str, Any]) -> Event:
        """
        Convert a raw Application Insights row to a correlation Event.

        Maps standard App Insights columns to Event fields.
        """
        # Determine event_id
        event_id = (
            row.get("itemId")
            or row.get("operation_Id")
            or row.get("id")
            or f"evt_{hashlib.sha256(str(row).encode()).hexdigest()[:12]}"
        )

        # Determine event type
        item_type = str(row.get("itemType", row.get("type", ""))).lower()
        event_type = _TYPE_MAP.get(item_type, EventType.ALERT)

        # Determine severity
        sev_raw = str(row.get("severityLevel", row.get("severity", "1"))).lower()
        severity = _SEVERITY_MAP.get(sev_raw, EventSeverity.INFO)

        # Determine timestamp
        ts_raw = row.get("timestamp")
        if isinstance(ts_raw, str):
            try:
                timestamp = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                # Strip timezone for consistency with existing code
                timestamp = timestamp.replace(tzinfo=None)
            except ValueError:
                timestamp = datetime.utcnow()
        elif isinstance(ts_raw, datetime):
            timestamp = ts_raw
        else:
            timestamp = datetime.utcnow()

        # Title and description
        title = (
            row.get("name")
            or row.get("problemId")
            or row.get("message", "")[:100]
            or f"Event {event_id[:20]}"
        )
        description = row.get("message") or row.get("outerMessage") or ""

        # Source system
        source_system = row.get("cloud_RoleName") or row.get("appName") or "app-insights"

        # Affected components
        components = []
        role = row.get("cloud_RoleName")
        if role:
            components.append(role)
        target = row.get("target")
        if target:
            components.append(target)

        return Event(
            event_id=event_id,
            event_type=event_type,
            title=str(title)[:200],
            description=str(description)[:2000],
            severity=severity,
            timestamp=timestamp,
            source_system=source_system,
            affected_components=components,
            tags=_extract_tags(row),
            metadata=_extract_metadata(row),
            raw_data=row,
        )


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _sanitize_kql(value: str) -> str:
    """Sanitize a value for safe KQL interpolation (prevent injection)."""
    return value.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")


def _severity_to_level(severity: EventSeverity) -> int:
    """Convert EventSeverity to App Insights numeric level."""
    level_map = {
        EventSeverity.INFO: 1,
        EventSeverity.WARNING: 2,
        EventSeverity.ERROR: 3,
        EventSeverity.CRITICAL: 4,
    }
    return level_map.get(severity, 0)


def _extract_keywords(text: str) -> List[str]:
    """
    Extract meaningful keywords from text for KQL search.

    Filters out common stop words and short tokens.
    """
    stop_words = {
        "the", "a", "an", "is", "was", "are", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "must", "shall",
        "can", "need", "dare", "ought", "used", "to", "of", "in",
        "for", "on", "with", "at", "by", "from", "as", "into",
        "through", "during", "before", "after", "above", "below",
        "between", "out", "off", "over", "under", "again", "further",
        "then", "once", "here", "there", "when", "where", "why",
        "how", "all", "both", "each", "few", "more", "most", "other",
        "some", "such", "no", "nor", "not", "only", "own", "same",
        "so", "than", "too", "very", "and", "but", "or", "if",
        "while", "because", "until", "about", "this", "that", "it",
    }
    tokens = text.lower().split()
    return [
        t for t in tokens
        if len(t) >= 3 and t.isalpha() and t not in stop_words
    ]


def _calculate_keyword_similarity(text1: str, text2: str) -> float:
    """
    Calculate keyword overlap similarity between two texts.

    Uses Jaccard-like coefficient on keyword sets.
    """
    kw1 = set(_extract_keywords(text1))
    kw2 = set(_extract_keywords(text2))
    if not kw1 or not kw2:
        return 0.0
    intersection = kw1 & kw2
    union = kw1 | kw2
    return len(intersection) / len(union) if union else 0.0


def _extract_tags(row: Dict[str, Any]) -> List[str]:
    """Extract tags from App Insights row."""
    tags: List[str] = []
    item_type = row.get("itemType") or row.get("type")
    if item_type:
        tags.append(f"type:{item_type}")
    role = row.get("cloud_RoleName")
    if role:
        tags.append(f"service:{role}")
    op = row.get("operation_Name")
    if op:
        tags.append(f"operation:{op}")
    return tags


def _extract_metadata(row: Dict[str, Any]) -> Dict[str, Any]:
    """Extract useful metadata from App Insights row."""
    metadata: Dict[str, Any] = {}
    for key in (
        "operation_Id", "operation_Name", "operation_ParentId",
        "cloud_RoleName", "cloud_RoleInstance",
        "appId", "appName", "sdkVersion",
        "duration", "resultCode", "success",
    ):
        if key in row and row[key] is not None:
            metadata[key] = row[key]
    return metadata
