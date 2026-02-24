"""Unit tests for AgentFrameworkCheckpointAdapter.

Sprint 121 -- Story 121-1a: Tests for the adapter that wraps the existing
BaseCheckpointStorage from the agent_framework multiturn module to implement
the CheckpointProvider protocol.

Tests cover:
    - provider_name returns "agent_framework" by default
    - custom provider_name works
    - save_checkpoint delegates to storage.save with correct session_id and payload
    - save_checkpoint preserves metadata in the saved envelope
    - load_checkpoint returns unified_data when present
    - load_checkpoint returns raw data when no unified_data key (backward compat)
    - load_checkpoint returns None when not found
    - list_checkpoints lists all session_ids and converts to CheckpointEntry
    - list_checkpoints applies session_id filter
    - list_checkpoints applies limit
    - list_checkpoints gracefully skips sessions that fail to load
    - delete_checkpoint delegates to storage.delete
    - delete_checkpoint returns False when not found
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.infrastructure.checkpoint.protocol import CheckpointEntry
from src.integrations.agent_framework.multiturn.checkpoint_storage import (
    BaseCheckpointStorage,
)
from src.infrastructure.checkpoint.adapters.agent_framework_adapter import (
    AgentFrameworkCheckpointAdapter,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_storage() -> MagicMock:
    """Create a mock BaseCheckpointStorage with async methods."""
    storage = MagicMock(spec=BaseCheckpointStorage)
    storage.save = AsyncMock(return_value=None)
    storage.load = AsyncMock(return_value=None)
    storage.delete = AsyncMock(return_value=True)
    storage.list = AsyncMock(return_value=[])
    return storage


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_storage():
    """Create a mock storage backend."""
    return _make_mock_storage()


@pytest.fixture
def adapter(mock_storage):
    """Create an AgentFrameworkCheckpointAdapter with mocked storage."""
    return AgentFrameworkCheckpointAdapter(storage=mock_storage, name="agent_framework")


# =========================================================================
# provider_name
# =========================================================================


class TestProviderName:
    """Tests for AgentFrameworkCheckpointAdapter.provider_name property."""

    def test_provider_name(self, adapter):
        """Verify 'agent_framework' is returned as the default provider name."""
        assert adapter.provider_name == "agent_framework"

    def test_custom_provider_name(self, mock_storage):
        """Verify custom name is returned when specified."""
        custom_adapter = AgentFrameworkCheckpointAdapter(
            storage=mock_storage, name="custom_af"
        )
        assert custom_adapter.provider_name == "custom_af"


# =========================================================================
# save_checkpoint
# =========================================================================


class TestSaveCheckpoint:
    """Tests for AgentFrameworkCheckpointAdapter.save_checkpoint."""

    @pytest.mark.asyncio
    async def test_save_delegates_to_storage(self, adapter, mock_storage):
        """Verify storage.save is called with correct session_id and envelope data."""
        data = {"session_id": "sess-af-1", "step": 5}
        metadata = {"tag": "important"}

        result = await adapter.save_checkpoint(
            checkpoint_id="cp-af-001",
            data=data,
            metadata=metadata,
        )

        assert result == "cp-af-001"
        mock_storage.save.assert_awaited_once()

        # Verify the call arguments: save(session_id, payload)
        call_args = mock_storage.save.call_args
        saved_session_id = call_args[0][0]
        saved_payload = call_args[0][1]

        assert saved_session_id == "cp-af-001"
        assert saved_payload["unified_data"] == data
        assert saved_payload["metadata"] == metadata

    @pytest.mark.asyncio
    async def test_save_preserves_metadata(self, adapter, mock_storage):
        """Verify metadata is included in the saved envelope when provided."""
        data = {"key": "value"}
        metadata = {"version": 3, "source": "test"}

        await adapter.save_checkpoint(
            checkpoint_id="cp-af-meta",
            data=data,
            metadata=metadata,
        )

        call_args = mock_storage.save.call_args
        saved_payload = call_args[0][1]
        assert saved_payload["metadata"] == {"version": 3, "source": "test"}

    @pytest.mark.asyncio
    async def test_save_default_metadata_empty(self, adapter, mock_storage):
        """Verify metadata defaults to empty dict when not provided."""
        data = {"key": "value"}

        await adapter.save_checkpoint(
            checkpoint_id="cp-af-no-meta",
            data=data,
        )

        call_args = mock_storage.save.call_args
        saved_payload = call_args[0][1]
        assert saved_payload["metadata"] == {}


# =========================================================================
# load_checkpoint
# =========================================================================


class TestLoadCheckpoint:
    """Tests for AgentFrameworkCheckpointAdapter.load_checkpoint."""

    @pytest.mark.asyncio
    async def test_load_returns_unified_data(self, adapter, mock_storage):
        """Return unified_data when present in loaded payload."""
        unified_data = {"session_id": "sess-1", "step": 5}
        mock_storage.load.return_value = {
            "unified_data": unified_data,
            "metadata": {"tag": "info"},
        }

        result = await adapter.load_checkpoint("cp-af-001")

        assert result == unified_data
        mock_storage.load.assert_awaited_once_with("cp-af-001")

    @pytest.mark.asyncio
    async def test_load_returns_raw_data_without_unified_key(self, adapter, mock_storage):
        """Return full raw payload when no unified_data key for backward compat."""
        raw_data = {"old_format": True, "state": "legacy"}
        mock_storage.load.return_value = raw_data

        result = await adapter.load_checkpoint("cp-af-legacy")

        assert result == raw_data
        assert result.get("old_format") is True

    @pytest.mark.asyncio
    async def test_load_not_found(self, adapter, mock_storage):
        """Return None when checkpoint does not exist."""
        mock_storage.load.return_value = None

        result = await adapter.load_checkpoint("nonexistent")

        assert result is None


# =========================================================================
# list_checkpoints
# =========================================================================


class TestListCheckpoints:
    """Tests for AgentFrameworkCheckpointAdapter.list_checkpoints."""

    @pytest.mark.asyncio
    async def test_list_checkpoints_all(self, adapter, mock_storage):
        """List all session_ids, load and convert each to CheckpointEntry."""
        mock_storage.list.return_value = ["sess-1", "sess-2"]
        mock_storage.load.side_effect = [
            {"unified_data": {"key": "val1"}, "metadata": {"tag": "a"}},
            {"unified_data": {"key": "val2"}, "metadata": {"tag": "b"}},
        ]

        result = await adapter.list_checkpoints()

        assert len(result) == 2
        assert all(isinstance(e, CheckpointEntry) for e in result)
        assert result[0].checkpoint_id == "sess-1"
        assert result[0].provider_name == "agent_framework"
        assert result[0].data == {"key": "val1"}
        assert result[0].metadata == {"tag": "a"}
        assert result[1].checkpoint_id == "sess-2"
        assert result[1].data == {"key": "val2"}

        mock_storage.list.assert_awaited_once_with("*")

    @pytest.mark.asyncio
    async def test_list_checkpoints_with_session_filter(self, adapter, mock_storage):
        """Only return entries matching the session_id filter."""
        mock_storage.list.return_value = ["sess-1", "sess-2", "sess-3"]
        mock_storage.load.return_value = {
            "unified_data": {"filtered": True},
            "metadata": {},
        }

        result = await adapter.list_checkpoints(session_id="sess-2")

        assert len(result) == 1
        assert result[0].checkpoint_id == "sess-2"
        assert result[0].data == {"filtered": True}

    @pytest.mark.asyncio
    async def test_list_checkpoints_with_limit(self, adapter, mock_storage):
        """Apply limit to the number of returned entries."""
        mock_storage.list.return_value = ["sess-1", "sess-2", "sess-3", "sess-4"]
        mock_storage.load.return_value = {
            "unified_data": {"data": True},
            "metadata": {},
        }

        result = await adapter.list_checkpoints(limit=2)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_checkpoints_skip_failed_loads(self, adapter, mock_storage):
        """Gracefully skip sessions that fail to load (exception in _load_as_entry)."""
        mock_storage.list.return_value = ["sess-ok", "sess-fail", "sess-ok2"]
        mock_storage.load.side_effect = [
            {"unified_data": {"ok": 1}, "metadata": {}},
            Exception("Storage error"),
            {"unified_data": {"ok": 2}, "metadata": {}},
        ]

        result = await adapter.list_checkpoints()

        # sess-fail should be skipped, returning only 2 entries
        assert len(result) == 2
        assert result[0].checkpoint_id == "sess-ok"
        assert result[1].checkpoint_id == "sess-ok2"

    @pytest.mark.asyncio
    async def test_list_checkpoints_entry_uses_raw_when_no_unified_data(
        self, adapter, mock_storage
    ):
        """When loaded data has no unified_data key, entry.data uses raw dict."""
        mock_storage.list.return_value = ["sess-raw"]
        mock_storage.load.return_value = {"legacy_field": "value"}

        result = await adapter.list_checkpoints()

        assert len(result) == 1
        entry = result[0]
        assert isinstance(entry.data, dict)
        assert entry.data.get("legacy_field") == "value"
        assert entry.metadata == {}


# =========================================================================
# delete_checkpoint
# =========================================================================


class TestDeleteCheckpoint:
    """Tests for AgentFrameworkCheckpointAdapter.delete_checkpoint."""

    @pytest.mark.asyncio
    async def test_delete_delegates_to_storage(self, adapter, mock_storage):
        """Verify storage.delete is called with the checkpoint_id."""
        mock_storage.delete.return_value = True

        result = await adapter.delete_checkpoint("cp-af-del")

        assert result is True
        mock_storage.delete.assert_awaited_once_with("cp-af-del")

    @pytest.mark.asyncio
    async def test_delete_not_found(self, adapter, mock_storage):
        """Return False when checkpoint does not exist."""
        mock_storage.delete.return_value = False

        result = await adapter.delete_checkpoint("nonexistent")

        assert result is False
