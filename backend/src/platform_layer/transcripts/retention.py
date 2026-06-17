"""
File: backend/src/platform_layer/transcripts/retention.py
Purpose: apply_transcript_retention — delete (or dry-run count) transcript rows past retention.
Category: Phase 57 platform_layer.transcripts (data lifecycle)
Scope: Sprint 57.134 (transcript retention — apply/preview on the canonical tenants.retention_days)

Description:
    Enforces a tenant's transcript retention window by deleting messages + message_events
    older than (now - retention_days). The retention window is the CANONICAL
    tenants.retention_days SaaS-settings column (Sprint 57.46; settable via the admin
    PATCH /tenants/{id}) — this module does NOT introduce a parallel config (Day-0 pivot,
    Sprint 57.134: avoids the AP-6 parallel-config anti-pattern; the column already exists).

    apply_transcript_retention supports a dry_run mode that COUNTS the rows that would be
    deleted (no mutation) — backs the admin "preview" GET so an operator can see the impact
    before running the destructive apply POST.

    Provider-neutral; no SDK / agent_harness import.

    RLS: messages / message_events / audit_log are FORCE ROW LEVEL SECURITY (migration 0009),
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid). The admin path uses a
    plain (non-tenant) session, so this sets app.tenant_id for the txn (set_config local)
    before the DELETE / COUNT so the cross-tenant admin operation satisfies the USING policy;
    the explicit WHERE tenant_id filter is the real scope (correct even if the app role owns
    the schema and bypasses FORCE in dev/test).

Key Components:
    - RetentionStats — (messages, events, cutoff); apply=deleted, dry_run=matched counts
    - apply_transcript_retention(db, tenant_id, retention_days, *, now, dry_run) -> RetentionStats

Created: 2026-06-17 (Sprint 57.134)
Last Modified: 2026-06-17

Modification History (newest-first):
    - 2026-06-17: Initial creation (Sprint 57.134) — apply/preview on tenants.retention_days

Related:
    - infrastructure/db/models/identity.py — Tenant.retention_days (canonical SaaS col, 57.46)
    - infrastructure/db/models/sessions.py — Message + MessageEvent (tenant_id, created_at)
    - migrations/versions/0009_rls_policies.py — FORCE RLS on the transcript tables (SET LOCAL)
    - api/v1/admin/tenants.py — the apply POST + preview GET endpoints that consume this module
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import delete, func, select, text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class RetentionStats:
    """Outcome of one retention run. apply -> deleted counts; dry_run -> would-delete counts."""

    messages: int
    events: int
    cutoff: datetime


async def apply_transcript_retention(
    db: AsyncSession,
    tenant_id: UUID,
    retention_days: int,
    *,
    now: datetime | None = None,
    dry_run: bool = False,
) -> RetentionStats:
    """Delete (or, when dry_run, COUNT) messages + message_events older than the retention window.

    retention_days is the tenant's canonical tenants.retention_days (NOT NULL, >= 1). cutoff =
    now - retention_days. `now` is injectable for deterministic tests; defaults to UTC now.
    Strictly tenant-scoped (explicit WHERE + a SET LOCAL app.tenant_id for the FORCE'd RLS on
    messages/message_events). Runs inside the caller's transaction (the apply endpoint commits
    after auditing; the preview endpoint does not mutate, so it never commits).
    """
    resolved_now = now if now is not None else datetime.now(timezone.utc)
    cutoff = resolved_now - timedelta(days=retention_days)

    # RLS context for this txn (messages / message_events are FORCE ROW LEVEL SECURITY).
    await db.execute(
        text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": str(tenant_id)}
    )

    from infrastructure.db.models.sessions import Message, MessageEvent

    if dry_run:
        msg_n = await _count_older(db, Message, tenant_id, cutoff)
        evt_n = await _count_older(db, MessageEvent, tenant_id, cutoff)
        return RetentionStats(messages=msg_n, events=evt_n, cutoff=cutoff)

    msg_result = await db.execute(
        delete(Message)
        .where(Message.tenant_id == tenant_id, Message.created_at < cutoff)
        .execution_options(synchronize_session=False)
    )
    evt_result = await db.execute(
        delete(MessageEvent)
        .where(MessageEvent.tenant_id == tenant_id, MessageEvent.created_at < cutoff)
        .execution_options(synchronize_session=False)
    )
    return RetentionStats(
        messages=int(getattr(msg_result, "rowcount", 0) or 0),
        events=int(getattr(evt_result, "rowcount", 0) or 0),
        cutoff=cutoff,
    )


async def _count_older(db: AsyncSession, model: Any, tenant_id: UUID, cutoff: datetime) -> int:
    """COUNT rows of `model` for the tenant older than cutoff (dry-run helper)."""
    result = await db.execute(
        select(func.count())
        .select_from(model)
        .where(model.tenant_id == tenant_id, model.created_at < cutoff)
    )
    return int(result.scalar_one() or 0)
