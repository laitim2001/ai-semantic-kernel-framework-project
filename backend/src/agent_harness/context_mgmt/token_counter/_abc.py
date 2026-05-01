"""
File: backend/src/agent_harness/context_mgmt/token_counter/_abc.py
Purpose: TokenCounter ABC — per-provider tokenizer abstraction.
Category: 範疇 4 (Context Management)
Scope: Phase 52 / Sprint 52.1

Description:
    TokenCounter abstracts the per-provider token-counting logic so that
    Cat 4 Compactor + Cat 5 PromptBuilder can stay LLM-neutral.

    Concrete impls (Day 3):
      - TiktokenCounter      — exact, OpenAI/Azure (cl100k_base / o200k_base)
      - ClaudeTokenCounter   — exact when anthropic.tokenizer is available; else approximate
      - GenericApproxCounter — approximate (4 chars/token + 30% tools buffer)

    Adapter integration: ChatClient.count_tokens() routes to a TokenCounter
    instance owned by the adapter (per Day 3.10).

Owner: 01-eleven-categories-spec.md §範疇 4
Single-source: 17-cross-category-interfaces.md §2.1

Related:
    - 10-server-side-philosophy.md §原則 2 (LLM Provider Neutrality)
    - adapters/_base/chat_client.py (count_tokens())

Created: 2026-05-01 (Sprint 52.1, Day 1)

Modification History:
    - 2026-05-01: Initial creation (Sprint 52.1 Day 1) — TokenCounter ABC with count + accuracy
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal

from agent_harness._contracts import Message, ToolSpec


class TokenCounter(ABC):
    """Per-provider tokenizer abstraction. Lives at adapter boundary."""

    @abstractmethod
    def count(
        self,
        *,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
    ) -> int:
        """Return the total token count for messages + tools schema.

        Includes per-message role overhead and serialised tools schema tokens
        (concrete impls decide exact formula). Used by Cat 4 Compactor to
        evaluate budget thresholds.
        """
        ...

    @abstractmethod
    def accuracy(self) -> Literal["exact", "approximate"]:
        """Quality of the token estimate.

        - "exact": matches provider billing within ±1 token (e.g. tiktoken)
        - "approximate": heuristic (e.g. len/4); error margin up to ~10%
        """
        ...
