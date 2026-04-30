"""Unit tests for HybridCheckpointAdapter.

Sprint 120 -- Story 120-2: Tests for the adapter that wraps the existing
UnifiedCheckpointStorage from the hybrid integration module to implement
the CheckpointProvider protocol.

Tests cover:
    - save_checkpoint delegates to storage.save with HybridCheckpoint
    - load_checkpoint returns unified_data from metadata
    - load_checkpoint falls back to full to_dict() when no unified_data
    - load_checkpoint returns None for missing checkpoint
    - list_checkpoints converts HybridCheckpoints to CheckpointEntry list
    - delete_checkpoint delegates to storage.delete
    - provider_name property returns "hybrid"
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infrastructure.checkpoint.protocol import CheckpointEntry
from src.integrations.hybrid.checkpoint.models import (
    CheckpointStatus,
    CheckpointType,
    HybridCheckpoint,
)
from src.integrations.hybrid.checkpoint.storage import (
    CheckpointQuery,
    UnifiedCheckpointStorage,
)
from src.infrastructure.checkpoint.adapters.hybrid_adapter import (
    HybridCheckpointAdapter,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_storage() -> MagicMock:
    """Create a mock UnifiedCheckpointStorage with async methods."""
    storage = MagicMock(spec=UnifiedCheckpointStorage)
    storage.save = AsyncMock(return_value="cp-001")
    storage.load = AsyncMock(return_value=None)
    storage.delete = AsyncMock(return_value=True)
    storage.query = AsyncMock(return_value=[])
    return storage


def _make_hybrid_checkpoint(
    checkpoint_id: str = "cp-001",
    session_id: str = "sess-1",
    execution_mode: str = "chat",
    checkpoint_type: CheckpointType = CheckpointType.AUTO,
    metadata: dict | None = None,
    created_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> HybridCheckpoint:
    """Create a HybridCheckpoint for testing."""
    return HybridCheckpoint(
        checkpoint_id=checkpoint_id,
        session_id=session_id,
        execution_mode=execution_mode,
        checkpoint_type=checkpoint_type,
        status=CheckpointStatus.ACTIVE,
        metadata=metadata or {},
        created_at=created_at or datetime.utcnow(),
        expires_at=expires_at,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_storage():
    """Create a mock storage backend."""
    return _make_mock_storage()


@pytest.fixture
def adapter(mock_storage):
    """Create a HybridCheckpointAdapter with mocked storage."""
    return HybridCheckpointAdapter(storage=mock_storage, name="hybrid")


# =========================================================================
# provider_name
# =========================================================================


class TestProviderName:
    """Tests for HybridCheckpointAdapter.provider_name property."""

    def test_provider_name(self, adapter):
        """Verify 'hybrid' is returned as the provider name."""
        assert adapter.provider_name == "hybrid"

    def test_custom_provider_name(self, mock_storage):
        """Verify custom name is returned when specified."""
        custom_adapter = HybridCheckpointAdapter(
            storage=mock_storage, name="custom_hybrid"
        )
        assert custom_adapter.provider_name == "custom_hybrid"


# =========================================================================
# save_checkpoint
# =========================================================================


class TestSaveCheckpoint:
    """Tests for HybridCheckpointAdapter.save_checkpoint."""

    @pytest.mark.asyncio
    async def test_save_delegates_to_storage(self, adapter, mock_storage):
        """Verify storage.save is called with a HybridCheckpoint."""
        data = {
            "session_id": "sess-save",
            "execution_mode": "workflow",
            "checkpoint_type": "mode_switch",
            "workflow_step": 3,
        }
        metadata = {"tag": "important"}

        result = await adapter.save_checkpoint(
            checkpoint_id="cp-save",
            data=data,
            metadata=metadata,
        )

        assert result == "cp-001"  # Mocked return
        mock_storage.save.assert_awaited_once()

        # Verify the HybridCheckpoint passed to storage.save
        saved_cp = mock_storage.save.call_args[0][0]
        assert isinstance(saved_cp, HybridCheckpoint)
        assert saved_cp.checkpoint_id == "cp-save"
        assert saved_cp.session_id == "sess-save"
        assert saved_cp.execution_mode == "workflow"
        assert saved_cp.checkpoint_type == CheckpointType.MODE_SWITCH
        assert saved_cp.status == CheckpointStatus.ACTIVE
        # unified_data should be in metadata
        assert saved_cp.metadata["unified_data"] == data
        assert saved_cp.metadata["tag"] == "important"

    @pytest.mark.asyncio
    async def test_save_invalid_checkpoint_type_defaults_to_auto(
        self, adapter, mock_storage
    ):
        """Verify invalid checkpoint_type defaults to AUTO."""
        data = {"checkpoint_type": "nonexistent_type"}

        await adapter.save_checkpoint(
            checkpoint_id="cp-invalid-type",
            data=data,
        )

        saved_cp = mock_storage.save.call_args[0][0]
        assert saved_cp.checkpoint_type == CheckpointType.AUTO


# =========================================================================
# load_checkpoint
# =========================================================================


class TestLoadCheckpoint:
    """Tests for HybridCheckpointAdapter.load_checkpoint."""

    @pytest.mark.asyncio
    async def test_load_returns_unified_data(self, adapter, mock_storage):
        """Return metadata['unified_data'] when present in checkpoint."""
        unified_data = {"session_id": "sess-1", "step": 5}
        cp = _make_hybrid_checkpoint(
            metadata={"unified_data": unified_data, "extra": "info"}
        )
        mock_storage.load.return_value = cp

        result = await adapter.load_checkpoint("cp-001")

        assert result == unified_data
        mock_storage.load.assert_awaited_once_with("cp-001")

    @pytest.mark.asyncio
    async def test_load_returns_full_dict_when_no_unified_data(
        self, adapter, mock_storage
    ):
        """Return full to_dict() when metadata has no unified_data."""
        cp = _make_hybrid_checkpoint(metadata={"other_key": "value"})
        mock_storage.load.return_value = cp

        result = await adapter.load_checkpoint("cp-001")

        assert result is not None
        assert isinstance(result, dict)
        assert result["checkpoint_id"] == "cp-001"
        assert result["session_id"] == "sess-1"

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
    """Tests for HybridCheckpointAdapter.list_checkpoints."""

    @pytest.mark.asyncio
    async def test_list_checkpoints_converts_to_entries(
        self, adapter, mock_storage
    ):
        """Verify HybridCheckpoints are converted to CheckpointEntry list."""
        cp1 = _make_hybrid_checkpoint(
            checkpoint_id="cp-1",
            session_id="sess-list",
            metadata={"unified_data": {"key": "val1"}},
        )
        cp2 = _make_hybrid_checkpoint(
            checkpoint_id="cp-2",
            session_id="sess-list",
            metadata={"unified_data": {"key": "val2"}},
        )
        mock_storage.query.return_value = [cp1, cp2]

        result = await adapter.list_checkpoints(
            session_id="sess-list",
            limit=50,
        )

        assert len(result) == 2
        assert all(isinstance(e, CheckpointEntry) for e in result)
        assert result[0].checkpoint_id == "cp-1"
        assert result[0].provider_name == "hybrid"
        assert result[0].session_id == "sess-list"
        assert result[0].data == {"key": "val1"}
        assert result[1].checkpoint_id == "cp-2"

        # Verify the query was constructed correctly
        mock_storage.query.assert_awaited_once()
        query_arg = mock_storage.query.call_args[0][0]
        assert isinstance(query_arg, CheckpointQuery)
        assert query_arg.session_id == "sess-list"
        assert query_arg.limit == 50

    @pytest.mark.asyncio
    async def test_list_checkpoints_metadata_fields(self, adapter, mock_storage):
        """Verify converted entry metadata includes checkpoint_type, status, execution_mode."""
        cp = _make_hybrid_checkpoint(
            checkpoint_id="cp-meta",
            execution_mode="workflow",
            checkpoint_type=CheckpointType.MODE_SWITCH,
        )
        mock_storage.query.return_value = [cp]

        result = await adapter.list_checkpoints()

        entry = result[0]
        assert entry.metadata["checkpoint_type"] == "mode_switch"
        assert entry.metadata["status"] == "active"
        assert entry.metadata["execution_mode"] == "workflow"

    @pytest.mark.asyncio
    async def test_list_checkpoints_no_unified_data_uses_to_dict(
        self, adapter, mock_storage
    ):
        """When no unified_data in metadata, entry.data should be full to_dict()."""
        cp = _make_hybrid_checkpoint(
            checkpoint_id="cp-full",
            metadata={"tag": "no-unified"},
        )
        mock_storage.query.return_value = [cp]

        result = await adapter.list_checkpoints()

        entry = result[0]
        # data should be the full to_dict() of the checkpoint
        assert isinstance(entry.data, dict)
        assert entry.data["checkpoint_id"] == "cp-full"


# =========================================================================
# delete_checkpoint
# =========================================================================


class TestDeleteCheckpoint:
    """Tests for HybridCheckpointAdapter.delete_checkpoint."""

    @pytest.mark.asyncio
    async def test_delete_delegates_to_storage(self, adapter, mock_storage):
        """Verify storage.delete is called with the checkpoint_id."""
        mock_storage.delete.return_value = True

        result = await adapter.delete_checkpoint("cp-del")

        assert result is True
        mock_storage.delete.assert_awaited_once_with("cp-del")

    @pytest.mark.asyncio
    async def test_delete_not_found(self, adapter, mock_storage):
        """Return False when checkpoint does not exist."""
        mock_storage.delete.return_value = False

        result = await adapter.delete_checkpoint("nonexistent")

        assert result is False
