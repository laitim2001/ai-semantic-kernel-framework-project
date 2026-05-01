"""
File: backend/src/agent_harness/context_mgmt/token_counter/claude_counter.py
Purpose: ClaudeTokenCounter — Claude-family approximate tokenizer (DI-friendly for exact upgrade).
Category: 範疇 4 (Context Management)
Scope: Phase 52 / Sprint 52.1 Day 3

Description:
    Claude-family approximate tokenizer using the same 4-chars/token heuristic
    as GenericApproxCounter, plus a 30 % tools schema inflation buffer. The
    estimate is conservative enough for Cat 4 Compactor to make budget
    decisions without ever calling out to the Anthropic SDK.

    For an exact tokenizer the constructor accepts an optional
    `tokenizer_callable: Callable[[str], int]` that the future Anthropic
    *adapter* (see adapters/anthropic/, Phase 50+) will supply. When that
    callable is present, accuracy() returns "exact"; otherwise "approximate".

LLM neutrality (per 10-server-side-philosophy.md §原則 2 + .claude/rules/llm-provider-neutrality.md):
    `agent_harness/**` MUST NOT import openai / anthropic. This file
    therefore does NOT probe `from anthropic.tokenizer ...`. The exact-
    tokenizer path is reached only via dependency injection from an
    adapter, keeping the SDK boundary clean. Lint rule 1 is enforced by
    CI; this module is verified by grep `import anthropic` = 0.

Owner: 01-eleven-categories-spec.md §範疇 4
Single-source: 17-cross-category-interfaces.md §2.1 (TokenCounter row)

Related:
    - token_counter/_abc.py TokenCounter ABC
    - token_counter/generic_approx.py — fallback formula reused here
    - adapters-layer.md (.claude/rules/) — exact tokenizer DI path

Created: 2026-05-01 (Sprint 52.1 Day 3.8)
Last Modified: 2026-05-01 (Sprint 52.1 Day 4.9)

Modification History:
    - 2026-05-01: Drop direct `from anthropic.tokenizer ...` probe — violates
      LLM neutrality. Replace with constructor-injected `tokenizer_callable`
      so adapters can wire an exact path (Sprint 52.1 Day 4.9).
    - 2026-05-01: Initial creation (Sprint 52.1 Day 3.8) — exact-or-approx Claude counter
"""

from __future__ import annotations

import json
import math
from typing import Any, Callable, Literal

from agent_harness._contracts import Message, ToolSpec
from agent_harness.context_mgmt.token_counter._abc import TokenCounter

# Default: no exact tokenizer wired in. Adapters can supply one via constructor.
_ANTHROPIC_COUNTER: Callable[[str], int] | None = None


_PER_MESSAGE_OVERHEAD: int = 3
_PER_TOOL_BUFFER_FACTOR: float = 1.3
_APPROX_CHARS_PER_TOKEN: float = 4.0


def _approx_count(text: str) -> int:
    """4 chars per token heuristic; matches GenericApproxCounter."""
    if not text:
        return 0
    return max(1, math.ceil(len(text) / _APPROX_CHARS_PER_TOKEN))


class ClaudeTokenCounter(TokenCounter):
    """Counter for Anthropic Claude models.

    Uses anthropic.tokenizer.count_tokens when available (accuracy="exact"),
    otherwise falls back to a 4-chars/token heuristic (accuracy="approximate").
    """

    def __init__(
        self,
        *,
        tokenizer_callable: Callable[[str], int] | None = None,
        force_approximate: bool = False,
    ) -> None:
        # tokenizer_callable: an exact tokenizer supplied by the future
        # Anthropic adapter (Phase 50+). When None, falls back to approx.
        # force_approximate=True overrides any injected callable — used by
        # tests that want to exercise the fallback path deterministically.
        if force_approximate:
            self._counter = None
        else:
            self._counter = tokenizer_callable or _ANTHROPIC_COUNTER

    def _count_text(self, text: str) -> int:
        if self._counter is not None:
            try:
                return int(self._counter(text))
            except Exception:  # noqa: BLE001 - any tokenizer failure → fallback
                return _approx_count(text)
        return _approx_count(text)

    def count(
        self,
        *,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
    ) -> int:
        total = 0

        for msg in messages:
            total += _PER_MESSAGE_OVERHEAD
            total += self._count_text(str(msg.role))

            content = msg.content
            if isinstance(content, str):
                total += self._count_text(content)
            elif isinstance(content, list):
                for block in content:
                    text_attr = getattr(block, "text", None)
                    if isinstance(text_attr, str):
                        total += self._count_text(text_attr)

            if msg.name:
                total += self._count_text(msg.name)
            if msg.tool_call_id:
                total += self._count_text(msg.tool_call_id)
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    total += self._count_text(tc.name)
                    try:
                        args_repr = json.dumps(tc.arguments, sort_keys=True, default=str)
                    except (TypeError, ValueError):
                        args_repr = str(tc.arguments)
                    total += self._count_text(args_repr)

        if tools:
            tools_total_text = 0
            for tool in tools:
                schema_obj: dict[str, Any] = {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema,
                }
                tools_total_text += self._count_text(
                    json.dumps(schema_obj, sort_keys=True, default=str)
                )
            # 30 % schema buffer accounts for adapter-side wrapping (consistent
            # with GenericApproxCounter and our overall conservative bias).
            total += math.ceil(tools_total_text * _PER_TOOL_BUFFER_FACTOR)

        return total

    def accuracy(self) -> Literal["exact", "approximate"]:
        return "exact" if self._counter is not None else "approximate"
