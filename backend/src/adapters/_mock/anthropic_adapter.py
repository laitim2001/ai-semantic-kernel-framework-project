"""
File: backend/src/adapters/_mock/anthropic_adapter.py
Purpose: Test-only Anthropic-shaped mock for cache_control marker contract verification.
Category: Adapters / Test infrastructure (test-only)
Scope: Phase 52 / Sprint 52.2 (Day 3.4)

Description:
    A ChatClient implementation that mimics the Anthropic provider's
    cache_control marker translation, WITHOUT importing the anthropic SDK.

    Why this exists:
      - Plan §3.4: V2 needs an Anthropic adapter eventually (Phase 50+).
      - Before that lands, we want a contract test that proves
        CacheBreakpoint → cache_control marker translation works the way
        Anthropic expects: each breakpoint annotates the corresponding
        message with `cache_control: {"type": <breakpoint_type>}`.
      - This mock builds a list of Anthropic-native message dicts (role +
        content + optional cache_control) so tests can assert the marker
        landed at the expected position with the expected type.

    Constraints:
      - MUST NOT `import anthropic` (verified by lint + test_imports check).
      - MUST implement the ChatClient ABC fully so it can drop into the
        Loop in place of the Azure adapter for cross-provider behavior tests.
      - Tests inspect `last_anthropic_messages` and `last_cache_breakpoints`
        to verify marker placement.

    Real Anthropic adapter (Phase 50+ wiring) lives in `adapters/anthropic/`
    and will use the actual SDK; that is a separate effort.

Created: 2026-05-01 (Sprint 52.2 Day 3.4)
Last Modified: 2026-05-01

Modification History (newest-first):
    - 2026-05-01: Initial creation (Sprint 52.2 Day 3.4) — cache_control marker
        contract verification mock; deliberately SDK-free.

Related:
    - 17-cross-category-interfaces.md §2.1 ChatClient ABC
    - llm-provider-neutrality.md (.claude/rules/) — `agent_harness/**` SDK ban
    - sprint-52-2-plan.md §3.4 + §3.7 (4 cache_control contract tests)
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Literal

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
from agent_harness._contracts.chat import StopReason, TokenUsage


class MockAnthropicAdapter(ChatClient):
    """Test-only mock; DOES NOT import the anthropic SDK.

    Inspection points (set by chat() / stream()):
      - last_anthropic_messages: list[dict] — Anthropic-native shape with
        cache_control markers injected at breakpoint positions.
      - last_cache_breakpoints: list[CacheBreakpoint] — verbatim record of
        what the caller passed.

    Usage:
        adapter = MockAnthropicAdapter()
        await adapter.chat(request, cache_breakpoints=[bp1, bp2])
        assert adapter.last_anthropic_messages[0]["cache_control"] == {"type": "ephemeral"}
    """

    def __init__(
        self,
        *,
        model: str = "claude-3-5-sonnet-20241022",
        canned_response: str = "OK",
    ) -> None:
        self._model = model
        self._canned_response = canned_response
        self.last_anthropic_messages: list[dict[str, Any]] | None = None
        self.last_cache_breakpoints: list[CacheBreakpoint] | None = None
        self.chat_call_count = 0
        self.stream_call_count = 0

    # -- core: chat --------------------------------------------------------

    async def chat(
        self,
        request: ChatRequest,
        *,
        cache_breakpoints: list[CacheBreakpoint] | None = None,
        trace_context: TraceContext | None = None,
    ) -> ChatResponse:
        self.chat_call_count += 1
        self.last_anthropic_messages = self._build_anthropic_messages(
            request.messages, cache_breakpoints
        )
        self.last_cache_breakpoints = list(cache_breakpoints) if cache_breakpoints else None
        return ChatResponse(
            model=self._model,
            content=self._canned_response,
            stop_reason=StopReason.END_TURN,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=2, total_tokens=12),
        )

    # -- core: stream ------------------------------------------------------

    def stream(
        self,
        request: ChatRequest,
        *,
        cache_breakpoints: list[CacheBreakpoint] | None = None,
        trace_context: TraceContext | None = None,
    ) -> AsyncIterator[StreamEvent]:
        self.stream_call_count += 1
        self.last_anthropic_messages = self._build_anthropic_messages(
            request.messages, cache_breakpoints
        )
        self.last_cache_breakpoints = list(cache_breakpoints) if cache_breakpoints else None
        return self._stream_impl()

    async def _stream_impl(self) -> AsyncIterator[StreamEvent]:
        # Single canned event suffices for marker contract test.
        yield StreamEvent(
            event_type="content_delta",
            payload={"text": self._canned_response},
        )
        yield StreamEvent(event_type="stop", payload={"reason": "end_turn"})

    # -- token / pricing / capability --------------------------------------

    async def count_tokens(
        self,
        *,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
    ) -> int:
        # Mock fixed count; real Anthropic adapter would use claude-tokenizer.
        return 10

    def get_pricing(self) -> PricingInfo:
        return PricingInfo(
            input_per_million=3.0,
            output_per_million=15.0,
            cached_input_per_million=0.3,
        )

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
        return feature in {"caching", "thinking", "vision", "parallel_tool_calls"}

    def model_info(self) -> ModelInfo:
        return ModelInfo(
            model_name=self._model,
            model_family="claude",
            provider="anthropic",
            context_window=200_000,
            max_output_tokens=8192,
        )

    # -- internal helpers --------------------------------------------------

    @staticmethod
    def _build_anthropic_messages(
        messages: list[Message],
        cache_breakpoints: list[CacheBreakpoint] | None,
    ) -> list[dict[str, Any]]:
        """Translate neutral Messages → Anthropic-native dicts + cache_control markers.

        Anthropic places `cache_control` on the message (or content block) that
        marks the END of a cacheable prefix. Per plan §2.6 + §3.4:
          messages[bp.position]["cache_control"] = {"type": bp.breakpoint_type}
        """
        out: list[dict[str, Any]] = [{"role": msg.role, "content": msg.content} for msg in messages]
        if not cache_breakpoints:
            return out
        for bp in cache_breakpoints:
            if 0 <= bp.position < len(out):
                out[bp.position]["cache_control"] = {"type": bp.breakpoint_type}
        return out
