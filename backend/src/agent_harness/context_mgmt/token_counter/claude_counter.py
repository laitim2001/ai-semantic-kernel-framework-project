"""
File: backend/src/agent_harness/context_mgmt/token_counter/claude_counter.py
Purpose: ClaudeTokenCounter — Anthropic tokenizer (exact when available, approximate fallback).
Category: 範疇 4 (Context Management)
Scope: Phase 52 / Sprint 52.1 Day 3

Description:
    Anthropic does not publish a Python tokenizer in lockstep with their
    models. The optional `anthropic` library historically exposed
    `count_tokens()` via the SDK; this counter probes for that capability
    and falls back to a 4-chars-per-token heuristic with a tools schema
    inflation buffer (matching GenericApproxCounter) when unavailable.

LLM neutrality (per 10-server-side-philosophy.md §原則 2):
    The probe is wrapped in try/except around `import anthropic`. The
    Anthropic library is NOT imported into agent_harness — this module
    lives under context_mgmt and is treated as a tokenizer adapter.
    When the library is missing, the counter still returns a usable
    estimate so Cat 4 Compactor can run.

Owner: 01-eleven-categories-spec.md §範疇 4
Single-source: 17-cross-category-interfaces.md §2.1 (TokenCounter row)

Related:
    - token_counter/_abc.py TokenCounter ABC
    - token_counter/generic_approx.py — fallback formula reused here

Created: 2026-05-01 (Sprint 52.1 Day 3.8)

Modification History:
    - 2026-05-01: Initial creation (Sprint 52.1 Day 3.8) — exact-or-approx Claude counter
"""

from __future__ import annotations

import json
import math
from typing import Any, Callable, Literal

from agent_harness._contracts import Message, ToolSpec
from agent_harness.context_mgmt.token_counter._abc import TokenCounter

# Detect anthropic.tokenizer at module load. Two known surfaces:
#   - anthropic.tokenizer.count_tokens(text)  (older SDKs)
#   - client.count_tokens(...)                 (newer; requires a client instance)
# Day 3.8 supports the static-callable form; client form left for Phase 53+.
_ANTHROPIC_COUNTER: Callable[[str], int] | None
try:
    from anthropic.tokenizer import count_tokens as _anthropic_count_tokens  # type: ignore[import-not-found]

    _ANTHROPIC_COUNTER = _anthropic_count_tokens
except ImportError:
    _ANTHROPIC_COUNTER = None


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
        force_approximate: bool = False,
    ) -> None:
        # force_approximate exists primarily for tests that want to exercise
        # the fallback path even on an environment where the lib is installed.
        self._counter = None if force_approximate else _ANTHROPIC_COUNTER

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
