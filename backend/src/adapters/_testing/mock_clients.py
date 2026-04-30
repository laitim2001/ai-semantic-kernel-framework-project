"""
File: backend/src/adapters/_testing/mock_clients.py
Purpose: MockChatClient — fully-implemented ChatClient ABC for unit tests.
Category: Adapters / Testing helpers
Scope: Phase 49 / Sprint 49.4

Description:
    Drop-in ChatClient ABC implementation that does NOT call any LLM provider.
    Used by agent_harness/ unit tests to exercise category code without
    network / API key dependencies. Critical for AP-10 (mock and real share ABC):
    by sharing the ABC with AzureOpenAIAdapter, mock-only tests catch interface
    drift immediately.

    Usage:
        client = MockChatClient(
            responses=[ChatResponse(model="mock", content="hi", ...)],
        )
        out = await client.chat(request, ...)

Created: 2026-04-29 (Sprint 49.4)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.4)

Related:
    - chat_client.py — ABC owner
    - test_contract.py — common contract suite both mock + Azure must pass
"""

from __future__ import annotations

from typing import AsyncIterator, Literal

from adapters._base.chat_client import ChatClient
from adapters._base.pricing import PricingInfo
from adapters._base.types import ModelInfo, StreamEvent
from agent_harness._contracts import (
    CacheBreakpoint,
    ChatRequest,
    ChatResponse,
    Message,
    ToolSpec,
    TraceContext,
)
from agent_harness._contracts.chat import StopReason


class MockChatClient(ChatClient):
    """In-memory ChatClient for unit tests. No LLM calls, no network."""

    def __init__(
        self,
        *,
        responses: list[ChatResponse] | None = None,
        stream_events: list[StreamEvent] | None = None,
        token_count: int = 100,
        pricing: PricingInfo | None = None,
        model_metadata: ModelInfo | None = None,
        feature_flags: dict[str, bool] | None = None,
    ) -> None:
        self._responses = list(responses or [])
        self._stream_events = list(stream_events or [])
        self._token_count = token_count
        self._pricing = pricing or PricingInfo(
            input_per_million=0.0,
            output_per_million=0.0,
            cached_input_per_million=None,
        )
        self._model_metadata = model_metadata or ModelInfo(
            model_name="mock-model",
            model_family="mock",
            provider="mock",
            context_window=8_192,
            max_output_tokens=2_048,
        )
        self._feature_flags: dict[str, bool] = feature_flags or {
            "thinking": False,
            "caching": False,
            "vision": False,
            "audio": False,
            "computer_use": False,
            "structured_output": True,
            "parallel_tool_calls": True,
        }
        self.chat_call_count = 0
        self.stream_call_count = 0
        self.last_request: ChatRequest | None = None

    async def chat(
        self,
        request: ChatRequest,
        *,
        cache_breakpoints: list[CacheBreakpoint] | None = None,
        trace_context: TraceContext | None = None,
    ) -> ChatResponse:
        self.chat_call_count += 1
        self.last_request = request
        if not self._responses:
            return ChatResponse(
                model=self._model_metadata.model_name,
                content="(mock empty)",
                stop_reason=StopReason.END_TURN,
            )
        return self._responses.pop(0)

    def stream(
        self,
        request: ChatRequest,
        *,
        cache_breakpoints: list[CacheBreakpoint] | None = None,
        trace_context: TraceContext | None = None,
    ) -> AsyncIterator[StreamEvent]:
        self.stream_call_count += 1
        self.last_request = request
        return self._stream_impl()

    async def _stream_impl(self) -> AsyncIterator[StreamEvent]:
        for ev in self._stream_events:
            yield ev

    async def count_tokens(
        self,
        *,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
    ) -> int:
        return self._token_count

    def get_pricing(self) -> PricingInfo:
        return self._pricing

    def supports_feature(
        self,
        feature: Literal[
            "thinking",
            "caching",
            "vision",
            "audio",
            "computer_use",
            "structured_output",
            "parallel_tool_calls",
        ],
    ) -> bool:
        return self._feature_flags.get(feature, False)

    def model_info(self) -> ModelInfo:
        return self._model_metadata
