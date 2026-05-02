"""
File: backend/src/agent_harness/state_mgmt/checkpointer.py
Purpose: Concrete DBCheckpointer — V2 范疇 7 wrapping Sprint 49.2 state_snapshots ORM.
Category: 范疇 7 (State Management)
Scope: Phase 53.1 / Sprint 53.1

Description:
    Wraps the Sprint 49.2 infrastructure (state_snapshots table, append-only
    trigger, append_snapshot helper) to provide V2 范疇 7 Checkpointer ABC
    contract: save / load / time_travel.

    US-3 split enforcement: only DurableState fields + transient SCALAR
    summary (current_turn / elapsed_ms / token_usage_so_far) are persisted.
    The messages buffer + pending_tool_calls list are NOT serialized — they
    are recreatable from messages history (Cat 3 / range 4 responsibility)
    or re-fetched on resume.

    Optimistic concurrency: 49.2 helper uses StateVersion 雙因子 (counter +
    state_hash). On save, we look up the latest snapshot for this session
    (single-writer assumption per AgentLoop) and pass parent_version +
    expected_parent_hash; concurrent writers race on UNIQUE(session_id,
    version) and one gets StateConflictError.

    Bound checkpointer pattern: each instance is bound to ONE (session_id,
    tenant_id) pair via constructor. The Checkpointer ABC's load() takes
    only `version` — session is implicit from constructor binding.

Key Components:
    - DBCheckpointer: production impl of Checkpointer ABC
    - _serialize_state_for_db: LoopState -> JSONB-safe dict (US-3 split)
    - _deserialize_state_from_db: JSONB -> LoopState (transient buffers empty)

Owner: 01-eleven-categories-spec.md §范疇 7
Single-source: 17.md §2.1 (Checkpointer ABC)
Reuses: Sprint 49.2 (0004_state.py migration + models/state.py)

Created: 2026-05-02 (Sprint 53.1 Day 2)
Last Modified: 2026-05-02

Modification History (newest-first):
    - 2026-05-02: Initial creation (Sprint 53.1 Day 2) — wraps 49.2 append_snapshot

Related:
    - 01-eleven-categories-spec.md §范疇 7
    - 17-cross-category-interfaces.md §2.1 Checkpointer ABC
    - infrastructure/db/models/state.py (StateSnapshot ORM + append_snapshot helper)
    - infrastructure/db/migrations/versions/0004_state.py
    - 09-db-schema-design.md Group 5 State (L508-555)
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_harness._contracts import (
    DurableState,
    LoopState,
    StateVersion,
    TraceContext,
    TransientState,
)
from agent_harness.state_mgmt._abc import Checkpointer
from infrastructure.db.models import (
    StateSnapshot,
    append_snapshot,
)


class StateNotFoundError(Exception):
    """Raised when load() / time_travel() cannot find the requested version."""


class StateMismatchError(Exception):
    """Raised when state.durable.{session_id,tenant_id} doesn't match Checkpointer binding."""


# === DBCheckpointer: production-grade DB checkpoint ===
# Why: V1 had no persistent checkpoints — process restart lost all state,
# HITL pause/resume was impossible. V2 §范疇 7 mandates DB-backed snapshots
# at safe points (after tool / verify / on HITL pause) so the loop can be
# rebuilt at any past version (time-travel for debugging + replay).
#
# Alternative considered:
#   - Redis-backed snapshot — rejected: not durable across Redis flush;
#     also we already have PostgreSQL append-only trigger for audit value
#   - File-system serialization — rejected: no tenant isolation, no
#     concurrency safety, fails in container/k8s
# Reference: agent-harness-planning/01-eleven-categories-spec.md §范疇 7;
# Sprint 49.2 plan §4 (StateVersion 雙因子 design).
class DBCheckpointer(Checkpointer):
    """DB-backed Checkpointer; bound to one (session_id, tenant_id).

    Each AgentLoop instance creates its own DBCheckpointer for the session
    it is processing. save() and load() operations always scope to the
    bound session + tenant, providing isolation + simplifying the Checkpointer
    ABC's load(version=...) signature (no need to pass session_id each call).

    Uses 49.2 append_snapshot helper for optimistic concurrency. Range 7
    Reducer is the in-memory mutator; Checkpointer is the DB persistor —
    they are decoupled (Reducer doesn't know about DB).
    """

    def __init__(
        self,
        db_session: AsyncSession,
        *,
        session_id: UUID,
        tenant_id: UUID,
    ) -> None:
        self._db = db_session
        self._session_id = session_id
        self._tenant_id = tenant_id

    async def save(
        self,
        state: LoopState,
        *,
        trace_context: TraceContext | None = None,
    ) -> StateVersion:
        # Binding validation — caller bug if these mismatch
        if state.durable.session_id != self._session_id:
            raise StateMismatchError(
                f"state.durable.session_id={state.durable.session_id} "
                f"!= checkpointer session_id={self._session_id}"
            )
        if state.durable.tenant_id != self._tenant_id:
            raise StateMismatchError(
                f"state.durable.tenant_id={state.durable.tenant_id} "
                f"!= checkpointer tenant_id={self._tenant_id}"
            )

        state_data = _serialize_state_for_db(state)
        prev = await self._latest_snapshot()
        parent_version = prev.version if prev else None
        expected_parent_hash = prev.state_hash if prev else None

        snapshot = await append_snapshot(
            self._db,
            session_id=self._session_id,
            tenant_id=self._tenant_id,
            state_data=state_data,
            turn_num=state.transient.current_turn,
            parent_version=parent_version,
            expected_parent_hash=expected_parent_hash,
            reason=state.version.created_by_category,
        )

        # Tracer hook — actual emit wired in observability pipeline.
        _ = trace_context

        return StateVersion(
            version=snapshot.version,
            parent_version=snapshot.parent_version,
            created_at=snapshot.created_at,
            created_by_category=snapshot.reason,
        )

    async def load(
        self,
        *,
        version: int,
        trace_context: TraceContext | None = None,
    ) -> LoopState:
        result = await self._db.execute(
            select(StateSnapshot).where(
                (StateSnapshot.session_id == self._session_id)
                & (StateSnapshot.tenant_id == self._tenant_id)
                & (StateSnapshot.version == version)
            )
        )
        row: StateSnapshot | None = result.scalar_one_or_none()
        if row is None:
            raise StateNotFoundError(
                f"no snapshot for session_id={self._session_id} version={version}"
            )
        _ = trace_context
        return _deserialize_state_from_db(row)

    async def time_travel(
        self,
        *,
        target_version: int,
        trace_context: TraceContext | None = None,
    ) -> LoopState:
        # Same query path as load(); semantic difference is debugging intent.
        return await self.load(version=target_version, trace_context=trace_context)

    # === Helpers ===
    async def _latest_snapshot(self) -> StateSnapshot | None:
        """Latest snapshot for the bound session (DESC index 49.2 Day 4.3)."""
        result = await self._db.execute(
            select(StateSnapshot)
            .where(
                (StateSnapshot.session_id == self._session_id)
                & (StateSnapshot.tenant_id == self._tenant_id)
            )
            .order_by(StateSnapshot.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


# === Serialization helpers (US-3 transient/durable split) ===
# Why: messages buffer + pending_tool_calls list are large and recreatable
# from messages history (Cat 3) — persisting them per-snapshot would balloon
# DB row size (could exceed 100KB for long conversations). We persist only
# DurableState + transient SCALAR summary (per US-3 acceptance: row < 5KB).
#
# On load, transient buffers are rehydrated as empty; the AgentLoop is
# responsible for refilling messages from messages table on resume.


def _serialize_state_for_db(state: LoopState) -> dict[str, Any]:
    """LoopState -> JSONB-safe dict. Excludes messages + pending_tool_calls."""
    return {
        "durable": {
            "session_id": str(state.durable.session_id),
            "tenant_id": str(state.durable.tenant_id),
            "user_id": (str(state.durable.user_id) if state.durable.user_id is not None else None),
            "pending_approval_ids": [str(aid) for aid in state.durable.pending_approval_ids],
            "last_checkpoint_version": state.durable.last_checkpoint_version,
            "conversation_summary": state.durable.conversation_summary,
            "metadata": dict(state.durable.metadata),
        },
        "transient_summary": {
            "current_turn": state.transient.current_turn,
            "elapsed_ms": state.transient.elapsed_ms,
            "token_usage_so_far": state.transient.token_usage_so_far,
        },
        "version_meta": {
            "version": state.version.version,
            "parent_version": state.version.parent_version,
            "created_at_iso": state.version.created_at.isoformat(),
            "created_by_category": state.version.created_by_category,
        },
    }


def _deserialize_state_from_db(row: StateSnapshot) -> LoopState:
    """state_snapshots row -> LoopState with empty transient buffers.

    StateVersion is reconstructed from DB row authoritative fields
    (row.version / row.parent_version / row.created_at / row.reason),
    NOT from the version_meta embedded in state_data — the DB chain
    is the source of truth post-save (see save() — append_snapshot may
    assign a different version than state.version had).
    """
    data = row.state_data
    durable_data = data["durable"]
    summary = data["transient_summary"]

    return LoopState(
        transient=TransientState(
            messages=[],  # US-3: caller rehydrates from messages history
            pending_tool_calls=[],  # US-3: ephemeral; not persisted
            current_turn=summary["current_turn"],
            elapsed_ms=summary["elapsed_ms"],
            token_usage_so_far=summary["token_usage_so_far"],
        ),
        durable=DurableState(
            session_id=UUID(durable_data["session_id"]),
            tenant_id=UUID(durable_data["tenant_id"]),
            user_id=(
                UUID(durable_data["user_id"]) if durable_data["user_id"] is not None else None
            ),
            pending_approval_ids=[UUID(aid) for aid in durable_data["pending_approval_ids"]],
            last_checkpoint_version=durable_data["last_checkpoint_version"],
            conversation_summary=durable_data["conversation_summary"],
            metadata=dict(durable_data["metadata"]),
        ),
        version=StateVersion(
            version=row.version,
            parent_version=row.parent_version,
            created_at=row.created_at,
            created_by_category=row.reason,
        ),
    )
