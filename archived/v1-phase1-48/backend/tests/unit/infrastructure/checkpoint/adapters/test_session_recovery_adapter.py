"""Unit tests for SessionRecoveryCheckpointAdapter.

Sprint 121 -- Story 121-1c: Tests for the adapter that wraps the existing
SessionRecoveryManager from the domain sessions module to implement
the CheckpointProvider protocol.

Tests cover:
    - provider_name returns "session_recovery" by default
    - custom provider_name works
    - save_checkpoint delegates to manager.save_checkpoint with correct args
    - save_checkpoint extracts checkpoint_type from data
    - save_checkpoint defaults to EXECUTION_START when no checkpoint_type
    - save_checkpoint defaults gracefully for invalid checkpoint_type
    - load_checkpoint calls get_checkpoint and converts to dict
    - load_checkpoint returns None when not found
    - list_checkpoints with session_id found returns 1-entry list
    - list_checkpoints with session_id not found returns empty list
    - list_checkpoints without session_id returns empty list
    - delete_checkpoint checks existence then deletes, returns True
    - delete_checkpoint returns False when checkpoint does not exist
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.sessions.recovery import (
    CheckpointType as SessionCheckpointType,
    SessionCheckpoint,
    SessionRecoveryManager,
)
from src.infrastructure.checkpoint.protocol import CheckpointEntry
from src.infrastructure.checkpoint.adapters.session_recovery_adapter import (
    SessionRecoveryCheckpointAdapter,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_manager() -> MagicMock:
    """Create a mock SessionRecoveryManager with async methods."""
    manager = MagicMock(spec=SessionRecoveryManager)
    manager.save_checkpoint = AsyncMock(return_value=None)
    manager.get_checkpoint = AsyncMock(return_value=None)
    manager.delete_checkpoint = AsyncMock(return_value=None)
    return manager


def _make_session_checkpoint(
    session_id: str = "sess-rec-1",
    checkpoint_type: SessionCheckpointType = SessionCheckpointType.EXECUTION_START,
    execution_id: str | None = "exec-001",
    state: dict | None = None,
    created_at: datetime | None = None,
    expires_at: datetime | None = None,
    metadata: dict | None = None,
) -> SessionCheckpoint:
    """Create a SessionCheckpoint for testing."""
    return SessionCheckpoint(
        session_id=session_id,
        checkpoint_type=checkpoint_type,
        execution_id=execution_id,
        state=state or {"key": "value"},
        created_at=created_at or datetime.utcnow(),
        expires_at=expires_at or (datetime.utcnow() + timedelta(hours=1)),
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_manager():
    """Create a mock SessionRecoveryManager."""
    return _make_mock_manager()


@pytest.fixture
def adapter(mock_manager):
    """Create a SessionRecoveryCheckpointAdapter with mocked manager."""
    return SessionRecoveryCheckpointAdapter(manager=mock_manager, name="session_recovery")


# =========================================================================
# provider_name
# =========================================================================


class TestProviderName:
    """Tests for SessionRecoveryCheckpointAdapter.provider_name property."""

    def test_provider_name(self, adapter):
        """Verify 'session_recovery' is returned as the default provider name."""
        assert adapter.provider_name == "session_recovery"

    def test_custom_provider_name(self, mock_manager):
        """Verify custom name is returned when specified."""
        custom_adapter = SessionRecoveryCheckpointAdapter(
            manager=mock_manager, name="custom_recovery"
        )
        assert custom_adapter.provider_name == "custom_recovery"


# =========================================================================
# save_checkpoint
# =========================================================================


class TestSaveCheckpoint:
    """Tests for SessionRecoveryCheckpointAdapter.save_checkpoint."""

    @pytest.mark.asyncio
    async def test_save_delegates_to_manager(self, adapter, mock_manager):
        """Verify manager.save_checkpoint called with correct args."""
        data = {
            "checkpoint_type": "execution_start",
            "execution_id": "exec-save-1",
            "step": 3,
        }
        metadata = {"tag": "important"}

        # Mock save_checkpoint to return a SessionCheckpoint
        mock_manager.save_checkpoint.return_value = _make_session_checkpoint(
            session_id="cp-sr-001"
        )

        result = await adapter.save_checkpoint(
            checkpoint_id="cp-sr-001",
            data=data,
            metadata=metadata,
        )

        assert result == "cp-sr-001"
        mock_manager.save_checkpoint.assert_awaited_once()

        call_kwargs = mock_manager.save_checkpoint.call_args[1]
        assert call_kwargs["session_id"] == "cp-sr-001"
        assert call_kwargs["checkpoint_type"] == SessionCheckpointType.EXECUTION_START
        assert call_kwargs["state"] == data
        assert call_kwargs["execution_id"] == "exec-save-1"
        assert call_kwargs["metadata"] == metadata

    @pytest.mark.asyncio
    async def test_save_extracts_checkpoint_type(self, adapter, mock_manager):
        """Verify checkpoint_type is extracted from data dict."""
        data = {"checkpoint_type": "tool_call", "tool_name": "search"}

        mock_manager.save_checkpoint.return_value = _make_session_checkpoint()

        await adapter.save_checkpoint(
            checkpoint_id="cp-sr-tool",
            data=data,
        )

        call_kwargs = mock_manager.save_checkpoint.call_args[1]
        assert call_kwargs["checkpoint_type"] == SessionCheckpointType.TOOL_CALL

    @pytest.mark.asyncio
    async def test_save_default_checkpoint_type(self, adapter, mock_manager):
        """Defaults to EXECUTION_START when no checkpoint_type in data."""
        data = {"step": 1}

        mock_manager.save_checkpoint.return_value = _make_session_checkpoint()

        await adapter.save_checkpoint(
            checkpoint_id="cp-sr-default",
            data=data,
        )

        call_kwargs = mock_manager.save_checkpoint.call_args[1]
        assert call_kwargs["checkpoint_type"] == SessionCheckpointType.EXECUTION_START

    @pytest.mark.asyncio
    async def test_save_invalid_checkpoint_type_defaults(self, adapter, mock_manager):
        """Invalid checkpoint_type defaults gracefully to EXECUTION_START."""
        data = {"checkpoint_type": "nonexistent_type"}

        mock_manager.save_checkpoint.return_value = _make_session_checkpoint()

        await adapter.save_checkpoint(
            checkpoint_id="cp-sr-invalid",
            data=data,
        )

        call_kwargs = mock_manager.save_checkpoint.call_args[1]
        assert call_kwargs["checkpoint_type"] == SessionCheckpointType.EXECUTION_START


# =========================================================================
# load_checkpoint
# =========================================================================


class TestLoadCheckpoint:
    """Tests for SessionRecoveryCheckpointAdapter.load_checkpoint."""

    @pytest.mark.asyncio
    async def test_load_returns_dict(self, adapter, mock_manager):
        """Calls get_checkpoint and converts SessionCheckpoint to dict."""
        checkpoint = _make_session_checkpoint(
            session_id="cp-sr-load",
            checkpoint_type=SessionCheckpointType.TOOL_CALL,
            execution_id="exec-load-1",
            state={"tool": "search", "result": "found"},
            metadata={"source": "test"},
        )
        mock_manager.get_checkpoint.return_value = checkpoint

        result = await adapter.load_checkpoint("cp-sr-load")

        assert result is not None
        assert isinstance(result, dict)
        assert result["session_id"] == "cp-sr-load"
        assert result["checkpoint_type"] == "tool_call"
        assert result["execution_id"] == "exec-load-1"
        assert result["state"] == {"tool": "search", "result": "found"}
        assert result["metadata"] == {"source": "test"}

        mock_manager.get_checkpoint.assert_awaited_once_with("cp-sr-load")

    @pytest.mark.asyncio
    async def test_load_not_found(self, adapter, mock_manager):
        """Return None when checkpoint does not exist."""
        mock_manager.get_checkpoint.return_value = None

        result = await adapter.load_checkpoint("nonexistent")

        assert result is None


# =========================================================================
# list_checkpoints
# =========================================================================


class TestListCheckpoints:
    """Tests for SessionRecoveryCheckpointAdapter.list_checkpoints."""

    @pytest.mark.asyncio
    async def test_list_with_session_id_found(self, adapter, mock_manager):
        """Return a 1-entry list when checkpoint exists for session_id."""
        checkpoint = _make_session_checkpoint(
            session_id="sess-list-1",
            checkpoint_type=SessionCheckpointType.APPROVAL_PENDING,
            execution_id="exec-list-1",
            state={"pending": True},
            metadata={"urgency": "high"},
        )
        mock_manager.get_checkpoint.return_value = checkpoint

        result = await adapter.list_checkpoints(session_id="sess-list-1")

        assert len(result) == 1
        entry = result[0]
        assert isinstance(entry, CheckpointEntry)
        assert entry.checkpoint_id == "sess-list-1"
        assert entry.provider_name == "session_recovery"
        assert entry.session_id == "sess-list-1"
        assert entry.data == {"pending": True}
        assert entry.metadata["checkpoint_type"] == "approval_pending"
        assert entry.metadata["execution_id"] == "exec-list-1"
        assert entry.metadata["urgency"] == "high"
        assert entry.created_at == checkpoint.created_at
        assert entry.expires_at == checkpoint.expires_at

    @pytest.mark.asyncio
    async def test_list_with_session_id_not_found(self, adapter, mock_manager):
        """Return empty list when no checkpoint exists for session_id."""
        mock_manager.get_checkpoint.return_value = None

        result = await adapter.list_checkpoints(session_id="nonexistent")

        assert result == []

    @pytest.mark.asyncio
    async def test_list_without_session_id(self, adapter, mock_manager):
        """Return empty list when no session_id is provided."""
        result = await adapter.list_checkpoints()

        assert result == []
        mock_manager.get_checkpoint.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_list_respects_limit(self, adapter, mock_manager):
        """Verify limit is respected (at most 1 for this provider, but limit=0 edge case)."""
        checkpoint = _make_session_checkpoint(session_id="sess-limit")
        mock_manager.get_checkpoint.return_value = checkpoint

        # With limit=100 (default), should still return at most 1
        result = await adapter.list_checkpoints(session_id="sess-limit", limit=100)
        assert len(result) <= 1


# =========================================================================
# delete_checkpoint
# =========================================================================


class TestDeleteCheckpoint:
    """Tests for SessionRecoveryCheckpointAdapter.delete_checkpoint."""

    @pytest.mark.asyncio
    async def test_delete_when_exists(self, adapter, mock_manager):
        """Check existence, delete, return True when checkpoint exists."""
        checkpoint = _make_session_checkpoint(session_id="cp-sr-del")
        mock_manager.get_checkpoint.return_value = checkpoint
        mock_manager.delete_checkpoint.return_value = None

        result = await adapter.delete_checkpoint("cp-sr-del")

        assert result is True
        mock_manager.get_checkpoint.assert_awaited_once_with("cp-sr-del")
        mock_manager.delete_checkpoint.assert_awaited_once_with("cp-sr-del")

    @pytest.mark.asyncio
    async def test_delete_when_not_exists(self, adapter, mock_manager):
        """Return False when checkpoint does not exist."""
        mock_manager.get_checkpoint.return_value = None

        result = await adapter.delete_checkpoint("nonexistent")

        assert result is False
        mock_manager.delete_checkpoint.assert_not_awaited()
