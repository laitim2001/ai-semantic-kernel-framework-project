"""Unit tests for RedisSwitchCheckpointStorage.

Sprint 120 -- Story 120-1: Tests for Redis-backed checkpoint storage
for ModeSwitcher, replacing InMemoryCheckpointStorage.

Tests cover:
    - Save / get / delete checkpoint lifecycle
    - Session-based indexing (sadd / srem / smembers)
    - Stale index cleanup
    - Latest checkpoint retrieval
    - Clear operation via scan_iter
    - Error handling for Redis failures and corrupt data
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.hybrid.switching.models import SwitchCheckpoint
from src.integrations.hybrid.switching.redis_checkpoint import (
    RedisSwitchCheckpointStorage,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_checkpoint(
    checkpoint_id: str = "cp-001",
    switch_id: str = "sw-001",
    mode_before: str = "chat",
    session_id: str | None = "sess-001",
    created_at: datetime | None = None,
) -> SwitchCheckpoint:
    """Create a SwitchCheckpoint with sensible defaults for testing."""
    context_snapshot = {}
    if session_id is not None:
        context_snapshot["session_id"] = session_id
    return SwitchCheckpoint(
        checkpoint_id=checkpoint_id,
        switch_id=switch_id,
        context_snapshot=context_snapshot,
        mode_before=mode_before,
        created_at=created_at or datetime.utcnow(),
    )


# ---------------------------------------------------------------------------
# Async iterator helper for scan_iter mock
# ---------------------------------------------------------------------------


class _AsyncIter:
    """Async iterator wrapper for mocking scan_iter."""

    def __init__(self, items):
        self._items = list(items)
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._index]
        self._index += 1
        return item


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_redis():
    """Create a mock async Redis client with all required methods."""
    redis = AsyncMock()
    redis.setex = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.delete = AsyncMock(return_value=1)
    redis.sadd = AsyncMock()
    redis.srem = AsyncMock()
    redis.smembers = AsyncMock(return_value=set())
    redis.expire = AsyncMock()
    redis.scan_iter = MagicMock(return_value=_AsyncIter([]))
    return redis


@pytest.fixture
def storage(mock_redis):
    """Create a RedisSwitchCheckpointStorage with mocked Redis."""
    return RedisSwitchCheckpointStorage(
        redis_client=mock_redis,
        key_prefix="test_switch_cp",
        ttl_seconds=3600,
    )


# =========================================================================
# save_checkpoint
# =========================================================================


class TestSaveCheckpoint:
    """Tests for RedisSwitchCheckpointStorage.save_checkpoint."""

    @pytest.mark.asyncio
    async def test_save_checkpoint_stores_in_redis(self, storage, mock_redis):
        """Verify setex is called with the correct key, TTL, and JSON data."""
        cp = _make_checkpoint(session_id=None)

        result = await storage.save_checkpoint(cp)

        assert result == cp.checkpoint_id
        mock_redis.setex.assert_awaited_once()
        call_args = mock_redis.setex.call_args
        key = call_args[0][0]
        ttl = call_args[0][1]
        data = call_args[0][2]
        assert key == f"test_switch_cp:{cp.checkpoint_id}"
        assert ttl == 3600
        parsed = json.loads(data)
        assert parsed["checkpoint_id"] == cp.checkpoint_id
        assert parsed["switch_id"] == cp.switch_id

    @pytest.mark.asyncio
    async def test_save_checkpoint_with_session_id_updates_index(
        self, storage, mock_redis
    ):
        """Verify sadd and expire are called when session_id is present."""
        cp = _make_checkpoint(session_id="sess-abc")

        await storage.save_checkpoint(cp)

        session_key = "test_switch_cp:session:sess-abc"
        mock_redis.sadd.assert_awaited_once_with(
            session_key, cp.checkpoint_id
        )
        mock_redis.expire.assert_awaited_once_with(session_key, 3600)

    @pytest.mark.asyncio
    async def test_save_checkpoint_without_session_id_skips_index(
        self, storage, mock_redis
    ):
        """No sadd should be called when context_snapshot lacks session_id."""
        cp = _make_checkpoint(session_id=None)

        await storage.save_checkpoint(cp)

        mock_redis.sadd.assert_not_awaited()
        mock_redis.expire.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_redis_error_in_save_raises(self, storage, mock_redis):
        """Verify that RedisError in save propagates to the caller."""
        import redis.asyncio as aioredis

        mock_redis.setex.side_effect = aioredis.RedisError("Connection lost")
        cp = _make_checkpoint()

        with pytest.raises(aioredis.RedisError, match="Connection lost"):
            await storage.save_checkpoint(cp)


# =========================================================================
# get_checkpoint
# =========================================================================


class TestGetCheckpoint:
    """Tests for RedisSwitchCheckpointStorage.get_checkpoint."""

    @pytest.mark.asyncio
    async def test_get_checkpoint_found(self, storage, mock_redis):
        """Return deserialized SwitchCheckpoint when key exists."""
        cp = _make_checkpoint()
        mock_redis.get.return_value = json.dumps(
            cp.to_dict(), default=str
        )

        result = await storage.get_checkpoint(cp.checkpoint_id)

        assert result is not None
        assert result.checkpoint_id == cp.checkpoint_id
        assert result.switch_id == cp.switch_id
        assert result.mode_before == cp.mode_before
        mock_redis.get.assert_awaited_once_with(
            f"test_switch_cp:{cp.checkpoint_id}"
        )

    @pytest.mark.asyncio
    async def test_get_checkpoint_not_found(self, storage, mock_redis):
        """Return None when key does not exist in Redis."""
        mock_redis.get.return_value = None

        result = await storage.get_checkpoint("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_checkpoint_invalid_json(self, storage, mock_redis):
        """Return None and handle corrupt data gracefully."""
        mock_redis.get.return_value = "not-valid-json{{"

        result = await storage.get_checkpoint("corrupt-id")

        assert result is None

    @pytest.mark.asyncio
    async def test_redis_error_in_get_returns_none(self, storage, mock_redis):
        """Handle Redis errors in get gracefully by returning None."""
        import redis.asyncio as aioredis

        mock_redis.get.side_effect = aioredis.RedisError("Timeout")

        result = await storage.get_checkpoint("any-id")

        assert result is None


# =========================================================================
# delete_checkpoint
# =========================================================================


class TestDeleteCheckpoint:
    """Tests for RedisSwitchCheckpointStorage.delete_checkpoint."""

    @pytest.mark.asyncio
    async def test_delete_checkpoint_exists(self, storage, mock_redis):
        """Return True and clean session index when checkpoint is deleted."""
        cp = _make_checkpoint(session_id="sess-del")
        mock_redis.get.return_value = json.dumps(
            cp.to_dict(), default=str
        )
        mock_redis.delete.return_value = 1

        result = await storage.delete_checkpoint(cp.checkpoint_id)

        assert result is True
        mock_redis.delete.assert_awaited()
        mock_redis.srem.assert_awaited_once_with(
            "test_switch_cp:session:sess-del",
            cp.checkpoint_id,
        )

    @pytest.mark.asyncio
    async def test_delete_checkpoint_not_exists(self, storage, mock_redis):
        """Return False when checkpoint does not exist."""
        mock_redis.get.return_value = None
        mock_redis.delete.return_value = 0

        result = await storage.delete_checkpoint("nonexistent")

        assert result is False


# =========================================================================
# list_checkpoints
# =========================================================================


class TestListCheckpoints:
    """Tests for RedisSwitchCheckpointStorage.list_checkpoints."""

    @pytest.mark.asyncio
    async def test_list_checkpoints_returns_all_for_session(
        self, storage, mock_redis
    ):
        """Return all checkpoints found via the session index."""
        cp1 = _make_checkpoint(checkpoint_id="cp-1")
        cp2 = _make_checkpoint(checkpoint_id="cp-2")

        mock_redis.smembers.return_value = {"cp-1", "cp-2"}

        # Mock sequential get calls
        async def _get_side_effect(key):
            if "cp-1" in key:
                return json.dumps(cp1.to_dict(), default=str)
            if "cp-2" in key:
                return json.dumps(cp2.to_dict(), default=str)
            return None

        mock_redis.get.side_effect = _get_side_effect

        result = await storage.list_checkpoints("sess-001")

        assert len(result) == 2
        ids = {cp.checkpoint_id for cp in result}
        assert ids == {"cp-1", "cp-2"}

    @pytest.mark.asyncio
    async def test_list_checkpoints_cleans_stale_entries(
        self, storage, mock_redis
    ):
        """Verify srem is called for stale session index entries."""
        mock_redis.smembers.return_value = {"cp-good", "cp-stale"}

        cp_good = _make_checkpoint(checkpoint_id="cp-good")

        async def _get_side_effect(key):
            if "cp-good" in key:
                return json.dumps(cp_good.to_dict(), default=str)
            return None  # cp-stale is missing

        mock_redis.get.side_effect = _get_side_effect

        result = await storage.list_checkpoints("sess-001")

        assert len(result) == 1
        assert result[0].checkpoint_id == "cp-good"
        mock_redis.srem.assert_awaited_once_with(
            "test_switch_cp:session:sess-001",
            "cp-stale",
        )


# =========================================================================
# get_latest_checkpoint
# =========================================================================


class TestGetLatestCheckpoint:
    """Tests for RedisSwitchCheckpointStorage.get_latest_checkpoint."""

    @pytest.mark.asyncio
    async def test_get_latest_checkpoint(self, storage, mock_redis):
        """Return the checkpoint with the latest created_at."""
        older = datetime(2026, 1, 1, 10, 0, 0)
        newer = datetime(2026, 2, 1, 10, 0, 0)
        cp_old = _make_checkpoint(checkpoint_id="cp-old", created_at=older)
        cp_new = _make_checkpoint(checkpoint_id="cp-new", created_at=newer)

        mock_redis.smembers.return_value = {"cp-old", "cp-new"}

        async def _get_side_effect(key):
            if "cp-old" in key:
                return json.dumps(cp_old.to_dict(), default=str)
            if "cp-new" in key:
                return json.dumps(cp_new.to_dict(), default=str)
            return None

        mock_redis.get.side_effect = _get_side_effect

        result = await storage.get_latest_checkpoint("sess-001")

        assert result is not None
        assert result.checkpoint_id == "cp-new"

    @pytest.mark.asyncio
    async def test_get_latest_checkpoint_empty(self, storage, mock_redis):
        """Return None when session has no checkpoints."""
        mock_redis.smembers.return_value = set()

        result = await storage.get_latest_checkpoint("sess-empty")

        assert result is None


# =========================================================================
# clear
# =========================================================================


class TestClear:
    """Tests for RedisSwitchCheckpointStorage.clear."""

    @pytest.mark.asyncio
    async def test_clear_scans_and_deletes(self, storage, mock_redis):
        """Verify scan_iter + delete is called for all matching keys."""
        keys = [b"test_switch_cp:cp-1", b"test_switch_cp:session:sess-1"]
        mock_redis.scan_iter = MagicMock(
            return_value=_AsyncIter(keys)
        )

        await storage.clear()

        assert mock_redis.delete.await_count == 2
