# Sprint 57.106 Plan — C3 per-tenant harness policy 面 + risky-action detector: the chat handler's hardcoded escalate phrases / escalate-tool list / verification config become tenant-governable via one `meta_data["harness_policy"]` JSONB + TTL resolver + admin PUT/GET + a tenant-settings tab; a NEW Cat 9 TOOL-chain `RiskyActionDetector` (CC bashSecurity's server-side equivalent) screens python_sandbox code patterns, per-tenant switchable

**Status**: Draft (pending user approval)
**Branch**: `feature/sprint-57-106-harness-policy`
**Base**: `main` HEAD `7e358a6a` (post-#280 merge)
**Slice**: harness-deepening Workflow C slice C3 (proposal §3.4; per interleave decision RBAC → **C3** → B3 → UX → C2 → B4)
**Scope decisions (user, 2026-06-12)**: hitl_policies read-side Potemkin → independent AD deferred (NOT folded in); FE tab → INCLUDED (mirror ModelPolicyTab).

---

## 0. Background

C1 (Sprint 57.104) proved the config-tiering pattern: `tenant.meta_data` JSONB + TTL-cached resolver + pricing-validated admin PUT + a tenant-settings tab. C3 widens the policy 面 to the **Cat 9 / Cat 10 knobs the chat handler currently hardcodes**, and lands the **risky-action detector** (proposal: "CC bashSecurity 的 server-side 等價物"), closing the C-class dangerous-command parity gap + cc-parity §7.5 兩項.

### Design decision (one sparse JSONB key; template-NAME override only; detector ESCALATEs, never BLOCKs)

- **One `meta_data["harness_policy"]` key** (sparse; absent field = system default) over per-concern keys or a dedicated table — C1 precedent; 專表畢業 is evaluated in the design note, not built (proposal §3.2: "C3 政策面擴寬時畢業" = evaluate).
- **Verification template override is by NAME only** (must be one of the 5 shipped `verification/templates/*.txt`) — raw-template upload is rejected (prompt-injection + unbounded-size risk; 422 on unknown name).
- **`RiskyActionDetector` returns ESCALATE, not BLOCK** — routes into the EXISTING Cat 9 HITL approval chain (human decides); BLOCK would be a silent denial the user can't appeal. Default ON; tenant can disable (proposal DoD: "可 per-tenant 關閉").
- **Rejected**: per-request DB read of policy (hot-path cost — TTL cache per C1); per-tenant capability_matrix role/tenant_scope/max_calls overrides (only the escalate dimension is in scope); folding the hitl_policies read-side fix (user decision — own AD).

### Ground truth (Day-0 head-start — 3 Explore recon agents, file:line anchors on `main` HEAD `7e358a6a`)

- **Hardcodes to retire into policy** (`api/v1/chat/handler.py`): `CHAT_HITL_ESCALATE_TOOLS = frozenset({"echo_tool"})` (:163) · `CHAT_HITL_ESCALATE_INPUT_PHRASES = frozenset({"approval required"})` (:173) · between-turns `{"checkpoint"}` (:184) · output `{"confidential"}` (:196). Comments at :160 + :171-172 self-describe these as deferred per-tenant policy.
- **Verification config (global env today)**: `chat_verification_mode` / `chat_verification_judge_template` / `chat_verification_escalate_on_max` (`core/config/__init__.py:116/124/132`); read at `handler.py:510-515` (verifier registry) + `:537` (escalate flag into loop ctor). Templates: 5 `.txt` under `agent_harness/verification/templates/` via `load_template()` (`templates/__init__.py:34-52`).
- **C1 mirror pattern**: `platform_layer/billing/model_policy.py` — `_ModelPolicyCache` (TTL 60s) + `resolve_tenant_model_policy(db, tenant_id)` + `invalidate_tenant_model_policy`; router resolves pre-handler at `api/v1/chat/router.py:238`; admin PUT/GET at `api/v1/admin/tenants.py:1527-1605` (validation + composite-replace + `append_audit` + invalidate); FE `ModelPolicyTab.tsx` + `tenantSettingsService.ts:295-358` + `TenantSettingsView.tsx:56-66` (7-tab `TAB_ITEMS`).
- **Guardrail chain**: `GuardrailEngine` fail-fast chains (`guardrails/engine.py:68-182`); `Guardrail` ABC `check(*, content, trace_context) -> GuardrailResult` (`_abc.py:67-78`); actions PASS|BLOCK|SANITIZE|ESCALATE|REROLL (`_abc.py:47-55`); TOOL chain cut point `check_tool_call` / `batch_check_tool_calls` (engine:154-181). `GuardrailTriggered` event EXISTS (`_contracts/events.py:303-307`) — **no new event type**.
- **python_sandbox**: `agent_harness/tools/exec_tools.py:27-97` → `sandbox.py` Docker exec of `python -c <code>` — **zero code-pattern screening today**; risk MEDIUM.
- **RBAC**: `require_admin_platform_role` JWT-claim gate is production-drivable since 57.105 (PR #280) — the C3 admin endpoints + tab are drive-through-able with a real founding admin (the persisted `dt57105-rbac` tenant + `founder@dt57105.test`).

### STALE / drift anchors to re-confirm in the formal Day-0 三-prong (§ checklist 0.1)

All file:line above are from recon on `7e358a6a` and must be re-verified: handler.py :163/:173/:184/:196/:510-515/:537 · config :116-132 · router.py :238 · model_policy.py shape · tenants.py :1473-1605 · TAB_ITEMS :56-66 · exec_tools.py :27-97 · engine.py register/priority semantics · the 5 template filenames · `ToolCall` argument access shape for the detector (Prong-2: read the actual `ToolCall` dataclass body — nested-shape rule).

## 1. Sprint Goal

A tenant governs its own escalate phrases (3 chains), escalate-tool list, and verification mode/template/escalate-on-max via an admin-written `harness_policy`; a new `RiskyActionDetector` screens `python_sandbox` code (+ tenant extra patterns) into the existing HITL approval flow, per-tenant switchable — proven by a two-tenant drive-through (A escalates where B passes through; a risky payload intercepted; the per-tenant off-switch works).

## 2. User Stories

- **US-1**: 作為 platform，我希望有一個 TTL-cached `resolve_tenant_harness_policy(db, tenant_id)`（mirror C1），以便 per-request 取得租戶的 harness policy 而不打热路徑 DB。
- **US-2**: 作為 tenant admin,我希望 escalate phrases / escalate tools / verification mode+template+escalate-on-max 來自我的 policy（缺省回系統預設），以便不同租戶有不同的治理行為。
- **US-3**: 作為 platform，我希望一個 `RiskyActionDetector`（TOOL chain）攔截 python_sandbox 危險代碼模式 + 租戶自訂 patterns 並 ESCALATE 進既有 HITL 審批，以便破壞性操作有人類把關（per-tenant 可關）。
- **US-4**: 作為 platform admin，我希望 `PUT`/`GET /api/v1/admin/tenants/{id}/harness-policy`（422 驗證 + audit + cache invalidation）+ tenant-settings「Harness Policy」tab（mirror ModelPolicyTab），以便用真 UI 治理。
- **US-5**: 作為 reviewer，我希望 drive-through 證明：租戶 A 的工具 ESCALATE / 租戶 B 直通；risky payload 被攔 + per-tenant 關閉後直通——全程真 UI + 真後端 + 真 LLM。

## 3. Technical Specifications

### 3.0 Architecture (resolve-then-thread; loop.py diff 0; no migration; no new event)

```
router (per request): policy = await resolve_tenant_harness_policy(db, tenant_id)   ← mirror router.py:238
  → build_real_llm_handler(..., harness_policy=policy)
      → escalate phrases/tools: policy.X or HARDCODED_DEFAULT (the :163/:173/:184/:196 frozensets become defaults)
      → verifier registry: policy.verification_* or settings.chat_verification_*
      → guardrail engine: + RiskyActionDetector(enabled=policy.risky_action_enabled (default True),
                                                extra_patterns=policy.risky_action_extra_patterns)
loop.py: UNCHANGED (verifier_registry + verification_escalate_on_max are EXISTING ctor params)
```

**Policy shape v1** (all fields optional/sparse): `escalate_input_phrases` / `escalate_between_turns_phrases` / `escalate_output_phrases`: `list[str]` · `escalate_tools`: `list[str]` · `verification_mode`: `"enabled"|"disabled"` · `verification_judge_template`: shipped-template name · `verification_escalate_on_max`: `bool` · `risky_action_enabled`: `bool` · `risky_action_extra_patterns`: `list[str]` (regex, compile-validated at PUT).

### 3.1 Value object + resolver (US-1)

`platform_layer/governance/harness_policy.py` (NEW): frozen `HarnessPolicy` dataclass + `_HarnessPolicyCache` (TTL 60s, injectable clock) + `resolve_tenant_harness_policy` (fail-open → empty policy) + `invalidate_tenant_harness_policy` — byte-pattern mirror of `model_policy.py`. Risk Class C: autouse reset fixture.

### 3.2 Handler wiring (US-2)

`handler.py`: the 4 module frozensets renamed `_DEFAULT_*` (kept as fallback defaults — NOT deleted); `build_real_llm_handler` gains `harness_policy: HarnessPolicy | None = None`; phrase/tool/verification sourcing = `policy-field or default`. Echo handler untouched. `router.py`: one resolve call + threading (mirror C1's).

### 3.3 RiskyActionDetector (US-3)

`agent_harness/guardrails/tool/risky_action_detector.py` (NEW, Cat 9): `guardrail_type=TOOL`, priority 8 (before ToolGuardrail). For `python_sandbox` tool_calls: scan the `code` arg against a conservative builtin deny-list (`os.system` / `subprocess` / `shutil.rmtree` / `eval(` / `exec(` / `__import__` / `socket` — exact list finalized Day 1 with tests); for ANY tool: scan serialized args against tenant `extra_patterns`. Hit → `GuardrailResult(ESCALATE, reason="risky_action: <pattern>")` → existing HITL approval pause. Disabled (`enabled=False`) → not registered (zero-cost off). Emits via the EXISTING `GuardrailTriggered(guardrail_type="tool")` path — no event change.

### 3.4 Admin write/read + FE tab (US-4) + What is explicitly NOT done

Backend (`api/v1/admin/tenants.py`): `HarnessPolicyUpsertRequest`/`Response` (snake_case, `extra='forbid'`) + `PUT`/`GET /{tenant_id}/harness-policy` mirroring model-policy (composite-replace; 422 on unknown template name / non-compiling or oversize regex / non-string lists; `append_audit("tenant_harness_policy_upsert")`; invalidate). FE: `HarnessPolicyTab.tsx` (mirror ModelPolicyTab view/edit + 422 inline) + service get/put mappers + `TAB_ITEMS` 7→8.
**NOT done**: hitl_policies read-side wiring (own AD per user decision) · capability_matrix role/scope/max_calls per-tenant override · raw template upload · per-tenant injection policy (B-family) · 專表 migration (evaluation ¶ in design note only) · 17.md row for `HarnessPolicy` (platform_layer precedent per 57.105 D12 — `RiskyActionDetector` registers under the EXISTING Guardrail ABC row; confirm at Day 4).

### 3.5 Validation (US-1..US-5)

Unit: resolver (TTL/invalidate/fail-open) · detector (each builtin pattern + extra-pattern + clean code passes + disabled) · PUT validation poles. Integration: admin PUT/GET round-trip + 422 poles + cross-tenant isolation (foreign admin token → 404/403 per existing suites' precedent) + handler sources policy (A/B difference at guardrail level). FE Vitest: tab render/edit/save/422. Gates: mypy strict 0 · run_all 10/10 (event count UNCHANGED) · full pytest 0 del · mockup-fidelity 53 · loop.py / DB / migration / wire diff = 0.

## 4. File Change List

| # | File | Action |
|---|------|--------|
| 1 | `backend/src/platform_layer/governance/harness_policy.py` | NEW — value object + TTL resolver + invalidate |
| 2 | `backend/src/agent_harness/guardrails/tool/risky_action_detector.py` | NEW — Cat 9 TOOL guardrail |
| 3 | `backend/src/api/v1/chat/handler.py` | EDIT — policy param + defaults rename + detector registration |
| 4 | `backend/src/api/v1/chat/router.py` | EDIT — resolve + thread (1 call site) |
| 5 | `backend/src/api/v1/admin/tenants.py` | EDIT — schemas + PUT/GET + validation + audit |
| 6 | `backend/tests/unit/platform_layer/governance/test_harness_policy.py` | NEW |
| 7 | `backend/tests/unit/agent_harness/guardrails/test_risky_action_detector.py` | NEW |
| 8 | `backend/tests/integration/api/test_admin_harness_policy.py` | NEW (mirror model-policy suite) |
| 9 | `frontend/src/features/tenant-settings/components/tabs/HarnessPolicyTab.tsx` | NEW (mirror ModelPolicyTab) |
| 10 | `frontend/src/features/tenant-settings/services/tenantSettingsService.ts` | EDIT — get/put + mappers |
| 11 | `frontend/src/features/tenant-settings/components/TenantSettingsView.tsx` | EDIT — TAB_ITEMS 7→8 |
| 12 | FE Vitest for the tab | NEW |
| — | `loop.py` / DB models / migrations / `event_wire_schema` | **UNTOUCHED** |

## 5. Acceptance Criteria

1. Tenant with NO policy → behavior byte-identical to today (defaults; existing suites green unchanged).
2. Tenant A `escalate_tools: ["mock_patrol_check_servers"]` → that tool ESCALATEs for A; tenant B 直通 (proposal §3.5 DoD).
3. Risky payload (`python_sandbox` with `os.system(...)`) → ESCALATE + `GuardrailTriggered`; `risky_action_enabled: false` → passes through.
4. PUT unknown template name / bad regex → 422 inline (tab renders it); valid PUT → audit row + cache invalidated (next chat reflects).
5. All gates green; 0 test deletions; drive-through US-5 PASS with screenshots.

## 6. Deliverables

- [ ] US-1 resolver + US-3 detector + unit tests
- [ ] US-2 handler/router wiring (defaults preserved)
- [ ] US-4 admin PUT/GET + FE tab + Vitest
- [ ] US-5 two-tenant drive-through PASS (screenshots + observed-vs-intended)
- [ ] CHANGE-073 + design note 28 (spike extract — NEW domain: per-tenant harness policy + detector) + 專表畢業 evaluation ¶
- [ ] Closeout (retro Q1-Q7 + calibration + navigators + next-phase-candidates incl. NEW `AD-HITL-Policy-ReadSide-Potemkin-Phase58`)

## 7. Workload Calibration

- Scope class **`config-tiering-model-policy-spike` 0.60 (2nd validation data point)** — C3 is the same config-tiering family shape as C1 (value object + TTL resolver + admin write + tab + per-request wiring), widened by the detector; C1 1st point ran ~0.9-0.95 IN band.
- **Agent-delegated: partial** — backend parent-direct (Cat 9 chain + handler are security-sensitive); FE tab agent-delegated-then-parent-re-verified (57.104 precedent: blended full-stack → no single agent_factor; 3-segment form).
- Bottom-up est ~18 hr (policy+resolver ~2 + handler wiring ~2 + detector ~2.5 + admin ~2 + FE tab ~2.5 + tests ~3 + drive-through ~2 + docs/closeout ~2) → class-calibrated commit ~10.8 hr (mult 0.60). Day 4 retro Q2 verifies.

## 8. Dependencies & Risks

| Risk | Mitigation |
|------|------------|
| Risk Class C — TTL cache singleton across test event loops | autouse reset fixture (model_policy precedent) |
| Risk Class E — stale backend masks wiring | clean no-reload restart + startup log before drive-through |
| Detector false positives (legit code mentions `subprocess`) | conservative builtin list + ESCALATE-not-BLOCK (human can approve) + per-tenant off |
| Regex DoS via `extra_patterns` | PUT-side compile + length cap (e.g. ≤20 patterns × ≤200 chars) |
| Two-tenant drive-through needs 2 real logins | reuse persisted `dt57105-rbac` founder (admin, password-login) + `jamie@acme.com`; NO dev-login |
| `ToolCall` args shape assumption (code arg access) | Day-0 Prong-2 read the `ToolCall` dataclass body (nested-shape rule) |
| Tab count 7→8 layout regressions | mockup-fidelity gate + Vitest tab-list assertion |

## 9. Out of Scope (this sprint; → separate slices / ADs)

- **`AD-HITL-Policy-ReadSide-Potemkin-Phase58`** (NEW, user decision 2026-06-12) — `DBHITLPolicyStore`/`get_policy()` write-side works but is never consumed at tool-execution (ToolGuardrail Stage 3 hardcodes `requires_approval`); risk-threshold semantics redesign = own slice.
- capability_matrix per-tenant override of `role_required` / `tenant_scope` / `max_calls_per_session` (only the escalate dimension ships).
- Raw verification-template upload; per-tenant injection policy (B-family); business-tool destructive-op pattern packs beyond ToolSpec metadata; 專表 `tenant_policies` migration (evaluated in note 28 only); C2 compaction cheap tier (next C slice).
