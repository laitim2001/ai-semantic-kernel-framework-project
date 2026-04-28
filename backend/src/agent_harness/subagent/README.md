# Category 11 — Subagent Orchestration

**ABC**: `SubagentDispatcher` (in `_abc.py`)
**Spec**: `01-eleven-categories-spec.md` §範疇 11
**Implementation Phase**: 54.2
**V1 Alignment**: 35% → V2 target 75%+

## 4 modes (NO worktree)

| Mode      | Behavior |
|-----------|----------|
| FORK      | Parallel sub-task; result merged back via summary |
| TEAMMATE  | Peer-to-peer mailbox communication (multi-agent) |
| HANDOFF   | Transfer control entirely to another agent |
| AS_TOOL   | LLM calls subagent as if it were a tool |

**Worktree mode** (CC has it) is intentionally absent — V2 runs
server-side, no per-process git checkout.

## Budget enforcement

`SubagentBudget` caps token / duration / concurrency / depth. Prevents
runaway cost from recursive spawn explosion.

## Cross-category tools owned

Per 17.md §3.1 — `task_spawn` and `handoff` tools are owned here and
registered into Cat 2 Registry.

## Sprint roadmap

| Sprint | Adds |
|--------|------|
| 49.1   | ABC stub (this) |
| 54.2   | 4 modes implementation + budget enforcement + mailbox + handoff |
