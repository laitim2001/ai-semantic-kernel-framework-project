"""
File: backend/tests/unit/agent_harness/state_mgmt/test_checkpointer_serialization.py
Purpose: Unit tests for DBCheckpointer pure serialization helpers (no DB).
Category: Tests / 范疇 7
Scope: Phase 53.1 / Sprint 53.1 Day 2

Description:
    Verifies the US-3 transient/durable split serialization logic without
    requiring a real PostgreSQL connection. Tests:
    - _serialize_state_for_db excludes messages + pending_tool_calls
    - _serialize_state_for_db handles UUID / datetime / Optional / nested dict
    - _deserialize_state_from_db rebuilds LoopState with empty transient buffers
    - Round-trip durable equality

Created: 2026-05-02 (Sprint 53.1 Day 2)
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from agent_harness._contracts import (
    DurableState,
    LoopState,
    StateVersion,
    TransientState,
)
from agent_harness._contracts.chat import Message
from agent_harness.state_mgmt.checkpointer import (
    _deserialize_state_from_db,
    _serialize_state_for_db,
)


def _build_state(*, with_messages: bool = False) -> LoopState:
    """Helper: build a populated LoopState for serialization tests."""
    transient = TransientState(
        current_turn=3,
        elapsed_ms=1234.5,
        token_usage_so_far=987,
    )
    if with_messages:
        transient.messages = [
            Message(role="user", content="hello"),
            Message(role="assistant", content="hi"),
        ]
        transient.pending_tool_calls = ["fake_tool_call_obj"]
    return LoopState(
        transient=transient,
        durable=DurableState(
            session_id=uuid4(),
            tenant_id=uuid4(),
            user_id=uuid4(),
            pending_approval_ids=[uuid4(), uuid4()],
            last_checkpoint_version=2,
            conversation_summary="user asked about pricing",
            metadata={"feature_x": True, "experiment": "abc"},
        ),
        version=StateVersion(
            version=3,
            parent_version=2,
            created_at=datetime(2026, 5, 2, 10, 30, 0, tzinfo=timezone.utc),
            created_by_category="orchestrator_loop",
        ),
    )


def test_serialize_excludes_messages_buffer() -> None:
    """US-3: messages list must NOT be in serialized output."""
    state = _build_state(with_messages=True)
    data = _serialize_state_for_db(state)
    # No messages field anywhere
    assert "messages" not in data
    assert "messages" not in data["transient_summary"]
    assert "messages" not in data["durable"]


def test_serialize_excludes_pending_tool_calls() -> None:
    """US-3: pending_tool_calls list must NOT be in serialized output."""
    state = _build_state(with_messages=True)
    data = _serialize_state_for_db(state)
    assert "pending_tool_calls" not in data
    assert "pending_tool_calls" not in data["transient_summary"]


def test_serialize_includes_only_transient_scalars() -> None:
    """US-3: transient_summary contains only scalar fields."""
    state = _build_state()
    data = _serialize_state_for_db(state)
    summary = data["transient_summary"]
    assert summary == {
        "current_turn": 3,
        "elapsed_ms": 1234.5,
        "token_usage_so_far": 987,
    }


def test_serialize_uuid_and_datetime_jsonsafe() -> None:
    """UUIDs as str; datetime as ISO 8601."""
    state = _build_state()
    data = _serialize_state_for_db(state)
    durable = data["durable"]
    assert isinstance(durable["session_id"], str)
    assert isinstance(durable["tenant_id"], str)
    assert isinstance(durable["user_id"], str)
    assert all(isinstance(aid, str) for aid in durable["pending_approval_ids"])
    assert "T" in data["version_meta"]["created_at_iso"]  # ISO format


def test_serialize_optional_user_id_none() -> None:
    """user_id=None must serialize to JSON null (Python None)."""
    state = _build_state()
    state.durable.user_id = None
    data = _serialize_state_for_db(state)
    assert data["durable"]["user_id"] is None


def test_deserialize_rehydrates_empty_transient_buffers() -> None:
    """US-3: load() returns empty messages + pending_tool_calls."""
    state = _build_state(with_messages=True)
    data = _serialize_state_for_db(state)

    # Build a fake StateSnapshot row with state_data + DB chain meta
    fake_row = SimpleNamespace(
        state_data=data,
        version=3,
        parent_version=2,
        created_at=datetime(2026, 5, 2, 10, 30, 0, tzinfo=timezone.utc),
        reason="orchestrator_loop",
    )
    rehydrated = _deserialize_state_from_db(fake_row)  # type: ignore[arg-type]

    assert rehydrated.transient.messages == []
    assert rehydrated.transient.pending_tool_calls == []


def test_deserialize_preserves_transient_scalars() -> None:
    """Scalar transient fields survive round-trip."""
    state = _build_state()
    data = _serialize_state_for_db(state)
    fake_row = SimpleNamespace(
        state_data=data,
        version=3,
        parent_version=2,
        created_at=datetime(2026, 5, 2, 10, 30, 0, tzinfo=timezone.utc),
        reason="orchestrator_loop",
    )
    rehydrated = _deserialize_state_from_db(fake_row)  # type: ignore[arg-type]

    assert rehydrated.transient.current_turn == 3
    assert rehydrated.transient.elapsed_ms == 1234.5
    assert rehydrated.transient.token_usage_so_far == 987


def test_deserialize_round_trip_durable_equality() -> None:
    """All DurableState fields survive serialization round-trip."""
    state = _build_state()
    data = _serialize_state_for_db(state)
    fake_row = SimpleNamespace(
        state_data=data,
        version=3,
        parent_version=2,
        created_at=datetime(2026, 5, 2, 10, 30, 0, tzinfo=timezone.utc),
        reason="orchestrator_loop",
    )
    rehydrated = _deserialize_state_from_db(fake_row)  # type: ignore[arg-type]

    assert rehydrated.durable.session_id == state.durable.session_id
    assert rehydrated.durable.tenant_id == state.durable.tenant_id
    assert rehydrated.durable.user_id == state.durable.user_id
    assert set(rehydrated.durable.pending_approval_ids) == set(state.durable.pending_approval_ids)
    assert rehydrated.durable.last_checkpoint_version == 2
    assert rehydrated.durable.conversation_summary == "user asked about pricing"
    assert rehydrated.durable.metadata == {"feature_x": True, "experiment": "abc"}


def test_deserialize_version_metadata() -> None:
    """StateVersion is reconstructed including frozen contract."""
    state = _build_state()
    data = _serialize_state_for_db(state)
    fake_row = SimpleNamespace(
        state_data=data,
        version=3,
        parent_version=2,
        created_at=datetime(2026, 5, 2, 10, 30, 0, tzinfo=timezone.utc),
        reason="orchestrator_loop",
    )
    rehydrated = _deserialize_state_from_db(fake_row)  # type: ignore[arg-type]

    assert rehydrated.version.version == 3
    assert rehydrated.version.parent_version == 2
    assert rehydrated.version.created_by_category == "orchestrator_loop"
    assert rehydrated.version.created_at == datetime(2026, 5, 2, 10, 30, 0, tzinfo=timezone.utc)


def test_serialize_size_under_5kb_for_typical_state() -> None:
    """US-3 acceptance: serialized state row stays small."""
    import json

    state = _build_state(with_messages=True)
    # Simulate heavy transient buffer (100 messages) — must NOT bloat DB
    state.transient.messages = [Message(role="user", content="x" * 200) for _ in range(100)]
    data = _serialize_state_for_db(state)
    encoded = json.dumps(data)
    assert len(encoded) < 5 * 1024, (
        f"serialized state {len(encoded)} bytes exceeds 5KB; "
        f"transient buffers may have leaked into output"
    )
