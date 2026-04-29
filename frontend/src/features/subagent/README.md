# features/subagent

UI components for **Category 11 (Subagent Orchestration)** — swarm visualizer.

**Backend pair**: `backend/src/agent_harness/subagent/`
**First impl**: Phase 54.2

## Components (planned)

- `<SubagentTree>` — recursive view of fork / handoff / as_tool subagent chain
- `<SubagentBudgetMeter>` — current usage vs `SubagentBudget` (token / duration / concurrency / depth)
- `<SubagentModeBadge>` — FORK / TEAMMATE / HANDOFF / AS_TOOL visual (no WORKTREE per V2 design)
