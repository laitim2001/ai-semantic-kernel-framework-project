# Sprint 57.124 Plan — HITL gate consolidation + 2 chrome/governance Potemkin fixes (3-track bundle). **Track 1 (Item 1, the meaty track)**: `PermissionChecker` (Sprint 51.1, `agent_harness/tools/permissions.py`) is a PARALLEL HITL/risk gate wired into `ToolExecutorImpl` (`executor.py:145`, default-on) that the chat main flow runs AFTER the authoritative 57.122 `_cat9_tool_check` (per-tenant `HITLPolicy`). Its three hardcoded dimensions (hitl_policy ALWAYS_ASK→REQUIRE_APPROVAL / risk HIGH→REQUIRE_APPROVAL / destructive→DENY) NOW CONFLICT with + can OVERRIDE the load-bearing per-tenant policy 57.122 just shipped (a permissive tenant's `auto_approve_max_risk=HIGH` is silently re-blocked; a human-APPROVED destructive tool still fails "permission denied" at the executor). **Fix B (user-chosen 2026-06-15)**: remove `PermissionChecker` gating from the executor (single source of truth = `_cat9`/per-tenant policy) + compensate by making `resolve_tool_risk` treat `ToolSpec.annotations.destructive` as a risk FLOOR (HIGH) so destructive tools ESCALATE (human-approvable) under the default policy instead of being hard-DENY'd — closing both the override conflict AND the "approved-but-still-fails" latent bug. **Track 2 (Item 2)**: `AppShellV2.tsx:79` `FIXTURE_UNREAD_COUNT=3` + the whole `NotificationsPanel` 6-item fixture masquerade as real chrome notifications with NO backend (`AD-NotificationsPanel-Backend-Feed`) — **Fix A (user-chosen)**: add a visible DEMO banner (`BackendGapBanner`) + derive the badge count from the shared fixture source (drop the standalone hardcoded `3`). **Track 3 (Item 3)**: the admin HITL-policy PUT (`admin/tenants.py:971`) validates each risk field but NOT the cross-field invariant `auto_approve_max_risk < require_approval_min_risk` (`AD-HITL-Policy-Threshold-Validation`) — add a `@model_validator` → 422 (runtime is safe via 57.122 escalate-first, but a misconfigured overlap silently means "escalate"). CHANGE-091 + design note 36 (Track 1 HITL gate-consolidation semantics; Tracks 2+3 feature-continuation, no note). NO migration / wire (count 24) / codegen.

**Status**: Approved-to-execute (user 2026-06-15: picked the 3 carryover items together — `PermissionChecker`/`ToolSpec.hitl_policy` audit + `FIXTURE_UNREAD_COUNT` + `AD-HITL-Policy-Threshold-Validation`; the Item 1 audit verdict + the Fix B vs Fix A scope decisions resolved via AskUserQuestion 2026-06-15 — **Item 1 = Fix B (complete; single source of truth + destructive floor)** + **Item 2 = Fix A (DEMO banner + derive badge)**).
**Branch**: `feature/sprint-57-124-hitl-gate-consolidation`
**Base**: `main` HEAD `6a691621` (post-#298 — Sprint 57.123 tenant-display real-data).
**Slice**: Item 1 `AD-PermissionChecker-Shadow-Gate-Phase58` (NEW — the audit verdict: a stale pre-57.122 duplicate gate that conflicts with the load-bearing per-tenant HITL policy) · Item 2 `AD-NotificationsPanel-Backend-Feed` (a C-class chrome Potemkin, honest-label) · Item 3 `AD-HITL-Policy-Threshold-Validation` (57.122 carryover).
**Scope decisions** (AskUserQuestion 2026-06-15): (a) **Item 1 = Fix B** — remove `PermissionChecker` from the executor path ENTIRELY (delete `permissions.py` + the executor gate + the `__init__` exports); the `_cat9`/per-tenant policy becomes the single tool-gating source of truth; compensate by extending `resolve_tool_risk` with a `destructive` HIGH-floor so destructive tools escalate-then-run-on-approval instead of being unconditionally hard-DENY'd. (b) **Item 2 = Fix A** — a visible DEMO `BackendGapBanner` inside `NotificationsPanel` + derive the Topbar badge count from the shared (still-fixture) source (drop the standalone `FIXTURE_UNREAD_COUNT`); NO notifications backend built (a large greenfield, out of scope). (c) **Item 3** — a `@model_validator(mode="after")` on `HITLPolicyUpsertRequest` rejecting `auto_approve_max_risk >= require_approval_min_risk` → 422 (reuse the existing `_RISK_ORDER`). (d) NO migration / new wire event / codegen / new dependency; mockup-fidelity 51 unchanged (the DEMO banner is an additive reuse of the existing `BackendGapBanner`, panel CSS byte-identical, no new oklch/hex literal).

---

## 0. Background

### Item 1 — `PermissionChecker` is a stale shadow gate that conflicts with 57.122 (the audit verdict)

The chat main flow builds its executor via `make_default_executor` (`business_domain/_register_all.py:178`), which constructs `ToolExecutorImpl(registry=, handlers=, tracer=)` (`:357`) **without** a `permission_checker` → `ToolExecutorImpl.__init__` (`executor.py:145`) defaults to `self._permission = PermissionChecker()`. So `PermissionChecker` (Sprint 51.1, `agent_harness/tools/permissions.py`) IS active on the 主流量.

The loop runs tools as: `_cat9_tool_check` (`loop.py:2828`, the authoritative 57.122 guardrail + per-tenant `HITLPolicy` ESCALATE) FIRST → then `_tool_executor.execute` (`loop.py:2918`) which internally runs `PermissionChecker.check()` AGAIN (`executor.py:169`). `PermissionChecker` has three HARDCODED dimensions (`permissions.py:93-105`):

| Dim | Rule | Conflict with 57.122 |
|-----|------|----------------------|
| 1 | `hitl_policy in (ALWAYS_ASK, ASK_ONCE)` → REQUIRE_APPROVAL | duplicates the capability-matrix `requires_approval` flag (`_cat9`), and returns a FAILED ToolResult **string** ("approval required: …", `executor.py:178-188`), NOT a real ESCALATE pause |
| 2 | `risk_level in (HIGH, CRITICAL)` → REQUIRE_APPROVAL | **the exact flat hardcoding 57.122 REMOVED from `loop.py:1007`**; OVERRIDES a permissive tenant's `auto_approve_max_risk` (a tenant that trusts HIGH is silently re-blocked) |
| 3 | `annotations.destructive and not context.explicit_approval` → DENY | the loop's `exec_ctx` (`loop.py:2886-2890`) NEVER sets `explicit_approval=True` → **every** destructive business tool (incident/rootcause/patrol/audit — `destructive=True`) is unconditionally hard-DENY'd in chat, even after a human APPROVES it via the 57.122 ESCALATE→resume |

`_cat9_tool_check` (`loop.py:905-1020`) does NOT read `annotations.destructive` — destructive gating lives ONLY in `PermissionChecker` dim 3. So this is not a benign AP-4 Potemkin (no-content stub) — it is **worse**: a stale pre-57.122 duplicate gate whose dims 1+2 can OVERRIDE the load-bearing per-tenant policy, and whose dim 3 hard-blocks every destructive tool (an "approved-but-still-fails" latent bug + an advertised-but-unrunnable tool surface).

**Why Fix B (remove + compensate) is safe** — Day-0 confirmed the chat capability matrix flags ONLY `echo_tool` as `requires_approval` by default (`handler.py:178` `CHAT_HITL_ESCALATE_TOOLS = frozenset({"echo_tool"})`; per-tenant `policy.escalate_tools` can override). So after removing `PermissionChecker`, a tool still escalates via `_cat9` IFF: it is in `escalate_tools` (→ guardrail ESCALATE → flagged) **OR** its `ToolSpec.risk_level` ≥ `require_approval_min_risk` (the 57.122 risk-threshold path — covers HIGH/CRITICAL tools) **OR** (NEW) it is `destructive` and the destructive HIGH-floor lifts it to escalate. A LOW-risk destructive tool that is NOT in `escalate_tools` would, after a naive removal, AUTO-RUN (a safety regression) — which is exactly why the destructive HIGH-floor compensating change is mandatory, not optional.

### Item 2 — the chrome notifications are a fixture with no backend

`AppShellV2.tsx:79` `const FIXTURE_UNREAD_COUNT = 3` (comment `:78`: "AD-NotificationsPanel-Backend-Feed Sprint 57.21+ wires real feed") feeds the Topbar bell badge (`:118` `unreadCount={FIXTURE_UNREAD_COUNT}`). The dropdown `NotificationsPanel.tsx` renders a 6-item `NOTIFS` fixture (`:153-158`, n1-n6 hitl/incident/verify/tripwire/system) and computes its OWN `unreadCount = items.filter(n => n.unread).length` (`:175`, = 3). There is NO notifications backend (Day-0 grep — only an unrelated SLA `hitl_queue_notif_p99_ms` metric + an orchestrator "Off-platform notifications" config field). The badge + panel look real with no DEMO disclosure → AP-4. Per CLAUDE.md §Drive-Through ("後端沒接就用假資料但不標示 demo → 要嘛標 DEMO，要嘛留白") the honest minimal fix (no backend built) is the DEMO label + a single fixture source.

### Item 3 — the admin HITL-policy PUT has no cross-field validation

`HITLPolicyUpsertRequest` (`admin/tenants.py:971-1000`) validates each risk field is a valid `RiskLevel` name (`@field_validator` `:995`) but NOT the invariant `auto_approve_max_risk < require_approval_min_risk`. A misconfigured overlap (`auto >= require`) is runtime-SAFE (57.122 `decide_tool_hitl` is escalate-first → errs to ESCALATE) but silently means "escalate everything in the gray band" with no operator feedback. The `_RISK_ORDER` map already exists (`admin/tenants.py:892-893`) for reuse.

### Ground truth (Day-0 head-start — direct reads on `main` HEAD `6a691621`; ALL re-verified in the formal Day-0 三-prong §checklist 0.1)

**Item 1 anchors:**
- `agent_harness/tools/permissions.py` — `PermissionChecker` (`:84-105`) + `PermissionDecision` (`:76-81`). To DELETE.
- `agent_harness/tools/executor.py:87` import / `:138` `permission_checker` param / `:145` `self._permission` / `:169-188` the DENY+REQUIRE_APPROVAL gate block. REMOVE the gating (executor keeps schema-validate + dispatch + rate-limit + metrics + tracing).
- `agent_harness/tools/__init__.py:37,129,130` — `PermissionChecker` / `PermissionDecision` imports + `__all__`. REMOVE.
- `agent_harness/_contracts/hitl.py:127-150` — `resolve_tool_risk(spec_risk, *, rule_requires_approval)`. ADD a `destructive: bool = False` param → floor to HIGH when `destructive`.
- `agent_harness/orchestrator_loop/loop.py:540-548` — `_resolve_tool_call_risk(tool_name, *, flagged)` reads `spec` from the registry; pass `destructive=spec.annotations.destructive` into `resolve_tool_risk`.
- `agent_harness/_contracts/tools.py:66-67` docstring (PermissionChecker ref — update) + `:122` `explicit_approval` field (its only consumer was PermissionChecker dim 3 — leave the frozen-dataclass field, update the docstring; note as a tidy-up AD, removing a contract field is a separate structural change).
- `handler.py:178` `CHAT_HITL_ESCALATE_TOOLS = frozenset({"echo_tool"})` (confirms only echo is flagged on chat).
- Destructive tools: `audit_domain/tools.py:98`, `patrol/tools.py:113,130`, `rootcause/tools.py:99` (also HIGH+ALWAYS_ASK), `incident/tools.py:69,90,111` (`destructive=True`).
- Test homes: `tests/unit/agent_harness/tools/test_executor.py:376-382` (PermissionChecker/Decision direct tests) · `tests/integration/agent_harness/tools/test_builtin_tools.py:129,271-275` (PermissionChecker resolution) · `tests/integration/business_domain/test_business_tools_via_registry.py:49-104` (`_AllowAllPermissionChecker` workaround + `permission_checker=` kwarg).

**Item 2 anchors:**
- `AppShellV2.tsx:78-79` `FIXTURE_UNREAD_COUNT` / `:118` `unreadCount` prop.
- `NotificationsPanel.tsx:153-158` `NOTIFS` fixture / `:175` derived `unreadCount` / `:187-216` panel header region (banner insertion point).
- `components/ui/BackendGapBanner.tsx:25-29` — `BackendGapBanner({ reason })`, the existing gold AP-2 marker (reused on ~15 fixture surfaces).

**Item 3 anchors:**
- `admin/tenants.py:971-1000` `HITLPolicyUpsertRequest` (+ `@field_validator` `:995`) / `:892-893` `_RISK_ORDER` / `:1010-1039` the PUT handler.

**Baselines (57.123 closeout)**: full pytest **2696+5skip** · wire **24** · Vitest **892** · mockup-fidelity **51** · mypy `src` **0/371** · run_all **10/10**. Re-verify Day-0.

### STALE / drift anchors to re-confirm in the formal Day-0 三-prong (§ checklist 0.1)

(1) **Prong-1 path**: all Item 1/2/3 anchors + the 3 Item-1 test files exist as above; `CHANGE-091-*.md` + design-note `36-*.md` free; NO new src file except the new fixture module (if extracted) + new test files. (2) **Prong-2 content** — the safety linchpins:
- **D-escalate-coverage (⚠️ the central Item-1 safety check)**: enumerate EVERY tool that `PermissionChecker` currently returns non-ALLOW for (dims 1/2/3) and confirm EACH still escalates via `_cat9` after removal — via `escalate_tools` membership OR `risk_level ≥ MEDIUM` OR the new destructive-floor. Specifically: `request_approval` (`hitl_tools.py:87` ALWAYS_ASK — is it HIGH-risk OR must it be added to `escalate_tools`?); each `destructive=True` business tool's `risk_level` (those already HIGH are covered twice; LOW/MEDIUM destructive rely on the new floor). Any tool that would LOSE escalation = a regression my change MUST cover (the destructive floor, the risk threshold, or an explicit `escalate_tools` add).
- **D-resolve-risk-callers**: `resolve_tool_risk` callers (`loop.py:548` + any test) — adding an optional `destructive` param is backward-compatible; confirm no positional-arg caller breaks.
- **D-executor-other-callers**: `ToolExecutorImpl` is also built by `echo_tool.py:75` (a self-test) + the subagent child loops (via `make_default_executor`) — confirm removing the permission gate doesn't orphan a non-loop SOLE-gate caller (subagent children run their own `_cat9` since B4/57.110 — so they are covered).
- **D-notif-fixture-source**: confirm `NOTIFS` is a module const in `NotificationsPanel.tsx` (extractable to a shared module) + the panel's mark-read mutates local state only (the derived Topbar badge stays static = acceptable demo, disclosed by the banner).
- **D-backendgapbanner-fidelity**: `BackendGapBanner` uses existing tokens (no new oklch/hex literal) → mockup-fidelity 51 holds when added inside the panel.
(3) **Prong-3 schema**: N/A — NO new table/migration (Item 3 is a Pydantic validator only). (4) Baselines re-verify (pytest 2696+5skip / wire 24 / Vitest 892 / mockup 51 / mypy 0/371 / run_all 10/10). (5) A deterministic real-LLM trigger for a HIGH-risk OR destructive tool for the Item-1 drive-through (per 57.122 `AD-DriveThrough-Deterministic-Tool-Trigger`) — business mode + a targeted prompt, or a permissive-tenant auto-approve scenario; integration tests cover the path deterministically if the LLM trigger is unreliable.

## 1. Sprint Goal

The chat tool-gating path has a SINGLE source of truth — the 57.122 `_cat9`/per-tenant `HITLPolicy` — with the stale `PermissionChecker` shadow gate removed and destructive tools moved into the load-bearing policy path via a `resolve_tool_risk` HIGH-floor (so a destructive tool ESCALATEs and, on approval, actually RUNS — closing the override conflict + the approved-but-fails latent bug). The chrome notifications are honestly labelled DEMO with a single fixture source (no fake unread masquerade). The admin HITL-policy PUT rejects an overlapping `auto >= require` threshold with a 422. Closes `AD-PermissionChecker-Shadow-Gate-Phase58` + `AD-NotificationsPanel-Backend-Feed` + `AD-HITL-Policy-Threshold-Validation`. Proven by: integration tests (escalate→approve→RUN for a destructive tool; no executor re-block) + a real-UI drive-through (Item 1 escalate-then-run / Item 2 DEMO banner visible / Item 3 PUT 422). NO migration / wire (24) / codegen; mockup-fidelity 51 unchanged. CHANGE-091 + design note 36.

## 2. User Stories

- **US-1** (Item 1, contract): 作為 Cat 9 risk resolution，我希望 `resolve_tool_risk` 接受 `destructive` 參數並對 destructive 工具設 HIGH risk floor，以便 destructive 工具在預設 policy 下經 `_cat9` 升級（取代 PermissionChecker 的硬 DENY）。
- **US-2** (Item 1, loop): 作為 loop `_resolve_tool_call_risk`，我希望把 `spec.annotations.destructive` 傳入 `resolve_tool_risk`，以便 destructive 訊號進入 load-bearing 的 per-tenant policy 判斷。
- **US-3** (Item 1, executor): 作為 `ToolExecutorImpl`，我希望移除 `PermissionChecker` gating（保留 schema/dispatch/rate-limit/metrics），以便 `_cat9`/per-tenant policy 成為唯一 tool-gating 真相，不再二次覆蓋。
- **US-4** (Item 1, cleanup): 作為 codebase，我希望刪除 orphaned `permissions.py` + `__init__` 匯出 + 更新 3 個相關測試（測試已移除元件），以便無 stale shadow gate 殘留（Karpathy clean-my-orphans）。
- **US-5** (Item 3): 作為 admin HITL-policy PUT，我希望 `auto_approve_max_risk >= require_approval_min_risk` 回 422，以便誤設的重疊門檻 fail-loud 而非靜默全升級。
- **US-6** (Item 2): 作為 chrome，我希望 NotificationsPanel 顯示可見 DEMO banner + badge 由共用 fixture 來源計算（移除獨立寫死 `FIXTURE_UNREAD_COUNT`），以便假通知誠實標示、不假裝真。
- **US-7** (tests): 作為 platform，我希望測試守住：Item 1（`resolve_tool_risk` destructive floor + `decide_tool_hitl` + loop `_cat9` destructive escalate + executor 無二次 gate）+ Item 3（PUT 422 overlap）+ Item 2（DEMO banner + derived badge）。
- **US-8** (drive-through): 作為 user，我希望真 drive-through：Item 1（destructive/HIGH 工具 escalate→approve→**真的執行**，或 permissive tenant auto-approve→run；非 gate-only）+ Item 3（PUT overlap→422）+ Item 2（bell → DEMO banner 可見）；截圖 + observed-vs-intended。
- **US-9** (closeout): 作為 future dev，我希望 CHANGE-091 + 設計筆記 36（Item 1 HITL gate-consolidation + destructive-floor 語意 + rollback）+ 收尾，以便此安全決策可溯。

## 3. Technical Specifications

### 3.0 Architecture (Item 1 backend Cat 2/9/1 consolidation + Item 3 admin validator + Item 2 FE chrome DEMO; NO migration / wire / codegen)

```
# Item 1 (Cat 9 contract + Cat 1 loop + Cat 2 executor + cleanup)
backend/src/agent_harness/_contracts/hitl.py        (EDIT): resolve_tool_risk += destructive HIGH-floor
backend/src/agent_harness/orchestrator_loop/loop.py (EDIT): _resolve_tool_call_risk passes destructive=spec.annotations.destructive
backend/src/agent_harness/tools/executor.py         (EDIT): remove PermissionChecker import/param/gate (keep schema/dispatch/rate-limit/metrics)
backend/src/agent_harness/tools/permissions.py      (DELETE): PermissionChecker + PermissionDecision (the shadow gate)
backend/src/agent_harness/tools/__init__.py         (EDIT): drop PermissionChecker/PermissionDecision exports
backend/src/agent_harness/_contracts/tools.py       (EDIT): docstring update (PermissionChecker ref); explicit_approval field left + noted
backend/src/business_domain/_register_all.py        (EDIT): docstring "with PermissionChecker" → updated
backend/tests/unit/agent_harness/tools/test_executor.py            (EDIT): remove PermissionChecker/Decision tests
backend/tests/integration/agent_harness/tools/test_builtin_tools.py(EDIT): remove PermissionChecker resolution tests
backend/tests/integration/business_domain/test_business_tools_via_registry.py (EDIT): drop _AllowAllPermissionChecker workaround + permission_checker kwarg
backend/tests/unit/agent_harness/...hitl / loop _cat9 destructive   (NEW/EDIT): destructive-floor + escalate tests
# Item 3 (admin validator)
backend/src/api/v1/admin/tenants.py                 (EDIT): HITLPolicyUpsertRequest @model_validator(after) auto<require → 422
backend/tests/integration/api/admin/...hitl_policies (EDIT/NEW): PUT overlap → 422
# Item 2 (FE chrome DEMO)
frontend/src/components/topbar/notificationsFixture.ts (NEW): shared DEMO_NOTIFICATIONS source (extracted from NotificationsPanel)
frontend/src/components/topbar/NotificationsPanel.tsx  (EDIT): import shared fixture + add BackendGapBanner DEMO banner
frontend/src/components/AppShellV2.tsx                  (EDIT): derive unreadCount from shared fixture; drop FIXTURE_UNREAD_COUNT
frontend/src/i18n/locales/{en,zh-TW}/common.json       (EDIT): + notifications.demoBanner copy
frontend/tests/unit/components/...NotificationsPanel/AppShellV2/Topbar (EDIT/NEW): DEMO banner + derived badge
# docs
claudedocs/4-changes/feature-changes/CHANGE-091-*.md   (NEW)
docs/.../36-hitl-gate-consolidation-destructive-floor.md (NEW design note — Track 1 only)
migrations / events.py / sse.py / codegen / styles-mockup.css: UNTOUCHED
```

### 3.1 Item 1 — `resolve_tool_risk` destructive HIGH-floor (US-1) — `_contracts/hitl.py`

- `resolve_tool_risk(spec_risk, *, rule_requires_approval, destructive=False)`: after the existing `rule_requires_approval` MEDIUM-floor, add: `if destructive: base = max(base, HIGH)` (via `RISK_ORDER`). Rationale (design note 36): destructive ops are the highest-consequence tool calls; flooring to HIGH makes them escalate under the DEFAULT policy (`require_approval_min_risk=MEDIUM`) while still letting a CRITICAL-trusting tenant... no — a HIGH floor means a tenant with `auto_approve_max_risk=HIGH` auto-approves; that is the per-tenant policy being load-bearing (the 57.122 philosophy: the tenant explicitly trusts HIGH). Documented as the deliberate semantic.
- Backward-compatible: `destructive` defaults False → existing callers unchanged.

### 3.2 Item 1 — loop threads destructive (US-2) — `loop.py`

- `_resolve_tool_call_risk` (`:540-548`): `destructive = spec.annotations.destructive if spec is not None else False`; `return resolve_tool_risk(spec_risk, rule_requires_approval=flagged, destructive=destructive)`. The spec is already fetched (`:546`). No other loop change — `_cat9` already calls `_resolve_tool_call_risk` on both PASS and ESCALATE (`:962`).

### 3.3 Item 1 — remove `PermissionChecker` from the executor (US-3) — `executor.py`

- Drop `from .permissions import PermissionChecker, PermissionDecision` (`:87`); drop the `permission_checker` ctor param (`:138`) + `self._permission = …` (`:145`); REMOVE the gate block (`:169-188`) — `execute` flows straight from `registry.get` → `_validate_arguments` → handler dispatch → rate-limit → span (the executor's real, non-duplicated responsibilities). The `ExecutionContext` import stays (still used for the handler-context arity path).

### 3.4 Item 1 — cleanup (US-4) — delete `permissions.py` + exports + tests

- DELETE `agent_harness/tools/permissions.py`.
- `agent_harness/tools/__init__.py`: remove the import (`:37`) + the two `__all__` entries (`:129-130`).
- `_contracts/tools.py:66-67` docstring: replace the "PermissionChecker (Sprint 51.1) consumes this" note with "the loop's `_cat9_tool_check` + per-tenant `HITLPolicy` (Sprint 57.122/57.124) gate tool execution"; the `explicit_approval` field (`:122`) stays (frozen-dataclass field; its sole consumer is removed → note `AD-ExecutionContext-ExplicitApproval-Tidy` as a follow-up, removing a contract field is a separate structural change).
- `business_domain/_register_all.py:197` docstring: drop "with PermissionChecker".
- Tests (testing the REMOVED component — legitimate per Karpathy clean-my-orphans, NOT skip-to-pass): `test_executor.py` remove the `PermissionDecision`/`PermissionChecker` direct-test block (`:376-382` + `:28` import); `test_builtin_tools.py` remove the PermissionChecker resolution tests (`:129,271-275` + `:18` import); `test_business_tools_via_registry.py` drop the `_AllowAllPermissionChecker` subclass (`:59-73`) + the `permission_checker=` kwarg (`:104`) — the workaround is unneeded once the gate is gone. The removed gating behavior is REPLACED by new tests (§3.5) at the authoritative `_cat9`/policy layer.

### 3.5 Item 1 — new tests (US-7, the safety net)

- `resolve_tool_risk` destructive floor: LOW+destructive → HIGH · MEDIUM+destructive → HIGH · HIGH+destructive → HIGH · LOW+non-destructive → LOW (unchanged) · destructive+rule_requires_approval interplay.
- `decide_tool_hitl` end-to-end with a destructive-floored risk under DEFAULT policy → ESCALATE; under a permissive tenant (`auto_approve_max_risk=HIGH`) → auto-approve (policy load-bearing).
- loop `_cat9` integration: a registered destructive LOW-risk tool → `_cat9` ESCALATEs (not auto-run) — the regression guard proving the floor compensates for the removed PermissionChecker dim 3.
- executor: a destructive/HIGH tool now reaches the handler (no "permission denied"/"approval required" error from the executor) — proving the second gate is gone.

### 3.6 Item 3 — admin PUT cross-field validator (US-5) — `admin/tenants.py`

- Add a module-level `_RISK_ORDER`-based check OR reuse the existing `_RISK_ORDER` (`:892`): `@model_validator(mode="after")` on `HITLPolicyUpsertRequest`: `if _RISK_ORDER[auto_approve_max_risk] >= _RISK_ORDER[require_approval_min_risk]: raise ValueError("auto_approve_max_risk must be strictly less than require_approval_min_risk")` → FastAPI maps to 422. (The per-field `@field_validator` already guarantees both are valid `RiskLevel` names before the model validator runs.)
- Test: PUT with `auto=HIGH, require=MEDIUM` → 422; `auto=LOW, require=MEDIUM` → 200 (the existing happy path).

### 3.7 Item 2 — notifications DEMO honesty (US-6) — `NotificationsPanel.tsx` + `AppShellV2.tsx`

- Extract the `NOTIFS` fixture to `components/topbar/notificationsFixture.ts` (`DEMO_NOTIFICATIONS` + the `NotificationItem` type) — the single source for both the panel list and the badge count.
- `NotificationsPanel.tsx`: import `DEMO_NOTIFICATIONS` (replace the inline `NOTIFS`); add a `<BackendGapBanner reason={t("topbar.notifications.demoBanner")} />` at the top of the panel body (additive; panel CSS classes byte-identical; the banner is the existing gold component → no new oklch/hex literal).
- `AppShellV2.tsx`: `import { DEMO_NOTIFICATIONS }`; `const unreadCount = DEMO_NOTIFICATIONS.filter((n) => n.unread).length` (drop the standalone `FIXTURE_UNREAD_COUNT = 3` — the badge now derives from the shared source = 3, but is no longer an independent magic number). The badge stays static across panel mark-read (acceptable DEMO limitation, disclosed by the banner — making it reactive needs state-lifting, out of scope).
- i18n: `topbar.notifications.demoBanner` en ("Demo data — notifications backend not yet wired") + zh-TW ("示範資料 — 通知後端尚未接通").

### 3.8 Drive-through (US-8) — real chrome + real backend + real LLM

1. Clean restart (Risk Class E — backend `loop.py`/`executor.py`/`hitl.py`/`tenants.py` changed; `Win32_Process` PID/PPID/StartTime sweep; confirm the fresh PID is the sole :8000 owner + a startup log line). Vite :3007 (node) NOT stopped.
2. **Item 1** (the load-bearing proof): trigger a destructive OR HIGH-risk tool in chat (business mode + a targeted prompt, e.g. an incident/rootcause action; OR a permissive-tenant scenario via admin PUT `auto_approve_max_risk=HIGH` then a HIGH-risk tool). Observe: under a strict/default policy → ESCALATE (`awaiting_approval`) → APPROVE → the tool **actually executes + returns a result** (NOT a "permission denied"/"approval required" error — proving the executor's second gate is gone). If a reliable LLM trigger is elusive, the deterministic proof is the §3.5 integration tests + an honest note (the path is integration-verified; the UI leg covers whatever tool the LLM reliably calls).
3. **Item 3**: admin Tenant settings → HITL Policies → set `auto=HIGH, require=MEDIUM` → save → **422 with the cross-field message** (not silently saved).
4. **Item 2**: click the topbar bell → the panel opens with the **DEMO banner visible** + the badge count derived from the fixture (still 3, but honest).
5. Screenshots + observed-vs-intended in progress.md. AP-4: Item 2 discloses DEMO; Item 1 proves a real per-tenant-policy gate (not a stale shadow gate).

### 3.9 What is explicitly NOT done

A real notifications backend (table + RLS + feed/poll endpoint — a large greenfield); removing `ExecutionContext.explicit_approval` (a contract structural change → `AD-ExecutionContext-ExplicitApproval-Tidy`); making `PermissionChecker`'s destructive logic configurable per-tenant beyond the HIGH-floor (the per-tenant policy already governs via `auto_approve_max_risk`); a reactive Topbar badge that updates on panel mark-read (state-lifting, out of scope); any migration / new wire event / codegen / `styles-mockup.css` change.

### 3.10 Validation (US-1..US-9)

Gates: mypy strict `src` **0/371** · run_all **10/10** (count 24) · full pytest **2696+5skip ± N** (PermissionChecker tests removed; destructive-floor + 422 tests added — net delta documented) · Vitest **892 + N** (notif DEMO + badge) · mockup-fidelity **51 UNCHANGED** · `diff styles-mockup.css` empty · migrations / events / sse / codegen **UNTOUCHED**. Plus: the §3.5 integration tests prove escalate→approve→RUN for a destructive tool with no executor re-block; the drive-through proves the per-tenant gate is the single source of truth + Item 2 DEMO disclosure + Item 3 422.

## 4. File Change List

| # | File | Action |
|---|------|--------|
| 1 | `backend/src/agent_harness/_contracts/hitl.py` | EDIT — `resolve_tool_risk` += `destructive` HIGH-floor |
| 2 | `backend/src/agent_harness/orchestrator_loop/loop.py` | EDIT — `_resolve_tool_call_risk` passes `destructive=spec.annotations.destructive` |
| 3 | `backend/src/agent_harness/tools/executor.py` | EDIT — remove `PermissionChecker` import/param/gate (keep schema/dispatch/rate-limit/metrics) |
| 4 | `backend/src/agent_harness/tools/permissions.py` | **DELETE** — the stale shadow gate |
| 5 | `backend/src/agent_harness/tools/__init__.py` | EDIT — drop `PermissionChecker`/`PermissionDecision` exports |
| 6 | `backend/src/agent_harness/_contracts/tools.py` | EDIT — docstring update; `explicit_approval` field left + AD-noted |
| 7 | `backend/src/business_domain/_register_all.py` | EDIT — docstring "with PermissionChecker" removed |
| 8 | `backend/src/api/v1/admin/tenants.py` | EDIT — `HITLPolicyUpsertRequest` `@model_validator` auto<require → 422 |
| 9 | `backend/tests/unit/agent_harness/tools/test_executor.py` | EDIT — remove PermissionChecker/Decision tests |
| 10 | `backend/tests/integration/agent_harness/tools/test_builtin_tools.py` | EDIT — remove PermissionChecker resolution tests |
| 11 | `backend/tests/integration/business_domain/test_business_tools_via_registry.py` | EDIT — drop `_AllowAllPermissionChecker` + `permission_checker=` kwarg |
| 12 | `backend/tests/unit/agent_harness/_contracts/test_hitl_decision.py` (or existing) | EDIT/NEW — `resolve_tool_risk` destructive floor + `decide_tool_hitl` |
| 13 | `backend/tests/integration/.../test_loop_hitl_policy.py` (or existing _cat9 test) | EDIT/NEW — destructive LOW-risk tool → `_cat9` ESCALATE |
| 14 | `backend/tests/integration/api/admin/test_*hitl_policies*.py` | EDIT/NEW — PUT overlap → 422 |
| 15 | `frontend/src/components/topbar/notificationsFixture.ts` | NEW — shared `DEMO_NOTIFICATIONS` source |
| 16 | `frontend/src/components/topbar/NotificationsPanel.tsx` | EDIT — import shared fixture + `BackendGapBanner` DEMO banner |
| 17 | `frontend/src/components/AppShellV2.tsx` | EDIT — derive `unreadCount` from shared fixture; drop `FIXTURE_UNREAD_COUNT` |
| 18 | `frontend/src/i18n/locales/en/common.json` | EDIT — + `topbar.notifications.demoBanner` |
| 19 | `frontend/src/i18n/locales/zh-TW/common.json` | EDIT — + `topbar.notifications.demoBanner` |
| 20 | `frontend/tests/unit/components/topbar/NotificationsPanel.test.tsx` | EDIT/NEW — DEMO banner present |
| 21 | `frontend/tests/unit/components/AppShellV2.test.tsx` (or Topbar badge test) | EDIT/NEW — badge derives from shared fixture |
| 22 | `claudedocs/4-changes/feature-changes/CHANGE-091-hitl-gate-consolidation-bundle.md` | NEW — change record (3 tracks + drive-through) |
| 23 | `docs/03-implementation/agent-harness-planning/36-hitl-gate-consolidation-destructive-floor.md` | NEW — design note (Track 1 only; 8-pt gate) |
| — | migrations / `events.py` / `sse.py` / codegen / `styles-mockup.css` | **UNTOUCHED / NONE** |

## 5. Acceptance Criteria

1. **Item 1**: `PermissionChecker` deleted; the executor no longer permission-gates; `_cat9`/per-tenant `HITLPolicy` is the single tool-gating source. `grep -rn "PermissionChecker\|PermissionDecision" backend/src` → 0 hits.
2. **Item 1 safety**: `resolve_tool_risk` floors destructive → HIGH; a destructive LOW-risk tool ESCALATEs via `_cat9` under the default policy (integration test); a permissive tenant (`auto_approve_max_risk=HIGH`) auto-approves it (policy load-bearing); an approved destructive/HIGH tool RUNS through the executor (no second-gate error).
3. **Item 1 coverage (Day-0 D-escalate-coverage)**: every tool `PermissionChecker` previously non-ALLOW'd still escalates via `escalate_tools` OR risk-threshold OR the destructive floor — documented in progress.md (no silent loss of escalation).
4. **Item 3**: PUT `auto >= require` → 422 with a clear message; `auto < require` → 200.
5. **Item 2**: the NotificationsPanel shows a visible DEMO `BackendGapBanner`; the Topbar badge derives from `DEMO_NOTIFICATIONS` (the standalone `FIXTURE_UNREAD_COUNT` is gone); `grep "FIXTURE_UNREAD_COUNT" frontend/src` → 0 hits.
6. Gates: mypy 0/371 · run_all 10/10 (count 24) · pytest 2696+5skip ± documented delta · Vitest 892 + N · mockup-fidelity 51 unchanged · `diff styles-mockup.css` empty · migrations/events/sse/codegen UNTOUCHED.
7. Real drive-through PASS (live, NOT gate-only): Item 1 escalate→approve→RUN (or integration-test-backed + honest UI note) · Item 3 PUT 422 · Item 2 DEMO banner visible; screenshots + observed-vs-intended.
8. `AD-PermissionChecker-Shadow-Gate-Phase58` + `AD-NotificationsPanel-Backend-Feed` + `AD-HITL-Policy-Threshold-Validation` shipped; CHANGE-091 + design note 36; calibration recorded (`mixed-multidomain-bundle` 0.65, parent-direct `agent_factor` 1.0); navigators + next-phase-candidates updated.

## 6. Deliverables

- [ ] US-1 `resolve_tool_risk` destructive HIGH-floor (`_contracts/hitl.py`)
- [ ] US-2 loop `_resolve_tool_call_risk` threads `destructive`
- [ ] US-3 executor drops `PermissionChecker` gating (keeps schema/dispatch/rate-limit/metrics)
- [ ] US-4 delete `permissions.py` + exports + update the 3 PermissionChecker test files + `tools.py`/`_register_all.py` docstrings
- [ ] US-5 admin PUT cross-field `@model_validator` (auto<require → 422) + test
- [ ] US-6 NotificationsPanel DEMO banner + shared fixture + derived badge (drop `FIXTURE_UNREAD_COUNT`) + i18n
- [ ] US-7 new tests (destructive floor + `decide_tool_hitl` + loop `_cat9` escalate + executor-no-second-gate + PUT 422 + notif DEMO/badge)
- [ ] US-8 drive-through PASS (Item 1 escalate→approve→RUN / Item 3 422 / Item 2 DEMO banner; screenshots + observed-vs-intended)
- [ ] US-9 CHANGE-091 + design note 36 + closeout (retro Q1-Q7 + calibration + navigators + next-phase-candidates)

## 7. Workload Calibration

- Scope class **`mixed-multidomain-bundle` 0.65** (3 independent tracks: Cat 2/9/1 backend HITL gate consolidation + a destructive-floor semantic + a delete-with-test-update + an admin validator + a FE chrome DEMO honesty). Per the matrix 3-sprint mean (~0.8-0.9, latest 57.107 ≈0.8-0.9 IN band) — KEEP 0.65.
- **Agent-delegated: no** (parent-direct; Item 1 is a precise safety change — the shadow-gate removal + destructive floor + the escalate-coverage enumeration are best hand-authored and self-verified; Item 2/3 are small). `agent_factor` 1.0 → 3-segment form.
- Bottom-up est ~9.0 hr (Day-0 三-prong + escalate-coverage enumeration ~1.0 · hitl.py floor + loop thread ~0.75 · executor remove + permissions.py delete + exports + tools.py/register docstrings ~1.0 · update 3 PermissionChecker test files ~1.0 · new Item-1 tests ~1.5 · Item 3 validator + test ~0.75 · Item 2 fixture extract + banner + badge + i18n + tests ~1.5 · drive-through ~1.25 · CHANGE-091 + design note 36 + closeout ~1.5) → class-calibrated commit ~5.85 hr (mult 0.65). Day-4 retro Q2 verifies (`mixed-multidomain-bundle` data point; flag if the Item-1 escalate-coverage or the drive-through trigger over-runs).

## 8. Dependencies & Risks

| Risk | Mitigation |
|------|------------|
| **D-escalate-coverage (⚠️ central Item-1 safety; Day-0)**: removing `PermissionChecker` could silently drop escalation for a tool that was only gated by its dim 1/2/3 (e.g. a LOW-risk destructive tool not in `escalate_tools`; `request_approval` ALWAYS_ASK) | Day-0 enumerate every non-ALLOW tool + confirm each still escalates via `escalate_tools` OR risk≥MEDIUM OR the destructive floor; the destructive HIGH-floor is the compensating change; if `request_approval` is neither HIGH nor destructive, add it to `CHAT_HITL_ESCALATE_TOOLS` (its purpose IS to escalate). Document the coverage table in progress.md |
| **Item-1 drive-through needs a HIGH/destructive tool the LLM reliably calls** (per 57.122 `AD-DriveThrough-Deterministic-Tool-Trigger`) | prefer a permissive-tenant scenario (admin PUT `auto_approve_max_risk=HIGH` → a HIGH-risk tool auto-approves+runs, previously re-blocked) OR business mode + a targeted incident/rootcause prompt; the §3.5 integration tests are the deterministic backbone; label the UI leg honestly (integration-verified path + whatever the LLM reliably triggers) |
| Removing `PermissionChecker` orphans `ExecutionContext.explicit_approval` (sole consumer) | leave the frozen-dataclass field (harmless forward-compat), update the `tools.py` docstring, note `AD-ExecutionContext-ExplicitApproval-Tidy` — removing a contract field is a separate structural change, out of this surgical scope |
| Deleting tests of `PermissionChecker` looks like "skip-to-pass" (Never-Delete-Tests rule) | these test a DELIBERATELY-removed component (Karpathy clean-my-orphans); the gating BEHAVIOR is re-covered by the new `_cat9`/policy-layer tests (§3.5) at a higher, authoritative level — document the 1:1 behavior-coverage mapping in the retro |
| A non-loop SOLE-gate caller of `ToolExecutorImpl` relied on `PermissionChecker` | Day-0 `D-executor-other-callers`: `echo_tool.py:75` is a self-test; subagent children run their own `_cat9` (B4/57.110) → covered; no production sole-gate path |
| Item 2 DEMO banner inside the verbatim-mockup `NotificationsPanel` risks a mockup-fidelity regression | the banner is the EXISTING `BackendGapBanner` (additive, like FIX-029/030 page banners); panel CSS classes byte-identical; `diff styles-mockup.css` empty + `check:mockup-fidelity` 51 in the gate; no new oklch/hex literal |
| Item 2 badge non-reactive to panel mark-read (derived from a static source) | acceptable DEMO limitation, disclosed by the banner; a reactive badge needs state-lifting (out of scope, noted) |
| `pytest` count moves both ways (PermissionChecker tests removed + new tests added) | document the exact net delta in the retro (removed N, added M); the gate asserts the final number, not a monotonic increase |
| Item 3 `@model_validator` ordering vs `@field_validator` | the field validators run first (guarantee valid RiskLevel names) → the model validator can safely index `_RISK_ORDER`; test both 422 (overlap) + 200 (valid) |
| **Risk Class E** — a stale `--reload` backend serves old gating code (this sprint changes `loop.py`/`executor.py`/`hitl.py`/`tenants.py`) | clean restart before the drive-through (`Win32_Process` PID/PPID/StartTime sweep — kill orphan spawn-workers holding :8000 via SO_REUSEADDR); confirm the fresh PID is the sole owner; capture a startup log line; probe a tool call before trusting the gate behavior |
| Vite HMR serves stale FE during the drive-through | hard-reload the browser; do NOT stop the Vite/node process (user constraint — node also runs Claude Code) |

## 9. Out of Scope (this sprint; → separate slices / ADs)

- **A real notifications backend** (table + RLS + feed/poll/SSE endpoint) — a large greenfield; `AD-NotificationsPanel-Backend-Feed` is honest-labelled now, wired later.
- **Removing `ExecutionContext.explicit_approval`** — a contract structural change (`AD-ExecutionContext-ExplicitApproval-Tidy`).
- **Per-tenant-configurable destructive policy beyond the HIGH-floor** — the per-tenant `HITLPolicy` already governs via `auto_approve_max_risk`.
- **A reactive Topbar unread badge** (updates on panel mark-read) — state-lifting, deferred.
- **`PermissionChecker`'s annotation dimensions (`open_world` etc.) beyond `destructive`** — not gated today; not introduced.
- Any migration / new wire event / codegen / SSE / `styles-mockup.css` change (count 24 unchanged).
