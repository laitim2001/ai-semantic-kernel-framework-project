"""
File: backend/src/adapters/_base/chat_client.py
Purpose: ChatClient ABC — the LLM-provider-neutral interface used by all categories.
Category: Adapters (LLM provider boundary; per 10-server-side-philosophy.md §原則 2)
Scope: Phase 49 / Sprint 49.1 (ABC stub; Azure adapter impl in Sprint 49.3)

Description:
    THE single LLM interface. Every category in agent_harness/ depends
    only on this ABC. Concrete adapters (azure_openai / anthropic /
    openai) live in sibling directories and translate to/from
    provider-native formats.

    7 abstract methods:
    - chat() / stream() — core
    - count_tokens() — for Cat 4 token budget
    - get_pricing() — for cost tracking
    - supports_feature() — capability detection (multi-provider routing)
    - model_info() — model metadata

Owner: 10-server-side-philosophy.md §原則 2
Single-source: 17.md §2.1 (`ChatClient` ABC)

Created: 2026-04-29 (Sprint 49.1)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial ABC stub (Sprint 49.1)

Related:
    - 10-server-side-philosophy.md §原則 2 (LLM Provider Neutrality)
    - llm-provider-neutrality.md (.claude/rules/)
    - adapters-layer.md (.claude/rules/) — provider onboarding SOP
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncIterator, Literal

from agent_harness._contracts import (
    CacheBreakpoint,
    ChatRequest,
    ChatResponse,
    Message,
    ToolSpec,
    TraceContext,
)


@dataclass(frozen=True)
class ModelInfo:
    """ChatClient.model_info() returns this. Used for routing + cache key + metric labels."""

    model_name: str  # "gpt-5.4" / "claude-3.7-sonnet" / "gpt-4o"
    model_family: str  # "gpt" / "claude" / "azure-openai"
    provider: str  # "azure_openai" / "anthropic" / "openai" / "foundry"
    context_window: int  # max input tokens
    max_output_tokens: int
    knowledge_cutoff: datetime | None = None


@dataclass(frozen=True)
class PricingInfo:
    """ChatClient.get_pricing() returns this. USD per 1M tokens."""

    input_per_million: float
    output_per_million: float
    cached_input_per_million: float | None = None  # if provider supports caching
    currency: Literal["USD"] = "USD"


@dataclass(frozen=True)
class StreamEvent:
    """Emitted by ChatClient.stream(); adapter normalizes provider event types."""

    event_type: Literal["content_delta", "tool_call_delta", "stop", "thinking_delta", "usage"]
    payload: dict[str, object]


class ChatClient(ABC):
    """LLM-neutral chat client. THE only LLM interface for agent_harness/."""

    # -- core ---------------------------------------------------------------

    @abstractmethod
    async def chat(
        self,
        request: ChatRequest,
        *,
        cache_breakpoints: list[CacheBreakpoint] | None = None,
        trace_context: TraceContext | None = None,
    ) -> ChatResponse: ...

    @abstractmethod
    async def stream(
        self,
        request: ChatRequest,
        *,
        cache_breakpoints: list[CacheBreakpoint] | None = None,
        trace_context: TraceContext | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Server-Sent Events compatible. Yields StreamEvent."""
        raise NotImplementedError
        yield

    # -- token / pricing / capability --------------------------------------

    @abstractmethod
    async def count_tokens(
        self,
        *,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
    ) -> int:
        """Per-provider tokenizer (tiktoken / claude-tokenizer / o200k_base)."""
        ...

    @abstractmethod
    def get_pricing(self) -> PricingInfo: ...

    @abstractmethod
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
    ) -> bool: ...

    @abstractmethod
    def model_info(self) -> ModelInfo: ...
