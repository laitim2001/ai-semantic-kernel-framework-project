"""
File: backend/tests/integration/agent_harness/tools/test_builtin_tools.py
Purpose: Integration tests — 4 built-in tools register + execute via ToolExecutorImpl.
Category: Tests / 範疇 2 (Tool Layer)
Scope: Phase 51 / Sprint 51.1 Day 4.5
Created: 2026-04-30
"""

from __future__ import annotations

import json

import httpx
import pytest

from agent_harness._contracts import ToolCall
from agent_harness.tools import (
    ToolExecutorImpl,
    ToolHandler,
    ToolRegistryImpl,
    register_builtin_tools,
)

# === register_builtin_tools wiring ========================================


def test_register_builtin_tools_registers_six_specs() -> None:
    reg = ToolRegistryImpl()
    handlers: dict[str, ToolHandler] = {}
    register_builtin_tools(reg, handlers)
    names = sorted(s.name for s in reg.list())
    assert names == [
        "echo_tool",
        "memory_search",
        "memory_write",
        "python_sandbox",
        "request_approval",
        "web_search",
    ]
    assert set(handlers.keys()) == set(names)


def test_register_builtin_tools_duplicate_raises() -> None:
    reg = ToolRegistryImpl()
    handlers: dict[str, ToolHandler] = {}
    register_builtin_tools(reg, handlers)
    with pytest.raises(ValueError, match="already registered"):
        register_builtin_tools(reg, handlers)


# === Built-in tool execution via ToolExecutorImpl =========================


@pytest.mark.asyncio
async def test_echo_tool_via_executor() -> None:
    reg = ToolRegistryImpl()
    handlers: dict[str, ToolHandler] = {}
    register_builtin_tools(reg, handlers)
    exe = ToolExecutorImpl(registry=reg, handlers=handlers)

    result = await exe.execute(ToolCall(id="e1", name="echo_tool", arguments={"text": "ping"}))
    assert result.success is True
    assert "ping" in result.content


@pytest.mark.asyncio
async def test_python_sandbox_via_executor() -> None:
    reg = ToolRegistryImpl()
    handlers: dict[str, ToolHandler] = {}
    register_builtin_tools(reg, handlers)
    exe = ToolExecutorImpl(registry=reg, handlers=handlers)

    result = await exe.execute(
        ToolCall(
            id="p1",
            name="python_sandbox",
            arguments={"code": "print(40 + 2)", "timeout_seconds": 3, "memory_mb": 64},
        )
    )
    assert result.success is True
    assert isinstance(result.content, str)
    payload = json.loads(result.content)
    assert payload["exit_code"] == 0
    assert "42" in payload["stdout"]


@pytest.mark.asyncio
async def test_request_approval_runs_through_executor_no_gate() -> None:
    """Sprint 57.124: the executor no longer gates on hitl_policy. request_approval
    (ALWAYS_ASK) is NOT short-circuited with an "approval required" error at the
    executor layer — the loop's _cat9 escalates it upstream (covered in the
    loop/_cat9 tests). The executor reaches the handler."""
    reg = ToolRegistryImpl()
    handlers: dict[str, ToolHandler] = {}
    register_builtin_tools(reg, handlers)
    exe = ToolExecutorImpl(registry=reg, handlers=handlers)

    result = await exe.execute(
        ToolCall(
            id="a1",
            name="request_approval",
            arguments={"message": "send urgent email", "severity": "high"},
        )
    )
    # No executor-level "approval required" gate anymore (gating → loop _cat9).
    assert "approval required" not in (result.error or "")


@pytest.mark.asyncio
async def test_memory_search_placeholder_returns_error_json() -> None:
    """memory_search placeholder returns error JSON content (no real backend wired).

    Sprint 53.1 #27 reactivation: CARRY-035 expected raised exception, but
    Sprint 52.x changed placeholder to return error JSON inside ToolResult.content
    while result.success=True. Updated assertion reflects current contract.
    """
    import json as _json

    reg = ToolRegistryImpl()
    handlers: dict[str, ToolHandler] = {}
    register_builtin_tools(reg, handlers)
    exe = ToolExecutorImpl(registry=reg, handlers=handlers)

    result = await exe.execute(
        ToolCall(id="m1", name="memory_search", arguments={"query": "find me"})
    )
    payload = _json.loads(result.content)
    assert payload["ok"] is False
    assert "memory" in payload["error"].lower()


@pytest.mark.asyncio
async def test_memory_write_placeholder_returns_error_json() -> None:
    """memory_write placeholder returns error JSON content (no real backend wired).

    Sprint 53.1 #27 reactivation: same shift as memory_search — placeholder now
    surfaces error via JSON content (success=True at tool layer, ok=False inside).
    """
    import json as _json

    reg = ToolRegistryImpl()
    handlers: dict[str, ToolHandler] = {}
    register_builtin_tools(reg, handlers)
    exe = ToolExecutorImpl(registry=reg, handlers=handlers)

    result = await exe.execute(
        ToolCall(
            id="m2",
            name="memory_write",
            arguments={"scope": "session", "key": "k", "content": "v"},
        )
    )
    payload = _json.loads(result.content)
    assert payload["ok"] is False
    assert "memory" in payload["error"].lower()


# === web_search via mocked httpx ==========================================


@pytest.mark.asyncio
async def test_web_search_handler_with_mocked_httpx(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mock httpx so CI doesn't need a real Bing API key. CARRY-024 covers
    real-key smoke tests run manually by operator."""
    monkeypatch.setenv("BING_SEARCH_API_KEY", "dummy_key_for_test")

    fake_payload = {
        "webPages": {
            "value": [
                {
                    "name": "Result 1",
                    "url": "https://example.com/1",
                    "snippet": "First result snippet",
                },
                {
                    "name": "Result 2",
                    "url": "https://example.com/2",
                    "snippet": "Second result snippet",
                },
            ]
        }
    }

    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=fake_payload))
    async with httpx.AsyncClient(transport=transport) as client:
        from agent_harness.tools import make_web_search_handler

        handler = make_web_search_handler(client=client)
        result_str = await handler(
            ToolCall(
                id="s1",
                name="web_search",
                arguments={"query": "phase 51 spec", "top_k": 2},
            )
        )

    payload = json.loads(result_str)
    assert payload["query"] == "phase 51 spec"
    assert len(payload["results"]) == 2
    assert payload["results"][0]["title"] == "Result 1"
    assert payload["results"][0]["url"] == "https://example.com/1"


@pytest.mark.asyncio
async def test_web_search_missing_api_key_raises() -> None:
    """No BING_SEARCH_API_KEY → WebSearchConfigError on handler invocation."""
    from agent_harness.tools import WebSearchConfigError, make_web_search_handler

    handler = make_web_search_handler()
    # Ensure env var is not set in this test scope
    import os

    os.environ.pop("BING_SEARCH_API_KEY", None)

    with pytest.raises(WebSearchConfigError, match="missing env"):
        await handler(ToolCall(id="s2", name="web_search", arguments={"query": "test"}))


# === Permission gating sanity =============================================


def test_builtin_specs_have_first_class_hitl_and_risk() -> None:
    """All 6 built-in specs use first-class hitl_policy + risk_level fields
    (no tags-encoded workaround). CARRY-021 verification at builtin level."""
    reg = ToolRegistryImpl()
    handlers: dict[str, ToolHandler] = {}
    register_builtin_tools(reg, handlers)

    for spec in reg.list():
        # tags must NOT contain `hitl_policy:*` or `risk:*` encoded values
        for tag in spec.tags:
            assert not tag.startswith(
                "hitl_policy:"
            ), f"{spec.name}: tag '{tag}' indicates legacy encoding"
            assert not tag.startswith(
                "risk:"
            ), f"{spec.name}: tag '{tag}' indicates legacy encoding"
        # first-class fields must be present (default values are OK)
        assert spec.hitl_policy is not None
        assert spec.risk_level is not None
