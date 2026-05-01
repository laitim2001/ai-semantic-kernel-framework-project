"""Anthropic mock adapter contract tests. Sprint 52.2 Day 3.7 — 4 tests.

Verifies CacheBreakpoint → Anthropic-native cache_control marker translation
WITHOUT importing the anthropic SDK.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from adapters._mock.anthropic_adapter import MockAnthropicAdapter
from agent_harness._contracts import (
    CacheBreakpoint,
    ChatRequest,
    Message,
)


@pytest.fixture
def adapter() -> MockAnthropicAdapter:
    return MockAnthropicAdapter()


def _request(messages: list[Message]) -> ChatRequest:
    return ChatRequest(messages=messages, tools=[])


@pytest.mark.asyncio
async def test_chat_returns_response(adapter: MockAnthropicAdapter) -> None:
    """Basic ChatClient ABC contract: chat() returns a ChatResponse."""
    response = await adapter.chat(
        _request([Message(role="user", content="hi")]),
        cache_breakpoints=None,
    )
    assert response.content == "OK"
    assert response.model.startswith("claude-")
    assert adapter.chat_call_count == 1


@pytest.mark.asyncio
async def test_cache_control_marker_injected(adapter: MockAnthropicAdapter) -> None:
    """cache_breakpoints=[bp@pos1] → messages[1] gets cache_control marker."""
    msgs = [
        Message(role="system", content="sys"),
        Message(role="user", content="q"),
        Message(role="assistant", content="a"),
    ]
    bp = CacheBreakpoint(position=1, breakpoint_type="ephemeral")

    await adapter.chat(_request(msgs), cache_breakpoints=[bp])

    assert adapter.last_anthropic_messages is not None
    assert "cache_control" not in adapter.last_anthropic_messages[0]
    assert adapter.last_anthropic_messages[1]["cache_control"] == {
        "type": "ephemeral"
    }
    assert "cache_control" not in adapter.last_anthropic_messages[2]
    assert adapter.last_cache_breakpoints == [bp]


@pytest.mark.asyncio
async def test_no_breakpoints_no_marker(adapter: MockAnthropicAdapter) -> None:
    """cache_breakpoints=None → no cache_control on any message."""
    msgs = [
        Message(role="system", content="sys"),
        Message(role="user", content="q"),
    ]

    await adapter.chat(_request(msgs), cache_breakpoints=None)

    assert adapter.last_anthropic_messages is not None
    for msg_dict in adapter.last_anthropic_messages:
        assert "cache_control" not in msg_dict
    assert adapter.last_cache_breakpoints is None


def test_does_not_import_anthropic_sdk() -> None:
    """Anthropic SDK ban: file content must not contain `import anthropic`.

    Per llm-provider-neutrality.md and plan §3.4 DoD. The mock exists precisely
    so we can verify cache_control contract without taking the anthropic
    dependency. Real adapter (Phase 50+) lives in adapters/anthropic/.
    """
    here = Path(__file__).resolve()
    adapter_path = (
        here.parents[4]
        / "src"
        / "adapters"
        / "_mock"
        / "anthropic_adapter.py"
    )
    content = adapter_path.read_text(encoding="utf-8")

    forbidden_patterns = ("\nimport anthropic", "\nfrom anthropic ")
    for pattern in forbidden_patterns:
        assert pattern not in content, (
            f"MockAnthropicAdapter must not import the anthropic SDK; "
            f"found `{pattern.strip()}` in {adapter_path}"
        )
