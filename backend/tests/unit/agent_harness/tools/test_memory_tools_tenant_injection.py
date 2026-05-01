"""
File: backend/tests/unit/agent_harness/tools/test_memory_tools_tenant_injection.py
Purpose: P0 #18 (CARRY-030) — memory_tools handlers source tenant scope from
    ExecutionContext, NOT from LLM-supplied ToolCall.arguments.
Category: Tests / Unit / Agent harness / Tools
Scope: Sprint 52.5 Day 9

Test groups:
    Tampering defence (LLM-supplied args disagreeing with ctx -> reject)
    Server-authoritative happy path (ctx flows through to retrieval / layer)
    Dual-arity protocol regression (handlers must accept (call, context))

Created: 2026-05-01 (Sprint 52.5 Day 9)
"""

from __future__ import annotations

import inspect
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from agent_harness._contracts import (
    ExecutionContext,
    MemoryHint,
    ToolCall,
)
from agent_harness.tools.memory_tools import (
    make_memory_search_handler,
    make_memory_write_handler,
    memory_placeholder_handler,
)


# Fixtures ----------------------------------------------------------


@pytest.fixture
def authenticated_context() -> ExecutionContext:
    """ExecutionContext with all 3 scope fields populated (canonical happy path)."""
    return ExecutionContext(
        tenant_id=UUID("11111111-1111-1111-1111-111111111111"),
        user_id=UUID("22222222-2222-2222-2222-222222222222"),
        session_id=UUID("33333333-3333-3333-3333-333333333333"),
    )


@pytest.fixture
def mock_retrieval() -> MagicMock:
    m = MagicMock()
    m.search = AsyncMock(return_value=[])
    return m


@pytest.fixture
def mock_user_layer() -> MagicMock:
    layer = MagicMock()
    layer.write = AsyncMock(return_value=uuid4())
    return layer


@pytest.fixture
def mock_session_layer() -> MagicMock:
    layer = MagicMock()
    layer.write = AsyncMock(return_value=uuid4())
    return layer


def _call(name: str, **args: object) -> ToolCall:
    return ToolCall(id="tc-1", name=name, arguments=dict(args))


# Tampering defence -------------------------------------------------


@pytest.mark.asyncio
async def test_search_rejects_mismatched_tenant_id_in_args(
    mock_retrieval: MagicMock, authenticated_context: ExecutionContext
) -> None:
    """LLM tries to read another tenant's memory by injecting tenant_id."""
    handler = make_memory_search_handler(mock_retrieval)
    other_tenant = uuid4()
    result = await handler(
        _call("memory_search", query="x", tenant_id=str(other_tenant)),
        authenticated_context,
    )
    payload = json.loads(result)
    assert payload["ok"] is False
    assert "tenant_id" in payload["error"]
    mock_retrieval.search.assert_not_called()


@pytest.mark.asyncio
async def test_search_rejects_mismatched_user_id_in_args(
    mock_retrieval: MagicMock, authenticated_context: ExecutionContext
) -> None:
    handler = make_memory_search_handler(mock_retrieval)
    result = await handler(
        _call("memory_search", query="x", user_id=str(uuid4())),
        authenticated_context,
    )
    assert json.loads(result)["ok"] is False


@pytest.mark.asyncio
async def test_search_rejects_mismatched_session_id_in_args(
    mock_retrieval: MagicMock, authenticated_context: ExecutionContext
) -> None:
    handler = make_memory_search_handler(mock_retrieval)
    result = await handler(
        _call("memory_search", query="x", session_id=str(uuid4())),
        authenticated_context,
    )
    assert json.loads(result)["ok"] is False


@pytest.mark.asyncio
async def test_search_rejects_non_uuid_tenant_id_in_args(
    mock_retrieval: MagicMock, authenticated_context: ExecutionContext
) -> None:
    """Garbled tenant_id string from a malicious / buggy LLM."""
    handler = make_memory_search_handler(mock_retrieval)
    result = await handler(
        _call("memory_search", query="x", tenant_id="not-a-uuid"),
        authenticated_context,
    )
    payload = json.loads(result)
    assert payload["ok"] is False
    assert "not a valid UUID" in payload["error"]


@pytest.mark.asyncio
async def test_write_rejects_mismatched_tenant_id_in_args(
    mock_user_layer: MagicMock, authenticated_context: ExecutionContext
) -> None:
    """LLM tries to write into another tenant by tenant_id mismatch."""
    handler = make_memory_write_handler({"user": mock_user_layer})
    result = await handler(
        _call(
            "memory_write",
            scope="user",
            key="k",
            content="bad",
            tenant_id=str(uuid4()),
        ),
        authenticated_context,
    )
    assert json.loads(result)["ok"] is False
    mock_user_layer.write.assert_not_called()


# Tampering defence — tolerance for legacy callers ----------------


@pytest.mark.asyncio
async def test_search_tolerates_matching_tenant_id_legacy_callers(
    mock_retrieval: MagicMock, authenticated_context: ExecutionContext
) -> None:
    """Pre-52.5 callers may re-pass the same tenant_id; tolerated, not rejected."""
    handler = make_memory_search_handler(mock_retrieval)
    result = await handler(
        _call(
            "memory_search",
            query="x",
            tenant_id=str(authenticated_context.tenant_id),
        ),
        authenticated_context,
    )
    assert json.loads(result)["ok"] is True


@pytest.mark.asyncio
async def test_search_tolerates_empty_string_tenant_id(
    mock_retrieval: MagicMock, authenticated_context: ExecutionContext
) -> None:
    """Empty string in args is a JSON serialiser quirk — treat as 'not set'."""
    handler = make_memory_search_handler(mock_retrieval)
    result = await handler(
        _call("memory_search", query="x", tenant_id=""),
        authenticated_context,
    )
    assert json.loads(result)["ok"] is True


# Server-authoritative happy path ---------------------------------


@pytest.mark.asyncio
async def test_search_passes_context_tenant_to_retrieval(
    mock_retrieval: MagicMock, authenticated_context: ExecutionContext
) -> None:
    handler = make_memory_search_handler(mock_retrieval)
    await handler(_call("memory_search", query="alpha"), authenticated_context)
    mock_retrieval.search.assert_awaited_once()
    kwargs = mock_retrieval.search.await_args.kwargs
    assert kwargs["tenant_id"] == authenticated_context.tenant_id
    assert kwargs["user_id"] == authenticated_context.user_id
    assert kwargs["session_id"] == authenticated_context.session_id


@pytest.mark.asyncio
async def test_write_user_layer_uses_context_user_id(
    mock_user_layer: MagicMock, authenticated_context: ExecutionContext
) -> None:
    handler = make_memory_write_handler({"user": mock_user_layer})
    await handler(
        _call("memory_write", scope="user", key="k", content="hello"),
        authenticated_context,
    )
    mock_user_layer.write.assert_awaited_once()
    kwargs = mock_user_layer.write.await_args.kwargs
    assert kwargs["tenant_id"] == authenticated_context.tenant_id
    assert kwargs["user_id"] == authenticated_context.user_id


@pytest.mark.asyncio
async def test_write_session_layer_uses_context_session_id(
    mock_session_layer: MagicMock, authenticated_context: ExecutionContext
) -> None:
    """For scope=session, layer.write receives context.session_id in user_id slot
    (session-layer overload — Sprint 51.2 design)."""
    handler = make_memory_write_handler({"session": mock_session_layer})
    await handler(
        _call("memory_write", scope="session", key="k", content="hello"),
        authenticated_context,
    )
    mock_session_layer.write.assert_awaited_once()
    kwargs = mock_session_layer.write.await_args.kwargs
    assert kwargs["tenant_id"] == authenticated_context.tenant_id
    assert kwargs["user_id"] == authenticated_context.session_id


# Dual-arity protocol regression -----------------------------------


def test_handlers_have_two_arg_signature() -> None:
    """All memory handlers MUST accept (call, context) — guards against
    accidental revert to single-arg form."""
    fake_retrieval = MagicMock()
    fake_retrieval.search = AsyncMock(return_value=[])
    fake_layer = MagicMock()
    fake_layer.write = AsyncMock(return_value=uuid4())

    for handler in (
        make_memory_search_handler(fake_retrieval),
        make_memory_write_handler({"user": fake_layer}),
        memory_placeholder_handler,
    ):
        sig = inspect.signature(handler)
        params = list(sig.parameters.values())
        assert len(params) == 2, (
            f"{handler!r} signature {sig} — must take (call, context)"
        )
        assert params[1].name == "context"


@pytest.mark.asyncio
async def test_placeholder_handler_accepts_context(
    authenticated_context: ExecutionContext,
) -> None:
    """Placeholder still works under the dual-arity protocol (accepts ctx, ignores)."""
    result = await memory_placeholder_handler(
        _call("memory_search", query="x"), authenticated_context
    )
    payload = json.loads(result)
    assert payload["ok"] is False
    assert "no Cat 3 backend wired" in payload["error"]


# Search returns hints — sanity ------------------------------------


@pytest.mark.asyncio
async def test_search_serialises_returned_hints(
    authenticated_context: ExecutionContext,
) -> None:
    hint = MemoryHint(
        hint_id=uuid4(),
        layer="user",
        time_scale="long_term",
        summary="ok",
        confidence=0.9,
        relevance_score=0.8,
        full_content_pointer="ptr",
        timestamp=datetime.now(timezone.utc),
        last_verified_at=None,
        verify_before_use=False,
        source_tool_call_id="tc-x",
        expires_at=None,
        tenant_id=authenticated_context.tenant_id,
    )
    fake_retrieval = MagicMock()
    fake_retrieval.search = AsyncMock(return_value=[hint])
    handler = make_memory_search_handler(fake_retrieval)
    result = await handler(
        _call("memory_search", query="alpha"), authenticated_context
    )
    payload = json.loads(result)
    assert payload["ok"] is True
    assert len(payload["hints"]) == 1
    assert payload["hints"][0]["hint_id"] == str(hint.hint_id)
