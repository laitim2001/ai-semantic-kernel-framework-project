# Sprint 57.106 Progress — C3 per-tenant harness policy 面 + risky-action detector

[Plan](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-106-plan.md) · [Checklist](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-106-checklist.md)

---

## Day 0 — 2026-06-12 — Three-prong plan-vs-repo verify ✅ GO

**Baseline**: `main` HEAD `7e358a6a` (post-#280 RBAC-wiring merge). Branch `feature/sprint-57-106-harness-policy` created.

### Drift findings

| ID | Finding | Implication |
|----|---------|-------------|
| D1 | Integration-suite naming precedent is `test_admin_tenant_model_policy.py` (plan §4 #8 said `test_admin_harness_policy.py`). | New suite named **`test_admin_tenant_harness_policy.py`** (mirror exact). Plan file list NOT silently rewritten (audit-trail rule); this entry is the record. |
| D2 | env `chat_verification_judge_template` accepts a template NAME **or a raw `{output}` string** (config docstring :117-124) — broader than recon claimed. | Per-tenant override stays **NAME-only** (deliberate tightening vs env; prompt-injection + size risk). Asymmetry documented in CHANGE-073 + note 28. |
| D3 | `python_sandbox` spec today: `hitl_policy=AUTO`, `destructive=False`, `risk_level=MEDIUM` (`exec_tools.py:27-70`) — arbitrary code executes with ZERO approval. `code` arg confirmed (required string). | Detector adds a real gate; spec itself untouched (detector is orthogonal, chain-level). |
| D4 | `ToolCall = {id: str, name: str, arguments: dict[str, Any]}` (`_contracts/chat.py:67-72`, flat — no nesting); loop passes per-call `tc` via singular `check_tool_call` (`loop.py:876`); `batch_check_tool_calls` is NOT used by the loop. | Detector reads `content.name` / `content.arguments` (mirror ToolGuardrail's content handling). Nested-shape rule satisfied by reading the body. |
| D5 | `TenantSettingsView.tsx` needs THREE edits, not one: `TabId` union (:56) + `TAB_ITEMS` (:58-66) + the tab-router switch — same file. | §4 #11 covers; micro-scope note. |
| D6 | `Tenant.meta_data` alias is a MULTI-LINE `mapped_column(\n "metadata", ...)` (`identity.py:139-140`, also :249-250) — the single-line Prong-3 grep pattern missed it first pass. | No raw SQL in this slice (ORM update mirrors C1) → no impact; catalogued for the physical-column rule's grep pattern (add `-A 1` next time). |
| D7 | Prong 2.5: `ModelPolicyTab.tsx` mirror source is CLEAN — 0 shadcn-utility residue; 7 inline `style={{` sites are lint-compliant escapes. | Mirror-copy inherits compliance. |
| D8 | `engine.register` appends duplicates on re-register (docstring: caller dedupes); chains are built fresh per session in the handler (:465-500). | Detector registered once per session build — no dedupe risk. |
| D9 | `grep harness_policy backend/src` = 0 hits. | JSONB key name free. |

### Anchors re-verified (all ✓)

handler.py `:163/:173/:184/:196` 4 frozensets + `:460-467` PermissionRule-from-frozenset + `:480/:488/:498` registrations + `:510-515` verifier registry + escalate flag into loop ctor · config 3 fields `:116/:124/:132` (mode default **"enabled"**) · router.py `:238` resolve site + `:111` import · tenants.py `:1474-1605` (schemas/validate/PUT/audit/invalidate/GET) · `TAB_ITEMS` 7 tabs · 5 template filenames exact · engine register/priority/fail-fast (`engine.py:86-117`) + `check_tool_call` (`:154-161`) · `KeywordEscalationGuardrail` ctor pattern (`escalation_keyword_detector.py:48-80` — frozenset-in-ctor + `_extract_text`, the detector's mirror).

### Go/no-go

**GO** — scope shift ≈ 0 (D1/D5 naming + micro-edits; D2-D4 confirm the design; D3 strengthens the detector's rationale).

---

## Day 1 — 2026-06-12 — Backend core: resolver + detector (US-1/US-3) ✅

- **`harness_policy.py`** (NEW, platform_layer/governance): `HarnessPolicy` frozen value object — 9 sparse fields with a deliberate tri-state (`None` = not-set/use-default vs `()` = explicit off-override, e.g. `escalate_tools: []` turns the default escalate list OFF); `_HarnessPolicyCache` (TTL 60s, injectable clock) + `resolve_tenant_harness_policy` (fail-open) + invalidate + reset — byte-pattern mirror of `model_policy.py`. Value object lives in-file (NOT adapters/_base — it's a governance concern, not provider-related; ModelPolicy's adapters home was provider-specific).
- **`risky_action_detector.py`** (NEW, Cat 9 TOOL chain): 9 builtin word-bounded deny patterns over the sandbox `code` arg + tenant `extra_patterns` over ANY tool's serialized args → ESCALATE (never BLOCK; risk HIGH); invalid hand-written tenant pattern skipped defensively (the PUT validates, but meta_data can be hand-edited); exported via `tool/__init__.py`.
- **Unit tests**: 38/38 (policy 22 + detector 16) — incl. near-miss cleans proving the `\b` + `(` anchoring (`evaluate(` / `execute_query(` / `list.remove` do NOT fire).
- Gates: mypy `src` **0/359** (+2 files) · flake8/black/isort clean (3 E501 Purpose-line trims — the MHist char-budget lesson applies to Purpose lines too) · `run_all` 10/10 (`check_cross_category_import` green — detector imports no platform_layer; `check_event_schema_sync` unchanged).

---

## Day 2 — 2026-06-12 — Handler/router wiring + admin PUT/GET (US-2/US-4 backend) ✅

### Drift finding

| ID | Finding | Implication |
|----|---------|-------------|
| D10 | The 4 escalate frozensets (`CHAT_HITL_ESCALATE_*`) are referenced BY NAME in 2 unrelated modules' comments (`note_tool.py:9`, `_register_all.py:247`). | Deviation from plan §3.2's cosmetic `_DEFAULT_*` rename: KEPT the names as the system-default values (renaming would churn 2 unrelated files' comments — surgical-changes rule). The policy-sourcing reads `frozenset(policy.X) if policy.X is not None else <NAME>`. No behavior change; the names ARE the defaults. |

### Work

- **`handler.py`**: `build_real_llm_handler` + `build_handler` gain `harness_policy` param; a resolved-values block computes `escalate_{tools,input,between,output}` (tri-state: `None`→default, `()`/values→override), `verification_{mode,template,escalate_on_max}` (template NAME-validated via `list_templates()` — a hand-edited bad name falls back to the env default instead of crashing `load_template`), and registers `RiskyActionDetector(priority=8)` unless `risky_action_enabled is False`.
- **`router.py`**: `resolve_tenant_harness_policy` resolved pre-handler (mirror C1 line 238) + threaded.
- **`templates/__init__.py`**: NEW `list_templates()` — single-source template-NAME allow-list shared by the handler (fallback) + the PUT (422).
- **`tenants.py`**: `HarnessPolicyUpsertRequest/Response` + `PUT`/`GET /{id}/harness-policy` + `_validate_harness_policy` (422: bad mode / unknown template / non-compiling regex / >20 patterns / >200-char) + audit + cache-invalidate — byte-pattern mirror of model-policy.
- **conftest.py**: `HARNESSPOL_PUT_%` committed-row sweep + `reset_harness_policy_cache()` at both reset points (Risk Class C).
- **Tests**: 17 integration (auth/404 · persistence/composite-replace/`[]`-off/clear · 5 validation poles · isolation · audit · GET). Byte-identical proof: chat handler/router + guardrail suites **506 passed UNCHANGED**.
- Gates: mypy 0/359 · flake8 clean · run_all 10/10 · full pytest **2438 passed + 4 skip**.

### Pre-existing flake (NOT a C3 regression)

`tests/unit/business_domain/incident/test_service.py::test_create_returns_incident` failed ONCE in the full-suite run but **passes isolated (1/1) and in its own file (12/12)**; `git diff main...HEAD` touches **zero** incident files; the conftest I edited is `tests/integration/api/` (a different tree from the failing `tests/unit/business_domain/incident/`). It's a full-suite ordering interaction (some earlier test's global state — Risk Class C class), pre-existing and out of C3 scope. Logged, not chased.

---
