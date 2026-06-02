# Sprint 57.70 Progress — Real Per-Tenant Agent-Spec Catalog + Admin CRUD API (backend slice; FE → 57.71)

**Plan**: `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-70-plan.md`
**Checklist**: `.../sprint-57-70-checklist.md`
**Branch**: `feature/sprint-57-70-agent-catalog` (from main `3090e8b7`)

---

## Day 0 — 2026-06-02 — Plan-vs-Repo Verify + Reframe + Branch

### Scope selection (AskUserQuestion 2026-06-02)
- After 57.69 closed, the user picked the A-3b carryover item **real per-tenant agent catalog** for 57.70, then **+ Admin CRUD API + FE page** for scope.

### Three-prong Day-0 verify — drift D1-D7 (3 researcher rounds; reframed the plan)

The original plan (committed `ba3e7086`) assumed a NEW generic `agent_catalog` table + a NEW "Manage-Agents" FE page. Day-0 found the real shape:

- **D1** — the "agent catalog" IS the existing **Subagent Registry of AgentSpec definitions** (mockup `page-agents.jsx:311-438` `SubagentsRegistry`, faithful 57.38 port; fields role/model/system_prompt/allowed_modes/status + 4 detail tabs AgentSpec/Budget/Tools/Stats); 09-schema **Group 9 Subagent** is the home; `AgentSpec` (`_contracts/subagent.py:74-86`) is the in-code shape.
- **D2** — the `/subagents` FE page ALREADY EXISTS (`SubagentsPage.tsx` + `features/subagents/*`), a faithful mockup port (57.20+) but **read-only fixture** (4 detail tabs `defaultValue`/`readOnly`, zero CRUD). → making it real = moderate-to-large FE → **deferred to 57.71**.
- **D3** — the existing `GET /api/v1/subagents` is a **STUB about INVOCATIONS** (`subagents.py:67,95-121`; empty + `not_implemented_reason`; `SubagentItem` = invocation shape), a DIFFERENT concept from AgentSpec definitions (`AD-Subagent-RealList-Phase58`). → the definitions CRUD is a NEW endpoint; the invocations STUB is untouched.
- **D4** — NO registry table (33-table scan); next migration `0023`. → CREATE `agent_catalog` (per-tenant + RLS).
- **D5** — `resolve_persona` sync + global; 2 consumers (`service.py:131` boot_handoff resolves before txn / `handler.py:405` resolve_session_persona, both async). → make async + tenant-scoped; preserve None=reject / DEMO-fallback.
- **D6** — per-tenant must be added (existing surface global; tenant param `noqa`-unused). → table tenant_id + RLS + repo filter.
- **D7** — conventions confirmed (TenantScopedMixin / RLS 2-policy+FORCE `0019` / repo `session_repository` / admin CRUD `admin/tenants.py` / no real seed mechanism → 0023 data-migration + hardcoded fallback).

### go/no-go = **GO (plan REVISED + user re-confirmed)**
- >20% drift (FE-target + field-set + invocations-vs-definitions). Per the Day-0 rule, plan REVISED (not silently — §0 documents the drift; original framing preserved in MHist) + re-confirmed with user via AskUserQuestion → **backend registry + CRUD API this sprint; FE → 57.71**. Plan + checklist rewritten to the refined scope.

### Decisions
- catalog = AgentSpec registry (Group 9, fields per mockup); table `agent_catalog` (per-tenant, RLS); resolver = DB→DEFAULT_AGENTS→None (empty still works, no lazy-write); seed = 0023 data-migration + hardcoded fallback; CRUD = admin (`/admin/.../agents`, distinct from invocations STUB); default chat persona stays DEMO; budget/tools/modes STORED not enforced (§9); **FE → 57.71**.
- **Agent-delegated: yes** — Stage-1a backend (table + migration + repo + resolver rewire + seed); Stage-1b (admin CRUD API + integration). Parent independently re-verifies each stage (57.64+ discipline).
