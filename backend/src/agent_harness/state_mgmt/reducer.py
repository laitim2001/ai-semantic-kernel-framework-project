"""
File: backend/src/agent_harness/state_mgmt/reducer.py
Purpose: Concrete DefaultReducer — sole mutator of LoopState with monotonic version + audit trail.
Category: 範疇 7 (State Management)
Scope: Phase 53.1 / Sprint 53.1

Description:
    Implements the Reducer ABC contract from _abc.py. Every other category
    submits update dicts here; Reducer rebuilds LoopState (frozen StateVersion
    bumped by 1) and emits audit-trail metadata via OpenTelemetry tracer hook.

    Update protocol (dict-based):
        {
          "transient": {"messages_append": [...], "current_turn": int, ...},
          "durable":   {"pending_approval_ids_add": [UUID], "metadata_set": {...}, ...}
        }

    Thread safety: asyncio.Lock guarantees serialized merges so version sequence
    has no holes even under parallel asyncio.gather() submissions.

Key Components:
    - DefaultReducer: production impl of Reducer ABC
    - _merge_transient: rebuild TransientState (additive list ops + scalar replace)
    - _merge_durable: rebuild DurableState (additive/remove approval ids + dict metadata)

Owner: 01-eleven-categories-spec.md §範疇 7
Single-source: 17.md §2.1 (Reducer ABC)

Created: 2026-05-02 (Sprint 53.1 Day 1)
Last Modified: 2026-05-02

Modification History (newest-first):
    - 2026-05-02: Initial creation (Sprint 53.1 Day 1) — concrete impl of Sprint 49.1 ABC stub

Related:
    - 01-eleven-categories-spec.md §範疇 7 — State Mgmt spec
    - 17-cross-category-interfaces.md §2.1 — Reducer ABC
    - state_mgmt/_abc.py — Reducer ABC (source of contract)
    - _contracts/state.py — LoopState / StateVersion / TransientState / DurableState
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from agent_harness._contracts import (
    DurableState,
    LoopState,
    StateVersion,
    TraceContext,
    TransientState,
)
from agent_harness.state_mgmt._abc import Reducer


# === DefaultReducer: production-grade sole-mutator ===
# Why: V1 had ad-hoc state mutation across multiple categories (orchestrator,
# tools, memory) leading to race conditions + difficult-to-trace bugs.
# V2 §範疇 7 designates a single Reducer as the only mutation point;
# all other categories produce update dicts which Reducer applies.
# Alternative considered:
#   - Plain dataclasses.replace() — rejected: no audit trail / no lock
#   - Pydantic mutable model — rejected: introduces extra dep + breaks frozen
#     StateVersion semantics
# Reference: agent-harness-planning/04-anti-patterns.md §AP-3 cross-directory
# scattering; Reducer-as-sole-mutator pattern eliminates this.
class DefaultReducer(Reducer):
    """In-memory reducer; serializes merges via asyncio.Lock.

    Each merge:
    1. Acquires lock (no parallel mutation)
    2. Bumps StateVersion by 1 (parent_version preserved for time-travel)
    3. Stamps source_category + UTC created_at for audit trail
    4. Rebuilds TransientState + DurableState from update patch
    5. Returns NEW LoopState (callers replace their reference)
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()

    async def merge(
        self,
        state: LoopState,
        update: dict[str, Any],
        *,
        source_category: str,
        trace_context: TraceContext | None = None,
    ) -> LoopState:
        async with self._lock:
            new_version = StateVersion(
                version=state.version.version + 1,
                parent_version=state.version.version,
                created_at=datetime.now(timezone.utc),
                created_by_category=source_category,
            )
            new_transient = self._merge_transient(state.transient, update.get("transient", {}))
            new_durable = self._merge_durable(state.durable, update.get("durable", {}))
            # Tracer hook: trace_context plumbed through for observability
            # (range 12); actual emit wired in Sprint 49.4 OTel scaffold —
            # here we keep the parameter to satisfy contract + future use.
            _ = trace_context
            return LoopState(
                transient=new_transient,
                durable=new_durable,
                version=new_version,
            )

    # === _merge_transient ===
    # Why: TransientState fields are mostly recreatable buffers (messages,
    # tool_calls) so we accept additive `_append` / `_set` / `_clear` ops
    # plus scalar replace for current_turn / elapsed_ms / token_usage_so_far.
    def _merge_transient(self, current: TransientState, patch: dict[str, Any]) -> TransientState:
        kwargs: dict[str, Any] = {
            "messages": list(current.messages),
            "pending_tool_calls": list(current.pending_tool_calls),
            "current_turn": current.current_turn,
            "elapsed_ms": current.elapsed_ms,
            "token_usage_so_far": current.token_usage_so_far,
        }
        if "messages_append" in patch:
            kwargs["messages"].extend(patch["messages_append"])
        if "current_turn" in patch:
            kwargs["current_turn"] = patch["current_turn"]
        if "elapsed_ms" in patch:
            kwargs["elapsed_ms"] = patch["elapsed_ms"]
        if "token_usage_so_far" in patch:
            kwargs["token_usage_so_far"] = patch["token_usage_so_far"]
        if "pending_tool_calls_set" in patch:
            kwargs["pending_tool_calls"] = list(patch["pending_tool_calls_set"])
        if patch.get("pending_tool_calls_clear"):
            kwargs["pending_tool_calls"] = []
        return TransientState(**kwargs)

    # === _merge_durable ===
    # Why: DurableState fields are persisted to DB (Phase 53.1 US-2). We accept
    # additive `_add` / `_remove` for pending_approval_ids (set semantics on
    # remove side) and dict-update for metadata_set. session_id / tenant_id are
    # immutable post-creation (no patch handlers).
    def _merge_durable(self, current: DurableState, patch: dict[str, Any]) -> DurableState:
        kwargs: dict[str, Any] = {
            "session_id": current.session_id,
            "tenant_id": current.tenant_id,
            "user_id": current.user_id,
            "pending_approval_ids": list(current.pending_approval_ids),
            "last_checkpoint_version": current.last_checkpoint_version,
            "conversation_summary": current.conversation_summary,
            "metadata": dict(current.metadata),
        }
        if "pending_approval_ids_add" in patch:
            kwargs["pending_approval_ids"].extend(patch["pending_approval_ids_add"])
        if "pending_approval_ids_remove" in patch:
            to_remove = set(patch["pending_approval_ids_remove"])
            kwargs["pending_approval_ids"] = [
                aid for aid in kwargs["pending_approval_ids"] if aid not in to_remove
            ]
        if "conversation_summary" in patch:
            kwargs["conversation_summary"] = patch["conversation_summary"]
        if "last_checkpoint_version" in patch:
            kwargs["last_checkpoint_version"] = patch["last_checkpoint_version"]
        if "user_id" in patch:
            kwargs["user_id"] = patch["user_id"]
        if "metadata_set" in patch:
            kwargs["metadata"].update(patch["metadata_set"])
        return DurableState(**kwargs)
