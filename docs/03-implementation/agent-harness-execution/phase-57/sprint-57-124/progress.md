# Sprint 57.124 Progress — HITL gate consolidation + 2 chrome/governance Potemkin fixes

**Branch**: `feature/sprint-57-124-hitl-gate-consolidation` (from `main` `6a691621`)
**Plan**: [sprint-57-124-plan.md](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-124-plan.md) · [checklist](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-124-checklist.md)

---

## Day 0 — Plan-vs-Repo Verify (三-prong) + Branch — YYYY-MM-DD

### Drift findings

**Prong 1 — path verify** ✅ all anchors present:
- Item 1: `permissions.py` (DELETE target) · `executor.py:87/138/145/169-188` · `__init__.py:37/129-130` · `hitl.py:127-150` `resolve_tool_risk` · `loop.py:540-548` `_resolve_tool_call_risk` · `tools.py:66-67/122` · 3 test files (`test_executor.py`/`test_builtin_tools.py`/`test_business_tools_via_registry.py`).
- Item 2: `AppShellV2.tsx:79/118` · `NotificationsPanel.tsx:153-175` `NOTIFS` · `BackendGapBanner.tsx:25-29`.
- Item 3: `admin/tenants.py:971-1000` `HITLPolicyUpsertRequest` + `:892-893` `_RISK_ORDER`.
- `CHANGE-091-*.md` + design-note `36-*.md` free.

**Prong 2 — content verify:**

| ID | Finding | Verdict |
|----|---------|---------|
| **D-escalate-coverage** ⚠️→✅ | **CENTRAL Item-1 safety.** See the coverage table below. ALL 8 ALWAYS_ASK/ASK_ONCE tools have `risk_level ≥ MEDIUM`; under the DEFAULT policy (`require_approval_min_risk=MEDIUM`) all escalate via the 57.122 risk threshold alone — NO tool loses escalation post-removal. The destructive floor adds permissive-tenant protection. **No `CHAT_HITL_ESCALATE_TOOLS` change needed.** GREEN. |
| **D-resolve-risk-callers** ✅ | `resolve_tool_risk` called at `loop.py:548` (keyword args) + tests; an optional `destructive=False` param is backward-compatible (no positional break). |
| **D-executor-other-callers** ✅ | `ToolExecutorImpl` built by `make_default_executor` (chat + subagent children — children run their own `_cat9` per B4/57.110 → covered) + `echo_tool.py:75` (self-test). No non-loop SOLE-gate production caller. |
| **D-notif-fixture-source** ✅ | `NOTIFS` is a module const in `NotificationsPanel.tsx:153-158` (extractable); the panel's `markAll`/`markOne` mutate local `useState` only → the derived Topbar badge stays static (acceptable DEMO, disclosed by the banner). |
| **D-backendgapbanner-fidelity** ✅ | `BackendGapBanner` (`components/ui/BackendGapBanner.tsx`) is the existing gold AP-2 marker (reused on ~15 surfaces) → no new oklch/hex literal; additive in-panel → mockup-fidelity 51 holds. |
| **D-explicit-approval-orphan** ✅ | `ExecutionContext.explicit_approval` (`tools.py:122`) sole consumer = PermissionChecker dim 3 → leave the frozen-dataclass field + AD-note `AD-ExecutionContext-ExplicitApproval-Tidy` (removing a contract field is a separate structural change). |

**Prong 3 — schema** ✅ N/A: NO new table/migration (Item 3 = a Pydantic `@model_validator` only).

### D-escalate-coverage table (the Item-1 safety proof)

Every tool `PermissionChecker` currently returns non-ALLOW for, and how it still escalates via `_cat9` after removal:

| Tool | hitl_policy | risk_level | destructive | PermissionChecker reason | Post-removal escalation |
|------|-------------|-----------|-------------|--------------------------|-------------------------|
| `rootcause` apply (`rootcause/tools.py:99-102`) | ALWAYS_ASK | HIGH | ✓ | dim1+2+3 | risk HIGH ≥ require_min(MEDIUM) → ESCALATE ✓ (+ floor) |
| `incident` (3rd, `incident/tools.py:111-114`) | ALWAYS_ASK | HIGH | ✓ | dim1+2+3 | risk HIGH → ESCALATE ✓ |
| `request_approval` (`hitl_tools.py:87-88`) | ALWAYS_ASK | MEDIUM | ✗ | dim1 | risk MEDIUM ≥ require_min(MEDIUM) → ESCALATE ✓ |
| `patrol` ×2 (`patrol/tools.py:113/115-116, 130/132-133`) | ASK_ONCE | MEDIUM | ✓ | dim1+3 | risk MEDIUM → ESCALATE ✓ (floor → HIGH protects permissive tenant) |
| `incident` ×2 (`incident/tools.py:69/71-72, 90/92-93`) | ASK_ONCE | MEDIUM | ✓ | dim1+3 | risk MEDIUM → ESCALATE ✓ (+ floor) |
| `audit` (`audit_domain/tools.py:98/100-101`) | ASK_ONCE | MEDIUM | ✓ | dim1+3 | risk MEDIUM → ESCALATE ✓ (+ floor) |

**Verdict**: GREEN. No CRITICAL-risk tools exist; no LOW-risk ALWAYS_ASK/ASK_ONCE tool exists. Under the default policy every non-ALLOW tool escalates via the risk threshold. The destructive HIGH-floor's load-bearing role is for PERMISSIVE tenants (`auto_approve_max_risk=MEDIUM`): without it a MEDIUM-risk destructive tool would auto-run; with it → HIGH → escalates unless the tenant trusts HIGH. The floor also fixes the latent bug (PermissionChecker dim 3 hard-DENY'd destructive tools even after a human approved them).

**D-baselines** (trusted from 57.123 merge `6a691621`): pytest 2696+5skip · wire 24 · Vitest 892 · mockup 51 · mypy `src` 0/371 · run_all 10/10. Re-capture Day 3/4.

**Go/no-go**: ✅ GO — scope shift 0% (D-escalate-coverage GREEN, no `escalate_tools` change; all anchors confirmed).

### 0.2 Branch ✅ `feature/sprint-57-124-hitl-gate-consolidation` from `main` `6a691621`.

---

## Day 1 — Item 1 backend: destructive floor + remove PermissionChecker (US-1/2/3/4) — 2026-06-16

### Accomplishments
- **`resolve_tool_risk` destructive HIGH-floor** (`_contracts/hitl.py`): added `destructive: bool = False`; `if destructive and base < HIGH: base = HIGH`. Backward-compatible (default False).
- **loop threads destructive** (`loop.py:540-549`): `_resolve_tool_call_risk` now passes `destructive=spec.annotations.destructive` into `resolve_tool_risk`. `_cat9` already calls it on both PASS + ESCALATE → destructive tools now escalate via the floor.
- **executor de-gated** (`executor.py`): removed the `PermissionChecker` import + `permission_checker` param + `self._permission` + the DENY/REQUIRE_APPROVAL gate block. Executor = registry.get → validate → dispatch → rate-limit → metric/span. Header docstring + MHist updated.
- **`permissions.py` DELETED** (`git rm`); `tools/__init__.py` exports dropped; `_contracts/tools.py` + `_register_all.py` + `hitl_tools.py` stale PermissionChecker docstrings updated to point at `_cat9`/`HITLPolicy`. `explicit_approval` field LEFT (forward-compat) + AD-noted (`AD-ExecutionContext-ExplicitApproval-Tidy`).
- **Test surgery (3 files)**: removed the 6 executor gate tests + the PermissionChecker enum/resolution tests + the `_AllowAllPermissionChecker` shim/kwarg (all testing the REMOVED component). Replaced with tests asserting the executor NO LONGER gates (runs ALWAYS_ASK + destructive/HIGH tools through the handler).
- **New safety-net tests**: `test_hitl_decision.py` — destructive-floor parametrize (7) + floor-beats-flag + escalate-under-default + escalate-under-MODERATE-tenant (the regression guard for the removed dim 3). `test_loop_hitl_policy.py` — `_registry`/`_build` += `destructive`; `test_destructive_tool_escalates_via_high_floor_under_default` (PASS guardrail → HIGH-floor → ESCALATE; ApprovalRequest risk == HIGH).

### Gate (partial)
- mypy `src` **0/370** (was 371; −1 from the deleted `permissions.py`) ✅
- flake8 **clean** ✅ (fixed 2 E501 in the new docstring/MHist + 3 `ExecutionContext` F401 left unused by the test removals)
- pytest 5 touched test files → **94 passed** in 2.66s ✅
- Broad `git grep PermissionChecker|permission_checker|PermissionDecision backend/src|tests` → only intentional removal-note docstrings/comments remain (0 code refs); `test_escalation_keyword_detector` "approval required" hits are an unrelated keyword guardrail.

### Test net-delta (Item 1)
- Removed: 6 (test_executor gate) + 1 (enum) + 2 (test_builtin approval) + 1 (resolution) = 10
- Added: 2 (executor no-gate) + 1 (builtin runs-through) + 7-param+3 (hitl destructive floor) + 1 (loop destructive escalate) = ~14 (parametrized cases counted per-id)
- Net executor/builtin coverage shifted from "executor gates" → "executor runs + loop _cat9/policy gates" (authoritative layer).

### Notes / decisions
- **D-escalate-coverage GREEN held**: no `CHAT_HITL_ESCALATE_TOOLS` change needed (all non-ALLOW tools risk ≥ MEDIUM; floor adds permissive-tenant protection).
- `request_approval` (ALWAYS_ASK, MEDIUM) still escalates via risk MEDIUM ≥ require_min(MEDIUM); the executor-level test now asserts the absence of the old gate message (handler-reach), not a specific handler result.

---

## Day 2 — Item 3 admin validator (US-5) + Item 2 notifications DEMO (US-6) — 2026-06-16

### Item 3 — admin PUT cross-field validator
- `admin/tenants.py`: `+model_validator` import; `HITLPolicyUpsertRequest` `@model_validator(mode="after")` rejects `_RISK_ORDER[auto] >= _RISK_ORDER[require]` → ValueError (FastAPI 422). The `@field_validator` runs first (guarantees valid RiskLevel names), so `RiskLevel(...)` in the model validator never raises. MHist + Last Modified.
- `test_admin_tenant_hitl_policies.py`: +3 tests — overlap (HIGH≥MEDIUM) → 422 + "strictly less than"; equal (MEDIUM==MEDIUM) → 422; valid (LOW<HIGH) → 200. **22 passed** (19 + 3).

### Item 2 — notifications DEMO honesty (Fix A)
- **NEW `notificationsFixture.ts`**: the single source — `DEMO_NOTIFICATIONS` + `DEMO_UNREAD_COUNT` (derived = 3) + `NotificationItem`/`NotificationKind`/`NotificationSeverity` types (extracted from the panel's inline `NOTIFICATIONS_SEED`).
- `NotificationsPanel.tsx`: imports the shared fixture (removed the local types + seed); `useState(DEMO_NOTIFICATIONS)`; added `<BackendGapBanner reason={t("topbar.notifications.demoBanner")} />` in a `padding: 8px 14px 0` wrapper after the head row. Panel CSS classes + inline mockup literals byte-identical. MHist.
- `AppShellV2.tsx`: `import { DEMO_UNREAD_COUNT }`; `unreadCount={DEMO_UNREAD_COUNT}`; **dropped the standalone `FIXTURE_UNREAD_COUNT = 3`**. MHist.
- i18n: en "Demo data — notifications backend not yet wired" + zh-TW "示範資料 — 通知後端尚未接通".
- Tests: extended `NotificationsPanel.test.tsx` (+1 DEMO-banner test; the existing 7 — incl. badge "3 new" + 6 items — still pass = refactor preserved behavior); NEW `notificationsFixture.test.ts` (DEMO_UNREAD_COUNT derives from unread items, not a magic number).

### Gate (Day 2)
- mypy `src` **0/370** (re-verified post-tenants.py) ✅
- flake8 (tenants.py + test) clean ✅ · FE `npm run lint` clean ✅ (TSSatisfiesExpression = pre-existing jsx-ast-utils noise, not my change)
- FE `npm run build` ✓ · `check:mockup-fidelity` **51 baseline unchanged + styles-mockup.css byte-identical** (DEMO banner = existing BackendGapBanner token utilities, no new oklch/hex literal) ✅
- vitest topbar dir **16 passed** ✅
- **Full backend pytest 2703 passed / 5 skipped** (baseline 2696+5 → +7 net: −10 PermissionChecker tests +17 new Item-1/3 tests) — confirms NO broad regression from the PermissionChecker removal ✅

---

## Day 3 — Drive-through (US-8) — real chrome + real backend + real LLM — 2026-06-16

### 3.1 Clean restart (Risk Class E — loop.py/executor.py/hitl.py/tenants.py changed)
- The running :8000 backend was PID 38744 (the 57.123 session, 6/15 10:56 PM = OLD code). `dev.py stop backend` reported success but **38744 still owned :8000 + orphan spawn-worker 7984 (PPID 38744) stayed alive** (the Risk Class E SO_REUSEADDR orphan). `Stop-Process -Force 38744, 7984` → :8000 FREE → `dev.py start backend` (absolute project root; the first attempt failed exit 2 because the cwd had drifted to `Downloads\` via repeated `cd ..`) → fresh **PID 43064 (reloader) + 39956 (worker)**, sole :8000 owner, 6/16 12:32 AM. Vite :3007 (node, PID 31616) NOT stopped. (Lesson reconfirmed: `dev.py stop` does NOT reliably kill the spawn-worker; force-kill by PID + verify the port is free.)

### 3.2 Item 2 — DEMO banner (FE user-facing) ✅ LIVE PASS
- Dev-login `dan@acme.com · admin` / acme-prod → /cost-dashboard → AppShellV2 chrome rendered (`app-shell` present). Bell badge = **"3"** (the shared `DEMO_UNREAD_COUNT`, not the removed hardcoded `FIXTURE_UNREAD_COUNT`). Click bell → panel opens → **`backend-gap-banner` present, role="note", text "⚠️ Demo data — notifications backend not yet wired"** + 6 item rows. AP-4 closed: the fixture is now honestly DEMO-labelled. Screenshot `artifacts/sprint-57-124-item2-notif-demo-banner.png`.

### 3.3 Item 3 — admin PUT 422 (real backend, real admin session) ✅ LIVE PASS
- In-browser `fetch` with the real admin session (`/auth/me` roles = `["user","admin","platform_admin"]`) against the freshly-restarted backend, tenant `09eb1b62…` (acme-prod):
  - **overlap (auto=HIGH, require=MEDIUM) → 422** "auto_approve_max_risk must be strictly less than require_approval_min_risk"
  - **equal (auto=MEDIUM, require=MEDIUM) → 422** same message
  - **valid (auto=LOW, require=HIGH) → 200** saved_policy returned
- This is a live drive-through of the new `@model_validator` through the REAL running backend + a REAL admin session (not the ASGITransport integration test). Side-effect: the valid PUT wrote acme-prod's HITL policy to `auto=LOW/require=HIGH` (a valid, slightly-more-permissive policy; left as-is on the dev tenant).

### 3.4 Item 1 — destructive escalate→run (the hard one) — INTEGRATION-VERIFIED; live-LLM trigger non-deterministic
- The chat-v2 **main flow drives live + works**: prompt → real Azure gpt-5.2 → loop → answer → `verification_passed llm_judge score=0.98` → trace/checkpoint → `loop_end stop=end_turn`.
- The SPECIFIC Item-1 demonstration (a destructive tool escalating then running) was **NOT triggered**: prompted "close incident INC-2451 … call the close-incident tool directly" → gpt-5.2 returned **`0 tool calls`** and answered conversationally ("I can't close INC-2451 yet because closing an incident…"). The model declined the destructive action; no tool call → no `_cat9` escalation to observe. This is the **`AD-DriveThrough-Deterministic-Tool-Trigger`** non-determinism (a destructive business tool has no reliable LLM trigger; gpt-5.2 is cautious about destructive ops). Not retried (low success probability, burns tokens).
- **Item 1's behavior is verified by REAL-COMPONENT integration tests** (NOT mocks of the gating): `test_loop_hitl_policy.py::test_destructive_tool_escalates_via_high_floor_under_default` drives the actual `AgentLoopImpl._cat9_tool_check` → a destructive LOW-risk tool ESCALATEs + the `ApprovalRequest` carries risk=HIGH; `test_executor.py` drives the actual `ToolExecutorImpl` → a destructive/ALWAYS_ASK tool reaches the handler with no second-gate error. Honest status: **integration-verified (real components) + chat main-flow drives live; the destructive-tool escalate UI path was not LLM-triggerable on demand** (documented, NOT claimed as a UI drive-through per the §Drive-Through constraint).

### Drive-through summary
| Item | Live drive-through | Verdict |
|------|--------------------|---------|
| Item 2 (DEMO banner) | ✅ real bell/panel UI | PASS — banner visible, badge derived |
| Item 3 (PUT 422) | ✅ real backend + admin session | PASS — overlap/equal → 422, valid → 200 |
| Item 1 (destructive escalate→run) | ⚠️ chat main-flow drives; destructive trigger declined by gpt-5.2 | real-component integration-verified; live-trigger non-deterministic (honest, not gate-only) |
