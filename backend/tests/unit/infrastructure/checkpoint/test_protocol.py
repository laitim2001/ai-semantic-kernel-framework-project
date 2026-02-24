"""Unit tests for CheckpointProvider Protocol and CheckpointEntry.

Sprint 120 -- Story 120-2: Tests for the unified checkpoint protocol,
including CheckpointEntry dataclass serialization, expiration logic,
and CheckpointProvider runtime_checkable Protocol verification.

Tests cover:
    - CheckpointEntry creation with defaults
    - Serialization (to_dict) and deserialization (from_dict)
    - Round-trip fidelity
    - Expiration logic (is_expired)
    - CheckpointProvider as runtime_checkable Protocol
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from src.infrastructure.checkpoint.protocol import (
    CheckpointEntry,
    CheckpointProvider,
)


# =========================================================================
# CheckpointEntry creation
# =========================================================================


class TestCheckpointEntryCreation:
    """Tests for CheckpointEntry default values and construction."""

    def test_checkpoint_entry_creation(self):
        """Verify default values are set correctly on construction."""
        entry = CheckpointEntry()

        assert entry.checkpoint_id != ""
        assert entry.provider_name == ""
        assert entry.session_id == ""
        assert entry.data == {}
        assert entry.metadata == {}
        assert isinstance(entry.created_at, datetime)
        assert entry.expires_at is None

    def test_checkpoint_entry_with_values(self):
        """Verify construction with explicit values."""
        now = datetime(2026, 2, 1, 12, 0, 0)
        expires = datetime(2026, 2, 2, 12, 0, 0)

        entry = CheckpointEntry(
            checkpoint_id="cp-test",
            provider_name="hybrid",
            session_id="sess-123",
            data={"key": "value"},
            metadata={"version": 1},
            created_at=now,
            expires_at=expires,
        )

        assert entry.checkpoint_id == "cp-test"
        assert entry.provider_name == "hybrid"
        assert entry.session_id == "sess-123"
        assert entry.data == {"key": "value"}
        assert entry.metadata == {"version": 1}
        assert entry.created_at == now
        assert entry.expires_at == expires


# =========================================================================
# Serialization
# =========================================================================


class TestCheckpointEntrySerialization:
    """Tests for CheckpointEntry.to_dict and from_dict."""

    def test_checkpoint_entry_to_dict(self):
        """Verify to_dict produces the expected dictionary structure."""
        now = datetime(2026, 2, 1, 12, 0, 0)
        entry = CheckpointEntry(
            checkpoint_id="cp-001",
            provider_name="hybrid",
            session_id="sess-1",
            data={"state": "active"},
            metadata={"tag": "test"},
            created_at=now,
            expires_at=None,
        )

        d = entry.to_dict()

        assert d["checkpoint_id"] == "cp-001"
        assert d["provider_name"] == "hybrid"
        assert d["session_id"] == "sess-1"
        assert d["data"] == {"state": "active"}
        assert d["metadata"] == {"tag": "test"}
        assert d["created_at"] == "2026-02-01T12:00:00"
        assert d["expires_at"] is None

    def test_checkpoint_entry_to_dict_with_expires(self):
        """Verify expires_at is serialized as ISO string when present."""
        expires = datetime(2026, 3, 1, 0, 0, 0)
        entry = CheckpointEntry(expires_at=expires)

        d = entry.to_dict()

        assert d["expires_at"] == "2026-03-01T00:00:00"

    def test_checkpoint_entry_from_dict(self):
        """Verify from_dict correctly deserializes a dictionary."""
        d = {
            "checkpoint_id": "cp-002",
            "provider_name": "agent_framework",
            "session_id": "sess-2",
            "data": {"step": 3},
            "metadata": {"priority": "high"},
            "created_at": "2026-02-10T08:30:00",
            "expires_at": "2026-02-11T08:30:00",
        }

        entry = CheckpointEntry.from_dict(d)

        assert entry.checkpoint_id == "cp-002"
        assert entry.provider_name == "agent_framework"
        assert entry.session_id == "sess-2"
        assert entry.data == {"step": 3}
        assert entry.metadata == {"priority": "high"}
        assert entry.created_at == datetime(2026, 2, 10, 8, 30, 0)
        assert entry.expires_at == datetime(2026, 2, 11, 8, 30, 0)

    def test_checkpoint_entry_from_dict_missing_optional(self):
        """Verify from_dict handles missing optional fields gracefully."""
        d = {}

        entry = CheckpointEntry.from_dict(d)

        assert entry.checkpoint_id != ""  # auto-generated
        assert entry.provider_name == ""
        assert entry.data == {}
        assert entry.expires_at is None

    def test_checkpoint_entry_roundtrip(self):
        """Verify to_dict -> from_dict preserves all data."""
        now = datetime(2026, 2, 15, 14, 30, 0)
        expires = datetime(2026, 2, 16, 14, 30, 0)

        original = CheckpointEntry(
            checkpoint_id="cp-rt",
            provider_name="domain",
            session_id="sess-rt",
            data={"workflow_id": "wf-1", "step": 5},
            metadata={"version": 2, "tags": ["important"]},
            created_at=now,
            expires_at=expires,
        )

        restored = CheckpointEntry.from_dict(original.to_dict())

        assert restored.checkpoint_id == original.checkpoint_id
        assert restored.provider_name == original.provider_name
        assert restored.session_id == original.session_id
        assert restored.data == original.data
        assert restored.metadata == original.metadata
        assert restored.created_at == original.created_at
        assert restored.expires_at == original.expires_at


# =========================================================================
# Expiration
# =========================================================================


class TestCheckpointEntryExpiration:
    """Tests for CheckpointEntry.is_expired."""

    def test_checkpoint_entry_is_expired_none(self):
        """expires_at=None means checkpoint never expires."""
        entry = CheckpointEntry(expires_at=None)

        assert entry.is_expired() is False

    def test_checkpoint_entry_is_expired_future(self):
        """Checkpoint with future expires_at is not expired."""
        future = datetime.utcnow() + timedelta(hours=24)
        entry = CheckpointEntry(expires_at=future)

        assert entry.is_expired() is False

    def test_checkpoint_entry_is_expired_past(self):
        """Checkpoint with past expires_at is expired."""
        past = datetime.utcnow() - timedelta(hours=1)
        entry = CheckpointEntry(expires_at=past)

        assert entry.is_expired() is True


# =========================================================================
# CheckpointProvider Protocol
# =========================================================================


class TestCheckpointProviderProtocol:
    """Tests for CheckpointProvider runtime_checkable Protocol."""

    def test_checkpoint_provider_is_runtime_checkable(self):
        """Verify isinstance works with a conforming class."""

        class _MockProvider:
            @property
            def provider_name(self) -> str:
                return "mock"

            async def save_checkpoint(self, checkpoint_id, data, metadata=None):
                return checkpoint_id

            async def load_checkpoint(self, checkpoint_id):
                return None

            async def list_checkpoints(self, session_id=None, limit=100):
                return []

            async def delete_checkpoint(self, checkpoint_id):
                return False

        provider = _MockProvider()

        assert isinstance(provider, CheckpointProvider)

    def test_non_conforming_object_fails_isinstance(self):
        """Verify isinstance returns False for non-conforming objects."""

        class _NotAProvider:
            pass

        assert not isinstance(_NotAProvider(), CheckpointProvider)
