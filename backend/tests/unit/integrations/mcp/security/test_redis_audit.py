"""Unit tests for RedisAuditStorage.

Sprint 120 -- Story 120-1: Tests for Redis-backed audit storage
for MCP operations, replacing InMemoryAuditStorage.

Tests cover:
    - Store event via zadd with timestamp score
    - Automatic trimming when exceeding max_size
    - Query with no filter, time filter, field filter, and pagination
    - delete_before using zremrangebyscore
    - count via zcard
    - clear via delete
    - Error handling for Redis failures
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.mcp.security.audit import (
    AuditEvent,
    AuditEventType,
    AuditFilter,
)
from src.integrations.mcp.security.redis_audit import RedisAuditStorage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(
    event_type: AuditEventType = AuditEventType.TOOL_EXECUTION,
    user_id: str = "user-1",
    server: str = "azure-mcp",
    tool: str = "list_vms",
    status: str = "success",
    timestamp: datetime | None = None,
    event_id: str | None = None,
) -> AuditEvent:
    """Create an AuditEvent with sensible defaults."""
    return AuditEvent(
        event_type=event_type,
        user_id=user_id,
        server=server,
        tool=tool,
        status=status,
        timestamp=timestamp or datetime.utcnow(),
        event_id=event_id or "evt-001",
    )


def _serialize_event(event: AuditEvent) -> str:
    """Serialize an AuditEvent to JSON string as Redis would store it."""
    return json.dumps(event.to_dict(), default=str, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_redis():
    """Create a mock async Redis client."""
    redis = AsyncMock()
    redis.zadd = AsyncMock()
    redis.zcard = AsyncMock(return_value=0)
    redis.zrangebyscore = AsyncMock(return_value=[])
    redis.zremrangebyscore = AsyncMock(return_value=0)
    redis.zremrangebyrank = AsyncMock()
    redis.delete = AsyncMock(return_value=1)
    return redis


@pytest.fixture
def storage(mock_redis):
    """Create a RedisAuditStorage with mocked Redis."""
    return RedisAuditStorage(
        redis_client=mock_redis,
        key="test:audit:events",
        max_size=100,
    )


# =========================================================================
# store
# =========================================================================


class TestStore:
    """Tests for RedisAuditStorage.store."""

    @pytest.mark.asyncio
    async def test_store_event_in_redis(self, storage, mock_redis):
        """Verify zadd is called with the event as JSON and timestamp as score."""
        event = _make_event()
        mock_redis.zcard.return_value = 1  # Under max_size

        result = await storage.store(event)

        assert result is True
        mock_redis.zadd.assert_awaited_once()
        call_args = mock_redis.zadd.call_args
        assert call_args[0][0] == "test:audit:events"
        mapping = call_args[0][1]
        assert len(mapping) == 1
        stored_json = list(mapping.keys())[0]
        score = list(mapping.values())[0]
        parsed = json.loads(stored_json)
        assert parsed["event_id"] == event.event_id
        assert parsed["event_type"] == event.event_type.value
        assert abs(score - event.timestamp.timestamp()) < 1.0

    @pytest.mark.asyncio
    async def test_store_trims_when_exceeds_max_size(self, storage, mock_redis):
        """Verify zremrangebyrank trims oldest when over max_size."""
        event = _make_event()
        mock_redis.zcard.return_value = 105  # Exceeds max_size=100

        result = await storage.store(event)

        assert result is True
        mock_redis.zremrangebyrank.assert_awaited_once_with(
            "test:audit:events", 0, 4  # 105 - 100 - 1 = 4
        )

    @pytest.mark.asyncio
    async def test_store_no_trim_under_max_size(self, storage, mock_redis):
        """No trimming when count is within limit."""
        event = _make_event()
        mock_redis.zcard.return_value = 50

        await storage.store(event)

        mock_redis.zremrangebyrank.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_redis_error_in_store_returns_false(self, storage, mock_redis):
        """Handle Redis errors gracefully by returning False."""
        import redis.asyncio as aioredis

        mock_redis.zadd.side_effect = aioredis.RedisError("Connection refused")
        event = _make_event()

        result = await storage.store(event)

        assert result is False


# =========================================================================
# query
# =========================================================================


class TestQuery:
    """Tests for RedisAuditStorage.query."""

    @pytest.mark.asyncio
    async def test_query_no_filter_returns_recent(self, storage, mock_redis):
        """Query without filter returns all events, newest first, capped at 100."""
        event = _make_event()
        mock_redis.zrangebyscore.return_value = [_serialize_event(event)]

        result = await storage.query()

        assert len(result) == 1
        assert result[0].event_id == event.event_id
        mock_redis.zrangebyscore.assert_awaited_once_with(
            "test:audit:events", "-inf", "+inf"
        )

    @pytest.mark.asyncio
    async def test_query_with_time_filter(self, storage, mock_redis):
        """Verify score range uses start_time and end_time from filter."""
        start = datetime(2026, 1, 1)
        end = datetime(2026, 1, 31)
        f = AuditFilter(start_time=start, end_time=end)

        mock_redis.zrangebyscore.return_value = []

        await storage.query(filter=f)

        mock_redis.zrangebyscore.assert_awaited_once_with(
            "test:audit:events",
            start.timestamp(),
            end.timestamp(),
        )

    @pytest.mark.asyncio
    async def test_query_with_field_filter(self, storage, mock_redis):
        """Verify AuditFilter.matches() filters events by user_id."""
        event_match = _make_event(user_id="target-user", event_id="evt-match")
        event_other = _make_event(user_id="other-user", event_id="evt-other")

        mock_redis.zrangebyscore.return_value = [
            _serialize_event(event_match),
            _serialize_event(event_other),
        ]

        f = AuditFilter(user_id="target-user")
        result = await storage.query(filter=f)

        assert len(result) == 1
        assert result[0].user_id == "target-user"

    @pytest.mark.asyncio
    async def test_query_pagination(self, storage, mock_redis):
        """Verify offset and limit from filter work correctly."""
        events = []
        for i in range(5):
            ts = datetime(2026, 1, 1, 10, i, 0)
            e = _make_event(
                event_id=f"evt-{i}",
                timestamp=ts,
            )
            events.append(_serialize_event(e))

        mock_redis.zrangebyscore.return_value = events

        f = AuditFilter(offset=1, limit=2)
        result = await storage.query(filter=f)

        # After sorting newest first and applying offset=1, limit=2
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_redis_error_in_query_returns_empty(self, storage, mock_redis):
        """Handle Redis errors in query gracefully by returning empty list."""
        import redis.asyncio as aioredis

        mock_redis.zrangebyscore.side_effect = aioredis.RedisError("Timeout")

        result = await storage.query()

        assert result == []


# =========================================================================
# delete_before
# =========================================================================


class TestDeleteBefore:
    """Tests for RedisAuditStorage.delete_before."""

    @pytest.mark.asyncio
    async def test_delete_before_uses_score(self, storage, mock_redis):
        """Verify zremrangebyscore uses correct score for timestamp."""
        cutoff = datetime(2026, 1, 15, 12, 0, 0)
        mock_redis.zremrangebyscore.return_value = 5

        result = await storage.delete_before(cutoff)

        assert result == 5
        mock_redis.zremrangebyscore.assert_awaited_once_with(
            "test:audit:events",
            "-inf",
            f"({cutoff.timestamp()}",
        )


# =========================================================================
# count
# =========================================================================


class TestCount:
    """Tests for RedisAuditStorage.count."""

    @pytest.mark.asyncio
    async def test_count_returns_zcard(self, storage, mock_redis):
        """Verify count delegates to zcard."""
        mock_redis.zcard.return_value = 42

        result = await storage.count()

        assert result == 42
        mock_redis.zcard.assert_awaited_with("test:audit:events")


# =========================================================================
# clear
# =========================================================================


class TestClear:
    """Tests for RedisAuditStorage.clear."""

    @pytest.mark.asyncio
    async def test_clear_deletes_key(self, storage, mock_redis):
        """Verify the sorted set key is deleted."""
        await storage.clear()

        mock_redis.delete.assert_awaited_once_with("test:audit:events")
