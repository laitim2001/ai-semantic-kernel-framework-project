# Sprint 55.2 — V2 22/22 Closure: Production Mode Swap + Chat Handler Wiring — Checklist

**Plan**: [sprint-55-2-plan.md](sprint-55-2-plan.md)
**Branch**: `feature/sprint-55-2-v2-closure`
**Day count**: 5 (Day 0-4) | **Bottom-up est**: ~17 hr | **Calibrated commit**: ~7 hr (multiplier **0.40** per AD-Sprint-Plan-3; **first application** after 53.7=1.01 / 54.1=0.69 / 54.2=0.65 / 55.1=0.68 → 4-sprint mean 0.76 BELOW [0.85, 1.20] band → reduce 0.50 → 0.40)

> **格式遵守**：每 Day 同 55.1 結構（progress.md update + sanity + commit + verify CI）。每 task 3-6 sub-bullets（case / DoD / Verify command）。Per AD-Lint-2 (53.7) — 不寫 per-day calibrated hour targets；只寫 sprint-aggregate calibration verify in retro。

---

## Day 0 — Setup + Day-0 探勘 + Pre-flight Verify

### 0.1 Branch + plan + checklist commit
- [ ] **Verify on main + clean** — `git status --short` empty + HEAD `7ef94d30`
- [ ] **Create branch + push plan/checklist** — `git checkout -b feature/sprint-55-2-v2-closure`
- [ ] **Stage + commit plan + checklist + push branch** — commit msg `chore(docs, sprint-55-2): plan + checklist for V2 22/22 closure`

### 0.2 Day-0 探勘 — verify plan §Technical Spec assertions against actual repo state

Per AD-Plan-1 (53.7) + feedback_day0_must_grep_plan_assumptions.md — grep each plan claim, not memory.

- [ ] **Verify 4 deferred domain tools.py NO mode kwarg** — grep `def register_(patrol|correlation|rootcause|audit_domain)_tools` for `mode:` keyword (expect: missing)
- [ ] **Verify incident/tools.py reference pattern** — grep `_build_service_handlers|_serialize_incident|mode == "service"` (expect: present from 55.1)
- [ ] **Verify BusinessServiceFactory + 5 service builders** — `business_domain/_service_factory.py` `get_(incident|patrol|correlation|rootcause|audit)_service` all present
- [ ] **Verify settings.business_domain_mode field** — `core/config/__init__.py` line for `Literal["mock", "service"]`
- [ ] **Verify chat handler current DI structure** — grep `api/v1/chat/handler.py` for current `Depends(get_db)` / `Depends(get_current_tenant)` / tracer Depends factory; document gaps
- [ ] **Verify get_tracer Depends factory exists** — grep `def get_tracer` in `api/` or `infrastructure/observability/` (expect: present from 53.x or 49.4)
- [ ] **Verify 4 deferred domain service classes ready** — each `business_domain/{domain}/service.py` has at least one async method matching factory builder return type
- [ ] **Verify _register_all.py current threading pattern** — grep `register_all_business_tools` arg list to confirm whether mode/factory_provider already partially threaded
- [ ] **Catalogue D-findings in progress.md** — any drift documented as `🚨 Dn` per 55.1 D1-D11 pattern

### 0.3 Calibration multiplier pre-read
- [ ] **Read 55.1 retrospective Q2** — confirm ratio 0.68 + 4-sprint mean 0.76 + AD-Sprint-Plan-3 recommendation 0.50→0.40
- [ ] **Compute 55.2 bottom-up** — 17 hr × 0.40 = 6.8 hr ≈ 7 hr commit
- [ ] **Document predicted vs banked** — banked from 55.1 (~3.5 hr below committed); 0.40 reflects sustained pattern

### 0.4 Pre-flight verify (main green baseline)
- [ ] **pytest collect baseline** — expect `1395 collected` (= 1395 passed + 4 skipped from 55.1)
- [ ] **6 V2 lints via run_all.py** — `python scripts/lint/run_all.py` → 6/6 green
- [ ] **Backend full pytest baseline** — `python -m pytest` → 1395 passed / 4 skipped / 0 fail
- [ ] **mypy --strict baseline** — `mypy backend/src --strict` → 0 errors / 266 files
- [ ] **LLM SDK leak baseline** — grep `^(from |import )(openai|anthropic|agent_framework)` → 0

### 0.5 Day 0 progress.md
- [ ] **Create `docs/03-implementation/agent-harness-execution/phase-55/sprint-55-2/progress.md`** — Day 0 entry with探勘 findings + baseline + Day 1 plan
- [ ] **Commit + push Day 0** — commit msg `docs(sprint-55-2): Day 0 progress + 探勘 baseline`

---

## Day 1 — US-1 patrol + correlation tools.py Mode Swap

### 1.1 patrol/tools.py mode swap
- [ ] **Add imports** — `from collections.abc import Callable` + `from business_domain._service_factory import BusinessServiceFactory`
- [ ] **Add `_serialize_*` helper if PatrolService returns ORM/dataclass** — JSON-friendly dict; or skip if service returns dict already
- [ ] **Add `_build_service_handlers(factory_provider)`** — 4 handlers (check_servers / get_results / schedule / cancel); each `factory_provider().get_patrol_service().method(...)`
- [ ] **Modify `register_patrol_tools(... mode='mock', factory_provider=None)`** — mock branch unchanged; service branch raises ValueError if no factory_provider
- [ ] **Update Modification History** — file header docstring add Sprint 55.2 entry
- DoD: mypy --strict green; black + isort + flake8 green
- Verify: `python -m pytest backend/tests/unit/business_domain/test_patrol_tools.py -v`

### 1.2 correlation/tools.py mode swap
- [ ] **Add imports + factory_provider closure** — same pattern as 1.1
- [ ] **Add `_serialize_*` helper if needed**
- [ ] **Add `_build_service_handlers(factory_provider)`** — 3 handlers (analyze / find_root_cause / get_related)
- [ ] **Modify `register_correlation_tools(... mode='mock', factory_provider=None)`**
- [ ] **Update Modification History**
- DoD: mypy --strict green; lints green
- Verify: `python -m pytest backend/tests/unit/business_domain/test_correlation_tools.py -v`

### 1.3 6 unit tests (patrol 3 + correlation 3)
- [ ] **test_register_patrol_tools_mode_mock_uses_executor** — mode='mock' default behavior unchanged
- [ ] **test_register_patrol_tools_mode_service_requires_factory_provider** — ValueError without factory
- [ ] **test_register_patrol_tools_mode_service_handler_calls_service** — full path: factory → service → return value (use mock factory_provider returning fake service)
- [ ] **test_register_correlation_tools_mode_mock_uses_executor** — same pattern
- [ ] **test_register_correlation_tools_mode_service_requires_factory_provider** — same
- [ ] **test_register_correlation_tools_mode_service_handler_calls_service** — same
- DoD: 6 passed in < 1s

### 1.4 Day 1 sanity checks
- [ ] **mypy --strict** — 0 errors / 266+ files (new test files only)
- [ ] **black + isort + flake8** — all clean
- [ ] **6 V2 lints via run_all.py** — 6/6 green
- [ ] **Backend full pytest** — 1395 + 6 = 1401 passed / 4 skipped / 0 fail
- [ ] **LLM SDK leak in business_domain/** — 0 (still)

### 1.5 Day 1 commit + push + progress.md
- [ ] **Stage + commit Day 1 source + tests** — commit msg `feat(business-domain, sprint-55-2): patrol + correlation tools.py mode swap (US-1 part 1/2)`
- [ ] **Update progress.md** with Day 1 actuals + drift findings if any
- [ ] **Push to origin**

---

## Day 2 — US-1 rootcause + audit_domain tools.py Mode Swap

### 2.1 rootcause/tools.py mode swap
- [ ] **Add imports + factory_provider closure** — same pattern as Day 1
- [ ] **Add `_serialize_*` helper if needed**
- [ ] **Add `_build_service_handlers(factory_provider)`** — 3 handlers (diagnose / suggest_fix / apply_fix)
- [ ] **apply_fix HIGH-RISK behavior** — service handler returns `{"status": "approval_pending"}` sentinel (mirror mock_executor; HITL ALWAYS_ASK enforcement at Cat 9 layer)
- [ ] **Modify `register_rootcause_tools(... mode='mock', factory_provider=None)`**
- [ ] **Update Modification History**
- DoD: mypy --strict green; lints green
- Verify: `python -m pytest backend/tests/unit/business_domain/test_rootcause_tools.py -v`

### 2.2 audit_domain/tools.py mode swap
- [ ] **Add imports + factory_provider closure** — same pattern
- [ ] **Add `_serialize_*` helper if needed**
- [ ] **Add `_build_service_handlers(factory_provider)`** — 3 handlers (query_logs / generate_report / flag_anomaly)
- [ ] **Modify `register_audit_domain_tools(... mode='mock', factory_provider=None)`** — note: function name might be `register_audit_tools` (Day 0 verify)
- [ ] **Update Modification History**
- DoD: mypy --strict green; lints green
- Verify: `python -m pytest backend/tests/unit/business_domain/test_audit_domain_tools.py -v`

### 2.3 6 unit tests (rootcause 3 + audit_domain 3)
- [ ] **test_register_rootcause_tools_mode_mock_uses_executor**
- [ ] **test_register_rootcause_tools_mode_service_requires_factory_provider**
- [ ] **test_register_rootcause_tools_mode_service_apply_fix_returns_approval_pending** — verify HIGH-RISK sentinel
- [ ] **test_register_audit_domain_tools_mode_mock_uses_executor**
- [ ] **test_register_audit_domain_tools_mode_service_requires_factory_provider**
- [ ] **test_register_audit_domain_tools_mode_service_handler_calls_service**
- DoD: 6 passed in < 1s

### 2.4 Day 2 sanity checks
- [ ] **mypy --strict** — 0 errors
- [ ] **black + isort + flake8** — clean
- [ ] **6 V2 lints** — 6/6 green
- [ ] **Backend full pytest** — 1401 + 6 = 1407 passed
- [ ] **51.0 + 51.1 + 55.1 baseline regression** — `pytest tests/unit/business_domain/` no regression
- [ ] **LLM SDK leak** — 0

### 2.5 AD-BusinessDomainPartialSwap-1 closure smoke test
- [ ] **All 5 register_*_tools accept mode kwarg** — `grep -E "def register_.*_tools.*mode" business_domain/` returns 5 matches
- [ ] **All 5 raise ValueError on mode='service' without factory** — explicit unit test or smoke check
- [ ] **Document closure** — progress.md note: "AD-BusinessDomainPartialSwap-1 5/5 domains uniformly mode-aware"

### 2.6 Day 2 commit + push + progress.md
- [ ] **Stage + commit Day 2** — commit msg `feat(business-domain, sprint-55-2): rootcause + audit_domain tools.py mode swap (US-1 part 2/2; closes AD-BusinessDomainPartialSwap-1)`
- [ ] **Update progress.md** with Day 2 actuals + AD closure note
- [ ] **Push to origin**

---

## Day 3 — US-2 + US-3 (_register_all Uniform Threading + Chat Handler Wiring)

### 3.1 _register_all.py uniform mode/factory_provider threading
- [ ] **Modify `register_all_business_tools(... mode='mock', factory_provider=None)`** — single signature change; thread kwargs to all 5 register_*_tools
- [ ] **Early ValueError if mode='service' AND factory_provider is None** — fail fast at register_all layer (caller error)
- [ ] **Update file header Modification History**
- DoD: mypy strict green; lints green
- Verify: `python -m pytest backend/tests/unit/business_domain/test_register_all.py -v`

### 3.2 make_default_executor uniform mode threading
- [ ] **Verify `make_default_executor(... mode=None, factory_provider=None)`** signature already from 55.1; confirm mode=None reads `settings.business_domain_mode`
- [ ] **Confirm passing factory_provider through to register_all** — should be straight-through
- DoD: existing 55.1 test `test_make_default_executor_reads_settings` still passes

### 3.3 2 unit tests (register_all + make_default_executor)
- [ ] **test_register_all_business_tools_mode_service_threads_factory_to_5_domains** — verify all 5 domain handlers built via factory_provider (not mock_executor)
- [ ] **test_register_all_business_tools_mode_service_no_factory_raises** — ValueError early
- DoD: 2 passed

### 3.4 Chat handler production wiring (api/v1/chat/handler.py)
- [ ] **Identify chat endpoint function** — `grep -n "def.*chat" api/v1/chat/handler.py` (or router/endpoint file)
- [ ] **Verify Depends(get_db, get_current_tenant) already present** — from 53.6 production HITL wiring; if missing, add
- [ ] **Add `tracer: Tracer = Depends(get_tracer)`** — if not already; thread to factory
- [ ] **Build `factory = BusinessServiceFactory(db=db, tenant_id=tenant_id, tracer=tracer)`** in endpoint
- [ ] **Modify `make_default_executor` call** — pass `mode=settings.business_domain_mode, factory_provider=lambda: factory`
- [ ] **Update file header Modification History**
- DoD: mypy strict green; lints green; existing 53.6 production HITL tests still pass

### 3.5 4 chat handler integration tests
- [ ] **test_chat_business_wiring_mode_mock_unchanged** — mode='mock' (default); 5 domain calls work via mock_executor
- [ ] **test_chat_business_wiring_mode_service_5_domains** — mode='service'; verify each domain reaches its service class via factory
- [ ] **test_chat_business_wiring_multi_tenant_isolation** — tenant A + tenant B concurrent; each gets own factory; no leakage
- [ ] **test_chat_business_wiring_tracer_span_emitted** — recording_tracer captures `business_service.*.method` span when service-mode call happens
- DoD: 4 passed; integration suite + autouse reset_service_factory fixture per testing.md §Module-level Singleton Reset Pattern

### 3.6 Day 3 sanity checks
- [ ] **mypy --strict** — 0 errors
- [ ] **6 V2 lints** — 6/6 green (especially `check_cross_category_import` — chat handler import BusinessServiceFactory is legal cross-layer)
- [ ] **Backend full pytest** — 1407 + 6 = 1413 passed (1 over plan estimate of 1410; OK if drift catalogued)
- [ ] **53.6 production HITL regression** — no regression (5 governance integration tests still green)
- [ ] **LLM SDK leak** — 0

### 3.7 Day 3 commit + push + progress.md
- [ ] **Stage + commit Day 3** — commit msg `feat(business-domain, api, sprint-55-2): uniform mode threading + chat handler production wiring (US-2 + US-3)`
- [ ] **Update progress.md** with Day 3 actuals + drift findings
- [ ] **Push to origin**

---

## Day 4 — US-5 V2 22/22 Closure Ceremony + Retro + Closeout

### 4.1 Cat 12 obs verification
- [ ] **Audit grep service-method spans** — `grep "async with business_service_span" business_domain/` count ≥ 9 (5 incident + ≥ 1 per 4 read-only domain from 55.1)
- [ ] **Verify no new service methods missing obs span** — if Day 1-3 added any service methods, ensure wrapped
- [ ] **Verify metric labels include tenant_id** — span attributes contain tenant_id

### 4.2 Multi-tenant integration test cross-domain
- [ ] **test_v2_closure_5_domains_multi_tenant_via_chat** — 2 tenants × 5 domain tools = 10 calls; each isolated
- [ ] **test_v2_closure_audit_chain_after_5_domain_ops** — audit log integrity preserved across all 5 domains

### 4.3 V2 22/22 main flow e2e test
- [ ] **test_v2_22_22_main_flow_chat_to_5_domains_service_mode** — chat endpoint → LLM emits 5 tool_calls → all 5 service-backed → responses serialize → SSE events
- [ ] **test_v2_22_22_main_flow_mode_mock_regression** — same but mode='mock'; legacy path still works

### 4.4 Final pytest + lints + LLM SDK leak final verify
- [ ] **Backend full pytest** — ≥ 1410 (target: ≥ 1395 + 15 new = 1410; allow over)
- [ ] **mypy --strict** — 0 errors
- [ ] **6 V2 lints** — 6/6 green
- [ ] **LLM SDK leak** — 0
- [ ] **Alembic upgrade head + downgrade base** — 0011-0012 cycle still green

### 4.5 retrospective.md (6 必答)
- [ ] **Q1** Sprint goal achievement — V2 22/22 closure achieved? AD-BusinessDomainPartialSwap-1 closed?
- [ ] **Q2** Calibration verify — `actual_total_hr / 7` → ratio (期望 [0.85, 1.20]); 5-sprint window mean recalc; if < 0.85 → AD-Sprint-Plan-4 (0.40→0.30); if ∈ band → 鎖 0.40 stable for Phase 56+
- [ ] **Q3** D-findings drift catalogue — Day 0-3 drift summary
- [ ] **Q4** V2 紀律 9 項 review — confirm all 9 still green at V2 closure
- [ ] **Q5** V2 closure summary — Phase 49-55 grand summary (22 sprints + 2 carryover bundles + 11+1 範疇 Level 4 + 5 business domains production-capable + key milestones)
- [ ] **Q6** Phase 56+ readiness — SaaS Stage 1 啟動條件清單 (multi-tenant DB / billing / SLA / DR — 已知 deferred to Phase 56-58)

### 4.6 Open PR + CI green + solo-dev merge
- [ ] **Push final commit + open PR** — PR title `feat(business-domain, api, sprint-55-2): V2 22/22 closure — production mode swap + chat handler wiring`
- [ ] **Wait CI green** — 5 active checks (Backend CI / V2 Lint / E2E Backend / E2E Summary / Frontend E2E chromium); paths-filter workaround if needed
- [ ] **Solo-dev normal merge to main** — squash merge

### 4.7 Closeout PR (V2 22/22 ceremony)
- [ ] **Branch `chore/sprint-55-2-closeout`**
- [ ] **Update SITUATION-V2-SESSION-START.md** — §9 milestones row + Last Updated + Update history (V2 22/22 (100%); Phase 55 完成 2/2; main progress closed)
- [ ] **Update CLAUDE.md** — V2 progress 21/22 → 22/22 (100%); main HEAD; status block "V2 重構完成"
- [ ] **Touch backend-ci.yml header + playwright-e2e.yml header** — paths-filter workarounds for docs-only closeout PR
- [ ] **Open closeout PR + merge** — solo-dev normal merge

### 4.8 Memory snapshot + V2 closure summary + final push
- [ ] **Create `memory/project_phase55_2_v2_closure.md`** — Sprint 55.2 summary
- [ ] **Create `memory/project_v2_closure_summary.md`** — Phase 49-55 grand summary (22 sprints + 11+1 範疇 全 Level 4 + 5 business domain production + AD closures + key learnings)
- [ ] **Update `memory/MEMORY.md`** index — entries for both new memory files
- [ ] **Verify main HEAD + working tree clean + delete merged branches** — `git status --short` empty; `gh pr merge --delete-branch` for both PRs
- [ ] **Final V2 22/22 (100%) milestone push** — all branches synced; SITUATION + CLAUDE + memory updated
