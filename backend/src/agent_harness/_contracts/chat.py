"""
File: backend/src/agent_harness/_contracts/chat.py
Purpose: Single-source LLM-neutral chat types (request/response/message/blocks/stop).
Category: cross-category single-source contracts (per 17.md §1)
Scope: Phase 49 / Sprint 49.1

Description:
    Defines the LLM-provider-neutral chat data types. All adapters
    (azure_openai / anthropic / openai) MUST translate their native
    formats into these types. Agent harness categories MUST consume
    only these types.

Key Components:
    - Message: role + content + tool_calls (provider-neutral)
    - ContentBlock: text / image / tool_use / tool_result block
    - StopReason: enum replacing per-provider strings
    - ChatRequest / ChatResponse: ChatClient ABC contracts

Owner: 10-server-side-philosophy.md §原則 2 §ChatClient ABC
Single-source: 17.md §1.1

Created: 2026-04-29 (Sprint 49.1)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.1) — stub types

Related:
    - 10-server-side-philosophy.md §原則 2
    - 17-cross-category-interfaces.md §1.1
    - llm-provider-neutrality.md (.claude/rules/)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


class StopReason(Enum):
    """LLM-provider-neutral stop reason; adapters translate from native strings."""

    END_TURN = "end_turn"
    TOOL_USE = "tool_use"
    MAX_TOKENS = "max_tokens"
    STOP_SEQUENCE = "stop_sequence"
    SAFETY_REFUSAL = "safety_refusal"
    PROVIDER_ERROR = "provider_error"


@dataclass(frozen=True)
class ContentBlock:
    """Single content block within a Message; supports multimodal."""

    type: Literal["text", "image", "tool_use", "tool_result"]
    text: str | None = None
    image_url: str | None = None
    tool_use_id: str | None = None
    tool_use_name: str | None = None
    tool_use_input: dict[str, Any] | None = None
    tool_result_for_id: str | None = None
    tool_result_content: str | None = None


@dataclass(frozen=True)
class ToolCall:
    """LLM-emitted tool call; lives inside ChatResponse / Message."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class Message:
    """LLM-neutral message. role / content / tool_calls / metadata.

    metadata (52.1 Day 2 extension) carries non-LLM-facing flags used by
    Cat 4 Compactor and Cat 5 PromptBuilder (e.g. {"hitl": True} preserves
    HITL approval messages through structural compaction; {"compacted_summary":
    True} tags semantic-compacted summary messages). Adapters MUST NOT serialise
    metadata into provider requests — it is local bookkeeping only.

    The dict default is mutable but the Message instance itself is frozen
    (cannot rebind fields). Unhashable due to mutable field — Message is not
    used as dict key / set member anywhere in the harness (verified Day 2).
    """

    role: Literal["system", "user", "assistant", "tool"]
    content: str | list[ContentBlock]
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None
    name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TokenUsage:
    """Per-call token accounting; populated by adapter from provider response."""

    prompt_tokens: int
    completion_tokens: int
    cached_input_tokens: int = 0
    total_tokens: int = 0


@dataclass(frozen=True)
class ChatRequest:
    """ChatClient.chat() input. LLM-neutral."""

    messages: list[Message]
    tools: list[Any] = field(default_factory=list)  # ToolSpec; avoid circular import
    tool_choice: Literal["auto", "any", "none"] | str = "auto"
    max_tokens: int | None = None
    temperature: float = 1.0
    stream: bool = False
    extra_options: dict[str, Any] | None = None


@dataclass(frozen=True)
class ChatResponse:
    """ChatClient.chat() output. LLM-neutral."""

    model: str
    content: str | list[ContentBlock]
    tool_calls: list[ToolCall] | None = None
    stop_reason: StopReason = StopReason.END_TURN
    usage: TokenUsage | None = None
    raw_provider_response: dict[str, Any] | None = None


@dataclass(frozen=True)
class CacheBreakpoint:
    """Cache_control marker for prompt-cache providers (Anthropic / OpenAI / Redis).

    Two layers of fields:
      Physical (51.1, owner: Cat 5 PromptBuilder) — provider-facing positioning:
        - position / ttl_seconds / breakpoint_type
      Logical (52.1, owner: Cat 4 PromptCacheManager) — internal cache lookup:
        - section_id / content_hash / cache_control (all default=None for 51.1 compat)

    The logical fields let Cat 4 deduplicate / invalidate cache entries by tenant + section
    without forcing 51.1 callers to migrate. 52.2 PromptBuilder bridges the two layers.
    """

    # Physical marker (51.1, retained verbatim — 5 callers depend on these)
    position: int
    ttl_seconds: int = 300
    breakpoint_type: Literal["ephemeral", "persistent"] = "ephemeral"

    # Logical metadata (52.1 extension — Cat 4 fills; Cat 5 may use; 52.2 wires through)
    section_id: str | None = None
    """Logical section id (e.g. "system", "tools", "memory_user_layer"); set by PromptCacheManager."""  # noqa: E501

    content_hash: str | None = None
    """sha256 of the cached content; key component for invalidation lookups."""

    cache_control: dict[str, object] | None = None
    """Provider-native cache_control dict (Anthropic-style); None = use physical fields only."""
