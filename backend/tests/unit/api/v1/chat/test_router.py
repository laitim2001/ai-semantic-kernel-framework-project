"""
File: backend/tests/unit/api/v1/chat/test_router.py
Purpose: Unit tests for /api/v1/chat router — POST SSE + sessions endpoints.
Category: tests
Scope: Phase 50 / Sprint 50.2 (Day 1.5)

Created: 2026-04-30
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.chat import router as chat_router
from api.v1.chat.session_registry import (
    SessionRegistry,
    get_default_registry,
)


@pytest.fixture
def app() -> FastAPI:
    """Minimal app — chat router only, no tenant middleware / OTel."""
    inst = FastAPI()
    inst.include_router(chat_router, prefix="/api/v1")
    return inst


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as tc:
        yield tc


@pytest.fixture(autouse=True)
def _reset_default_registry() -> Iterator[None]:
    """Each test starts with an empty default registry."""
    reg = get_default_registry()
    reg._entries.clear()  # type: ignore[attr-defined]
    yield
    reg._entries.clear()  # type: ignore[attr-defined]


def _parse_sse(body: bytes) -> list[dict]:
    """Parse `event:\\ndata:\\n\\n` frames into list of {type, data}."""
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


class TestPostChat:
    def test_echo_demo_streams_loop_events(self, client: TestClient) -> None:
        with client.stream(
            "POST",
            "/api/v1/chat/",
            json={"message": "zebra", "mode": "echo_demo"},
        ) as resp:
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("text/event-stream")
            assert "x-session-id" in {k.lower(): v for k, v in resp.headers.items()}
            body = b"".join(chunk for chunk in resp.iter_bytes())

        events = _parse_sse(body)
        types = [e["type"] for e in events]
        # echo demo emits: loop_start, llm_response (turn 1 thinking), tool_call_request, llm_response (turn 2), loop_end
        assert types[0] == "loop_start"
        assert "tool_call_request" in types
        assert "loop_end" == types[-1]
        # tool_call_request should carry the user's message as echo_tool args
        tool_req = next(e for e in events if e["type"] == "tool_call_request")
        assert tool_req["data"]["tool_name"] == "echo_tool"
        assert tool_req["data"]["args"] == {"text": "zebra"}
        # final llm_response should echo the message back
        last_thinking = [e for e in events if e["type"] == "llm_response"][-1]
        assert last_thinking["data"]["content"] == "zebra"

    def test_empty_message_rejected_422(self, client: TestClient) -> None:
        resp = client.post("/api/v1/chat/", json={"message": "", "mode": "echo_demo"})
        assert resp.status_code == 422

    def test_invalid_mode_rejected_422(self, client: TestClient) -> None:
        resp = client.post("/api/v1/chat/", json={"message": "x", "mode": "bogus"})
        assert resp.status_code == 422

    def test_missing_message_rejected_422(self, client: TestClient) -> None:
        resp = client.post("/api/v1/chat/", json={"mode": "echo_demo"})
        assert resp.status_code == 422

    def test_real_llm_without_env_returns_503(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_DEPLOYMENT_NAME", raising=False)
        resp = client.post("/api/v1/chat/", json={"message": "x", "mode": "real_llm"})
        assert resp.status_code == 503

    def test_session_id_persisted_after_stream(self, client: TestClient) -> None:
        with client.stream(
            "POST", "/api/v1/chat/", json={"message": "x", "mode": "echo_demo"}
        ) as resp:
            sid_header = resp.headers["x-session-id"]
            # drain
            for _ in resp.iter_bytes():
                pass

        sid = UUID(sid_header)
        # GET sessions/{id} should now report completed
        get_resp = client.get(f"/api/v1/chat/sessions/{sid}")
        assert get_resp.status_code == 200
        body = get_resp.json()
        assert body["status"] == "completed"


class TestGetSession:
    def test_returns_404_for_unknown_session(self, client: TestClient) -> None:
        resp = client.get(f"/api/v1/chat/sessions/{uuid4()}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_running_after_register(
        self, app: FastAPI, client: TestClient
    ) -> None:
        sid = uuid4()
        reg = get_default_registry()
        await reg.register(sid)
        resp = client.get(f"/api/v1/chat/sessions/{sid}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"


class TestCancelSession:
    @pytest.mark.asyncio
    async def test_cancel_running_session(
        self, app: FastAPI, client: TestClient
    ) -> None:
        sid = uuid4()
        reg = get_default_registry()
        await reg.register(sid)
        resp = client.post(f"/api/v1/chat/sessions/{sid}/cancel")
        assert resp.status_code == 204
        # GET reflects cancelled
        get_resp = client.get(f"/api/v1/chat/sessions/{sid}")
        assert get_resp.json()["status"] == "cancelled"

    def test_cancel_unknown_returns_404(self, client: TestClient) -> None:
        resp = client.post(f"/api/v1/chat/sessions/{uuid4()}/cancel")
        assert resp.status_code == 404
