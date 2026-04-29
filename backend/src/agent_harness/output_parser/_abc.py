"""
File: backend/src/agent_harness/output_parser/_abc.py
Purpose: Category 6 ABC — OutputParser (parse LLM responses + tool_calls).
Category: 範疇 6 (Output Parsing)
Scope: Phase 50 / Sprint 50.1 (refactor; ABC stub from Sprint 49.1)

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
Last Modified: 2026-04-29

Modification History (newest-first):
    - 2026-04-29: Refactor — move ParsedOutput to .types (Sprint 50.1 Day 1.1).
        ABC files own only ABC per category-boundaries.md.
    - 2026-04-29: Initial creation (Sprint 49.1) — ABC stub + ParsedOutput inline.

Related:
    - .types (ParsedOutput dataclass)
    - 01-eleven-categories-spec.md §範疇 6
    - 17-cross-category-interfaces.md §2.1
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from agent_harness._contracts import ChatResponse, TraceContext

from .types import ParsedOutput


class OutputParser(ABC):
    """Parses ChatResponse into uniform ParsedOutput; emits ToolCallRequested."""

    @abstractmethod
    async def parse(
        self,
        response: ChatResponse,
        *,
        trace_context: TraceContext | None = None,
    ) -> ParsedOutput: ...
