"""
File: backend/tests/unit/agent_harness/memory/test_extraction.py
Purpose: Unit tests for MemoryExtractor (session -> user; manual-trigger).
Category: Tests / 範疇 3
Scope: Phase 51 / Sprint 51.2 Day 3.4

Created: 2026-04-30
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from adapters._testing.mock_clients import MockChatClient
from agent_harness._contracts import ChatResponse, Message
from agent_harness._contracts.chat import StopReason
from agent_harness.memory.extraction import MemoryExtractor


class _UserLayerStub:
    """Mimics UserLayer.write() for extraction tests; records calls."""

    def __init__(self) -> None:
        self.writes: list[dict[str, object]] = []

    async def write(self, **kwargs: object) -> UUID:
        self.writes.append(kwargs)
        return uuid4()


@pytest.mark.asyncio
async def test_extract_writes_facts_to_user_layer() -> None:
    chat_client = MockChatClient(
        responses=[
            ChatResponse(
                model="mock",
                content=(
                    '[{"content": "user prefers detailed financial breakdowns", '
                    '"confidence": 0.85}, '
                    '{"content": "user works in PST timezone", "confidence": 0.7}]'
                ),
                stop_reason=StopReason.END_TURN,
            )
        ]
    )
    user_layer = _UserLayerStub()
    extractor = MemoryExtractor(chat_client=chat_client, user_layer=user_layer)  # type: ignore[arg-type]

    tenant = uuid4()
    user = uuid4()
    session = uuid4()
    messages = [
        Message(role="user", content="please give me detailed numbers"),
        Message(role="assistant", content="sure, here is a breakdown..."),
    ]

    new_ids = await extractor.extract_session_to_user(
        session_id=session, tenant_id=tenant, user_id=user, messages=messages
    )

    assert len(new_ids) == 2
    assert chat_client.chat_call_count == 1
    assert len(user_layer.writes) == 2
    assert user_layer.writes[0]["tenant_id"] == tenant
    assert user_layer.writes[0]["user_id"] == user
    assert user_layer.writes[0]["time_scale"] == "long_term"
    assert user_layer.writes[0]["confidence"] == 0.85


@pytest.mark.asyncio
async def test_extract_returns_empty_for_empty_messages() -> None:
    chat_client = MockChatClient()
    user_layer = _UserLayerStub()
    extractor = MemoryExtractor(chat_client=chat_client, user_layer=user_layer)  # type: ignore[arg-type]

    new_ids = await extractor.extract_session_to_user(
        session_id=uuid4(),
        tenant_id=uuid4(),
        user_id=uuid4(),
        messages=[],
    )
    assert new_ids == []
    assert chat_client.chat_call_count == 0  # no LLM call when no messages


@pytest.mark.asyncio
async def test_extract_tolerates_invalid_json() -> None:
    """LLM hallucinates prose around JSON or returns invalid JSON entirely."""
    chat_client = MockChatClient(
        responses=[
            ChatResponse(
                model="mock",
                content="I cannot extract facts. Sorry.",  # no JSON
                stop_reason=StopReason.END_TURN,
            )
        ]
    )
    user_layer = _UserLayerStub()
    extractor = MemoryExtractor(chat_client=chat_client, user_layer=user_layer)  # type: ignore[arg-type]

    new_ids = await extractor.extract_session_to_user(
        session_id=uuid4(),
        tenant_id=uuid4(),
        user_id=uuid4(),
        messages=[Message(role="user", content="hi")],
    )
    assert new_ids == []
    assert len(user_layer.writes) == 0  # nothing written


@pytest.mark.asyncio
async def test_extract_handles_prose_around_json() -> None:
    """LLM returns prose followed by JSON array; extractor should locate it."""
    chat_client = MockChatClient(
        responses=[
            ChatResponse(
                model="mock",
                content=(
                    "Here are the extracted facts:\n"
                    '[{"content": "user works on weekends", "confidence": 0.6}]\n'
                    "Done."
                ),
                stop_reason=StopReason.END_TURN,
            )
        ]
    )
    user_layer = _UserLayerStub()
    extractor = MemoryExtractor(chat_client=chat_client, user_layer=user_layer)  # type: ignore[arg-type]

    new_ids = await extractor.extract_session_to_user(
        session_id=uuid4(),
        tenant_id=uuid4(),
        user_id=uuid4(),
        messages=[Message(role="user", content="x")],
    )
    assert len(new_ids) == 1
    assert user_layer.writes[0]["content"] == "user works on weekends"
