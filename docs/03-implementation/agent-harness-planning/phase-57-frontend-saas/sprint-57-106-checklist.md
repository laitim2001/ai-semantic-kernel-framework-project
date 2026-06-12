# Sprint 57.106 — Checklist (C3 per-tenant harness policy 面 + risky-action detector: `meta_data["harness_policy"]` + TTL resolver + handler wiring + `RiskyActionDetector` + admin PUT/GET + "Harness Policy" tab → two-tenant drive-through)

[Plan](./sprint-57-106-plan.md)

**Status**: 🚧 Day 0 ✅ GO — Day 1 next
**Branch**: `feature/sprint-57-106-harness-policy`

---

## Day 0 — Plan-vs-Repo Verify + Branch ✅

### 0.1 Three-prong Day-0 verify (against `main` HEAD `7e358a6a`) — DONE, catalogued in progress.md D1-D9
- [x] **Prong 1 — path verify**: NEW files all Glob-0; EDIT files Glob-1; suites pinned — integration naming precedent `test_admin_tenant_model_policy.py` → mine `test_admin_tenant_harness_policy.py` (D1); unit dirs `tests/unit/platform_layer/governance/` + `tests/unit/agent_harness/guardrails/` exist
- [x] **Prong 2 — content verify**: ALL §0 STALE anchors ✓ — handler 4 frozensets `:163/:173/:184/:196` + registrations `:480/:488/:498` + verifier wiring `:510-515` + escalate flag; config 3 fields (mode default "enabled"); router `:238`; tenants.py `:1474-1605`; `TAB_ITEMS` 7; `exec_tools.py:27-70` `code` arg + AUTO/MEDIUM (D3); engine register/priority/fail-fast + `check_tool_call(content)` + loop `:876` singular call (D4); 5 templates exact; **`ToolCall` BODY read**: flat `{id, name, arguments: dict}` (D4); `harness_policy` grep-0 (D9); env judge_template also takes raw string → per-tenant NAME-only is deliberate tightening (D2)
- [x] **Prong 2.5 — FE tree audit**: ModelPolicyTab mirror source CLEAN (0 shadcn residue; 7 lint-compliant inline-style escapes — D7); `TabId` union + tab-router switch need edits too (D5)
- [x] **Prong 3 — schema verify**: no migration; `meta_data` alias confirmed MULTI-LINE `mapped_column("metadata", ...)` `identity.py:139-140/:249-250` (D6 — single-line grep misses; no raw SQL in scope)
- [x] **Catalog drift** in progress.md Day 0 (D1-D9 + implications)
- [x] **Go/no-go**: GO — scope shift ≈ 0

### 0.2 Branch
- [x] `git checkout -b feature/sprint-57-106-harness-policy` (from `main` `7e358a6a`)

---

## Day 1 — Backend core: resolver + detector (US-1 / US-3)

### 1.1 HarnessPolicy value object + resolver (US-1)
- [ ] **`platform_layer/governance/harness_policy.py`**: frozen `HarnessPolicy` (9 sparse fields per plan §3.0) + `_HarnessPolicyCache` (TTL 60s, injectable clock) + `resolve_tenant_harness_policy(db, tenant_id)` (fail-open → empty) + `invalidate_tenant_harness_policy`
  - Mirror `model_policy.py` byte-pattern; file header + MHist per convention
  - DoD: mypy green; unit tests (1.3) green
- [ ] **Risk Class C guard**: autouse reset fixture for the cache singleton (conftest of affected suites)

### 1.2 RiskyActionDetector (US-3)
- [ ] **`agent_harness/guardrails/tool/risky_action_detector.py`**: `guardrail_type=TOOL`; python_sandbox `code`-arg builtin deny-list scan + any-tool `extra_patterns` scan → `GuardrailResult(ESCALATE, reason="risky_action: …")`; `enabled=False` → not registered
  - Builtin list finalized WITH tests (each pattern: hit + near-miss clean case); patterns pre-compiled at ctor
  - DoD: existing `GuardrailTriggered` path only (no event change); category boundaries clean (Cat 9, no platform_layer import)

### 1.3 Unit tests
- [ ] **`test_harness_policy.py`**: TTL expiry / invalidate / fail-open / sparse-field parse / unknown-key tolerance
- [ ] **`test_risky_action_detector.py`**: per-pattern hit / clean pass / extra-pattern hit / disabled passthrough
  - DoD: `pytest tests/unit/platform_layer/governance tests/unit/agent_harness/guardrails -q` green

---

## Day 2 — Wiring + admin write/read (US-2 / US-4 backend)

### 2.1 Handler/router wiring (US-2)
- [ ] **`handler.py`**: 4 frozensets → `_DEFAULT_*` (kept as fallbacks, NOT deleted); `build_real_llm_handler(harness_policy=None)`; phrases/tools/verification sourcing = `policy or default`; `RiskyActionDetector` registered when enabled (priority 8)
  - DoD: NO-policy tenant byte-identical (existing chat/guardrail/verification suites green UNCHANGED — the role-less-pole equivalent)
- [ ] **`router.py`**: `resolve_tenant_harness_policy` pre-handler + thread (mirror C1 `:238` site); echo handler untouched

### 2.2 Admin PUT/GET (US-4 backend)
- [ ] **`tenants.py`**: `HarnessPolicyUpsertRequest/Response` (`extra='forbid'`) + `PUT`/`GET /{tenant_id}/harness-policy` — composite-replace; 422 poles (unknown template name / non-compiling regex / >20 patterns / >200-char pattern); `append_audit("tenant_harness_policy_upsert")` + invalidate; `require_admin_platform_role`
- [ ] **`test_admin_harness_policy.py`** (mirror model-policy suite): PUT→GET round-trip / 422 poles / clear-on-omit / audit row / cache-invalidation observable / cross-tenant isolation (鐵律)
  - DoD: suite green; full pytest 0 deletions

---

## Day 3 — FE tab + full gates + drive-through (US-4 FE / US-5) + CHANGE-073 + note 28

### 3.1 FE tab (US-4)
- [ ] **`HarnessPolicyTab.tsx`** mirror ModelPolicyTab (view/edit/Save/Cancel + 422 inline); list fields as comma/line-separated inputs; service get/put + case mappers; `TAB_ITEMS` 7→8
- [ ] FE Vitest: render / edit / save / 422; `npm run lint && npm run build && npm run check:mockup-fidelity` (no `--silent`)

### 3.2 Full gate sweep
- [ ] `black/isort/flake8` clean · `mypy src` 0 · `python scripts/lint/run_all.py` 10/10 (event count UNCHANGED)
- [ ] full `pytest` green (0 deletions) · FE Vitest green · mockup-fidelity 53
- [ ] `loop.py` / DB / migration / wire schema diff = 0

### 3.3 Drive-through (US-5 — two tenants, NO dev-login) — must PASS
- [ ] Clean restart (Risk Class E): fresh no-reload uvicorn sole :8000 + startup log; Vite :3007
- [ ] Tenant A (`dt57105-rbac` founder, password-login): Harness Policy tab → set `escalate_tools:[<real tool>]` + `risky_action_enabled:true` → **PUT 200**; 422 pole driven (bad regex inline)
- [ ] Tenant A chat (real LLM): the escalated tool → **HITL approval pause** renders; approve → completes
- [ ] Tenant B (`jamie@acme.com`, no policy): same prompt → **直通** (no pause) — A/B difference proven
- [ ] Risky payload: python_sandbox `os.system` payload → ESCALATE + `GuardrailTriggered` visible; tenant A sets `risky_action_enabled:false` → same payload 直通 (per-tenant off proven)
- [ ] Screenshots (`artifacts/dt57106-*.png`) + observed-vs-intended into progress.md; cleanup: clear policy override
- [ ] (negative) role-less JWT → harness-policy PUT **403**

### 3.4 CHANGE-073 + docs
- [ ] `CHANGE-073-per-tenant-harness-policy.md`
- [ ] design note **28-harness-policy-spike.md** (8-point gate; incl. 專表畢業 evaluation ¶ + detector deny-list rationale)
- [ ] 17.md decision recorded (expected: `HarnessPolicy` platform_layer → N/A per 57.105 D12 precedent; `RiskyActionDetector` rides the existing Guardrail ABC row — confirm)

---

## Day 4 — Closeout

### 4.1 Closeout
- [ ] progress.md Day 0-3 complete (drift catalog + drive-through table)
- [ ] retrospective.md Q1-Q7 (Q2: `config-tiering-model-policy-spike` 0.60 2nd-validation ratio → window)
- [ ] CLAUDE.md Current Sprint + Last Updated (lean) · MEMORY.md pointer + `project_phase57_106_harness_policy.md` subfile (auto-memory dir)
- [ ] next-phase-candidates.md: C3 ✅ + 🆕 `AD-HITL-Policy-ReadSide-Potemkin-Phase58` + next slice **B3** per interleave
- [ ] sprint-workflow.md calibration row update (`config-tiering-model-policy-spike` 2 pt)
- [ ] all checklist items `[x]` or annotated 🚧 (never delete unchecked)
