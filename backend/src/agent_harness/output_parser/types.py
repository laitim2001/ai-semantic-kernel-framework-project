"""
File: backend/src/agent_harness/output_parser/types.py
Purpose: Cat 6 internal types — ParsedOutput dataclass + OutputType classifier enum.
Category: 範疇 6 (Output Parsing)
Scope: Phase 50 / Sprint 50.1 (Day 1)

Description:
    Owns the parser-internal data types used by `OutputParser.parse()` and
    `classify_output()`. These are NOT in 17.md single-source registry — they
    are scoped to Cat 6 only and consumed by Cat 1 (orchestrator_loop) via
    the `OutputParser` ABC return type.

    `ParsedOutput` was originally defined inline in `_abc.py` (Sprint 49.1 stub).
    Sprint 50.1 Day 1 refactors it into this module so `_abc.py` only owns the
    ABC, following the Cat boundary rule "ABC files own only ABC, not data
    structures" (per .claude/rules/category-boundaries.md).

Key Components:
    - ParsedOutput: dataclass returned by OutputParser.parse()
        - text: assistant final text content
        - tool_calls: list of ToolCall objects from native tool calling
        - stop_reason: provider-neutral StopReason enum (carried from ChatResponse)
        - raw_response_id: provider-side response ID for tracing / debug
        - metadata: dict for future extension (e.g. handoff_request when Cat 11 lands)
    - OutputType: enum used by classify_output() — TOOL_USE / FINAL / HANDOFF

Created: 2026-04-29 (Sprint 50.1 Day 1.1)
Last Modified: 2026-04-29

Modification History (newest-first):
    - 2026-04-29: Initial creation (Sprint 50.1 Day 1.1) — extract ParsedOutput
        from _abc.py + add OutputType enum + metadata field for future ext.

Related:
    - 01-eleven-categories-spec.md §範疇 6 (Output Parsing)
    - 17-cross-category-interfaces.md §1.1 (ParsedOutput is parser-internal,
      NOT a single-source contract — only OutputParser.parse() return type
      is observable cross-cat)
    - .claude/rules/category-boundaries.md (ABC files own only ABC)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from agent_harness._contracts import StopReason, ToolCall


class OutputType(Enum):
    """Classification of an LLM ChatResponse for orchestrator dispatch.

    Used by `classify_output(response)` to drive the main TAO loop branch:
        - TOOL_USE → loop executes tool calls and feeds results back
        - FINAL → loop yields LoopCompleted(reason=END_TURN) and exits
        - HANDOFF → loop hands control to another agent (Cat 11; 50.1 leaves
          this enum value in place but no dispatch — `LoopCompleted` w/
          `reason=HANDOFF_NOT_IMPLEMENTED` until Phase 54.2)
    """

    TOOL_USE = "tool_use"
    FINAL = "final"
    HANDOFF = "handoff"


@dataclass(frozen=True)
class ParsedOutput:
    """Result of `OutputParser.parse()`.

    NOT a single-source contract (not in 17.md §1.1) — parser-internal type
    consumed only by Cat 1 (orchestrator_loop) via `OutputParser` ABC.

    Fields:
        text: assistant text content (joined if multi-block); empty if pure
            tool_use turn.
        tool_calls: list of ToolCall objects parsed from native tool calling.
            Empty list (not None) when no tool calls present — simplifies caller
            iteration without None-check.
        stop_reason: carried verbatim from ChatResponse.stop_reason; classifier
            uses this + tool_calls to determine OutputType.
        raw_response_id: optional provider response ID; used by Cat 12 for
            tracing correlation when emitting ToolCallRequested events.
        metadata: free-form dict for future extension (e.g. handoff target_agent
            when Cat 11 lands in Phase 54.2). 50.1 leaves this empty.
    """

    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: StopReason = StopReason.END_TURN
    raw_response_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
