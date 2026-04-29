"""
File: backend/src/adapters/_base/types.py
Purpose: Adapter-layer neutral types — ModelInfo / StreamEvent + StopReason re-export.
Category: Adapters (LLM provider boundary; per 10-server-side-philosophy.md §原則 2)
Scope: Phase 49 / Sprint 49.4

Description:
    Types that live at the adapter boundary (not in agent_harness/_contracts/
    because they describe how the LLM provider talks to us, not how categories
    talk to each other).

    - ModelInfo: returned by ChatClient.model_info(); routing + metric labels
    - StreamEvent: emitted by ChatClient.stream(); SSE-compatible delta events
    - StopReason: re-exported from agent_harness._contracts.chat (single-source)

    chat_client.py imports from here to keep the ABC file pure-interface.

Owner: 10-server-side-philosophy.md §原則 2
Single-source:
    - ModelInfo / StreamEvent: this file (adapters/_base/types.py)
    - StopReason: agent_harness._contracts.chat (per 17.md §1.1)

Created: 2026-04-29 (Sprint 49.4)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.4) — extracted from chat_client.py for SoC

Related:
    - chat_client.py — ChatClient ABC consumer
    - pricing.py — PricingInfo (sibling adapter type)
    - agent_harness/_contracts/chat.py — StopReason owner
    - 17-cross-category-interfaces.md §1.1 / §2.1
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from agent_harness._contracts.chat import StopReason

__all__ = ["ModelInfo", "StreamEvent", "StopReason"]


@dataclass(frozen=True)
class ModelInfo:
    """ChatClient.model_info() returns this. Used for routing / cache key / metric labels."""

    model_name: str  # "gpt-5.4" / "claude-3.7-sonnet" / "gpt-4o"
    model_family: str  # "gpt" / "claude" / "azure-openai"
    provider: str  # "azure_openai" / "anthropic" / "openai" / "foundry"
    context_window: int  # max input tokens
    max_output_tokens: int
    knowledge_cutoff: datetime | None = None


@dataclass(frozen=True)
class StreamEvent:
    """Emitted by ChatClient.stream(); adapter normalizes provider event types."""

    event_type: Literal[
        "content_delta",
        "tool_call_delta",
        "stop",
        "thinking_delta",
        "usage",
    ]
    payload: dict[str, object]
