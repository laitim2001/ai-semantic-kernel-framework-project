# Sprint 57.70 Retrospective — Real Per-Tenant Agent-Spec Catalog + Admin CRUD API (backend slice; FE → 57.71)

**Closed**: 2026-06-02
**Plan**: `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-70-plan.md`
**Branch**: `feature/sprint-57-70-agent-catalog` (from `3090e8b7`)

---

## Q1 — What was delivered?

A real DB-backed per-tenant agent-spec catalog replacing the 57.68 hardcoded persona stand-in: the `agent_catalog` table (per-tenant, RLS, Group 9, fields per the mockup AgentSpec), `AgentCatalogRepository`, an async tenant-scoped resolver (DB catalog → hardcoded `DEFAULT_AGENTS` → `None`, DB-error fail-safe) rewired into both HANDOFF consumers, the 3 defaults seeded per existing tenant, and an admin CRUD API for the AgentSpec definitions (distinct from the `/subagents` invocations STUB). Backend-only; FE wiring of the existing `/subagents` page → 57.71.

## Q2 — Estimate accuracy / calibration

- Scope class **`agent-catalog-backend` (0.55, NEW — 1 data point)**; `agent_factor` **`mechanical-greenfield-design-decisions` 0.65**; **Agent-delegated: yes** (2 staged `code-implementer` — Stage-1a backend foundation, Stage-1b CRUD API — + parent independent re-verify each; closeout parent-authored).
- Plan: bottom-up ~15 hr → class-calibrated ~8.2 hr (0.55) → agent-adjusted ~5.4 hr (0.65).
- **No clean wall-clock** (agent-delegated, multi-tool session) → **8th consecutive** agent-delegated no-clean-measure (57.63→57.70) → reinforces `AD-Calibration-AgentDelegated-WallClock-Measure`. CAVEATED; the NEW `agent-catalog-backend` 0.55 is a single unvalidated point — do NOT generalize. `agent_factor` 0.65 kept.

## Q3 — What went well?

- **Day-0 (3 researcher rounds) caught a >20% misframe before any code** — the original plan assumed a generic `agent_catalog` + new Manage-Agents page; Day-0 found the catalog = the existing Subagent Registry of AgentSpec definitions (mockup + 09 Group 9 + a read-only fixture `/subagents` page), the `/subagents` GET is a separate invocations STUB, and no registry table exists. Re-confirmed with the user → backend-only, FE → 57.71. This avoided building the wrong thing + a 2-sprint-sized FE in one sprint.
- **The resolver fallback chain preserved the contract cleanly** — DB → `DEFAULT_AGENTS` → `None` (+ DB-error fail-safe) means an empty/new-tenant catalog still resolves the 3 defaults; the 57.68/69 handoff behavior is unchanged (only the source moved DB-ward). The sync→async rewire rippled to just 2 already-async consumers.
- **Staged delegation + parent re-verify** — Stage-1a (foundation) re-verified before Stage-1b (CRUD) built on it; the parent read every contract-critical file (resolver, service/handler rewire, ORM alias, migration RLS/seed) rather than trusting the agent report.

## Q4 — What to improve / lessons

- **Day-0 depth paid off twice** — the first plan draft (generic catalog) would have shipped the wrong concept; only the mockup-existence check (`page-agents.jsx`) + the existing-`/subagents`-stack survey revealed the real shape. Lesson reinforced: for a feature that touches an existing UI surface, Day-0 MUST check `reference/design-mockups/` AND the existing FE/API for that surface before drafting the plan's FE/API sections.
- **Tooling note**: a Bash grep returned text-substituted output ("subagents"→"n/ns") — used a `codebase-researcher` for a clean structured map instead of trusting the corrupted grep. Lesson: when grep output looks corrupted, re-read via a dedicated reader, don't act on it.

## Q5 — Carryover / open items (plan §9)

- **FE: wire the existing `/subagents` page to the catalog** (replace fixture + editable AgentSpec/Budget/Tools/Stats tabs + create/edit/delete) → **Sprint 57.71** (user-confirmed).
- **allowed_modes / budget / tools loop-enforcement** — STORED (JSONB) but not enforced this slice.
- **`AD-Subagent-RealList-Phase58`** — the `/subagents` invocations real list (a different concept; the STUB is untouched).
- **Default (non-handoff) chat persona from the catalog** / provisioning-step seeding / tenant self-service — deferred.
- **Other A-3b carryover** — transcript continuity (message-persistence subsystem), summarize-carry, target auto-first-turn, multi-hop chains. Other Area-A: A-4 (loop tracer), A-5c (Inspector UI), A-6.

## Q6 — Anti-pattern audit (04-anti-patterns.md)

- AP-2 (no Potemkin / orphan): the catalog is exercised end-to-end (integration asserts the HANDOFF target resolves from the DB row + the CRUD persists/audits) — not a phantom. ✅
- AP-4 (Potemkin): the resolver demonstrably reads the DB; the CRUD writes real rows + audit. ✅ Distinct from the (acknowledged) `/subagents` invocations STUB — not conflated.
- LLM neutrality: catalog/repo/resolver provider-free (`check_llm_sdk_leak` 0); `agent_harness/**` untouched. ✅
- Multi-tenant: RLS (2 policies + FORCE, `check_rls_policies` green) + repo tenant-filter; cross-tenant rejected (tested). ✅
- AP-3 (cross-dir scatter): catalog cohered in `infrastructure/db/{models,repositories}` + `platform_layer/handoff` + `api/v1/admin`; no scatter. ✅

## Q7 — Final verification

pytest `tests/unit tests/integration` **2049 passed / 4 skipped / 0 failed**; `mypy src/` 0/329; `run_all.py` 10/10; black 603 unchanged + isort/flake8 0; Alembic 0023 up/down clean; Vitest unchanged (no FE). No design note (feature-continuation).
