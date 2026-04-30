"""
File: backend/src/agent_harness/context_mgmt/token_counter/tiktoken_counter.py
Purpose: TiktokenCounter — exact OpenAI/Azure tokenizer via the official tiktoken library.
Category: 範疇 4 (Context Management)
Scope: Phase 52 / Sprint 52.1 Day 3

Description:
    Uses OpenAI's official `tiktoken` library to count tokens for the
    GPT family. Encoding is selected per model name:

      - gpt-4o*, o1*, o3*, o4* (and gpt-5* family) → o200k_base
      - gpt-4*, gpt-3.5* and other text completions → cl100k_base
      - Anything else → cl100k_base (safe default)

    Per-message overhead follows the OpenAI cookbook formula
    (https://cookbook.openai.com/examples/how_to_count_tokens_with_tiktoken):

        per_message = 3   # role / name / content separator overhead
        per_request = 3   # priming tokens

    Tools schema is serialised to JSON and counted with the same encoding
    plus a small per-tool overhead.

LLM neutrality (per 10-server-side-philosophy.md §原則 2):
    `tiktoken` is OpenAI's tokenizer but it is NOT an LLM SDK; it ships
    no provider client. Importing it inside the agent_harness layer is
    permitted under the neutrality rule (provider-specific tokenisers
    are exactly what TokenCounter ABC abstracts).

Owner: 01-eleven-categories-spec.md §範疇 4
Single-source: 17-cross-category-interfaces.md §2.1 (TokenCounter row)

Related:
    - token_counter/_abc.py TokenCounter ABC
    - adapters/azure_openai/adapter.py — wires this counter via count_tokens()
    - sprint-52-1-plan.md §1 Story 3 (TokenCounter ABC + 3 concrete impls)

Created: 2026-05-01 (Sprint 52.1 Day 3.6)

Modification History:
    - 2026-05-01: Initial creation (Sprint 52.1 Day 3.6) — exact tiktoken impl
"""

from __future__ import annotations

import json
from typing import Any, Literal

try:
    import tiktoken
except ImportError as err:  # pragma: no cover - installation path
    raise ImportError(
        "TiktokenCounter requires the 'tiktoken' package. "
        "Install with `pip install tiktoken` or use GenericApproxCounter as fallback."
    ) from err

from agent_harness._contracts import Message, ToolSpec
from agent_harness.context_mgmt.token_counter._abc import TokenCounter

_DEFAULT_PER_MESSAGE_OVERHEAD: int = 3
_DEFAULT_PER_REQUEST_OVERHEAD: int = 3
_DEFAULT_PER_TOOL_OVERHEAD: int = 4  # function envelope keys (name/desc/parameters)


def _select_encoding_name(model: str) -> str:
    """Map a model name to a tiktoken encoding."""
    if not model:
        return "cl100k_base"
    lower = model.lower()
    # Newer GPT-4o / o-series / GPT-5 family use o200k_base
    if any(prefix in lower for prefix in ("gpt-4o", "gpt-5", "o1", "o3", "o4")):
        return "o200k_base"
    return "cl100k_base"


class TiktokenCounter(TokenCounter):
    """Exact tokenizer for OpenAI/Azure models via the tiktoken library."""

    def __init__(
        self,
        *,
        model: str = "gpt-4o",
        encoding_name: str | None = None,
        per_message_overhead: int = _DEFAULT_PER_MESSAGE_OVERHEAD,
        per_request_overhead: int = _DEFAULT_PER_REQUEST_OVERHEAD,
        per_tool_overhead: int = _DEFAULT_PER_TOOL_OVERHEAD,
    ) -> None:
        self.model = model
        self._encoding_name: str = encoding_name or _select_encoding_name(model)
        # Configurable overheads let adapters pass per_request_overhead=0 when
        # they need count_tokens([]) == 0 (e.g. 51.1 adapter contract).
        self._per_message_overhead = per_message_overhead
        self._per_request_overhead = per_request_overhead
        self._per_tool_overhead = per_tool_overhead
        try:
            self._encoding = tiktoken.get_encoding(self._encoding_name)
        except (KeyError, ValueError):
            # Fallback for environments where the chosen encoding is not bundled
            self._encoding_name = "cl100k_base"
            self._encoding = tiktoken.get_encoding(self._encoding_name)

    def count(
        self,
        *,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
    ) -> int:
        # Per OpenAI cookbook: per_request overhead only applies when the call
        # actually has messages. Empty input → 0 tokens (avoids surprise for
        # adapters whose callers expect count([]) == 0).
        if not messages and not tools:
            return 0

        total = self._per_request_overhead

        for msg in messages:
            total += self._per_message_overhead
            total += len(self._encoding.encode(str(msg.role)))

            content = msg.content
            if isinstance(content, str):
                total += len(self._encoding.encode(content))
            elif isinstance(content, list):
                # ContentBlock list — flatten text fields conservatively
                for block in content:
                    text_attr = getattr(block, "text", None)
                    if isinstance(text_attr, str):
                        total += len(self._encoding.encode(text_attr))

            if msg.name:
                total += len(self._encoding.encode(msg.name))
            if msg.tool_call_id:
                total += len(self._encoding.encode(msg.tool_call_id))
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    total += len(self._encoding.encode(tc.name))
                    try:
                        args_repr = json.dumps(tc.arguments, sort_keys=True, default=str)
                    except (TypeError, ValueError):
                        args_repr = str(tc.arguments)
                    total += len(self._encoding.encode(args_repr))

        if tools:
            for tool in tools:
                total += self._per_tool_overhead
                schema_obj: dict[str, Any] = {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema,
                }
                total += len(
                    self._encoding.encode(json.dumps(schema_obj, sort_keys=True, default=str))
                )

        return total

    def accuracy(self) -> Literal["exact", "approximate"]:
        return "exact"
