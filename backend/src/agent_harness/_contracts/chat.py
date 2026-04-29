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
    """LLM-neutral message. role / content / tool_calls."""

    role: Literal["system", "user", "assistant", "tool"]
    content: str | list[ContentBlock]
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None
    name: str | None = None


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
    """Anthropic-style cache_control marker; positions in the prompt."""

    position: int
    ttl_seconds: int = 300
    breakpoint_type: Literal["ephemeral", "persistent"] = "ephemeral"
