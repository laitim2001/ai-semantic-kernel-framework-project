"""
File: backend/src/agent_harness/subagent/modes/fork.py
Purpose: ForkExecutor — runs a single-shot subagent task via ChatClient with budget guards.
Category: 範疇 11 (Subagent Orchestration)
Scope: Sprint 54.2 US-2

Description:
    FORK mode executor. Per Day 2 simplification (D12): runs a single ChatClient
    call rather than a full child AgentLoop. The task string becomes the user
    message; the assistant response is the subagent output. This is the minimum
    viable Cat 11 Level 4 demonstration. Phase 55+ may extend to multi-turn
    child loops with tools.

    Budget enforcement:
    - max_tokens → ChatRequest.max_tokens cap on completion
    - max_duration_s → wall-clock timeout via asyncio.wait_for
    - max_concurrent / max_subagent_depth → enforced by caller (DefaultSubagentDispatcher)
    - summary cap → BudgetEnforcer.truncate_summary on response.content

    Failure modes (all return SubagentResult(success=False) — fail-closed):
    - ChatClient raises any exception → error="chat_error: {type}: {msg}"
    - asyncio.TimeoutError on max_duration_s → error="timeout: {N}s"
    - Empty / unexpected response.content → error="empty_response"

Created: 2026-05-04 (Sprint 54.2)

Modification History:
    - 2026-05-04: Initial creation (Sprint 54.2 US-2)

Related:
    - subagent/dispatcher.py — DefaultSubagentDispatcher.spawn(FORK)
    - subagent/budget.py — BudgetEnforcer
    - adapters/_base/chat_client.py — ChatClient ABC
    - 01-eleven-categories-spec.md §範疇 11
"""

from __future__ import annotations

import asyncio
import time
from uuid import UUID

from adapters._base.chat_client import ChatClient
from agent_harness._contracts import (
    ChatRequest,
    Message,
    SubagentBudget,
    SubagentMode,
    SubagentResult,
    TraceContext,
)
from agent_harness.subagent.budget import BudgetEnforcer


class ForkExecutor:
    """Single-shot subagent runner; no parent context inheritance (per Day 2 D12)."""

    def __init__(self, *, chat_client: ChatClient, enforcer: BudgetEnforcer | None = None) -> None:
        self._chat = chat_client
        self._enforcer = enforcer or BudgetEnforcer()

    async def execute(
        self,
        *,
        subagent_id: UUID,
        task: str,
        budget: SubagentBudget,
        trace_context: TraceContext | None = None,
    ) -> SubagentResult:
        """Run task as single-shot LLM call; return SubagentResult (fail-closed)."""
        start = time.monotonic()
        try:
            request = ChatRequest(
                messages=[Message(role="user", content=task)],
                max_tokens=budget.max_tokens,
            )
            # Wall-clock timeout from budget.max_duration_s.
            response = await asyncio.wait_for(
                self._chat.chat(request, trace_context=trace_context),
                timeout=budget.max_duration_s,
            )
            duration_ms = (time.monotonic() - start) * 1000.0

            content = response.content if isinstance(response.content, str) else ""
            if not content:
                return SubagentResult(
                    subagent_id=subagent_id,
                    mode=SubagentMode.FORK,
                    success=False,
                    summary="",
                    duration_ms=duration_ms,
                    error="empty_response",
                )

            summary, _ = self._enforcer.truncate_summary(content, cap_words=500)
            if response.usage is None:
                tokens_used = 0
            elif response.usage.total_tokens > 0:
                tokens_used = response.usage.total_tokens
            else:
                tokens_used = response.usage.prompt_tokens + response.usage.completion_tokens
            return SubagentResult(
                subagent_id=subagent_id,
                mode=SubagentMode.FORK,
                success=True,
                summary=summary,
                tokens_used=tokens_used,
                duration_ms=duration_ms,
            )
        except asyncio.TimeoutError:
            duration_ms = (time.monotonic() - start) * 1000.0
            return SubagentResult(
                subagent_id=subagent_id,
                mode=SubagentMode.FORK,
                success=False,
                summary="",
                duration_ms=duration_ms,
                error=f"timeout: {budget.max_duration_s}s",
            )
        except Exception as exc:  # noqa: BLE001 — fail-closed catches all
            duration_ms = (time.monotonic() - start) * 1000.0
            return SubagentResult(
                subagent_id=subagent_id,
                mode=SubagentMode.FORK,
                success=False,
                summary="",
                duration_ms=duration_ms,
                error=f"chat_error: {type(exc).__name__}: {exc}",
            )
