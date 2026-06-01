"""
File: backend/tests/integration/api/test_chat_keystone_wiring.py
Purpose: Integration tests proving Sprint 57.64 chat-path keystone wiring —
    build_real_llm_handler injects the Cat 5 PromptBuilder into AgentLoopImpl,
    so the production chat flow takes the structured build() path (emits
    PromptBuilt) instead of the naked fallback.
Category: Tests / integration / api
Scope: Phase 57 / Sprint 57.64 Day 1

Description:
    Cat 5 keystone (Day 1) only — Cat 3 memory tools + Cat 11 subagent tools are
    Day 2 and intentionally not exercised here.

    All deterministic and Azure-call-free: monkeypatch fake AZURE_OPENAI_* env so
    build_real_llm_handler constructs an AzureOpenAIAdapter config object (no
    network), then swap loop._chat_client for a MockChatClient before run() so
    the SSE flow is driven by a scripted response.

    - Injection completeness (AP-4 Potemkin guard): the handler-built loop carries
      a non-None _prompt_builder.
    - Positive runtime: running the wired loop on the chat SSE flow emits exactly
      one PromptBuilt event (the loop.py:881 true-branch is reached).
    - Negative guard: an otherwise-identical loop built WITHOUT prompt_builder
      emits NO PromptBuilt (proves the event is caused by the injection, not
      something else; mirrors the fallback path that existed before 57.64).

Created: 2026-06-01 (Sprint 57.64 Day 1)
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from adapters._testing.mock_clients import MockChatClient
from agent_harness._contracts import (
    ChatResponse,
    PromptBuilt,
    StopReason,
    TokenUsage,
)
from agent_harness.orchestrator_loop.loop import AgentLoopImpl
from api.v1.chat.handler import build_real_llm_handler

_FAKE_AZURE_ENV = {
    "AZURE_OPENAI_ENDPOINT": "https://fake.openai.azure.com/",
    "AZURE_OPENAI_API_KEY": "fake-key-not-used",
    "AZURE_OPENAI_DEPLOYMENT_NAME": "fake-deploy",
}


def _set_fake_azure(monkeypatch: pytest.MonkeyPatch) -> None:
    for k, v in _FAKE_AZURE_ENV.items():
        monkeypatch.setenv(k, v)


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    """Clear get_settings lru_cache before+after each test (mirrors the
    conftest module-level singleton-reset pattern used by the 57.63 wiring
    tests; build_real_llm_handler reads Settings)."""
    from core.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]
    yield
    get_settings.cache_clear()  # type: ignore[attr-defined]


def _final_response(text: str = "done") -> ChatResponse:
    """A single END_TURN response (no tool calls) — one-turn chat flow."""
    return ChatResponse(
        model="mock",
        content=text,
        stop_reason=StopReason.END_TURN,
        tool_calls=None,
        usage=TokenUsage(prompt_tokens=10, completion_tokens=2, total_tokens=12),
    )


# ============================================================
# Cat 5 keystone — injection completeness + runtime + negative guard
# ============================================================


def test_cat5_real_handler_injects_prompt_builder(monkeypatch: pytest.MonkeyPatch) -> None:
    """AP-4 Potemkin guard: the handler-built loop carries a PromptBuilder."""
    _set_fake_azure(monkeypatch)
    loop, _registry = build_real_llm_handler()
    # Cat 5 keystone: prompt_builder present → loop.py:881 true-branch is live.
    assert loop._prompt_builder is not None  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_cat5_chat_path_emits_prompt_built(monkeypatch: pytest.MonkeyPatch) -> None:
    """Running the wired chat loop emits a PromptBuilt event (fallback NOT taken).

    Swap the (config-only) Azure adapter for a MockChatClient so the SSE flow is
    scripted and offline; the prompt_builder injected by the handler is what
    drives the PromptBuilt emission.
    """
    _set_fake_azure(monkeypatch)
    loop, _registry = build_real_llm_handler()
    loop._chat_client = MockChatClient(responses=[_final_response()])  # type: ignore[attr-defined]

    events = [ev async for ev in loop.run(session_id=uuid4(), user_input="hello")]
    prompt_built = [ev for ev in events if isinstance(ev, PromptBuilt)]

    assert len(prompt_built) == 1
    assert prompt_built[0].messages_count >= 1


@pytest.mark.asyncio
async def test_cat5_no_prompt_built_when_builder_absent() -> None:
    """Negative guard: an AgentLoopImpl built WITHOUT prompt_builder emits no
    PromptBuilt — confirming the event in the positive test is caused by the
    Cat 5 injection (this is the pre-57.64 fallback behaviour)."""
    from agent_harness.output_parser import OutputParserImpl
    from business_domain._register_all import make_default_executor

    registry, executor = make_default_executor()
    loop = AgentLoopImpl(
        chat_client=MockChatClient(responses=[_final_response()]),
        output_parser=OutputParserImpl(),
        tool_executor=executor,
        tool_registry=registry,
        # prompt_builder deliberately omitted → fallback path.
    )

    events = [ev async for ev in loop.run(session_id=uuid4(), user_input="hello")]
    prompt_built = [ev for ev in events if isinstance(ev, PromptBuilt)]

    assert prompt_built == []
