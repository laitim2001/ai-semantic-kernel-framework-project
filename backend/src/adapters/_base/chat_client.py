"""
File: backend/src/adapters/_base/chat_client.py
Purpose: ChatClient ABC — the LLM-provider-neutral interface used by all categories.
Category: Adapters (LLM provider boundary; per 10-server-side-philosophy.md §原則 2)
Scope: Phase 49 / Sprint 49.1 (ABC stub) + 49.4 (refactor: types extracted)

Description:
    THE single LLM interface. Every category in agent_harness/ depends
    only on this ABC. Concrete adapters (azure_openai / anthropic /
    openai) live in sibling directories and translate to/from
    provider-native formats.

    6 abstract methods:
    - chat() / stream() — core
    - count_tokens() — for Cat 4 token budget
    - get_pricing() — for cost tracking
    - supports_feature() — capability detection (multi-provider routing)
    - model_info() — model metadata

    Neutral types live in sibling modules:
    - PricingInfo: pricing.py
    - ModelInfo / StreamEvent: types.py
    - StopReason / Message / ChatRequest / ChatResponse / TokenUsage:
      agent_harness/_contracts/chat.py

Owner: 10-server-side-philosophy.md §原則 2
Single-source: 17.md §2.1 (`ChatClient` ABC)

Created: 2026-04-29 (Sprint 49.1)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Refactor — extract PricingInfo to pricing.py;
      ModelInfo + StreamEvent to types.py (Sprint 49.4)
    - 2026-04-29: Initial ABC stub (Sprint 49.1)

Related:
    - 10-server-side-philosophy.md §原則 2 (LLM Provider Neutrality)
    - llm-provider-neutrality.md (.claude/rules/)
    - adapters-layer.md (.claude/rules/) — provider onboarding SOP
    - pricing.py / types.py — neutral types
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator, Literal

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

__all__ = ["ChatClient", "ModelInfo", "PricingInfo", "StreamEvent"]


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
    ) -> ChatResponse:
        """Single non-streaming chat completion."""
        ...

    @abstractmethod
    def stream(
        self,
        request: ChatRequest,
        *,
        cache_breakpoints: list[CacheBreakpoint] | None = None,
        trace_context: TraceContext | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Streaming completion. Returns async iterator of StreamEvent.

        Note: Declared as a regular method (not async def with yield) so
        adapters return an async iterator object. mypy --strict treats
        this signature uniformly across providers.
        """
        ...

    # -- token / pricing / capability --------------------------------------

    @abstractmethod
    async def count_tokens(
        self,
        *,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
    ) -> int:
        """Per-provider tokenizer (tiktoken / claude-tokenizer / o200k_base).

        Used by Cat 4 (Context Mgmt) for token budget enforcement.
        Implementations should match the provider's billing tokenizer
        exactly (off-by-one will leak to cost reporting).
        """
        ...

    @abstractmethod
    def get_pricing(self) -> PricingInfo:
        """Return USD per 1M token pricing for this model+provider.

        When provider raises rates, adapter must bump version + pricing
        together (no silent drift).
        """
        ...

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
    ) -> bool:
        """Capability check used by:
        - Multi-provider routing (Phase 50+ ProviderRouter)
        - Feature-gated code paths (e.g., skip vision pipeline if False)
        """
        ...

    @abstractmethod
    def model_info(self) -> ModelInfo:
        """Return model metadata (name / family / provider / context_window)."""
        ...
