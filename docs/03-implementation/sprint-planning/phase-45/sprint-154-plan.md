# Sprint 154 Plan - U2: HITL Approval Gate

## Phase 45: Agent Team V4 - P1 Upgrades

### Sprint Goal
Add human-in-the-loop approval checkpoint to agent work loop for high-risk tool calls, matching CC's Permission UI pattern.

---

## User Stories

### US-154-1: Tool Risk Assessment
**As** the system,
**I want** to classify tool calls by risk level,
**So that** high-risk operations require human approval.

### US-154-2: Per-Agent Approval Pause
**As** a human operator,
**I want** to approve/reject high-risk tool calls,
**So that** dangerous operations don't execute without oversight.

---

## Technical Specification

### Approval Flow
1. Agent LLM selects a tool → check `requires_approval(tool_name)`
2. HIGH risk → emit `APPROVAL_REQUIRED` SSE → poll HITLController every 2s
3. Only the requesting agent pauses (asyncio.sleep in its coroutine)
4. Other agents continue working (asyncio.gather natural isolation)
5. User approves/rejects via existing `POST /approvals/{id}/decision`
6. Agent resumes or skips tool

### Risk Classification (PoC-level)
- HIGH: `run_diagnostic_command`, `query_database`
- MEDIUM: `search_knowledge_base` (no approval needed)
- LOW: all other tools

### Reused Infrastructure
- HITLController from `integrations/orchestration/hitl/controller.py`
- Approval API from `api/v1/orchestration/approval_routes.py`
- SSE APPROVAL_REQUIRED event already in `sse_events.py`
- Frontend `useOrchestratorSSE.ts` already handles approval state

---

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/src/integrations/poc/approval_gate.py` | NEW | Risk check + approval helper (~120 LOC) |
| `backend/src/integrations/poc/agent_work_loop.py` | MODIFY | Insert approval checkpoint in tool execution |
| `backend/src/api/v1/poc/agent_team_poc.py` | MODIFY | Initialize HITLController |
| `frontend/src/pages/AgentTeamTestPage.tsx` | MODIFY | Approval dialog for team page |

---

## Acceptance Criteria

- [ ] HIGH risk tool → APPROVAL_REQUIRED SSE event emitted
- [ ] Approve → agent continues with tool execution
- [ ] Reject → agent skips tool, receives rejection message
- [ ] Other agents NOT blocked during approval wait
- [ ] 5 minute timeout → auto-expired
- [ ] Frontend shows approval dialog with tool name + agent name
