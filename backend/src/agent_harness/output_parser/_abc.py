"""
File: backend/src/agent_harness/output_parser/_abc.py
Purpose: Category 6 ABC — OutputParser (parse LLM responses + tool_calls).
Category: 範疇 6 (Output Parsing)
Scope: Phase 49 / Sprint 49.1 (stub; impl in Phase 50.1)

Description:
    Parses ChatResponse from any provider into a uniform ParsedOutput
    (text content + structured tool_calls). Cat 6 emits ToolCallRequested
    events as it parses out tool calls from the response.

    V2 uses native tool_calls (Anthropic-style + OpenAI function calling)
    via the LLM-neutral ChatResponse contract, so OutputParser does NOT
    do regex-based JSON parsing of free-text.

Owner: 01-eleven-categories-spec.md §範疇 6
Single-source: 17.md §2.1

Created: 2026-04-29 (Sprint 49.1)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from agent_harness._contracts import ChatResponse, StopReason, ToolCall, TraceContext


@dataclass(frozen=True)
class ParsedOutput:
    """Result of OutputParser.parse(); not in 17.md (parser-internal)."""

    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: StopReason = StopReason.END_TURN
    raw_response_id: str | None = None


class OutputParser(ABC):
    """Parses ChatResponse into uniform ParsedOutput; emits ToolCallRequested."""

    @abstractmethod
    async def parse(
        self,
        response: ChatResponse,
        *,
        trace_context: TraceContext | None = None,
    ) -> ParsedOutput: ...
