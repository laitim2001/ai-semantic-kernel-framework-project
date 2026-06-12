# Sprint 57.110 — Checklist (B4: subagent child governance — tenant-resolved Cat 9 engine into BOTH child loops + `GuardrailTriggered` relay visibility + spawn failure policies FAIL_FAST/SOFT/PARTIAL per-tenant — child verifier deferred)

[Plan](./sprint-57-110-plan.md)

---

## Day 0 — Plan-vs-Repo Verify + Branch

### 0.1 Three-prong Day-0 verify (against `main` HEAD `220ed587`) — DONE, catalogued in progress.md D1-D13
- [x] **Prong 1 — path verify**: EDIT files Glob-1 (`handler.py` / `_contracts/subagent.py` / `subagent/modes/fork.py` / `subagent/modes/teammate.py` / `subagent/tools.py` / `subagent/dispatcher.py` / `platform_layer/governance/harness_policy.py` / FE `chatStore.ts` + `InspectorTree.tsx` exact paths / `17-cross-category-interfaces.md` / design note `20-subagent-child-loop-design.md`); test suites pinned (8 subagent files + harness_policy tests + InspectorTree Vitest); **test-file basename pre-check** (Glob every NEW test basename across the whole test tree — 57.109 D-DAY1-2 collision lesson); NO new src files expected EXCEPT possibly the `SubagentFailureEscalation` error type location
- [x] **Prong 2 — content verify** (D1 engine composition HITL-conditional / D4 output-ESCALATE child no-op / D5 hardcoded budget + no LLM budget args / D6 FATAL mirror / D7 `_register_all.py` threading / D8 partial-salvage feasible + `empty_response` honest-label fix / D9 teammate mirror / D11 FE pins zero-codegen / D12 threading order / D13 PUT seam) (the plan §0 STALE anchors, ALL of): exact engine COMPOSITION lines in handler.py after `:528` (C3 keyword guardrails + RiskyActionDetector additions — the child must capture the COMPOSED instance) · engine chain statelessness · OUTPUT-gate ESCALATE fallback when hitl absent (:1511 region) · child `is_final_answer` output-gate firing semantics · GUARDRAIL_BLOCKED child run → which `SubagentResult.error` string · default `SubagentBudget` construction site for chat (tools.py vs dispatcher — the failure-policy threading point) · `task_spawn` ToolSpec budget args (LLM-controllable `max_duration_s`?) · `TeammateExecutor` catch sites shape · Cat 8 FATAL classification path for tool-handler raises (`RateLimitExceededError` precedent — pin the mirror for `SubagentFailureEscalation`; MUST NOT retry) · `_drive` partial-content retention (FAIL_PARTIAL salvage feasibility) · sse serializer generic over inner LoopEvent (GuardrailTriggered rides the wrapper?) · `chatStore` inner routing + `childTurnLabel` switch location (57.103 message_injected mirror) · harness_policy PUT-side field validation shape (422 seam) · HANDOFF child = full session boot (out-of-scope confirm) · 17.md current HarnessPolicy/SubagentBudget rows · baselines re-verify (pytest 2485 / wire 24 / Vitest 836 / mockup-fidelity 51)
- [x] **Prong 3 — schema verify**: N/A (no DB / no migration — harness_policy is meta_data JSONB, 57.106 infrastructure) — recorded explicitly
- [x] **Catalog drift** findings in progress.md Day 0 (D1-D13 + implications; plan §8 cross-ref)
- [x] **Go/no-go**: GO — D5/D7 file-list adjustment <10%; D4 narrows output semantics (test-pinned, dt unaffected); D8 adds in-scope honest-label fix

### 0.2 Branch
- [x] `git checkout -b feature/sprint-57-110-subagent-child-governance` (from `main` `220ed587`)

---

## Day 1 — Backend: child engine injection (US-1)

### 1.1 Engine injection (US-1)
- [ ] **`handler.py`**: `_make_child_loop` + `_make_teammate_child_loop` pass `guardrail_engine=<composed engine>` (closure capture; factory aliases unchanged); MHist 1-line
- [ ] **Injection identity tests ×2**: the child loop's engine IS the parent's composed instance (FORK + TEAMMATE)
- [ ] **Fail-closed pins**: child input-block before any LLM call → `SubagentResult success=False` · tool-gate block → error ToolResult + child continues · ESCALATE-in-child → NO pause checkpoint + NO pending_approval · default-guardrails-active-in-child (the intentional behavior change pin)
  - DoD: existing 8 subagent suites green UNCHANGED (0 del); `loop.py` diff EMPTY ✓; mypy strict 0 ✓

---

## Day 2 — Backend: relay visibility + failure policies (US-2 + US-3)

### 2.1 GuardrailTriggered relay + FE label (US-2)
- [ ] **`fork.py`**: `_TAO_CHILD_EVENT_TYPES` += `GuardrailTriggered` (additive; subset otherwise locked); MHist 1-line
- [ ] **FE**: `chatStore` inner `guardrail_triggered` routing (if not generic already) + `InspectorTree.childTurnLabel` case; Vitest +N (label + routing)
  - DoD: relay unit test extends (child guardrail event tagged + forwarded); wire count 24 unchanged + no codegen diff (run_all event-schema check) ✓; Vitest green ✓

### 2.2 Failure policies (US-3)
- [ ] **`_contracts/subagent.py`**: `SubagentFailurePolicy` Literal + `SubagentBudget.failure_policy: str = "fail_soft"` (frozen, defaulted); MHist 1-line
- [ ] **`fork.py` / `teammate.py`**: catch sites honor `fail_partial` (salvage last assistant text into `summary`, keep `error`, `metadata["failure_policy"]`); `fail_soft` byte-identical
- [ ] **`tools.py`**: task_spawn handler — `fail_fast` + `success=False` → raise `SubagentFailureEscalation` (FATAL-classified per Day-0 pin; NO retry / NO re-spawn)
- [ ] **`harness_policy.py`**: `HarnessPolicy` += `subagent_failure_policy: str | None = None` tri-state + parse + PUT-side literal validation (invalid → 422); threading in handler.py to the budget-default site (per Day-0)
- [ ] **Tests ADD**: budget field default + Literal · fail_partial salvage · fail_fast raise + FATAL + exactly-ONE-spawn pin · tri-state resolution (None → soft) · PUT 422 · chat-path integration (spawn → child-block → soft continuation)
  - DoD: full pytest +N (0 del) vs 2485; run_all 10/10; 17.md HarnessPolicy + SubagentBudget rows updated ✓

---

## Day 3 — Full gates + drive-through (US-4) + CHANGE-077

### 3.1 Full gate sweep
- [ ] mypy strict 0 · black/isort/flake8 0 (all four — 57.107 lesson) · run_all 10/10 from repo root (count 24; no codegen diff) · full pytest +N (0 del) · Vitest +N vs 836 · mockup-fidelity 51 holds · `loop.py` diff EMPTY · wire schema diff empty

### 3.2 Drive-through (US-4 — real UI :3007 + fresh no-reload backend + real Azure; zero dev-login; Risk Class E clean restart + `Win32_Process` orphan sweep; policy set via the C3 admin tab, NOT env hacks)
- [ ] **Leg A (soft default)**: tenant harness_policy escalate-input phrase → ask the parent to spawn a child whose task carries the phrase → child input gate BLOCKs (no child LLM call) → Inspector Tree child row shows the guardrail fire → parent continues + final answer honestly reflects the child failure
- [ ] **Leg B (fail_fast)**: same tenant flips `subagent_failure_policy="fail_fast"` (admin PUT; cache invalidation per C3) → same spawn → run terminates via the FATAL path (no re-spawn; loop error surface visible in UI) — flip back after
- [ ] **Non-regression probe**: a normal spawn (no phrase) under default policy → child runs + completes as before (57.102-shape Tree)
- [ ] Screenshots + run snapshot in `sprint-57-110/artifacts/` (never-commit) + observed-vs-intended table in progress.md
  - DoD: ALL legs PASS; no lingering policy state (fail_fast flipped back; phrases removed)

### 3.3 CHANGE-077
- [ ] `claudedocs/4-changes/feature-changes/CHANGE-077-subagent-child-governance-failure-policies.md` (1-page; spike design note NOT required — design note 20 continuation, §5.5 NOT-apply; note 20 §5 deferred pair → RESOLVED edit instead)

---

## Day 4 — Closeout

### 4.1 Closeout
- [ ] retrospective.md Q1-Q7 + calibration (NEW `subagent-child-governance` 0.55 1st data point; agent-delegated: no) + progress.md final
- [ ] Design note 20 §5 edit: `AD-Subagent-Child-Governance` + failure-policies rows → RESOLVED (depth>1 + child verifier stay open); MHist 1-line
- [ ] Navigators: CLAUDE.md Current-Sprint row + Last-Updated; MEMORY.md quality pointer + memory subfile; next-phase-candidates (closes proposal §2.5 B4; B-family 4/4 done; remaining slice = optional A3); sprint-workflow matrix NEW row
- [ ] PR (push + open on user authorization)
