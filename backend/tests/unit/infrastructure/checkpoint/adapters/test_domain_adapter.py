"""Unit tests for DomainCheckpointAdapter.

Sprint 121 -- Story 121-1b: Tests for the adapter that wraps the existing
DatabaseCheckpointStorage from the domain checkpoints module to implement
the CheckpointProvider protocol.

Tests cover:
    - provider_name returns "domain" by default
    - custom provider_name works
    - save_checkpoint extracts execution_id and node_id, delegates to storage
    - save_checkpoint uses default execution_id (null UUID) when missing
    - save_checkpoint returns domain-generated UUID as string
    - load_checkpoint converts string to UUID and delegates
    - load_checkpoint returns None when not found
    - load_checkpoint returns None for invalid UUID string
    - list_checkpoints with session_id converts to UUID and calls list_checkpoints
    - list_checkpoints without session_id returns empty list
    - list_checkpoints with invalid UUID returns empty list
    - list_checkpoints applies limit
    - delete_checkpoint converts string to UUID and delegates
    - delete_checkpoint returns False when not found
    - delete_checkpoint returns False for invalid UUID
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.domain.checkpoints.storage import DatabaseCheckpointStorage
from src.infrastructure.checkpoint.protocol import CheckpointEntry
from src.infrastructure.checkpoint.adapters.domain_adapter import (
    DomainCheckpointAdapter,
    _DEFAULT_EXECUTION_UUID,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAMPLE_UUID_1 = UUID("11111111-1111-1111-1111-111111111111")
_SAMPLE_UUID_2 = UUID("22222222-2222-2222-2222-222222222222")
_SAMPLE_EXEC_UUID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def _make_mock_storage() -> MagicMock:
    """Create a mock DatabaseCheckpointStorage with async methods."""
    storage = MagicMock(spec=DatabaseCheckpointStorage)
    storage.save_checkpoint = AsyncMock(return_value=_SAMPLE_UUID_1)
    storage.load_checkpoint = AsyncMock(return_value=None)
    storage.list_checkpoints = AsyncMock(return_value=[])
    storage.delete_checkpoint = AsyncMock(return_value=True)
    return storage


def _make_domain_checkpoint_dict(
    checkpoint_id: str = "11111111-1111-1111-1111-111111111111",
    execution_id: str = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    node_id: str = "checkpoint",
    status: str = "pending",
    created_at: str | None = None,
) -> dict:
    """Create a domain checkpoint dict as returned by DatabaseCheckpointStorage."""
    return {
        "id": checkpoint_id,
        "execution_id": execution_id,
        "node_id": node_id,
        "status": status,
        "payload": {"state": {"key": "value"}},
        "created_at": created_at or datetime.utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_storage():
    """Create a mock storage backend."""
    return _make_mock_storage()


@pytest.fixture
def adapter(mock_storage):
    """Create a DomainCheckpointAdapter with mocked storage."""
    return DomainCheckpointAdapter(storage=mock_storage, name="domain")


# =========================================================================
# provider_name
# =========================================================================


class TestProviderName:
    """Tests for DomainCheckpointAdapter.provider_name property."""

    def test_provider_name(self, adapter):
        """Verify 'domain' is returned as the default provider name."""
        assert adapter.provider_name == "domain"

    def test_custom_provider_name(self, mock_storage):
        """Verify custom name is returned when specified."""
        custom_adapter = DomainCheckpointAdapter(
            storage=mock_storage, name="custom_domain"
        )
        assert custom_adapter.provider_name == "custom_domain"


# =========================================================================
# save_checkpoint
# =========================================================================


class TestSaveCheckpoint:
    """Tests for DomainCheckpointAdapter.save_checkpoint."""

    @pytest.mark.asyncio
    async def test_save_extracts_execution_id_and_node_id(self, adapter, mock_storage):
        """Verify UUID conversion and delegation with extracted fields."""
        data = {
            "execution_id": str(_SAMPLE_EXEC_UUID),
            "node_id": "approval_node",
            "workflow_step": 3,
        }

        result = await adapter.save_checkpoint(
            checkpoint_id="hint-id",
            data=data,
            metadata={"tag": "test"},
        )

        assert result == str(_SAMPLE_UUID_1)
        mock_storage.save_checkpoint.assert_awaited_once()

        call_kwargs = mock_storage.save_checkpoint.call_args[1]
        assert call_kwargs["execution_id"] == _SAMPLE_EXEC_UUID
        assert call_kwargs["node_id"] == "approval_node"
        assert call_kwargs["state"] == data
        assert call_kwargs["metadata"] == {"tag": "test"}

    @pytest.mark.asyncio
    async def test_save_default_execution_id(self, adapter, mock_storage):
        """When no execution_id in data, default null UUID is used."""
        data = {"workflow_step": 1}

        await adapter.save_checkpoint(
            checkpoint_id="hint-id",
            data=data,
        )

        call_kwargs = mock_storage.save_checkpoint.call_args[1]
        assert call_kwargs["execution_id"] == _DEFAULT_EXECUTION_UUID
        assert call_kwargs["node_id"] == "checkpoint"

    @pytest.mark.asyncio
    async def test_save_returns_generated_uuid_as_string(self, adapter, mock_storage):
        """Domain storage returns UUID; adapter converts to string."""
        generated_uuid = uuid4()
        mock_storage.save_checkpoint.return_value = generated_uuid

        result = await adapter.save_checkpoint(
            checkpoint_id="hint-id",
            data={"key": "val"},
        )

        assert result == str(generated_uuid)
        assert isinstance(result, str)


# =========================================================================
# load_checkpoint
# =========================================================================


class TestLoadCheckpoint:
    """Tests for DomainCheckpointAdapter.load_checkpoint."""

    @pytest.mark.asyncio
    async def test_load_converts_to_uuid(self, adapter, mock_storage):
        """Verify string checkpoint_id is converted to UUID for delegation."""
        cp_dict = _make_domain_checkpoint_dict()
        mock_storage.load_checkpoint.return_value = cp_dict

        result = await adapter.load_checkpoint(str(_SAMPLE_UUID_1))

        assert result == cp_dict
        mock_storage.load_checkpoint.assert_awaited_once_with(_SAMPLE_UUID_1)

    @pytest.mark.asyncio
    async def test_load_not_found(self, adapter, mock_storage):
        """Return None when checkpoint does not exist."""
        mock_storage.load_checkpoint.return_value = None

        result = await adapter.load_checkpoint(str(uuid4()))

        assert result is None

    @pytest.mark.asyncio
    async def test_load_invalid_uuid_returns_none(self, adapter, mock_storage):
        """Return None for an invalid checkpoint_id string (not a valid UUID)."""
        result = await adapter.load_checkpoint("not-a-valid-uuid")

        assert result is None
        mock_storage.load_checkpoint.assert_not_awaited()


# =========================================================================
# list_checkpoints
# =========================================================================


class TestListCheckpoints:
    """Tests for DomainCheckpointAdapter.list_checkpoints."""

    @pytest.mark.asyncio
    async def test_list_with_session_id(self, adapter, mock_storage):
        """Convert session_id to UUID, call list_checkpoints, convert results."""
        cp1 = _make_domain_checkpoint_dict(
            checkpoint_id=str(_SAMPLE_UUID_1),
            node_id="node-1",
            status="pending",
        )
        cp2 = _make_domain_checkpoint_dict(
            checkpoint_id=str(_SAMPLE_UUID_2),
            node_id="node-2",
            status="active",
        )
        mock_storage.list_checkpoints.return_value = [cp1, cp2]

        result = await adapter.list_checkpoints(
            session_id=str(_SAMPLE_EXEC_UUID),
        )

        assert len(result) == 2
        assert all(isinstance(e, CheckpointEntry) for e in result)
        assert result[0].checkpoint_id == str(_SAMPLE_UUID_1)
        assert result[0].provider_name == "domain"
        assert result[0].session_id == str(_SAMPLE_EXEC_UUID)
        assert result[0].metadata["node_id"] == "node-1"
        assert result[1].checkpoint_id == str(_SAMPLE_UUID_2)

        mock_storage.list_checkpoints.assert_awaited_once_with(_SAMPLE_EXEC_UUID)

    @pytest.mark.asyncio
    async def test_list_without_session_id(self, adapter, mock_storage):
        """Return empty list when no session_id is provided."""
        result = await adapter.list_checkpoints()

        assert result == []
        mock_storage.list_checkpoints.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_list_invalid_uuid_returns_empty(self, adapter, mock_storage):
        """Return empty list when session_id is not a valid UUID."""
        result = await adapter.list_checkpoints(session_id="invalid-uuid")

        assert result == []
        mock_storage.list_checkpoints.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_list_applies_limit(self, adapter, mock_storage):
        """Verify limit is applied to the returned list."""
        checkpoints = [
            _make_domain_checkpoint_dict(checkpoint_id=str(uuid4()))
            for _ in range(5)
        ]
        mock_storage.list_checkpoints.return_value = checkpoints

        result = await adapter.list_checkpoints(
            session_id=str(_SAMPLE_EXEC_UUID),
            limit=3,
        )

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_list_extracts_state_from_payload(self, adapter, mock_storage):
        """Verify entry.data extracts 'state' from payload dict."""
        cp = {
            "id": str(_SAMPLE_UUID_1),
            "execution_id": str(_SAMPLE_EXEC_UUID),
            "node_id": "test-node",
            "status": "pending",
            "payload": {"state": {"restored_key": "restored_val"}},
            "created_at": datetime.utcnow().isoformat(),
        }
        mock_storage.list_checkpoints.return_value = [cp]

        result = await adapter.list_checkpoints(session_id=str(_SAMPLE_EXEC_UUID))

        assert len(result) == 1
        assert result[0].data == {"restored_key": "restored_val"}


# =========================================================================
# delete_checkpoint
# =========================================================================


class TestDeleteCheckpoint:
    """Tests for DomainCheckpointAdapter.delete_checkpoint."""

    @pytest.mark.asyncio
    async def test_delete_converts_to_uuid(self, adapter, mock_storage):
        """Verify string checkpoint_id is converted to UUID for delegation."""
        mock_storage.delete_checkpoint.return_value = True

        result = await adapter.delete_checkpoint(str(_SAMPLE_UUID_1))

        assert result is True
        mock_storage.delete_checkpoint.assert_awaited_once_with(_SAMPLE_UUID_1)

    @pytest.mark.asyncio
    async def test_delete_not_found(self, adapter, mock_storage):
        """Return False when checkpoint does not exist."""
        mock_storage.delete_checkpoint.return_value = False

        result = await adapter.delete_checkpoint(str(uuid4()))

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_invalid_uuid_returns_false(self, adapter, mock_storage):
        """Return False for an invalid checkpoint_id string."""
        result = await adapter.delete_checkpoint("not-a-valid-uuid")

        assert result is False
        mock_storage.delete_checkpoint.assert_not_awaited()
