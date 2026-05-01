"""
File: backend/tests/integration/adapters/azure_openai/test_integration.py
Purpose: Live Azure OpenAI integration tests — round-trip + streaming + tool call.
Category: Tests / Integration / Adapters
Scope: Sprint 52.5 Day 10 P1 #4 (W2-1 carryover)

Description:
    These tests speak to a real Azure OpenAI deployment. They are SKIPPED
    by default to keep the regular test suite hermetic and offline-safe.

    Enable by setting both:
        - RUN_AZURE_INTEGRATION=1
        - AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY,
          AZURE_OPENAI_DEPLOYMENT_NAME (read by AzureOpenAIConfig)

    Three contract-level assertions per case (per W2-1 audit P1 #4 spec):
        1. round-trip: a one-shot completion returns ChatResponse with
           non-empty content and a recognised StopReason.
        2. streaming: stream() yields at least one content_delta and one
           stop event before the iterator finishes.
        3. tool call: with a single ToolSpec available, the model emits
           a tool_call when prompted to use it.

    Cost: a single full run typically issues ~3 small completions with
    max_tokens=64 each — under $0.01 USD on GPT-4o family deployments.

Created: 2026-05-01 (Sprint 52.5 Day 10 P1 #4)

Related:
    - claudedocs/5-status/V2-AUDIT-W2-ADAPTER.md (audit source)
    - .claude/rules/adapters-layer.md §Contract test (every adapter)
    - backend/src/adapters/azure_openai/adapter.py
"""

from __future__ import annotations

import os

import pytest

from adapters.azure_openai.adapter import AzureOpenAIAdapter
from adapters.azure_openai.config import AzureOpenAIConfig
from agent_harness._contracts import (
    ChatRequest,
    ChatResponse,
    ConcurrencyPolicy,
    Message,
    StopReason,
    ToolAnnotations,
    ToolHITLPolicy,
    ToolSpec,
)


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_AZURE_INTEGRATION") != "1",
    reason=(
        "Live Azure OpenAI integration test — set RUN_AZURE_INTEGRATION=1 "
        "and AZURE_OPENAI_* env vars to enable."
    ),
)


@pytest.fixture(scope="module")
def adapter() -> AzureOpenAIAdapter:
    """Single adapter for the module — reuses the SDK client + tokenizer
    across the three test cases to keep cost low."""
    config = AzureOpenAIConfig()
    if not config.is_configured():
        pytest.skip(
            "AzureOpenAIConfig missing required env vars; cannot run live test."
        )
    return AzureOpenAIAdapter(config=config)


@pytest.mark.asyncio
async def test_round_trip_completion_returns_chat_response(
    adapter: AzureOpenAIAdapter,
) -> None:
    """One-shot non-streaming completion. Asserts the adapter wraps the
    SDK response into a well-formed ChatResponse."""
    request = ChatRequest(
        messages=[
            Message(role="user", content="Reply with the single word: pong"),
        ],
        tools=[],
        max_tokens=16,
        temperature=0.0,  # deterministic for CI stability
    )
    response = await adapter.chat(request)

    assert isinstance(response, ChatResponse)
    assert isinstance(response.model, str) and response.model
    assert response.content, "expected non-empty content"
    assert response.stop_reason in {
        StopReason.END_TURN,
        StopReason.MAX_TOKENS,
    }, f"unexpected stop_reason={response.stop_reason}"


@pytest.mark.asyncio
async def test_streaming_yields_content_deltas_and_stop(
    adapter: AzureOpenAIAdapter,
) -> None:
    """Streaming path emits at least one content_delta and exactly one stop."""
    request = ChatRequest(
        messages=[
            Message(role="user", content="Count from 1 to 5, comma-separated."),
        ],
        tools=[],
        max_tokens=32,
        temperature=0.0,
        stream=True,
    )
    saw_content = False
    saw_stop = False
    async for event in adapter.stream(request):
        if event.event_type == "content_delta":
            saw_content = True
        elif event.event_type == "stop":
            saw_stop = True
            assert event.payload["stop_reason"] in {
                StopReason.END_TURN.value,
                StopReason.MAX_TOKENS.value,
            }
    assert saw_content, "stream emitted no content_delta events"
    assert saw_stop, "stream did not terminate with a stop event"


@pytest.mark.asyncio
async def test_tool_call_round_trip(adapter: AzureOpenAIAdapter) -> None:
    """With a single tool available, the model emits a tool_call when prompted."""
    weather_tool = ToolSpec(
        name="get_current_weather",
        description="Look up the current weather in a given city.",
        input_schema={
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name."},
            },
            "required": ["city"],
        },
        annotations=ToolAnnotations(read_only=True, idempotent=True),
        concurrency_policy=ConcurrencyPolicy.READ_ONLY_PARALLEL,
        hitl_policy=ToolHITLPolicy.AUTO,
    )
    request = ChatRequest(
        messages=[
            Message(
                role="user",
                content="What is the current weather in Tokyo? Use the tool.",
            ),
        ],
        tools=[weather_tool],
        tool_choice="auto",
        max_tokens=128,
        temperature=0.0,
    )
    response = await adapter.chat(request)

    assert response.stop_reason == StopReason.TOOL_USE, (
        f"expected TOOL_USE stop_reason, got {response.stop_reason}; "
        "model may have answered directly — re-run or tighten the prompt"
    )
    assert response.tool_calls, "expected tool_calls to be populated"
    call = response.tool_calls[0]
    assert call.name == "get_current_weather"
    assert isinstance(call.arguments, dict)
    assert call.arguments.get("city")  # some city string supplied
