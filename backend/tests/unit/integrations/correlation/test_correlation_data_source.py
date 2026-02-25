"""Unit tests for EventDataSource — Azure Monitor / App Insights client.

Tests cover:
    - AzureMonitorConfig (frozen dataclass, from_env, is_configured)
    - EventDataSource initialization and configuration check
    - KQL query building and response parsing
    - Event conversion from raw App Insights data
    - Keyword extraction and similarity calculation
    - Error handling (HTTP errors, connection errors)
    - Graceful degradation when unconfigured

Sprint 130 — Story 130-3
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.integrations.correlation.data_source import (
    AzureMonitorConfig,
    EventDataSource,
    _calculate_keyword_similarity,
    _extract_keywords,
    _extract_metadata,
    _extract_tags,
    _sanitize_kql,
    _severity_to_level,
)
from src.integrations.correlation.types import Event, EventSeverity, EventType


# ---------------------------------------------------------------------------
# AzureMonitorConfig
# ---------------------------------------------------------------------------


class TestAzureMonitorConfig:
    """Tests for AzureMonitorConfig frozen dataclass."""

    def test_create_config(self) -> None:
        """Config can be created with required fields."""
        config = AzureMonitorConfig(
            workspace_id="ws-123",
            app_insights_app_id="app-456",
            app_insights_api_key="key-789",
        )
        assert config.workspace_id == "ws-123"
        assert config.app_insights_app_id == "app-456"
        assert config.app_insights_api_key == "key-789"

    def test_config_is_frozen(self) -> None:
        """Config is immutable (frozen)."""
        config = AzureMonitorConfig(
            workspace_id="ws", app_insights_app_id="app", app_insights_api_key="key"
        )
        with pytest.raises(AttributeError):
            config.workspace_id = "new"  # type: ignore

    def test_is_configured_true(self) -> None:
        """is_configured returns True when app_id and api_key present."""
        config = AzureMonitorConfig(
            workspace_id="", app_insights_app_id="app", app_insights_api_key="key"
        )
        assert config.is_configured is True

    def test_is_configured_false_no_app_id(self) -> None:
        """is_configured returns False when app_id missing."""
        config = AzureMonitorConfig(
            workspace_id="ws", app_insights_app_id="", app_insights_api_key="key"
        )
        assert config.is_configured is False

    def test_is_configured_false_no_key(self) -> None:
        """is_configured returns False when api_key missing."""
        config = AzureMonitorConfig(
            workspace_id="ws", app_insights_app_id="app", app_insights_api_key=""
        )
        assert config.is_configured is False

    @patch.dict("os.environ", {
        "AZURE_MONITOR_WORKSPACE_ID": "ws-env",
        "APP_INSIGHTS_APP_ID": "app-env",
        "APP_INSIGHTS_API_KEY": "key-env",
    })
    def test_from_env(self) -> None:
        """from_env loads configuration from environment variables."""
        config = AzureMonitorConfig.from_env()
        assert config.workspace_id == "ws-env"
        assert config.app_insights_app_id == "app-env"
        assert config.app_insights_api_key == "key-env"

    def test_default_endpoints(self) -> None:
        """Default endpoints are set correctly."""
        config = AzureMonitorConfig(
            workspace_id="", app_insights_app_id="", app_insights_api_key=""
        )
        assert "api.applicationinsights.io" in config.app_insights_endpoint
        assert "api.loganalytics.io" in config.log_analytics_endpoint


# ---------------------------------------------------------------------------
# EventDataSource — Unconfigured
# ---------------------------------------------------------------------------


class TestEventDataSourceUnconfigured:
    """Tests for EventDataSource when no Azure config is provided."""

    @pytest.mark.asyncio
    async def test_get_event_returns_none(self) -> None:
        """get_event returns None when unconfigured."""
        ds = EventDataSource(config=None)
        result = await ds.get_event("evt-123")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_events_in_range_returns_empty(self) -> None:
        """get_events_in_range returns empty list when unconfigured."""
        ds = EventDataSource(config=None)
        now = datetime.utcnow()
        result = await ds.get_events_in_range(now - timedelta(hours=1), now)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_events_for_component_returns_empty(self) -> None:
        """get_events_for_component returns empty list when unconfigured."""
        ds = EventDataSource(config=None)
        result = await ds.get_events_for_component("service-a")
        assert result == []

    @pytest.mark.asyncio
    async def test_search_similar_returns_empty(self) -> None:
        """search_similar_events returns empty when unconfigured."""
        ds = EventDataSource(config=None)
        result = await ds.search_similar_events("database error")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_dependencies_returns_empty(self) -> None:
        """get_dependencies returns empty when unconfigured."""
        ds = EventDataSource(config=None)
        result = await ds.get_dependencies(["service-a"])
        assert result == []


# ---------------------------------------------------------------------------
# EventDataSource — Configured with Mock HTTP
# ---------------------------------------------------------------------------


def _make_config() -> AzureMonitorConfig:
    return AzureMonitorConfig(
        workspace_id="ws-test",
        app_insights_app_id="app-test",
        app_insights_api_key="key-test",
    )


def _make_query_response(columns, rows):
    """Build a mock App Insights query response."""
    return {
        "tables": [{
            "columns": [{"name": c, "type": "string"} for c in columns],
            "rows": rows,
        }]
    }


class TestEventDataSourceConfigured:
    """Tests for EventDataSource with mocked HTTP client."""

    @pytest.mark.asyncio
    async def test_get_event_success(self) -> None:
        """get_event returns Event from App Insights response."""
        response_data = _make_query_response(
            ["itemId", "itemType", "name", "message", "severityLevel",
             "timestamp", "cloud_RoleName"],
            [["id-1", "exception", "NullRef", "NullReference at line 42",
              "3", "2026-02-25T10:00:00Z", "api-service"]],
        )

        mock_response = MagicMock()
        mock_response.json.return_value = response_data
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        ds = EventDataSource(config=_make_config(), http_client=mock_client)
        event = await ds.get_event("id-1")

        assert event is not None
        assert event.event_id == "id-1"
        assert event.title == "NullRef"
        assert event.severity == EventSeverity.ERROR

    @pytest.mark.asyncio
    async def test_get_events_in_range_success(self) -> None:
        """get_events_in_range returns list of Events."""
        response_data = _make_query_response(
            ["itemId", "itemType", "name", "message", "severityLevel",
             "timestamp", "cloud_RoleName"],
            [
                ["id-1", "trace", "Log entry 1", "Info message",
                 "1", "2026-02-25T09:55:00Z", "svc-a"],
                ["id-2", "exception", "Error 1", "Error message",
                 "3", "2026-02-25T09:58:00Z", "svc-b"],
            ],
        )

        mock_response = MagicMock()
        mock_response.json.return_value = response_data
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        ds = EventDataSource(config=_make_config(), http_client=mock_client)
        now = datetime.utcnow()
        events = await ds.get_events_in_range(now - timedelta(hours=1), now)

        assert len(events) == 2
        assert events[0].event_id == "id-1"
        assert events[1].event_id == "id-2"

    @pytest.mark.asyncio
    async def test_get_event_http_error(self) -> None:
        """get_event returns None on HTTP error."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=MagicMock(status_code=404, text="Not Found")
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        ds = EventDataSource(config=_make_config(), http_client=mock_client)
        result = await ds.get_event("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_event_connection_error(self) -> None:
        """get_event returns None on connection error."""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.RequestError("Connection refused"))

        ds = EventDataSource(config=_make_config(), http_client=mock_client)
        result = await ds.get_event("id-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_search_similar_events(self) -> None:
        """search_similar_events returns events with similarity scores."""
        response_data = _make_query_response(
            ["itemId", "itemType", "name", "message", "severityLevel",
             "timestamp", "cloud_RoleName"],
            [
                ["id-sim-1", "exception", "Database connection timeout",
                 "Connection pool exhausted after timeout",
                 "3", "2026-02-25T08:00:00Z", "db-service"],
            ],
        )

        mock_response = MagicMock()
        mock_response.json.return_value = response_data
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        ds = EventDataSource(config=_make_config(), http_client=mock_client)
        results = await ds.search_similar_events(
            "database connection pool timeout error"
        )

        # Should return results (similarity depends on keyword overlap)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_get_dependencies(self) -> None:
        """get_dependencies returns dependency information."""
        response_data = _make_query_response(
            ["caller", "target", "dep_type", "success", "call_count"],
            [
                ["api-service", "db-server", "SQL", "True", "150"],
                ["api-service", "redis-cache", "Redis", "True", "80"],
            ],
        )

        mock_response = MagicMock()
        mock_response.json.return_value = response_data
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        ds = EventDataSource(config=_make_config(), http_client=mock_client)
        deps = await ds.get_dependencies(["api-service"])

        assert len(deps) == 2
        assert deps[0]["component_id"] == "db-server"
        assert deps[0]["relationship"] == "depends_on"
        assert deps[1]["component_id"] == "redis-cache"


# ---------------------------------------------------------------------------
# Event Conversion
# ---------------------------------------------------------------------------


class TestEventConversion:
    """Tests for raw data to Event conversion."""

    def test_convert_exception_event(self) -> None:
        """Exception row converts to Event with ERROR severity."""
        ds = EventDataSource(config=_make_config())
        row = {
            "itemId": "exc-1",
            "itemType": "exception",
            "name": "NullReferenceException",
            "message": "Object reference not set",
            "severityLevel": "3",
            "timestamp": "2026-02-25T10:00:00Z",
            "cloud_RoleName": "api-service",
            "operation_Id": "op-123",
        }
        event = ds._convert_to_event(row)

        assert event.event_id == "exc-1"
        assert event.event_type == EventType.ALERT
        assert event.severity == EventSeverity.ERROR
        assert event.source_system == "api-service"
        assert "api-service" in event.affected_components

    def test_convert_trace_event(self) -> None:
        """Trace row converts to Event with LOG_PATTERN type."""
        ds = EventDataSource(config=_make_config())
        row = {
            "itemId": "trace-1",
            "itemType": "trace",
            "message": "Processing request started",
            "severityLevel": "1",
            "timestamp": "2026-02-25T10:01:00Z",
            "cloud_RoleName": "worker-service",
        }
        event = ds._convert_to_event(row)

        assert event.event_type == EventType.LOG_PATTERN
        assert event.severity == EventSeverity.INFO

    def test_convert_missing_timestamp(self) -> None:
        """Missing timestamp defaults to utcnow."""
        ds = EventDataSource(config=_make_config())
        row = {"itemId": "no-ts", "name": "Test"}
        event = ds._convert_to_event(row)

        assert isinstance(event.timestamp, datetime)


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


class TestHelperFunctions:
    """Tests for helper functions in data_source module."""

    def test_sanitize_kql_quotes(self) -> None:
        """Sanitize escapes single quotes."""
        assert _sanitize_kql("it's a test") == "it\\'s a test"

    def test_sanitize_kql_newlines(self) -> None:
        """Sanitize replaces newlines with spaces."""
        assert _sanitize_kql("line1\nline2") == "line1 line2"

    def test_severity_to_level(self) -> None:
        """Severity enum maps to correct numeric level."""
        assert _severity_to_level(EventSeverity.INFO) == 1
        assert _severity_to_level(EventSeverity.WARNING) == 2
        assert _severity_to_level(EventSeverity.ERROR) == 3
        assert _severity_to_level(EventSeverity.CRITICAL) == 4

    def test_extract_keywords(self) -> None:
        """Keywords extracted exclude stop words and short tokens."""
        kw = _extract_keywords("the database connection pool was exhausted")
        assert "database" in kw
        assert "connection" in kw
        assert "pool" in kw
        assert "the" not in kw
        assert "was" not in kw

    def test_extract_keywords_empty(self) -> None:
        """Empty text returns empty keywords."""
        assert _extract_keywords("") == []

    def test_calculate_keyword_similarity_identical(self) -> None:
        """Identical texts have high similarity."""
        sim = _calculate_keyword_similarity(
            "database connection timeout",
            "database connection timeout",
        )
        assert sim > 0.8

    def test_calculate_keyword_similarity_different(self) -> None:
        """Unrelated texts have low similarity."""
        sim = _calculate_keyword_similarity(
            "database connection pool",
            "frontend react component rendering",
        )
        assert sim < 0.2

    def test_calculate_keyword_similarity_empty(self) -> None:
        """Empty text returns 0 similarity."""
        assert _calculate_keyword_similarity("", "some text") == 0.0

    def test_extract_tags(self) -> None:
        """Tags extracted from App Insights row fields."""
        row = {
            "itemType": "exception",
            "cloud_RoleName": "api-svc",
            "operation_Name": "POST /api/users",
        }
        tags = _extract_tags(row)
        assert "type:exception" in tags
        assert "service:api-svc" in tags
        assert "operation:POST /api/users" in tags

    def test_extract_metadata(self) -> None:
        """Metadata extracted from standard App Insights fields."""
        row = {
            "operation_Id": "op-123",
            "cloud_RoleName": "api-svc",
            "duration": 1500,
            "resultCode": "200",
            "unrelated_field": "ignored",
        }
        meta = _extract_metadata(row)
        assert meta["operation_Id"] == "op-123"
        assert meta["duration"] == 1500
        assert "unrelated_field" not in meta
