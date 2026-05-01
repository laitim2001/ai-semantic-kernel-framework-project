"""
File: backend/src/agent_harness/context_mgmt/compactor/semantic.py
Purpose: LLM-driven Compactor; summarises old turns via injected ChatClient.
Category: 範疇 4 (Context Management)
Scope: Phase 52 / Sprint 52.1 Day 2

Description:
    SemanticCompactor delegates summarisation to the LLM via an injected
    ChatClient instance. It packages the early turns (older than
    keep_recent_turns) into a summary request and replaces them with one
    assistant message tagged metadata["compacted_summary"]=True. The recent
    turns are preserved verbatim.

    Failure handling:
      - Provider error / timeout → retry once
      - Still failing → raise SemanticCompactionFailedError
        (HybridCompactor catches this and falls back to structural-only result)

LLM neutrality (per 10-server-side-philosophy.md §原則 2):
    This module MUST NOT import openai / anthropic. The ChatClient ABC
    provides the only LLM interaction surface. CI lint enforces.

Owner: 01-eleven-categories-spec.md §範疇 4
Single-source: 17-cross-category-interfaces.md §2.1 (Compactor row)

Related:
    - compactor/_abc.py (Compactor ABC)
    - adapters/_base/chat_client.py (ChatClient ABC)
    - sprint-52-1-plan.md §1 Story 2 + §2 SemanticCompactor row

Created: 2026-05-01 (Sprint 52.1 Day 2.3)

Modification History:
    - 2026-05-01: Initial creation (Sprint 52.1 Day 2.3) — LLM-driven summarisation
"""

from __future__ import annotations

import time
from dataclasses import replace

from adapters._base.chat_client import ChatClient
from agent_harness._contracts import (
    ChatRequest,
    CompactionResult,
    CompactionStrategy,
    LoopState,
    Message,
    TraceContext,
)
from agent_harness.context_mgmt.compactor._abc import Compactor

SUMMARY_PROMPT = (
    "You are a context-compaction assistant. Read the conversation history "
    "below and produce a concise summary that preserves: (1) the user's "
    "original intent, (2) decisions already made, (3) any tool results that "
    "may matter for future turns, (4) outstanding questions. Drop transient "
    "tool retries and verbose intermediate reasoning. Do NOT invent new facts. "
    "Reply with a single dense paragraph; do not exceed the requested token budget."
)


class SemanticCompactionFailedError(RuntimeError):
    """Raised when SemanticCompactor exhausts retries on the underlying ChatClient."""


class SemanticCompactor(Compactor):
    """LLM-driven context compaction. Target p95 < 2s (per Sprint 52.1 §1)."""

    def __init__(
        self,
        *,
        chat_client: ChatClient,
        keep_recent_turns: int = 5,
        summary_max_tokens: int = 2_000,
        token_budget: int = 100_000,
        token_threshold_ratio: float = 0.75,
        turn_threshold: int = 30,
        retry_count: int = 1,
        summary_system_prompt: str = SUMMARY_PROMPT,
    ) -> None:
        self.chat_client = chat_client
        self.keep_recent_turns = keep_recent_turns
        self.summary_max_tokens = summary_max_tokens
        self.token_budget = token_budget
        self.token_threshold_ratio = token_threshold_ratio
        self.turn_threshold = turn_threshold
        self.retry_count = retry_count
        self.summary_system_prompt = summary_system_prompt

    def should_compact(self, state: LoopState) -> bool:
        """Override ABC default with concrete state path access."""
        if state.transient.token_usage_so_far > self.token_budget * self.token_threshold_ratio:
            return True
        if state.transient.current_turn > self.turn_threshold:
            return True
        return False

    async def _summarise(
        self,
        old_messages: list[Message],
        *,
        trace_context: TraceContext | None,
    ) -> str:
        """Call LLM to produce a summary. Retry once on failure; else raise."""
        history_text = "\n".join(
            f"{m.role}: {m.content if isinstance(m.content, str) else '[content blocks]'}"
            for m in old_messages
        )
        request_messages = [
            Message(role="system", content=self.summary_system_prompt),
            Message(
                role="user",
                content=(
                    f"Summarise the following conversation in <= {self.summary_max_tokens} "
                    f"tokens:\n\n{history_text}"
                ),
            ),
        ]
        request = ChatRequest(
            messages=request_messages,
            tools=[],
            max_tokens=self.summary_max_tokens,
            temperature=0.0,
        )

        last_err: Exception | None = None
        for attempt in range(self.retry_count + 1):
            try:
                response = await self.chat_client.chat(request, trace_context=trace_context)
                content = response.content
                if isinstance(content, str):
                    return content
                # If adapter returned ContentBlock list, join the text blocks
                text_parts: list[str] = []
                for block in content:
                    if block.type == "text" and block.text:
                        text_parts.append(block.text)
                return "\n".join(text_parts) if text_parts else "(empty summary)"
            except Exception as err:  # noqa: BLE001 — retry path needs broad catch
                last_err = err
                if attempt >= self.retry_count:
                    raise SemanticCompactionFailedError(
                        f"SemanticCompactor LLM call failed after {attempt + 1} attempts: {err}"
                    ) from err

        # Unreachable but keeps mypy happy
        raise SemanticCompactionFailedError(f"SemanticCompactor exhausted retries: {last_err}")

    async def compact_if_needed(
        self,
        state: LoopState,
        *,
        trace_context: TraceContext | None = None,
    ) -> CompactionResult:
        start = time.perf_counter()
        tokens_before = state.transient.token_usage_so_far

        if not self.should_compact(state):
            return CompactionResult(
                triggered=False,
                strategy_used=None,
                tokens_before=tokens_before,
                tokens_after=tokens_before,
                messages_compacted=0,
                duration_ms=(time.perf_counter() - start) * 1000.0,
                compacted_state=None,
            )

        messages = list(state.transient.messages)
        # "Turn" = one user→assistant exchange. Cutoff anchored at the
        # keep_recent_turns-th-from-last user message; everything from that
        # user onwards (including its assistant response + any tool messages)
        # survives verbatim.
        user_indices = [i for i, m in enumerate(messages) if m.role == "user"]

        if len(user_indices) <= self.keep_recent_turns:
            # nothing to summarise; return passthrough as triggered=False
            return CompactionResult(
                triggered=False,
                strategy_used=None,
                tokens_before=tokens_before,
                tokens_after=tokens_before,
                messages_compacted=0,
                duration_ms=(time.perf_counter() - start) * 1000.0,
                compacted_state=None,
            )

        cutoff_idx = user_indices[-self.keep_recent_turns]
        old_messages = messages[:cutoff_idx]
        recent_messages = messages[cutoff_idx:]

        # Always preserve system messages from old_messages segment by lifting them ahead
        system_old = [m for m in old_messages if m.role == "system"]
        old_to_summarise = [m for m in old_messages if m.role != "system"]

        if not old_to_summarise:
            return CompactionResult(
                triggered=False,
                strategy_used=None,
                tokens_before=tokens_before,
                tokens_after=tokens_before,
                messages_compacted=0,
                duration_ms=(time.perf_counter() - start) * 1000.0,
                compacted_state=None,
            )

        summary_text = await self._summarise(old_to_summarise, trace_context=trace_context)

        summary_msg = Message(
            role="assistant",
            content=summary_text,
            metadata={"compacted_summary": True},
        )
        new_messages = [*system_old, summary_msg, *recent_messages]

        original_count = len(messages)
        new_count = len(new_messages)
        new_transient = replace(
            state.transient,
            messages=new_messages,
            token_usage_so_far=int(tokens_before * new_count / max(original_count, 1)),
        )
        new_state = replace(state, transient=new_transient)

        return CompactionResult(
            triggered=True,
            strategy_used=CompactionStrategy.SEMANTIC,
            tokens_before=tokens_before,
            tokens_after=new_transient.token_usage_so_far,
            messages_compacted=original_count - new_count,
            duration_ms=(time.perf_counter() - start) * 1000.0,
            compacted_state=new_state,
        )
