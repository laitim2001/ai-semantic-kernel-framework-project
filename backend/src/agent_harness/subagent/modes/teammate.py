"""
File: backend/src/agent_harness/subagent/modes/teammate.py
Purpose: TeammateExecutor — runs a peer subagent that communicates via mailbox.
Category: 範疇 11 (Subagent Orchestration)
Scope: Sprint 54.2 US-3

Description:
    TEAMMATE mode (per CC peer-pane pattern): a subagent runs independently of
    the parent's context but can send messages back via MailboxStore. Unlike
    Fork (parent context copy), Teammate has its own fresh context — useful
    for parallel exploratory agents or specialist roles that should NOT see
    parent's full conversation history.

    Per Day 3 simplification (D15): single-shot LLM call (same as Fork) but
    with mailbox side effect — the subagent's response is also `send()`d to
    parent's "parent" recipient queue. This demonstrates mailbox infrastructure
    works without committing to multi-turn child loop semantics. Phase 55+
    may extend to multi-turn loop pulling from mailbox each iteration.

    Failure modes (all return SubagentResult(success=False) — fail-closed):
    - ChatClient raises any exception → error="chat_error: {type}: {msg}"
    - asyncio.TimeoutError on max_duration_s → error="timeout: {N}s"
    - Empty response.content → error="empty_response"
    - Mailbox.send() raises (rare) → swallowed; LLM result still returned

Created: 2026-05-04 (Sprint 54.2)

Modification History:
    - 2026-05-04: Initial creation (Sprint 54.2 US-3)

Related:
    - subagent/mailbox.py — MailboxStore (US-3 dependency)
    - subagent/modes/fork.py — sibling executor; same fail-closed pattern
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
from agent_harness.subagent.mailbox import MailboxStore


class TeammateExecutor:
    """Peer subagent runner; result also delivered to parent via mailbox.

    Per Day 3 D15 simplification: single-shot LLM call (no multi-turn child
    loop pulling from mailbox). The mailbox.send() at the end demonstrates
    the bidirectional communication infrastructure; Phase 55+ may extend.
    """

    def __init__(
        self,
        *,
        chat_client: ChatClient,
        mailbox: MailboxStore,
        enforcer: BudgetEnforcer | None = None,
    ) -> None:
        self._chat = chat_client
        self._mailbox = mailbox
        self._enforcer = enforcer or BudgetEnforcer()

    async def execute(
        self,
        *,
        subagent_id: UUID,
        parent_session_id: UUID,
        role: str,
        task: str,
        budget: SubagentBudget,
        trace_context: TraceContext | None = None,
    ) -> SubagentResult:
        """Run task as single-shot LLM call; deliver summary to parent's mailbox."""
        start = time.monotonic()
        try:
            request = ChatRequest(
                messages=[Message(role="user", content=task)],
                max_tokens=budget.max_tokens,
            )
            response = await asyncio.wait_for(
                self._chat.chat(request, trace_context=trace_context),
                timeout=budget.max_duration_s,
            )
            duration_ms = (time.monotonic() - start) * 1000.0

            content = response.content if isinstance(response.content, str) else ""
            if not content:
                return SubagentResult(
                    subagent_id=subagent_id,
                    mode=SubagentMode.TEAMMATE,
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

            # Deliver to parent's mailbox (best-effort; swallow exceptions).
            try:
                await self._mailbox.send(
                    session_id=parent_session_id,
                    sender=role,
                    recipient="parent",
                    content=summary,
                )
            except Exception:  # noqa: BLE001 — best-effort delivery
                pass

            return SubagentResult(
                subagent_id=subagent_id,
                mode=SubagentMode.TEAMMATE,
                success=True,
                summary=summary,
                tokens_used=tokens_used,
                duration_ms=duration_ms,
            )
        except asyncio.TimeoutError:
            duration_ms = (time.monotonic() - start) * 1000.0
            return SubagentResult(
                subagent_id=subagent_id,
                mode=SubagentMode.TEAMMATE,
                success=False,
                summary="",
                duration_ms=duration_ms,
                error=f"timeout: {budget.max_duration_s}s",
            )
        except Exception as exc:  # noqa: BLE001 — fail-closed catches all
            duration_ms = (time.monotonic() - start) * 1000.0
            return SubagentResult(
                subagent_id=subagent_id,
                mode=SubagentMode.TEAMMATE,
                success=False,
                summary="",
                duration_ms=duration_ms,
                error=f"chat_error: {type(exc).__name__}: {exc}",
            )
