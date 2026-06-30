"""
File: backend/tests/unit/agent_harness/memory/test_session_summarizer.py
Purpose: Unit tests for SessionSummarizer (ledger -> memory_session_summary upsert).
Category: Tests / 範疇 3
Scope: Phase 57 / Sprint 57.151 (US-2)

Created: 2026-06-30
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from adapters._testing.mock_clients import MockChatClient
from agent_harness._contracts import ChatResponse, Message
from agent_harness._contracts.chat import StopReason
from agent_harness.memory.session_summarizer import SessionSummarizer


class _StoreStub:
    """Mimics DBSessionSummaryStore.upsert_summary; records calls."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def upsert_summary(self, **kwargs: object) -> UUID:
        self.calls.append(kwargs)
        return uuid4()


def _resp(content: str) -> MockChatClient:
    return MockChatClient(
        responses=[ChatResponse(model="mock", content=content, stop_reason=StopReason.END_TURN)]
    )


@pytest.mark.asyncio
async def test_summarize_writes_structured_summary() -> None:
    """A JSON object response → one upsert with summary + key_decisions + issues."""
    chat = _resp(
        '{"summary": "Debugged the OIDC callback; pinned the redirect URI.", '
        '"key_decisions": ["pin redirect URI"], '
        '"unresolved_issues": ["refresh-token path"]}'
    )
    store = _StoreStub()
    summarizer = SessionSummarizer(chat_client=chat, store=store)  # type: ignore[arg-type]

    sid = uuid4()
    await summarizer.summarize_and_store(
        messages=[Message(role="user", content="help me debug OIDC")],
        session_id=sid,
    )

    assert chat.chat_call_count == 1
    assert len(store.calls) == 1
    call = store.calls[0]
    assert call["session_id"] == sid
    assert call["summary"] == "Debugged the OIDC callback; pinned the redirect URI."
    assert call["key_decisions"] == ["pin redirect URI"]
    assert call["unresolved_issues"] == ["refresh-token path"]


@pytest.mark.asyncio
async def test_empty_ledger_no_op() -> None:
    """No messages → no LLM call, no upsert."""
    chat = MockChatClient()
    store = _StoreStub()
    summarizer = SessionSummarizer(chat_client=chat, store=store)  # type: ignore[arg-type]

    await summarizer.summarize_and_store(messages=[], session_id=uuid4())

    assert chat.chat_call_count == 0
    assert store.calls == []


@pytest.mark.asyncio
async def test_blank_summary_no_op() -> None:
    """A parseable object with a blank summary → no upsert (nothing to recall)."""
    chat = _resp('{"summary": "   ", "key_decisions": [], "unresolved_issues": []}')
    store = _StoreStub()
    summarizer = SessionSummarizer(chat_client=chat, store=store)  # type: ignore[arg-type]

    await summarizer.summarize_and_store(
        messages=[Message(role="user", content="x")], session_id=uuid4()
    )
    assert store.calls == []


@pytest.mark.asyncio
async def test_tolerates_prose_around_json() -> None:
    """LLM wraps the JSON object in prose; the parser locates it."""
    chat = _resp('Sure!\n{"summary": "Talked about pricing.", "key_decisions": []}\nDone.')
    store = _StoreStub()
    summarizer = SessionSummarizer(chat_client=chat, store=store)  # type: ignore[arg-type]

    await summarizer.summarize_and_store(
        messages=[Message(role="user", content="x")], session_id=uuid4()
    )
    assert len(store.calls) == 1
    assert store.calls[0]["summary"] == "Talked about pricing."
    assert store.calls[0]["unresolved_issues"] == []  # missing field → []


@pytest.mark.asyncio
async def test_invalid_json_no_op() -> None:
    """No JSON object at all → no upsert."""
    chat = _resp("I cannot summarize this.")
    store = _StoreStub()
    summarizer = SessionSummarizer(chat_client=chat, store=store)  # type: ignore[arg-type]

    await summarizer.summarize_and_store(
        messages=[Message(role="user", content="x")], session_id=uuid4()
    )
    assert store.calls == []


@pytest.mark.asyncio
async def test_non_string_decision_items_dropped() -> None:
    """key_decisions / unresolved_issues coerce to list[str] (drop non-strings)."""
    chat = _resp(
        '{"summary": "ok", "key_decisions": ["keep", 42, "", "  trim  "], '
        '"unresolved_issues": "not a list"}'
    )
    store = _StoreStub()
    summarizer = SessionSummarizer(chat_client=chat, store=store)  # type: ignore[arg-type]

    await summarizer.summarize_and_store(
        messages=[Message(role="user", content="x")], session_id=uuid4()
    )
    assert store.calls[0]["key_decisions"] == ["keep", "trim"]
    assert store.calls[0]["unresolved_issues"] == []  # non-list → []
