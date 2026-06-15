# CHANGE-091: HITL gate consolidation + 2 chrome/governance Potemkin fixes (3-track bundle)

**Date**: 2026-06-16
**Sprint**: 57.124
**Scope**: Cat 2 (Tool Layer) + Cat 9 (Guardrails/HITL) + Cat 1 (Loop) + API Admin + Frontend chrome
**ADs closed**: `AD-PermissionChecker-Shadow-Gate-Phase58` (NEW, the audit verdict) · `AD-HITL-Policy-Threshold-Validation` (57.122 carryover) · `AD-NotificationsPanel-Backend-Feed` (honest-label)
**Design note**: `36-hitl-gate-consolidation-destructive-floor.md` (Track 1 only)

---

## Problem

Three carryover items, chosen together by the user (2026-06-15):

1. **Item 1 — `PermissionChecker` shadow gate** (audit). `PermissionChecker` (Sprint 51.1, `agent_harness/tools/permissions.py`) is a parallel HITL/risk gate wired into `ToolExecutorImpl` (default-on; `make_default_executor` never passed one). The chat loop runs it AFTER the authoritative 57.122 `_cat9_tool_check` (per-tenant `HITLPolicy`). Its three HARDCODED dims conflict with + can OVERRIDE the load-bearing per-tenant policy: dim 2 (`risk HIGH/CRITICAL → REQUIRE_APPROVAL`) is the exact flat hardcoding 57.122 removed from `loop.py:1007` and re-blocks a permissive tenant's `auto_approve_max_risk=HIGH`; dim 3 (`destructive → DENY`) unconditionally hard-blocks every destructive business tool in chat (`exec_ctx.explicit_approval` is never True) — an "approved-but-still-fails" latent bug.

2. **Item 2 — notifications fixture Potemkin.** `AppShellV2.tsx:79` `FIXTURE_UNREAD_COUNT=3` + the `NotificationsPanel` 6-item fixture masquerade as real chrome notifications with NO backend, no DEMO disclosure (AP-4).

3. **Item 3 — missing cross-field validation.** The admin HITL-policy PUT validated each risk field but not `auto_approve_max_risk < require_approval_min_risk`; a misconfigured overlap is runtime-safe (57.122 escalate-first) but silently means "escalate the gray band" with no operator feedback.

## Root Cause

- Item 1: `PermissionChecker` predates 57.122. When 57.122 made the per-tenant `HITLPolicy` the load-bearing tool-gating source, the executor's older duplicate gate was never retired → a stale shadow gate that overrides the new policy.
- Item 2: the notifications feature shipped as a mockup port (57.19) with a fixture + a "wire later" comment; the badge count was a separate hardcoded constant from the panel's own list.
- Item 3: the PUT schema (57.54) only had per-field validators.

## Solution

**Item 1 (Fix B — user-chosen: single source of truth + destructive floor):**
- `_contracts/hitl.py` `resolve_tool_risk(..., destructive=False)` → floors destructive tools to **HIGH** (the highest-consequence class) so they ESCALATE under the default policy and RUN on approval — moving the dim-3 protection into the load-bearing per-tenant policy path.
- `loop.py` `_resolve_tool_call_risk` threads `spec.annotations.destructive` into `resolve_tool_risk`.
- `executor.py` — removed the `PermissionChecker` import + param + `self._permission` + the DENY/REQUIRE_APPROVAL gate block (executor = validate → dispatch → rate-limit → metric/span).
- **DELETED** `permissions.py`; dropped the `tools/__init__.py` exports; updated stale PermissionChecker docstrings in `_contracts/tools.py` / `_register_all.py` / `hitl_tools.py`. `ExecutionContext.explicit_approval` left for forward-compat (`AD-ExecutionContext-ExplicitApproval-Tidy` tracks removing it).
- Day-0 `D-escalate-coverage` confirmed GREEN: all 8 ALWAYS_ASK/ASK_ONCE tools are risk ≥ MEDIUM → all still escalate under the default policy; the destructive floor adds permissive-tenant protection; no `CHAT_HITL_ESCALATE_TOOLS` change needed.

**Item 3:** `admin/tenants.py` `HITLPolicyUpsertRequest` `@model_validator(mode="after")` rejects `_RISK_ORDER[auto] >= _RISK_ORDER[require]` → 422.

**Item 2 (Fix A — DEMO label + single source):** NEW `notificationsFixture.ts` (`DEMO_NOTIFICATIONS` + derived `DEMO_UNREAD_COUNT` + types); `NotificationsPanel.tsx` imports it + renders a `BackendGapBanner` ("Demo data — notifications backend not yet wired"); `AppShellV2.tsx` derives the bell badge from `DEMO_UNREAD_COUNT` (dropped the standalone `FIXTURE_UNREAD_COUNT`); i18n en/zh-TW.

## Verification

- **Gates**: mypy `src` **0/370** (−1 deleted `permissions.py`) · flake8 clean · **full backend pytest 2703 passed / 5 skipped** (baseline 2696+5 → −10 PermissionChecker tests +17 new) · v2 lints **10/10** · FE `npm run lint` clean / `npm run build` ✓ / `check:mockup-fidelity` **51 baseline + styles byte-identical** / vitest topbar **16 passed**.
- **Real-component integration tests** (Item 1): `test_loop_hitl_policy.py::test_destructive_tool_escalates_via_high_floor_under_default` drives the actual `AgentLoopImpl._cat9_tool_check` → destructive LOW-risk tool ESCALATEs + ApprovalRequest risk=HIGH; `test_executor.py` drives the actual `ToolExecutorImpl` → destructive/ALWAYS_ASK tools reach the handler (no second gate).
- **Drive-through** (real backend PID 43064 + real LLM + real admin session; clean restart per Risk Class E):
  - **Item 2 ✅ LIVE**: dev-login admin → bell badge "3" (shared `DEMO_UNREAD_COUNT`) → panel → `backend-gap-banner` visible (role=note, "⚠️ Demo data…") + 6 items. Screenshot `sprint-57-124/artifacts/`.
  - **Item 3 ✅ LIVE**: in-browser PUT (real `platform_admin` session) — overlap (HIGH≥MEDIUM) → **422** "strictly less than"; equal → **422**; valid (LOW<HIGH) → **200**.
  - **Item 1 ⚠️**: chat-v2 main flow drives live (verification 0.98); the destructive-tool escalate path was NOT LLM-triggerable (gpt-5.2 returned 0 tool calls + declined to close the incident — `AD-DriveThrough-Deterministic-Tool-Trigger`) → integration-verified via the real-component tests above, NOT claimed as a UI drive-through.

## Impact

- Backend tool gating now has a SINGLE source of truth (the loop `_cat9` + per-tenant `HITLPolicy`); the stale shadow gate is gone; destructive tools escalate-then-run on approval (latent bug fixed). The change is backend-internal (no API/wire/migration change). Subagent child loops are covered (they run their own `_cat9`, B4/57.110).
- The admin HITL-policy PUT fails loud on an overlapping threshold (422).
- The chrome notifications are honestly DEMO-labelled with a single fixture source (no fake-real masquerade).
- NO migration / new wire event (count 24) / codegen / new dependency; mockup-fidelity 51 unchanged.

## Files

Backend (src): `_contracts/hitl.py` · `_contracts/tools.py` · `orchestrator_loop/loop.py` · `tools/executor.py` · `tools/__init__.py` · `tools/hitl_tools.py` · `business_domain/_register_all.py` · `api/v1/admin/tenants.py` · **DELETED** `tools/permissions.py`.
Backend (tests): `test_executor.py` · `test_builtin_tools.py` · `test_business_tools_via_registry.py` · `test_hitl_decision.py` · `test_loop_hitl_policy.py` · `test_admin_tenant_hitl_policies.py`.
Frontend: NEW `topbar/notificationsFixture.ts` · `topbar/NotificationsPanel.tsx` · `AppShellV2.tsx` · i18n en/zh-TW · NEW `tests/.../notificationsFixture.test.ts` · `tests/.../NotificationsPanel.test.tsx`.
Docs: this CHANGE-091 + design note 36.
