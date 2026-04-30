"""
File: backend/tests/unit/api/v1/chat/test_schemas.py
Purpose: Unit tests for ChatRequest / ChatSessionResponse Pydantic schemas.
Category: tests
Scope: Phase 50 / Sprint 50.2 (Day 1.1)

Created: 2026-04-30
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from api.v1.chat.schemas import ChatRequest, ChatSessionResponse


class TestChatRequest:
    def test_valid_minimal(self) -> None:
        req = ChatRequest(message="hello")
        assert req.message == "hello"
        assert req.mode == "echo_demo"
        assert req.session_id is None

    def test_valid_with_session_id(self) -> None:
        sid = uuid4()
        req = ChatRequest(message="hi", session_id=sid, mode="real_llm")
        assert req.session_id == sid
        assert req.mode == "real_llm"

    def test_empty_message_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ChatRequest(message="")

    def test_invalid_mode_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ChatRequest(message="hi", mode="bogus")  # type: ignore[arg-type]

    def test_oversized_message_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ChatRequest(message="x" * 10_001)


class TestChatSessionResponse:
    def test_valid(self) -> None:
        sid = uuid4()
        now = datetime.now(UTC)
        resp = ChatSessionResponse(session_id=sid, status="running", started_at=now)
        assert resp.session_id == sid
        assert resp.status == "running"

    def test_invalid_status_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ChatSessionResponse(
                session_id=uuid4(),
                status="bogus",  # type: ignore[arg-type]
                started_at=datetime.now(UTC),
            )
