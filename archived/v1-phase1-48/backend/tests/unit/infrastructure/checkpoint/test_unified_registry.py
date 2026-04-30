"""Unit tests for UnifiedCheckpointRegistry.

Sprint 120 -- Story 120-2: Tests for the central registry that coordinates
the platform's 4 independent checkpoint systems.

Tests cover:
    - Provider registration and unregistration
    - Duplicate registration raises ValueError
    - Save / load / delete delegation to providers
    - Unknown provider raises ValueError
    - list_all aggregation across providers
    - Graceful handling of provider errors in list_all
    - cleanup_expired logic
    - get_stats statistics retrieval
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from src.infrastructure.checkpoint.protocol import CheckpointEntry, CheckpointProvider
from src.infrastructure.checkpoint.unified_registry import UnifiedCheckpointRegistry


# ---------------------------------------------------------------------------
# Helper: Mock CheckpointProvider
# ---------------------------------------------------------------------------


def _make_mock_provider(name: str = "test_provider") -> MagicMock:
    """Create a MagicMock that satisfies CheckpointProvider protocol."""
    provider = MagicMock()
    type(provider).provider_name = PropertyMock(return_value=name)
    provider.save_checkpoint = AsyncMock(return_value="cp-001")
    provider.load_checkpoint = AsyncMock(return_value={"data": "test"})
    provider.list_checkpoints = AsyncMock(return_value=[])
    provider.delete_checkpoint = AsyncMock(return_value=True)
    return provider


def _make_entry(
    checkpoint_id: str = "cp-001",
    provider_name: str = "test",
    session_id: str = "sess-1",
    created_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> CheckpointEntry:
    """Create a CheckpointEntry for testing."""
    return CheckpointEntry(
        checkpoint_id=checkpoint_id,
        provider_name=provider_name,
        session_id=session_id,
        data={"state": "active"},
        created_at=created_at or datetime.utcnow(),
        expires_at=expires_at,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def registry():
    """Create a fresh UnifiedCheckpointRegistry."""
    return UnifiedCheckpointRegistry()


# =========================================================================
# Provider Management
# =========================================================================


class TestProviderManagement:
    """Tests for register, unregister, and list_providers."""

    @pytest.mark.asyncio
    async def test_register_provider(self, registry):
        """Register a provider and verify it appears in list_providers."""
        provider = _make_mock_provider("hybrid")

        await registry.register_provider(provider)

        assert "hybrid" in registry.list_providers()

    @pytest.mark.asyncio
    async def test_register_duplicate_raises(self, registry):
        """Registering two providers with the same name raises ValueError."""
        provider1 = _make_mock_provider("hybrid")
        provider2 = _make_mock_provider("hybrid")

        await registry.register_provider(provider1)

        with pytest.raises(ValueError, match="already registered"):
            await registry.register_provider(provider2)

    @pytest.mark.asyncio
    async def test_unregister_provider(self, registry):
        """Unregister a provider and verify it is removed."""
        provider = _make_mock_provider("hybrid")
        await registry.register_provider(provider)

        await registry.unregister_provider("hybrid")

        assert "hybrid" not in registry.list_providers()

    @pytest.mark.asyncio
    async def test_unregister_not_found_raises(self, registry):
        """Unregistering a non-existent provider raises ValueError."""
        with pytest.raises(ValueError, match="not registered"):
            await registry.unregister_provider("nonexistent")


# =========================================================================
# Save
# =========================================================================


class TestSave:
    """Tests for UnifiedCheckpointRegistry.save."""

    @pytest.mark.asyncio
    async def test_save_delegates_to_provider(self, registry):
        """Verify save calls provider.save_checkpoint with correct arguments."""
        provider = _make_mock_provider("hybrid")
        await registry.register_provider(provider)

        result = await registry.save(
            provider_name="hybrid",
            checkpoint_id="cp-100",
            data={"key": "value"},
            metadata={"tag": "test"},
        )

        assert result == "cp-001"  # Mocked return
        provider.save_checkpoint.assert_awaited_once_with(
            checkpoint_id="cp-100",
            data={"key": "value"},
            metadata={"tag": "test"},
        )

    @pytest.mark.asyncio
    async def test_save_unknown_provider_raises(self, registry):
        """Saving to an unknown provider raises ValueError."""
        with pytest.raises(ValueError, match="not registered"):
            await registry.save("unknown", "cp-1", {"data": "x"})


# =========================================================================
# Load
# =========================================================================


class TestLoad:
    """Tests for UnifiedCheckpointRegistry.load."""

    @pytest.mark.asyncio
    async def test_load_found(self, registry):
        """Return data from provider when checkpoint exists."""
        provider = _make_mock_provider("hybrid")
        provider.load_checkpoint.return_value = {"state": "loaded"}
        await registry.register_provider(provider)

        result = await registry.load("hybrid", "cp-100")

        assert result == {"state": "loaded"}
        provider.load_checkpoint.assert_awaited_once_with(
            checkpoint_id="cp-100"
        )

    @pytest.mark.asyncio
    async def test_load_not_found(self, registry):
        """Return None when checkpoint does not exist."""
        provider = _make_mock_provider("hybrid")
        provider.load_checkpoint.return_value = None
        await registry.register_provider(provider)

        result = await registry.load("hybrid", "nonexistent")

        assert result is None


# =========================================================================
# Delete
# =========================================================================


class TestDelete:
    """Tests for UnifiedCheckpointRegistry.delete."""

    @pytest.mark.asyncio
    async def test_delete_found(self, registry):
        """Return True when checkpoint is successfully deleted."""
        provider = _make_mock_provider("hybrid")
        provider.delete_checkpoint.return_value = True
        await registry.register_provider(provider)

        result = await registry.delete("hybrid", "cp-100")

        assert result is True
        provider.delete_checkpoint.assert_awaited_once_with(
            checkpoint_id="cp-100"
        )

    @pytest.mark.asyncio
    async def test_delete_not_found(self, registry):
        """Return False when checkpoint does not exist."""
        provider = _make_mock_provider("hybrid")
        provider.delete_checkpoint.return_value = False
        await registry.register_provider(provider)

        result = await registry.delete("hybrid", "nonexistent")

        assert result is False


# =========================================================================
# list_all
# =========================================================================


class TestListAll:
    """Tests for UnifiedCheckpointRegistry.list_all."""

    @pytest.mark.asyncio
    async def test_list_all_aggregates(self, registry):
        """Multiple providers, verify results from all are aggregated."""
        provider_a = _make_mock_provider("alpha")
        provider_b = _make_mock_provider("beta")
        entry_a = _make_entry(checkpoint_id="cp-a", provider_name="alpha")
        entry_b = _make_entry(checkpoint_id="cp-b", provider_name="beta")
        provider_a.list_checkpoints.return_value = [entry_a]
        provider_b.list_checkpoints.return_value = [entry_b]

        await registry.register_provider(provider_a)
        await registry.register_provider(provider_b)

        result = await registry.list_all()

        assert "alpha" in result
        assert "beta" in result
        assert len(result["alpha"]) == 1
        assert len(result["beta"]) == 1
        assert result["alpha"][0].checkpoint_id == "cp-a"
        assert result["beta"][0].checkpoint_id == "cp-b"

    @pytest.mark.asyncio
    async def test_list_all_handles_provider_error(self, registry):
        """One provider fails, others still return results."""
        provider_ok = _make_mock_provider("ok_provider")
        provider_fail = _make_mock_provider("fail_provider")
        entry = _make_entry(provider_name="ok_provider")
        provider_ok.list_checkpoints.return_value = [entry]
        provider_fail.list_checkpoints.side_effect = RuntimeError("DB down")

        await registry.register_provider(provider_ok)
        await registry.register_provider(provider_fail)

        result = await registry.list_all()

        assert len(result["ok_provider"]) == 1
        assert result["fail_provider"] == []

    @pytest.mark.asyncio
    async def test_list_all_with_session_filter(self, registry):
        """Verify session_id and limit are passed to providers."""
        provider = _make_mock_provider("hybrid")
        provider.list_checkpoints.return_value = []
        await registry.register_provider(provider)

        await registry.list_all(session_id="sess-abc", limit=50)

        provider.list_checkpoints.assert_awaited_once_with(
            session_id="sess-abc",
            limit=50,
        )


# =========================================================================
# cleanup_expired
# =========================================================================


class TestCleanupExpired:
    """Tests for UnifiedCheckpointRegistry.cleanup_expired."""

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, registry):
        """Verify deletion of old checkpoints across providers."""
        provider = _make_mock_provider("hybrid")

        # Create an old entry that should be cleaned up
        old_entry = _make_entry(
            checkpoint_id="cp-old",
            created_at=datetime.utcnow() - timedelta(hours=48),
        )
        # Create a recent entry that should be kept
        recent_entry = _make_entry(
            checkpoint_id="cp-recent",
            created_at=datetime.utcnow(),
        )

        provider.list_checkpoints.return_value = [old_entry, recent_entry]
        provider.delete_checkpoint.return_value = True
        await registry.register_provider(provider)

        result = await registry.cleanup_expired(max_age_hours=24)

        assert result["hybrid"] == 1
        provider.delete_checkpoint.assert_awaited_once_with("cp-old")

    @pytest.mark.asyncio
    async def test_cleanup_expired_with_expires_at(self, registry):
        """Verify entries with expired expires_at are also cleaned."""
        provider = _make_mock_provider("hybrid")

        expired_entry = _make_entry(
            checkpoint_id="cp-expired",
            created_at=datetime.utcnow(),  # Recent creation
            expires_at=datetime.utcnow() - timedelta(hours=1),  # But expired
        )

        provider.list_checkpoints.return_value = [expired_entry]
        provider.delete_checkpoint.return_value = True
        await registry.register_provider(provider)

        result = await registry.cleanup_expired(max_age_hours=168)  # 7 days

        assert result["hybrid"] == 1


# =========================================================================
# get_stats
# =========================================================================


class TestGetStats:
    """Tests for UnifiedCheckpointRegistry.get_stats."""

    @pytest.mark.asyncio
    async def test_get_stats(self, registry):
        """Verify provider stats are returned correctly."""
        provider = _make_mock_provider("hybrid")
        entries = [_make_entry() for _ in range(3)]
        provider.list_checkpoints.return_value = entries
        await registry.register_provider(provider)

        stats = await registry.get_stats()

        assert stats["provider_count"] == 1
        assert "hybrid" in stats["provider_names"]
        assert stats["providers"]["hybrid"]["registered"] is True
        assert stats["providers"]["hybrid"]["checkpoint_count"] == 3

    @pytest.mark.asyncio
    async def test_get_stats_handles_provider_error(self, registry):
        """Verify stats report errors gracefully when provider fails."""
        provider = _make_mock_provider("broken")
        provider.list_checkpoints.side_effect = RuntimeError("Crash")
        await registry.register_provider(provider)

        stats = await registry.get_stats()

        assert stats["providers"]["broken"]["checkpoint_count"] == -1
        assert "error" in stats["providers"]["broken"]
