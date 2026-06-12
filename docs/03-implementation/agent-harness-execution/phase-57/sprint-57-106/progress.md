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
