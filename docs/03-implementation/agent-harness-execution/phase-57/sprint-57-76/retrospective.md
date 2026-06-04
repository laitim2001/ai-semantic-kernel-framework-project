# Sprint 57.76 Retrospective — Memory ops-history backend

**Closed**: 2026-06-04
**Branch**: `feature/sprint-57-76-memory-ops-history`
**Commits**: `cc6c5a76` (Day-0) + `3133fb9c` (Track A backend) + closeout

---

## Q1 — Goal & delivery
Closed the **backend half** of `AD-Memory-OpsHistory-Backend` (Area-A remaining item). Delivered: NEW append-only `memory_ops` table (Option B) + Alembic 0024 (RLS 2-policy + FORCE mirror 0023) + `MemoryOp` ORM; `_record_memory_op` helper; user + tenant layer write/evict emit (same txn, SELECT-before-DELETE for value snapshot); `GET /memory/ops` (tenant-scoped, cursor-paginated, require_audit_role). All US met (US-3 role emit re-scoped — see Q4). Frontend → Sprint 57.77 (backend-then-FE split).

## Q2 — Calibration
Scope class `medium-backend` (0.80) + `agent_factor` `mixed-multidomain-bundle-mechanical` (0.45). Bottom-up ~11 hr → class-calibrated ~8.8 hr → agent-adjusted ~4 hr. **Agent-delegated: yes** (single Track A backend code-implementer ~13.5 min wall-clock + parent Day-0 3-researcher research + plan/checklist + full re-verify + closeout). **14th consecutive agent-delegated sprint with NO clean wall-clock** → ratio CAVEATED (`AD-Calibration-AgentDelegated-WallClock-Measure`). `medium-backend` 3-sprint-mean recalibration watch noted; this is a fresh data point for that class.

## Q3 — What went well
- **Day-0 3-researcher front-load + Prong-3 schema verify paid off**: migration slot 0024 free + 0023 RLS template confirmed at Day-0 → the 0024 migration mirrored verbatim first-pass (RLS lint green, no rework). Layer signatures + Risk-C session known upfront → emit wired correctly same-txn.
- **Risk Class C handled cleanly**: `_record_memory_op` takes the layer's session + only `session.add()` (no new session, no commit). The same-txn rollback test (`test_user_layer_write_op_same_txn_rollback`) proves atomicity — write→2 rows→rollback→0. This is the primary risk and it was the first thing the agent + I verified.
- **RLS tested with a non-BYPASSRLS role** (not superuser) — the correct way to test RLS (superuser bypasses it); both SELECT-scoping + INSERT WITH CHECK rejection asserted.
- **Honest scoping (AP-4)**: role/system layers raise → no emit (not unreachable dead code); session in-memory → not emitted; READ-path not emitted (volume). All documented, not faked.

## Q4 — What to improve / lessons
- **Researcher misreport on layer behavior (the real lesson)**: the schema researcher reported "`role_layer.py:76` = INSERT" → plan §0 D-DAY0-1 listed user/tenant/**role** emit. In reality `role_layer.py:89-111` write/evict **raise NotImplementedError** (the `:76` line was a `read()` SELECT). The code-implementer agent caught it on direct read + documented honestly; my parent re-verify confirmed by reading the file. **Lesson**: a researcher's one-line behavioral claim ("layer X does INSERT") is a Prong-2 *content* assertion that must be confirmed by reading the actual write/evict method body before the plan commits to it — exactly the Day-0 "verify premise against real repo" discipline, applied to researcher output, not just stale docs. Both the agent and the re-verify caught it, so no harm — but the plan §0 would have been more accurate if I'd had the agent (or myself) read the 3 layer write() bodies at Day-0 rather than trusting the researcher's line-number summary. (1 data point; if researcher behavioral-claim drift recurs, consider a Day-0 rule: "grep-confirm each `layer does X` claim against the method body".)
- **Endpoint path drift (minor)**: plan §3.4 said `api/v1/chat/memory.py`; the matrix + ops endpoints actually live in `api/v1/memory.py`. Agent placed it correctly (matrix sibling). Plan path was imprecise; no rework.
- **backend-then-FE split worked**: keeping this sprint backend-only kept it a healthy size; FE (hook + 2 components + e2e) is a clean 57.77.

## Q5 — Carryover
- **Sprint 57.77 (frontend half)**: `useMemoryOps` hook (mirror `useMemoryMatrix`) + wire `RecentMemoryOpsCard` (consume `GET /memory/ops`) + `TimeTravelScrubber` (timeline marks from ops) + remove fixtures + e2e. The `MemoryOpItem` shape maps to FE `RecentMemoryOp {op, scope, k, v, by, at}`.
- **READ-path emit** — write/evict only this sprint; sampled reads a future option (row-volume tradeoff).
- **role/session/system layer ops** — role/system raise (admin-managed/read-only); session in-memory volatile. Emittable if those layers gain live DB write paths.
- **Full point-in-time state reconstruction** — this sprint provides the time-ordered ops log (sufficient for RecentOps + TimeTravel marks); replaying snapshots to rebuild memory state at an arbitrary timestamp is a deeper future capability.
- **FE `/subagents` real list** (`AD-Subagent-RealList-Phase58`) — the last Area-A remaining item (agent_catalog specs already exist; needs tenant-facing GET + FE re-mount).

## Q6 — Anti-pattern / discipline check
- AP-4 (no Potemkin) ✅ — endpoint returns real persisted ops; role/system/session honest non-emit (not faked); evict no-fabrication on absent row. AP-2 (no orphan) ✅ — emit wired into the live user/tenant write/evict path. LLM-neutrality ✅ (`check_llm_sdk_leak` green; pure DB). Multi-tenant ✅ (tenant_id + RLS 2-policy + FORCE + explicit filter + non-BYPASSRLS RLS test + INSERT WITH CHECK). Sprint workflow ✅ (plan→checklist→Day-0→code→progress→retro). File headers ✅ (MHist on all touched + 3 new files).

## Q7 — Closeout verification (parent-run)
- mypy 0/331; pytest 2105 passed (8 emit + 3 RLS/Risk-C + 5 endpoint + 2 adjusted + regression); run_all 10/10; Alembic round-trip clean.
- **No design note** (feature-continuation: new table reuses 0023 RLS + TenantScopedMixin + matrix-endpoint pattern, like 57.70 agent_catalog new table — no new contract / no 17.md change).
