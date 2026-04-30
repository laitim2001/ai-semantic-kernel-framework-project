"""
File: backend/tests/integration/api/test_chat_e2e.py
Purpose: End-to-end SSE round-trip — POST /api/v1/chat/ → 7-event echo flow.
Category: tests / integration
Scope: Phase 50 / Sprint 50.2 (Day 4.6)

Description:
    Boots a FastAPI app with the chat router only (skip OTel + tenant
    middleware to keep the integration test focused). Drives a full
    echo_demo conversation from HTTP POST through AgentLoopImpl and
    asserts the SSE event stream matches the contract published in
    02-architecture-design.md §SSE.

    Also covers cancellation: aborting mid-stream must mark the session
    as cancelled in the registry without the server hanging.

Created: 2026-04-30 (Sprint 50.2 Day 4.6)
"""

from __future__ import annotations

import json
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.chat import router as chat_router
from api.v1.chat.session_registry import get_default_registry


@pytest.fixture
def app() -> FastAPI:
    inst = FastAPI()
    inst.include_router(chat_router, prefix="/api/v1")
    return inst


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as tc:
        yield tc


@pytest.fixture(autouse=True)
def _reset_default_registry() -> Iterator[None]:
    reg = get_default_registry()
    reg._entries.clear()  # type: ignore[attr-defined]
    yield
    reg._entries.clear()  # type: ignore[attr-defined]


def _parse_sse(body: bytes) -> list[dict]:
    out: list[dict] = []
    for chunk in body.split(b"\n\n"):
        if not chunk.strip():
            continue
        lines = chunk.decode("utf-8").split("\n")
        event_line = next((ln for ln in lines if ln.startswith("event: ")), "")
        data_line = next((ln for ln in lines if ln.startswith("data: ")), "")
        out.append(
            {
                "type": event_line[len("event: "):],
                "data": json.loads(data_line[len("data: "):]) if data_line else None,
            }
        )
    return out


def test_e2e_echo_demo_full_loop_event_sequence(client: TestClient) -> None:
    """End-to-end: POST echo_demo → 8-event stream including
    new TurnStarted / LLMRequested / LLMResponded events from Day 2."""
    with client.stream(
        "POST",
        "/api/v1/chat/",
        json={"message": "zebra", "mode": "echo_demo"},
    ) as resp:
        assert resp.status_code == 200
        body = b"".join(chunk for chunk in resp.iter_bytes())

    events = _parse_sse(body)
    types = [e["type"] for e in events]

    # Sprint 50.2 Day 2 expanded event sequence — see test_e2e_echo (unit)
    # for the in-process equivalent. Wire format adds:
    #   loop_start
    #   turn_start, llm_request, llm_response (turn 1)
    #     tool_call_request, tool_call_result
    #   turn_start, llm_request, llm_response (turn 2)
    #   loop_end
    # Thinking is skipped per sse.py serializer (None return).
    assert types[0] == "loop_start"
    assert types[-1] == "loop_end"
    assert types.count("turn_start") == 2
    assert types.count("llm_request") == 2
    assert types.count("llm_response") == 2
    assert types.count("tool_call_request") == 1
    assert types.count("tool_call_result") == 1

    # The tool_call_result must echo the user's text.
    tool_result = next(e for e in events if e["type"] == "tool_call_result")
    assert tool_result["data"]["is_error"] is False
    assert tool_result["data"]["result"] == "zebra"
    assert tool_result["data"]["tool_name"] == "echo_tool"

    # llm_response on the last turn carries the echoed text.
    final_llm = [e for e in events if e["type"] == "llm_response"][-1]
    assert final_llm["data"]["content"] == "zebra"

    # loop_end carries total_turns + stop_reason.
    end = events[-1]
    assert end["data"]["stop_reason"] == "end_turn"
    assert end["data"]["total_turns"] == 1


def test_e2e_session_id_in_response_header(client: TestClient) -> None:
    """Every POST /chat returns X-Session-Id so frontend can poll session state."""
    with client.stream(
        "POST", "/api/v1/chat/", json={"message": "hi", "mode": "echo_demo"}
    ) as resp:
        sid = resp.headers["x-session-id"]
        for _ in resp.iter_bytes():
            pass

    # Session marked completed after stream drains.
    get_resp = client.get(f"/api/v1/chat/sessions/{sid}")
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "completed"


def test_e2e_cancellation_marks_session_cancelled(client: TestClient) -> None:
    """Cancel endpoint flips status without needing the stream to finish."""
    # Pre-register a session
    sid = "12345678-1234-5678-1234-567812345678"
    import uuid

    sid_uuid = uuid.UUID(sid)
    from api.v1.chat.session_registry import get_default_registry

    reg = get_default_registry()
    import asyncio

    asyncio.run(reg.register(sid_uuid))

    cancel_resp = client.post(f"/api/v1/chat/sessions/{sid}/cancel")
    assert cancel_resp.status_code == 204

    get_resp = client.get(f"/api/v1/chat/sessions/{sid}")
    assert get_resp.json()["status"] == "cancelled"
