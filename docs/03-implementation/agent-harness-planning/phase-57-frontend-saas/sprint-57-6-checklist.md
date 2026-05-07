# Sprint 57.6 — Checklist (Reality Gap Fix Sprint + merged Phase 57.7 doc updates)

> [Sprint Plan](./sprint-57-6-plan.md)

**Sprint Goal**: Close Sprint 57.5 V2 Reality Check top 5 RED findings (R1+R2+R3+R4-partial+R5) + merged Phase 57.7 doc updates per Decision 4 (b);primary deliverable = real boot end-to-end + DB persist verified + AP-4 防再生 lint + E2E real-LLM smoke gate + 5 doc updates aligned (02.md / 16.md / SITUATION-V2 dual scoring / CLAUDE.md / sprint-workflow.md calibration matrix);NO new feature pages;closes 10 NEW AD-Reality-N + AD-Sprint-Plan-7。

---

## Day 0 — Setup + Branch + Pre-flight + 三-prong + Calibration

### 0.1 Branch + plan + checklist commit
- [ ] **Branch from main `426fce7b`**
  - DoD:`git checkout -b feature/sprint-57-6-reality-gap-fix`
  - Verify:`git branch --show-current` → `feature/sprint-57-6-reality-gap-fix`
- [ ] **Commit plan + checklist**
  - DoD:plan + checklist staged + committed with conventional message `docs(plan, sprint-57-6): Reality Gap Fix Sprint + merged Phase 57.7 doc updates per Decision 4 (b)`
  - Verify:`git log --oneline -1` shows commit;`git status --short` clean

### 0.2 Day-0 三-prong 探勘 v3
- [ ] **Prong 1 Path Verify**
  - `scripts/dev.py` exists(Glob)
  - `backend/src/api/main.py` exists
  - `backend/src/main.py` (D-12 stub status — exists OR not?)
  - `frontend/vite.config.ts` exists
  - `backend/requirements.txt` exists
  - `backend/src/api/v1/chat.py` exists
  - `scripts/lint/run_all.py` orchestrator + 8 existing lint scripts exist (check_ap1.py / check_promptbuilder.py / check_sole_mutator.py / check_neutrality.py / check_rls_policies.py / check_cross_category.py / check_no_orphan_code.py / check_observability_spans.py)
  - `.github/workflows/` directory exists
  - `backend/src/infrastructure/db/models/` ORM directory exists
  - Verify:Glob results + 列出 unexpected drift if any
- [ ] **Prong 2 Content Verify**
  - `scripts/dev.py` 真實 references which entry path (grep `uvicorn.*main:app` — confirm `main:app` vs `api.main:app`)
  - `vite.config.ts` 真實 proxy target (grep `target.*http` — confirm `8000` vs `8001`)
  - `backend/src/api/main.py` 已有 lifespan hook 嗎 (grep `@asynccontextmanager` + `lifespan`)
  - `backend/src/api/v1/chat.py` 既有 observer hooks structure (grep `record_llm_call|append|create_session|tool_call_repo`)
  - `backend/requirements.txt` 含 python-dotenv (grep `python-dotenv` OR `dotenv`)
  - 17.md ABCs status:ToolCallRepository / AuditAppendOnlyService / CostLedgerService / SessionRepository (grep file-system check + signature verify)
  - 8 existing lint scripts 全 in run_all.py orchestrator (grep run_all.py for `check_ap1|check_promptbuilder|...`)
- [ ] **Prong 3 Schema Verify**
  - `sessions` 表 schema 確認 (grep `class Session\(` in `backend/src/infrastructure/db/models/`)
  - `audit_log` 表 schema 確認 (grep `class AuditLog\(`)
  - `cost_ledger` 表 schema 確認 — column `input_tokens INT` + `output_tokens INT` + `cached_tokens INT` per Sprint 57.2 AD-Cost-Ledger-Token-Split (grep)
  - `tool_calls` 表 schema 確認 — column `tool_name VARCHAR` + `status` + `duration_ms` + `result_preview` (grep)
  - 確認 4 表 schema 全 match observer wiring needs;若 schema 缺 column → log AD + plan §Risks revision per AD-Plan-1 audit-trail

### 0.3 Calibration multiplier pre-read
- [ ] **`reality-gap-fix` 0.50 NEW class 1st application**
  - Bottom-up est ~22-26 hr (5 USs reality fix) + ~3 hr (5 doc updates merged) = ~25-29 hr
  - Calibrated commit ~13-15 hr (multiplier 0.50)
  - Day 4 retro Q2 verify:若 ratio in band [0.85, 1.20] → 0.50 baseline validated;若 < 0.85 → AD-Sprint-Plan-8 propose lift toward 0.65 (fix path 比預期更直接);若 > 1.20 → AD-Sprint-Plan-8 propose lower (complex fix path)
  - 1-data-point baseline; pending 2-3 sprint window evidence before AD-Sprint-Plan-7 promotion + this `reality-gap-fix` baseline promotion

### 0.4 Pre-flight verify(main green baseline)
- [ ] **Backend baselines (pre-sprint snapshot)**
  - `python -m pytest backend/tests/ -q --tb=no` → 1598 collected / 0 failures (57.5 baseline unchanged)
  - `python -m mypy backend/src --strict` → 0 errors / 295 source files
  - `python scripts/lint/run_all.py` → 8 V2 lints 8/8 green
  - `grep -rn "import openai\|import anthropic" backend/src/agent_harness/` → 0 (LLM SDK leak)
  - Verify:All 4 baselines documented in progress.md ✅ (1598 / 0/295 / 8/8 / 0)
- [ ] **Frontend baselines (pre-sprint snapshot)**
  - `cd frontend && npm run lint` → clean
  - `cd frontend && npm run build` → success / 75 modules / 209.11 kB
  - `cd frontend && npm run test` → 35 unit tests pass (57.5 baseline unchanged)
  - Playwright e2e 23 tests baseline (57.5 closeout)
  - Verify:All 4 baselines documented in progress.md ✅

### 0.5 Day 0 progress.md commit + push
- [ ] **Catalogue D-findings + decide Day 1 scope**
  - 列出 Day 0 D-findings (predicted 0-5 since Sprint 57.5 已 surface most)
  - Document 三-prong attempt time + findings count
  - Verify:`docs/03-implementation/agent-harness-execution/phase-57/sprint-57-6/progress.md` exists with Day 0 section ✅
- [ ] **Day 0 commit + push**
  - DoD:progress.md staged + committed `docs(progress, sprint-57-6): Day 0 三-prong + pre-flight baseline + calibration pre-read`
  - Verify:`git log --oneline -1` shows commit;remote up-to-date

---

## Day 1 — US-1 Entry-Point Drift + US-2 dotenv Lifespan

### 1.1 US-1 Entry-Point + Port Config Drift Unification (R1)
- [ ] **`scripts/dev.py` entry path fix**
  - Modify uvicorn invocation:`main:app` → `api.main:app` (or per Day 0 探勘 finding)
  - Set `cwd=backend/src` if needed for module resolution
  - Verify:grep result confirms new import path
- [ ] **`frontend/vite.config.ts` proxy port fix**
  - `server.proxy['/api'].target = 'http://localhost:8000'` (NOT 8001)
  - Verify:grep result confirms 8000 target
- [ ] **`backend/src/main.py` stub investigation + decision**
  - 若 exists + dead → remove + commit message references AD-Reality-1
  - 若 exists + still used → grep + refactor OR add deprecation comment
  - 若 not exists → no action (Day 0 探勘 already verified)
- [ ] **Manual verify`python scripts/dev.py start` boots all services**
  - DoD:Backend on 8000 + Frontend on 3005 + PG + Redis healthy
  - `curl http://localhost:8000/health` → 200
  - `curl http://localhost:3005/api/health` (via vite proxy) → 200 (proves frontend↔backend integration unbroken)
  - Capture log to progress.md
- [ ] **Sprint 57.5 D-12 + D-21 + D-27 closed**
  - Verify finding-by-finding closure cross-reference

### 1.2 US-2 uvicorn Lifespan dotenv Autoload (R2)
- [ ] **`backend/src/api/main.py` lifespan hook**
  - Add `from contextlib import asynccontextmanager` + `from dotenv import load_dotenv`
  - Define `@asynccontextmanager async def lifespan(app: FastAPI):` calling `load_dotenv()` then `yield`
  - Wire `app = FastAPI(lifespan=lifespan)` parameter
  - Update file header MHist with `2026-05-09: Sprint 57.6 — add lifespan dotenv autoload (closes AD-Reality-2 + Sprint 57.5 D-20)`
- [ ] **`backend/requirements.txt` python-dotenv verify or add**
  - Per Day 0 Prong 2 finding:若 already exists → no change;若 missing → add `python-dotenv>=1.0`
- [ ] **`backend/tests/unit/api/test_main_lifespan.py` NEW unit test**
  - 1 test: `test_lifespan_loads_dotenv` — patches `load_dotenv` + asserts called on FastAPI startup
  - File header per file-header-convention.md
- [ ] **Manual verify real_llm mode 不再 503**
  - With real `.env` set with `AZURE_OPENAI_API_KEY` etc.
  - `python scripts/dev.py start`
  - `curl POST /api/v1/chat` real_llm mode → SSE LLMResponded captured (NOT 503)
  - Capture SSE log to progress.md
- [ ] **Sprint 57.5 D-20 closed**

### 1.3 Day 1 commit + push + progress.md
- [ ] **Commit US-1 + US-2 evidence**
  - Stage scripts/dev.py + vite.config.ts + backend/src/api/main.py + backend/src/main.py (if removed/modified) + backend/requirements.txt (if changed) + test_main_lifespan.py + progress.md
  - Commit:`feat(platform, sprint-57-6): Day 1 US-1 entry-point drift fix + US-2 dotenv lifespan autoload (closes AD-Reality-1 + AD-Reality-2)`
  - Verify:`git log main..HEAD --oneline` shows new commit;remote up-to-date

---

## Day 2 — US-3 Chat Router Observer Wiring (4-stream DB Persist)

### 2.1 US-3 chat router observer hooks (R3)
- [ ] **`api/v1/chat.py` observer wiring**
  - On LoopStarted event: SessionRepository.create_session() — INSERT sessions row
  - On LoopCompleted event: AuditAppendOnlyService.append(operation="conversation_completed", ...) — INSERT audit_log chain entry
  - On LLMResponded event: CostLedgerService.record_llm_call(provider/model/input_tokens/output_tokens/cached_tokens) — INSERT 2-entry cost_ledger split per AD-Cost-Ledger-Token-Split
  - On ToolCallExecuted event: ToolCallRepository.create() + CostLedgerService.record_tool_call() — INSERT tool_calls + cost_ledger entries
  - On GuardrailTriggered event: AuditAppendOnlyService.append(operation="guardrail_triggered", ...) — INSERT audit_log
  - On VerificationPassed/Failed events: AuditAppendOnlyService.append(operation="verification_completed", ...) — INSERT audit_log
  - Best-effort failure pattern: try/except per observer to prevent observer errors from breaking SSE stream
  - Update file header MHist with `2026-05-10: Sprint 57.6 — wire 4-stream DB persist observer hooks (closes AD-Reality-3 + Sprint 57.5 D-16/17/18)`

### 2.2 US-3 unit tests (18+ new tests)
- [ ] **`backend/tests/unit/api/v1/test_chat_observer_hooks.py` NEW test file**
  - 5 tests for LoopStarted observer (sessions persist + tenant_id propagation)
  - 5 tests for LLMResponded observer (cost_ledger 2-entry split per token type)
  - 4 tests for ToolCallExecuted observer (tool_calls + cost_ledger per-call entry)
  - 2 tests for GuardrailTriggered observer (audit_log chain entry)
  - 2 tests for VerificationPassed/Failed observers (audit_log chain entry)
  - All tests use mock repositories + assert call counts
  - File header per file-header-convention.md

### 2.3 US-3 integration test
- [ ] **`backend/tests/integration/test_chat_db_persist_e2e.py` NEW integration test**
  - 1 test: `test_chat_session_persists_4_streams_e2e`
  - Setup: real PG + Redis + mock Azure OpenAI (use MockChatClient OR real_llm with cost guard)
  - Action: POST /api/v1/chat with simple message
  - Assert: `sessions` ≥ 1 row + `audit_log` ≥ 3 rows (started + LLM + completed) + `cost_ledger` ≥ 2 rows (LLM input + output) + `tool_calls` 0 (no tool calls in this simple chat)

### 2.4 Manual verify DB persist end-to-end
- [ ] **`python scripts/dev.py start` then chat then SQL count**
  - DoD:After 1 chat session, `psql -c "SELECT count(*) FROM sessions"` ≥ 1, `psql -c "SELECT count(*) FROM audit_log"` ≥ 3, `psql -c "SELECT count(*) FROM cost_ledger"` ≥ 2, `psql -c "SELECT count(*) FROM tool_calls"` ≥ 0
  - Capture SQL output to progress.md
- [ ] **Sprint 57.5 D-16 + D-17 + D-18 closed**

### 2.5 Day 2 commit + push + progress.md
- [ ] **Commit US-3 evidence**
  - Stage chat.py + test_chat_observer_hooks.py + test_chat_db_persist_e2e.py + progress.md
  - Commit:`feat(platform, sprint-57-6): Day 2 US-3 chat router 4-stream DB persist observer wiring (closes AD-Reality-3)`
  - Verify:`git log main..HEAD --oneline` shows new commit

---

## Day 3 — US-4 16.md Ship Timeline + US-5 AP-4 Lint + E2E Real-LLM Workflow

### 3.1 US-4 16.md V2 Ship Timeline section (R4-partial)
- [ ] **`16-frontend-design.md` add "V2 Ship Timeline" section**
  - 4 已 ship pages list (cost-dashboard / sla-dashboard / tenant-settings / admin-tenants with sprint reference)
  - Sprint 57.7-57.9 priority 3 (chat-v2 / governance / verification — ~10-12 hr each)
  - Sprint 57.10-57.13+ deferred 5 (agents / workflows / incidents / memory / audit / tools / admin / dashboard / devui — ~5-7 sprints)
  - Explicit "NOT V3 defer" statement per Decision 3 (a)
  - File header MHist update with `2026-05-10: Sprint 57.6 — add V2 Ship Timeline section per Decision 3 (a) (closes AD-Reality-4-partial + AD-Reality-7)`
- [ ] **Optional update Section "Per-Sprint接手時序" table**
  - Allocate Phase 57.x sprint slots for 8 待 ship pages
  - 若 update done → reference in MHist;若 skip → note in progress.md as deferred-to-Phase-57.7-Q5

### 3.2 US-5 NEW V2 lint check_ap4_frontend_placeholder.py (R5 part 1)
- [ ] **`scripts/lint/check_ap4_frontend_placeholder.py` NEW script**
  - Implement per plan §Technical Specifications US-5 spec
  - Forbidden text patterns: 6 regex (Coming in Phase / skeleton / placeholder / TODO / FIXME / land in subsequent sprints / will be added later / Not implemented / WIP)
  - Skip JSX `{/* ... */}` block comments
  - Exit codes: 0 clean / 1 findings / 2 directory missing
  - File header per file-header-convention.md
  - 0 unit tests this sprint (lint script self-tests via run_all.py orchestrator on existing frontend/src/pages/)

### 3.3 US-5 wire 9th V2 lint to run_all.py
- [ ] **`scripts/lint/run_all.py` orchestrator add 9th lint**
  - Add entry for check_ap4_frontend_placeholder.py
  - Wrapper invokes new lint with appropriate args
  - Exit aggregator reports 9 lints status
- [ ] **Manual verify lint orchestrator**
  - `python scripts/lint/run_all.py` → 9 lints orchestrated
  - 預期 既有 chat-v2 / governance / verification placeholder text → lint 報 N findings
  - 若 N > 0 → log Day 3 finding (this is expected per Sprint 57.5 D-23+24+25;not regression)
  - 若 user wants lint green this sprint → 加 ignore comment到 already-known placeholder pages OR exclude these 3 pages from lint scope (TBD per Day 3 mid-day decision)

### 3.4 US-5 NEW E2E real-LLM smoke workflow (R5 part 2)
- [ ] **`.github/workflows/e2e-real-llm-smoke.yml` NEW workflow**
  - Triggers: `schedule: cron '0 4 * * *'` (initially commented out per AD-CI-6 Phase 58 production launch dependency) + `workflow_dispatch: {}` (always available)
  - Services: postgres:16 + redis:7 + python:3.11
  - Steps: install deps + alembic upgrade + seed default tenant + start backend + real-LLM smoke chat + verify DB row delta
  - Cost guard: `max_tokens: 100`
  - Required-check status: NOT add to branch protection 5 active checks (informational only)
  - File header per `.github/workflows/` conventions

### 3.5 Day 3 commit + push + progress.md
- [ ] **Commit US-4 + US-5 evidence**
  - Stage 16-frontend-design.md + check_ap4_frontend_placeholder.py + run_all.py + e2e-real-llm-smoke.yml + progress.md
  - Commit:`feat(platform, sprint-57-6): Day 3 US-4 16.md ship timeline + US-5 AP-4 lint + E2E real-LLM workflow (closes AD-Reality-4-partial/7 + AD-Reality-5)`
  - Verify:`git log main..HEAD --oneline` shows new commit

---

## Day 4 — Closeout (Phase 57.7 USs Merged) + Retro + PR

### 4.1 Closeout doc updates (Phase 57.7 USs merged per Decision 4 (b))
- [ ] **AD-Reality-6: 02-architecture-design.md flat-layer drift fold-in**
  - Update §Architecture Diagram showing `platform_layer/{governance,identity,observability,middleware,workers,billing,tenant}/` nested-layer reality
  - Add §Naming Drift Note 2026-05-10 explaining why nested vs paper flat-layer
  - File header MHist update
- [ ] **AD-Reality-8: SITUATION-V2 §9 dual scoring format adoption**
  - SITUATION-V2 §9 milestones row table header note "every future sprint entry MUST include code-level + runtime-level dual scoring at end of entry summary"
  - Sprint 57.6 NEW entry inserted above 57.5 with full 5 USs closure summary + dual scoring (code-level ★★★★ ~88% post-fix / runtime-level ★★★ ~70% post-fix — TBD measure Day 4)
  - §11 Last Updated header sync (Previous chain to 57.5)
- [ ] **AD-Reality-9: CLAUDE.md sync**
  - Latest Sprint (57.5 → 57.6 with 5 USs + 10 AD-Reality closure)
  - main HEAD (`426fce7b` → Sprint 57.6 merged commit hash)
  - Last Updated (with Previous chain to 57.5)
  - Current Phase (added Sprint 57.6 reality gap fix closure)
  - main HEAD bottom field
- [ ] **AD-Reality-10: sprint-workflow.md Calibration matrix update**
  - §Workload Calibration matrix table add 2 new rows:
    - `reality-gap-fix` 0.50 multiplier (1-data-point baseline; this Sprint 57.6 evidence)
    - `reality-check` 0.85 multiplier (2-data-point baseline; Sprint 57.5 + 57.6 evidence — promote AD-Sprint-Plan-7 if 2-data-point sufficient)
  - File header MHist update

### 4.2 Retrospective.md
- [ ] **Create `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-6/retrospective.md`**
  - Q1 What went well — reality fix path 哪些 worked smoothly + 5 doc updates 哪些 doc 真實 align easily
  - Q2 What didn't go well + calibration ratio (`reality-gap-fix` 0.50 1st application;若 ratio in band → 0.50 baseline validated;若 outside → AD-Sprint-Plan-8 adjust)
  - Q3 What we learned — reality fix vs reality check 對比 learnings
  - Q4 Audit Debt deferred — top N findings carry-forward to Phase 57.7+
  - Q5 Next steps + Phase 57.7+ direction proposal (rolling planning;不寫具體未來 sprint 任務;Phase 57.7 候選 chat-v2 real ship per Decision 3 (a) priority)
  - Q6 Solo-dev policy validation
  - Verify:`wc -l retrospective.md` ≥ 250 lines

### 4.3 Memory snapshot + MEMORY.md index
- [ ] **Create `memory/project_phase57_6_reality_gap_fix.md`**
  - Same format as `project_phase57_5_v2_reality_check.md` (≤ 80 lines per memory budget)
  - Frontmatter complete
- [ ] **Update MEMORY.md index** add 1 line entry

### 4.4 Open PR + CI green + solo-dev merge
- [ ] **Push branch + open PR**
  - Push:`git push -u origin feature/sprint-57-6-reality-gap-fix`
  - PR title:`Sprint 57.6 — Reality Gap Fix Sprint (close R1+R2+R3+R4-partial+R5 + merged Phase 57.7 doc updates)`
  - PR body:Sprint goal + 5 USs + 10 AD-Reality closure + acceptance + Phase 57.7+ TBD per user decision
  - Verify:5 active CI checks green;solo-dev policy review_count=0 satisfied
- [ ] **Squash merge to main**
  - DoD:GitHub UI squash + merge;branch deleted post-merge
  - Verify:main HEAD updated

### 4.5 Closeout PR
- [ ] **Closeout branch + PR**
  - Branch:`chore/sprint-57-6-closeout`
  - Updates: 02.md + 16.md + SITUATION-V2 + CLAUDE.md + sprint-workflow.md (already committed in Day 4.1; closeout PR has no further updates per Decision 4 (b) — Phase 57.7 USs merged into Sprint 57.6 main PR)
  - **若 4.1 已 merge 進 main PR → skip 4.5 closeout PR**(per Decision 4 (b) merged closeout strategy)
  - **OR 若 4.1 留作 closeout PR**(separate from main PR for cleaner audit-trail)→ closeout branch + PR commit message:`docs(closeout, sprint-57-6): Phase 57.7 doc updates merged (02.md + 16.md ship timeline + SITUATION-V2 dual scoring + CLAUDE.md + sprint-workflow.md calibration matrix)`
  - Verify:Day 0 探勘 decision on whether merge or split closeout PR (logged in progress.md)

### 4.6 User decision interaction (Phase 57.7+ direction)
- [ ] **Present Sprint 57.6 closure summary + Phase 57.7+ direction question**
  - Direction options (per Decision 3 (a) priority hierarchy):
    - (a) Phase 57.7 chat-v2 real ship (~10-12 hr;backend ship complete;replace 50.2 skeleton with real chat UX wired to chat router)
    - (b) Phase 57.7 governance real ship (~10-12 hr;backend ship complete via 53.5;replace placeholder with real approvals UX)
    - (c) Phase 57.7 verification real ship (~10-12 hr;backend ship complete via 54.1;replace placeholder with real verification panel)
    - (d) Pivot to other Phase 57.x candidate (Onboarding self-serve / Audit log frontend / Compliance partial GDPR / DR + WAL streaming / SaaS Stage 2 / etc.)
  - Per rolling planning 紀律:不預寫 Phase 57.7 plan;等 user 明確選定 scope 才起草

---

## 重要備註

- **此 sprint 寫 source code** — Day 1 + Day 2 + Day 3 全寫 production code (US-1 entry path / US-2 lifespan dotenv / US-3 4-stream observer wiring / US-5 lint script + workflow file);US-4 純 doc;Day 4 closeout 純 doc
- **此 sprint 不算入 Phase 57+ Frontend SaaS 4/N counter** — 它是 reality gap fix 性質 verification gate;Frontend SaaS 進度仍 3/N 不變
- **若 Day 0 / Day 1 出現 critical service boot still broken after fix → 直接 sprint pivot 為 partial-fix mode** (US-3 deferred to next sprint;US-4 + US-5 仍 進行 + 將 partial-fix state catalogue 為 Phase 57.7+ MUST-FIX)
- **誠實 over completeness** — Day 4 retrospective 不必 sugar-coat;若 fix 比預期難或 surface 新 D-findings 是 sprint 主要 deliverable + V2 紀律 #2 主流量驗證真實 enforcement 的價值
- **不殺 node 流程** — 啟動 backend uvicorn / frontend vite 後保留 running(per CLAUDE.md global rule;node 流程同時跑 claude code)
- **Sprint 57.7 Re-baseline merged into Sprint 57.6 closeout per Decision 4 (b)** — Phase 57.7 將直接是 feature work resumption (chat-v2 real ship OR other candidate)
