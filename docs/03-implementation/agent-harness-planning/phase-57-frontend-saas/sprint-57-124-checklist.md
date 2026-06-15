# Sprint 57.124 — Checklist (HITL gate consolidation + 2 chrome/governance Potemkin fixes — 3-track bundle. **Item 1**: remove the stale `PermissionChecker` shadow gate from the executor (it conflicts with + overrides the 57.122 per-tenant `HITLPolicy`) + compensate with a `resolve_tool_risk` destructive HIGH-floor so destructive tools escalate-then-run via `_cat9` [Fix B]. **Item 2**: NotificationsPanel DEMO banner + derive the badge from a shared fixture, drop `FIXTURE_UNREAD_COUNT` [Fix A]. **Item 3**: admin HITL-policy PUT rejects `auto >= require` with a 422. CHANGE-091 + design note 36 [Track 1]; NO migration/wire/codegen)

[Plan](./sprint-57-124-plan.md)

---

## Day 0 — Plan-vs-Repo Verify (三-prong; the central check = D-escalate-coverage, Item-1 safety) + Branch

### 0.1 Three-prong Day-0 verify (against `main` HEAD `6a691621`) — catalogue in progress.md
- [x] **Prong 1 — path verify** ✅ all anchors present; `CHANGE-091`/design-note `36` free
- [x] **Prong 2 — content verify** (drift findings → progress.md):
  - [x] **D-escalate-coverage** ✅ GREEN: all 8 ALWAYS_ASK/ASK_ONCE tools risk ≥ MEDIUM → all escalate via risk threshold under default policy; NO tool loses escalation; destructive floor protects permissive tenants; **no `CHAT_HITL_ESCALATE_TOOLS` change needed**. Coverage table in progress.md
  - [x] **D-resolve-risk-callers** ✅: `loop.py:548` keyword-args; optional `destructive` backward-compatible
  - [x] **D-executor-other-callers** ✅: subagent children run own `_cat9` (B4/57.110); `echo_tool.py:75` self-test; no production sole-gate caller
  - [x] **D-notif-fixture-source** ✅: `NOTIFS` module const (extractable); static derived badge = acceptable DEMO
  - [x] **D-backendgapbanner-fidelity** ✅: existing tokens, no new literal → mockup 51 holds
  - [x] **D-explicit-approval-orphan** ✅: leave field + AD-note `AD-ExecutionContext-ExplicitApproval-Tidy`
- [x] **Prong 3 — schema** ✅ N/A: NO new table/migration (Item 3 = Pydantic validator only)
- [x] **D-baselines** ✅: pytest 2696+5skip · wire 24 · Vitest 892 · mockup 51 · mypy 0/371 · run_all 10/10 (trusted from 57.123 merge)
- [x] **Catalog drift** ✅: progress.md Day-0 table written
- [x] **Go/no-go** ✅: GO — scope shift 0% (D-escalate-coverage GREEN)

### 0.2 Branch
- [x] `git checkout -b feature/sprint-57-124-hitl-gate-consolidation` (from `main` `6a691621`) ✅

---

## Day 1 — Item 1 backend: destructive floor + remove PermissionChecker (US-1/2/3/4)

### 1.1 `resolve_tool_risk` destructive HIGH-floor (US-1) ✅
- [x] **`_contracts/hitl.py`** (EDIT): `resolve_tool_risk(..., destructive=False)` → `if destructive and base<HIGH: base=HIGH`; MHist ✅
  - DoD: LOW/MEDIUM+destructive → HIGH; non-destructive unchanged; backward-compatible ✅
- [x] **loop `_resolve_tool_call_risk`** (`loop.py:540-549`, EDIT): passes `destructive=spec.annotations.destructive`; MHist ✅
  - DoD: `_cat9` resolves a destructive tool's risk as HIGH (floored) ✅ (loop test confirms)

### 1.2 Remove PermissionChecker gating from the executor (US-3) ✅
- [x] **`executor.py`** (EDIT): dropped import + `permission_checker` param + `self._permission` + the gate block; kept `ExecutionContext` + schema/dispatch/rate-limit/metrics/span; header docstring + MHist ✅
  - DoD: `execute` flows registry.get → validate → dispatch → rate-limit → span; no permission gate ✅

### 1.3 Delete permissions.py + exports + docstrings (US-4) ✅
- [x] **`git rm permissions.py`** ✅ (shadow gate, Fix B)
- [x] **`tools/__init__.py`** (EDIT): dropped import + 2 `__all__` entries ✅
- [x] **`_contracts/tools.py`** (EDIT): ToolHITLPolicy + ExecutionContext docstrings → `_cat9`/`HITLPolicy`; `explicit_approval` left + AD-note; MHist ✅
- [x] **`_register_all.py`** + **`hitl_tools.py`** (EDIT): dropped/updated stale "PermissionChecker" docstring refs ✅
  - Verify: `git grep PermissionChecker backend/src` → only intentional removal-note docstrings (0 code refs) ✅

### 1.4 Update the 3 PermissionChecker test files (US-4) ✅
- [x] **`test_executor.py`** (EDIT): removed 6 gate tests + enum test → 2 new "executor no-gate" tests; dropped PermissionDecision + ExecutionContext imports ✅
- [x] **`test_builtin_tools.py`** (EDIT): removed 2 approval tests + resolution test → 1 "runs-through-executor" test; dropped imports ✅
- [x] **`test_business_tools_via_registry.py`** (EDIT): dropped `_AllowAllPermissionChecker` + `permission_checker=` kwarg + imports; docstring updated ✅
  - DoD: removed behavior re-covered by §1.5 at the authoritative `_cat9`/policy layer (retro maps 1:1) ✅

### 1.5 New Item-1 tests (US-7 safety net) ✅
- [x] **`test_hitl_decision.py`** (EDIT): `resolve_tool_risk` destructive-floor parametrize (7 cases) + floor-beats-flag + escalate-under-default + escalate-under-MODERATE-tenant ✅
- [x] **`test_loop_hitl_policy.py`** (EDIT): `_registry`/`_build` += `destructive`; new `test_destructive_tool_escalates_via_high_floor_under_default` (PASS guardrail → HIGH-floor → ESCALATE + ApprovalRequest risk=HIGH) ✅
- [x] **`test_executor.py`** (EDIT): executor runs ALWAYS_ASK + destructive/HIGH tool with no second-gate error ✅
  - Verify: `pytest <5 touched test files> -q` → **94 passed** ✅

### 1.6 Backend gate (partial) ✅
- [x] black/isort ✅ · flake8 **clean** ✅ (fixed 2 E501 + 3 ExecutionContext F401) · mypy `src` **0/370** (−1 deleted permissions.py) ✅ · pytest 5 touched files **94 passed** ✅ (run_all + full pytest → Day 4 sweep)

---

## Day 2 — Item 3 admin validator (US-5) + Item 2 notifications DEMO (US-6)

### 2.1 Item 3 — admin PUT cross-field validator (US-5) ✅
- [x] **`admin/tenants.py`** (EDIT): `+model_validator` import; `HITLPolicyUpsertRequest` `@model_validator(mode="after")` — `_RISK_ORDER[auto] >= _RISK_ORDER[require]` → `ValueError` (422). MHist ✅
  - DoD: `auto=HIGH,require=MEDIUM` → 422; `auto=LOW,require=MEDIUM` → 200 ✅
- [x] **`test_admin_tenant_hitl_policies.py`** (EDIT): +3 tests (overlap → 422 + "strictly less than"; equal → 422; valid LOW<HIGH → 200); MHist ✅
  - Verify: `pytest tests/integration/api/test_admin_tenant_hitl_policies.py -q` → **22 passed** ✅

### 2.2 Item 2 — shared fixture + DEMO banner + derived badge (US-6) ✅
- [x] **`notificationsFixture.ts`** (NEW): export `DEMO_NOTIFICATIONS` + `DEMO_UNREAD_COUNT` + `NotificationItem`/`NotificationKind`/`NotificationSeverity` (extracted from `NOTIFICATIONS_SEED`) ✅
- [x] **`NotificationsPanel.tsx`** (EDIT): import shared fixture (replace inline types + `NOTIFICATIONS_SEED`) + `<BackendGapBanner reason={t("topbar.notifications.demoBanner")} />` after head row; CSS byte-identical. MHist ✅
  - DoD: DEMO banner renders; panel list + badge unchanged visually ✅
- [x] **`AppShellV2.tsx`** (EDIT): `import { DEMO_UNREAD_COUNT }`; `unreadCount={DEMO_UNREAD_COUNT}`; dropped `FIXTURE_UNREAD_COUNT`. MHist ✅
  - Verify: `grep "FIXTURE_UNREAD_COUNT" frontend/src` → 0 hits ✅
- [x] **i18n**: en + zh-TW `topbar.notifications.demoBanner` ✅

### 2.3 Item 2 tests + FE gate ✅
- [x] **`NotificationsPanel.test.tsx`** (EDIT): +1 test — DEMO `backend-gap-banner` present + /Demo data/; existing 7 (badge "3 new" + 6 items) still pass (refactor preserved behavior) ✅
- [x] **`notificationsFixture.test.ts`** (NEW): `DEMO_UNREAD_COUNT` derives from unread items (=3, not a magic number) + 6-item count ✅ (covers the badge-source claim; no AppShellV2 render test needed)
- [x] `npm run lint` clean (no `--silent`) ✅ · `npm run build` ✅ · `check:mockup-fidelity` **51** + styles byte-identical ✅ · vitest topbar **16 passed** ✅
- [x] **mypy re-verify** (post-tenants.py) **0/370** ✅ · **full backend pytest 2703 passed/5skip** (no PermissionChecker-removal regression) ✅

---

## Day 3 — Drive-through (US-8) — real chrome + real backend + real LLM

### 3.1 Clean restart / probe (Risk Class E — `loop.py`/`executor.py`/`hitl.py`/`tenants.py` changed) ✅
- [x] Stale :8000 = PID 38744 (57.123 session, OLD code); `dev.py stop` left it + orphan worker 7984 alive → `Stop-Process -Force 38744,7984` → :8000 FREE → `dev.py start` (absolute root) → fresh **43064+39956** sole owner; Vite :3007 (node) NOT stopped ✅
  - DoD: live `/auth/me` (roles) + admin PUT probe confirm NEW code serving ✅

### 3.2 Item 1 drive-through (the load-bearing proof) ⚠️ integration-verified; live-trigger non-deterministic
- [x] Attempted: chat-v2 + real Azure gpt-5.2, prompt "close incident INC-2451 … call the close-incident tool directly" → gpt-5.2 returned **0 tool calls** + answered conversationally ("I can't close INC-2451 yet…"); the model DECLINED the destructive call → no `_cat9` escalation to observe (the `AD-DriveThrough-Deterministic-Tool-Trigger` non-determinism — no reliable destructive-tool LLM trigger). NOT retried.
  - **Verified by real-component integration tests instead** (NOT mocks): `test_loop_hitl_policy` drives the actual `AgentLoopImpl._cat9_tool_check` → destructive tool ESCALATEs + ApprovalRequest risk=HIGH; `test_executor` drives the actual `ToolExecutorImpl` → destructive tool reaches the handler (no 2nd gate). Chat main-flow itself drives live + works (verification 0.98). Honest status recorded (NOT claimed as a UI drive-through).
- [x] observed-vs-intended → progress.md §3.4

### 3.3 Item 3 + Item 2 drive-through ✅ LIVE PASS
- [x] **Item 3** (live, real backend + real admin session `platform_admin`, tenant acme-prod): in-browser `fetch` PUT — overlap (HIGH≥MEDIUM) → **422** "strictly less than"; equal (MEDIUM==MEDIUM) → **422**; valid (LOW<HIGH) → **200** ✅
- [x] **Item 2** (live, real bell/panel UI): badge "**3**" (shared `DEMO_UNREAD_COUNT`) → bell click → panel opens → **`backend-gap-banner` visible** ("⚠️ Demo data — notifications backend not yet wired", role=note) + 6 items; screenshot `artifacts/sprint-57-124-item2-notif-demo-banner.png` ✅
- [x] observed-vs-intended → progress.md §3.2-3.4. **AP-4 clear** (Item 2 DEMO-labelled; Item 3 validator live; Item 1 single per-tenant gate proven by real-component tests) ✅

---

## Day 4 — CHANGE-091 + design note 36 + closeout

### 4.1 CHANGE-091 + design note 36 ✅
- [x] **`CHANGE-091-hitl-gate-consolidation-bundle.md`** (1-page; 3 tracks + drive-through delta + test net-delta) ✅
- [x] **`36-hitl-gate-consolidation-destructive-floor.md`** (design note Track 1; 8-pt gate ~95% — audit verdict + destructive-floor semantics + escalate-coverage table + rollback) ✅

### 4.2 Closeout ✅
- [x] retrospective.md Q1-Q7 + calibration (`mixed-multidomain-bundle` 0.65 KEEP, parent-direct `agent_factor` 1.0; ratio ≈1.0-1.1 IN band) + progress.md final ✅
- [x] Final gate sweep: mypy **0/370** · run_all **10/10** (count 24) · full pytest **2703+5skip** (−10 PermissionChecker +17 new) · vitest topbar **16** · mockup **51** + styles byte-identical ✅
- [x] Navigators: CLAUDE.md Current-Sprint + Last-Updated · MEMORY.md pointer + memory subfile `project_phase57_124_hitl_gate_consolidation.md` · next-phase-candidates (3 ADs SHIPPED + `AD-ExecutionContext-ExplicitApproval-Tidy` NEW) · sprint-workflow matrix `mixed-multidomain-bundle` data point ✅
- [x] **Anti-pattern self-check** (retro Q5): AP-2 (shadow-gate removed, single source of truth) / AP-4 (Item 2 DEMO disclosed `check_ap4` green; Item 1 real per-tenant gate) / AP-1 / AP-3 / AP-6 → **0 violations**; v2 lints 10/10 ✅
- [ ] PR (push + open) — local commit done; **awaiting user confirm before `git push`** (destructive-confirm rule); CI → merge on green (gh-verified MERGED before main sync)
