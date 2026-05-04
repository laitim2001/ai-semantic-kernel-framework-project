"""
File: backend/src/agent_harness/subagent/modes/handoff.py
Purpose: HandoffExecutor — generates new session_id for control-transfer to target_agent.
Category: 範疇 11 (Subagent Orchestration)
Scope: Sprint 54.2 US-4

Description:
    HANDOFF mode (per OpenAI handoff pattern): parent agent transfers complete
    control to a target_agent identity. The new session_id is returned to the
    caller; the actual session creation / target_agent boot is the platform
    layer's responsibility (chat router / session manager) — Cat 11 dispatcher
    only allocates the identifier and audit-logs the transition intent.

    Per Day 4 D18 simplification: HandoffExecutor is intentionally lightweight
    (no LLM call, no mailbox). Phase 55+ may add policy checks (target_agent
    allowlist; tenant boundary enforcement) but for 54.2 minimal viable, the
    routing primitive is enough.

Created: 2026-05-04 (Sprint 54.2)

Modification History:
    - 2026-05-04: Initial creation (Sprint 54.2 US-4)

Related:
    - subagent/_abc.py — SubagentDispatcher.handoff() ABC
    - subagent/dispatcher.py — DefaultSubagentDispatcher.handoff
    - 01-eleven-categories-spec.md §範疇 11
"""

from __future__ import annotations

from uuid import UUID, uuid4

from agent_harness._contracts import TraceContext


class HandoffExecutor:
    """Allocate a new session_id for handoff to a target_agent identity.

    Stateless; no per-instance config. Phase 55+ may add per-tenant
    target_agent allowlist via constructor injection.
    """

    async def execute(
        self,
        *,
        target_agent: str,
        context: dict[str, object],
        trace_context: TraceContext | None = None,
    ) -> UUID:
        """Return a fresh session_id for the handed-off session.

        Per V2 contract: caller (chat router / API layer) is responsible for
        running the new session under target_agent identity using `context`
        as initial state. This method only allocates the UUID + (in future)
        emits an audit event.
        """
        # Validate target_agent is non-empty (cheap pre-check; deeper allowlist
        # check is the platform layer's responsibility).
        if not target_agent or not target_agent.strip():
            raise ValueError("target_agent must be non-empty")
        return uuid4()
