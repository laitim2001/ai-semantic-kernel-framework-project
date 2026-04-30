"""
File: backend/src/agent_harness/output_parser/parser.py
Purpose: Cat 6 concrete OutputParser implementation — provider-neutral parse.
Category: 範疇 6 (Output Parsing)
Scope: Phase 50 / Sprint 50.1 (Day 1)

Description:
    Concrete `OutputParserImpl(OutputParser)` that converts a provider-neutral
    `ChatResponse` (from any LLM adapter) into a uniform `ParsedOutput` for
    consumption by Cat 1 (orchestrator_loop).

    Pure transformation: NO regex/free-text parsing. All tool calls come from
    `ChatResponse.tool_calls` populated by the adapter from native tool calling
    (OpenAI function calling / Anthropic tool_use blocks). Text content is
    extracted by joining "text"-typed ContentBlocks if content is structured.

    `stop_reason` is carried verbatim from `ChatResponse` (already a neutral
    `StopReason` enum after adapter mapping). `raw_response_id` is best-effort
    extracted from `raw_provider_response.id` when available, for Cat 12
    tracing correlation.

Key Components:
    - OutputParserImpl: concrete implementation; injectable Tracer (defaults
      to NoOpTracer for tests / dev).
    - _extract_text(): static helper handling both str and list[ContentBlock].

Created: 2026-04-29 (Sprint 50.1 Day 1.1)
Last Modified: 2026-04-29

Modification History (newest-first):
    - 2026-04-29: Initial creation (Sprint 50.1 Day 1.1) — pure ChatResponse
        → ParsedOutput transformation. No regex; native tool_calls only.

Related:
    - .types (ParsedOutput dataclass)
    - ._abc (OutputParser ABC)
    - 01-eleven-categories-spec.md §範疇 6
    - .claude/rules/observability-instrumentation.md (Cat 12 5-point span coverage)
    - .claude/rules/anti-patterns-checklist.md §AP-9 (no regex parsing)
"""

from __future__ import annotations

from agent_harness._contracts import (
    ChatResponse,
    ContentBlock,
    SpanCategory,
    TraceContext,
)
from agent_harness.observability import NoOpTracer, Tracer

from ._abc import OutputParser
from .types import ParsedOutput


class OutputParserImpl(OutputParser):
    """Concrete OutputParser. Pure native-tool-calling transformation."""

    def __init__(self, tracer: Tracer | None = None) -> None:
        self._tracer = tracer or NoOpTracer()

    async def parse(
        self,
        response: ChatResponse,
        *,
        trace_context: TraceContext | None = None,
    ) -> ParsedOutput:
        async with self._tracer.start_span(
            name="output_parser.parse",
            category=SpanCategory.OUTPUT_PARSER,
            trace_context=trace_context,
        ):
            text = self._extract_text(response.content)
            tool_calls = list(response.tool_calls or [])
            raw_response_id = self._extract_response_id(response)
            return ParsedOutput(
                text=text,
                tool_calls=tool_calls,
                stop_reason=response.stop_reason,
                raw_response_id=raw_response_id,
            )

    @staticmethod
    def _extract_text(content: str | list[ContentBlock]) -> str:
        """Join text-typed ContentBlocks; pass-through if already str."""
        if isinstance(content, str):
            return content
        return "".join(block.text or "" for block in content if block.type == "text")

    @staticmethod
    def _extract_response_id(response: ChatResponse) -> str | None:
        """Best-effort: pull provider-side response ID from raw_provider_response."""
        raw = response.raw_provider_response
        if raw is None:
            return None
        rid = raw.get("id")
        return str(rid) if rid is not None else None
