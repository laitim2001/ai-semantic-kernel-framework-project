"""
File: backend/src/agent_harness/context_mgmt/token_counter/generic_approx.py
Purpose: GenericApproxCounter — provider-agnostic 4 chars/token approximation.
Category: 範疇 4 (Context Management)
Scope: Phase 52 / Sprint 52.1 Day 3

Description:
    Last-resort tokenizer for when no provider-specific tokenizer is
    available. Formula:

      content_tokens   = ceil(len(text) / 4)
      tools_tokens     = ceil(len(json(tool_schema)) / 4) * 1.3
                         (30 % buffer; tools schemas have less natural-language
                          redundancy and tokenise denser)
      per_message      = 3 (overhead)

    accuracy() = "approximate"

    This counter is provider-agnostic and never imports any LLM SDK.

Owner: 01-eleven-categories-spec.md §範疇 4
Single-source: 17-cross-category-interfaces.md §2.1 (TokenCounter row)

Related:
    - token_counter/_abc.py TokenCounter ABC
    - token_counter/claude_counter.py — reuses the same fallback formula

Created: 2026-05-01 (Sprint 52.1 Day 3.9)

Modification History:
    - 2026-05-01: Initial creation (Sprint 52.1 Day 3.9) — generic approx counter
"""

from __future__ import annotations

import json
import math
from typing import Any, Literal

from agent_harness._contracts import Message, ToolSpec
from agent_harness.context_mgmt.token_counter._abc import TokenCounter

_PER_MESSAGE_OVERHEAD: int = 3
_PER_TOOL_BUFFER_FACTOR: float = 1.3
_APPROX_CHARS_PER_TOKEN: float = 4.0


def _approx(text: str) -> int:
    if not text:
        return 0
    return max(1, math.ceil(len(text) / _APPROX_CHARS_PER_TOKEN))


class GenericApproxCounter(TokenCounter):
    """Provider-agnostic last-resort tokenizer (4 chars/token)."""

    def count(
        self,
        *,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
    ) -> int:
        total = 0

        for msg in messages:
            total += _PER_MESSAGE_OVERHEAD
            total += _approx(str(msg.role))

            content = msg.content
            if isinstance(content, str):
                total += _approx(content)
            elif isinstance(content, list):
                for block in content:
                    text_attr = getattr(block, "text", None)
                    if isinstance(text_attr, str):
                        total += _approx(text_attr)

            if msg.name:
                total += _approx(msg.name)
            if msg.tool_call_id:
                total += _approx(msg.tool_call_id)
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    total += _approx(tc.name)
                    try:
                        args_repr = json.dumps(tc.arguments, sort_keys=True, default=str)
                    except (TypeError, ValueError):
                        args_repr = str(tc.arguments)
                    total += _approx(args_repr)

        if tools:
            tools_text_tokens = 0
            for tool in tools:
                schema_obj: dict[str, Any] = {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema,
                }
                tools_text_tokens += _approx(json.dumps(schema_obj, sort_keys=True, default=str))
            total += math.ceil(tools_text_tokens * _PER_TOOL_BUFFER_FACTOR)

        return total

    def accuracy(self) -> Literal["exact", "approximate"]:
        return "approximate"
