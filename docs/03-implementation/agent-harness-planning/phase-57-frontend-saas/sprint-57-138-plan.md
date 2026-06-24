# Sprint 57.138 Plan — verification key-condition judge: per-task condition template + A/B accuracy spike

**Summary**: Close `AD-Verification-KeyCondition-PerTask` (research #3 in the canonical order; refines the 57.111 A3 judge). The Cat 10 LLM judge today uses `output_quality.txt` — a GENERIC 5-failure-mode list (refuses / incoherent / empty / off-topic / contradicts-trace) that is structurally BLIND to instruction-following failures (an answer that lists 5 items when "exactly 3" was asked, answers a paragraph when "one word" was asked, omits a required unit — all coherent, on-topic, non-empty → the generic judge PASSES). Research #8's key-condition verifier (EMNLP2024) = extract the per-task must-satisfy conditions, then check each. This **evidence-first thin spike** (same shape as 57.136/57.137): (1) ship a NEW `key_condition.txt` judge template that extracts the request's must-satisfy conditions and checks each (a superset of the generic usability floor), (2) MEASURE with a permanent A/B harness whether key-condition catches instruction-following failures the generic judge misses WITHOUT over-flagging acceptable answers, (3) decide the default by materiality. The selection lever ALREADY EXISTS (`chat_verification_judge_template` setting, 57.106 C3 per-tenant) — adding the template makes it selectable; DEFAULT stays `output_quality` (byte-unchanged). Backend-only, NO loop.py / config / handler / migration / wire / frontend change. A drive-through is MANDATORY (the judge runs on the chat-v2 主流量). A **design note (42)** is required — its headline is the measured generic-vs-key-condition accuracy on instruction-violation cases + the per-task-condition reframe.

**Status**: Draft (user said「可以開始 #8 key-condition verifier → AD-Verification-KeyCondition-PerTask」2026-06-24, following the canonical research §5 ranked order #6→#3→#8→…; awaiting plan approval before Day-0 / code)
**Branch**: `feature/sprint-57-138-verification-key-condition`
**Base**: `main` HEAD `57423a80` (PR #328 — flip 57.137 → MERGED + restore canonical ranked order)
**Slice**: closes `AD-Verification-KeyCondition-PerTask` (research #8; the 3rd item in the canonical order; standalone)
**Scope decisions**: (a) thin spike — MEASURE the generic-vs-key-condition gap on instruction-following cases BEFORE recommending a default flip, mirroring 57.136/57.137's evidence-first pattern; (b) the key-condition mechanism is a **single-call template** (extract conditions → check each → verdict in ONE judge call; Option A), NOT a two-phase extract-then-check (Option B = 2× judge cost + new code → follow-on if A proves value); (c) the template is a **superset** of the generic usability floor (keeps refuses/incoherent/empty/contradicts-trace + adds per-task conditions) so it strictly dominates on the floor categories; (d) DEFAULT stays `output_quality` (the existing `chat_verification_judge_template` setting selects `key_condition`; per-tenant via 57.106 C3) — zero behavior change unless an operator opts in; (e) NO loop.py / config / handler / VerificationResult contract change — the spike rides the existing template-selection wire (verify at Day-0).

---

## 0. Background

### The gap (`AD-Verification-KeyCondition-PerTask`)

- The Cat 10 LLM judge (`LLMJudgeVerifier`) screens the candidate answer against `output_quality.txt` — a fixed list of 5 GENERIC failure modes (refuses / incoherent / empty / off-topic / contradicts-trace), the SAME for every request.
- This is structurally blind to **instruction-following** failures: an answer that violates a precise task constraint (count / format / ordering / unit / inclusion) is still coherent, on-topic, and non-empty → the generic judge PASSES it.
- Research #8 (EMNLP2024 key-condition verifier): the judge should EXTRACT the per-task must-satisfy conditions for THIS request, then check each — turning "is this a usable answer?" into "does this satisfy condition 1, 2, 3?".

### Why it matters (the missing capability)

Enterprise agents are graded on instruction adherence ("list exactly N", "respond in JSON", "sort ascending", "cite the source"). A verifier blind to these passes wrong-shaped answers to the user. The reconciliation assessment rated #8 "partially done / refinable" — the templates are structured but generic; per-task condition extraction is the missing refinement. The spike settles, with numbers, whether key-condition extraction catches instruction-following failures the generic judge misses AND whether it over-flags acceptable answers (the stricter-judge risk), then lets evidence gate whether it becomes the default or stays an opt-in template.

### Root cause (recon code read, file:line; ALL re-verified §checklist 0.1)

| Layer | Reality (on `main` HEAD `57423a80`) | Anchor |
|-------|-------------------------------------|--------|
| generic failure-mode judge | `output_quality.txt` lists 5 generic modes; "When in doubt, pass" / "Default to passed=true" | `verification/templates/output_quality.txt:1-30` |
| judge resolves template by name OR raw | `_build_prompt`: `{output}` in raw → raw; else `load_template(name)`; substitutes `{output}`+`{trace}` | `verification/llm_judge.py:123-139` |
| JSON contract parsed | `passed` (req) + optional `score`/`reason`/`suggested_correction`; fail-closed on parse error | `verification/llm_judge.py:141-187` |
| template selection lever EXISTS | `chat_verification_judge_template: str = "output_quality"` (env `CHAT_VERIFICATION_JUDGE_TEMPLATE`) | `core/config/__init__.py:127` |
| handler resolves name dynamically | reads the setting, resolves vs shipped templates, builds the registry | `api/v1/chat/handler.py:659-679` |
| template enumeration | `load_template(name)` + `list_templates()` | `verification/templates/__init__.py:35-64` |
| A/B harness scaffold to mirror | `benchmark_judge.py` (load_cases / run_judge / build_report / report_to_markdown / _amain / main) + golden fixture + CI-safe unit | `scripts/benchmark_judge.py:73-349` + `tests/fixtures/verification/judge_benchmark.yaml` + `tests/unit/scripts/test_benchmark_judge.py` |

→ The fix must (1) add a `key_condition.txt` template that extracts per-task conditions + checks each (superset of the generic floor; same JSON contract + `{trace}`/`{output}` placeholders), (2) MEASURE generic-vs-key-condition accuracy on an instruction-following fixture with a permanent A/B harness, (3) verify the template is selectable via the EXISTING setting (zero code if `list_templates()` globs; +1 line if it's a hardcoded frozenset — confirm Day-0).

### The design (NEW `key_condition.txt` template + a mirror-benchmark A/B harness; the lever already exists)

```
# verification/templates/key_condition.txt (Cat 10): the judge is instructed to
#   1. EXTRACT the must-satisfy conditions implied by the user's request (count / format /
#      ordering / required content / unit / constraints) from the {trace}
#   2. CHECK the {output} against EACH condition
#   3. ALSO apply the generic usability floor (refuses / incoherent / empty / contradicts-trace)
#   4. passed = true IFF every CRITICAL condition is met AND the floor holds
#   same JSON contract: {passed, score, reason (the failed condition), suggested_correction}

# scripts/benchmark_key_condition.py (mirror benchmark_judge.py):
#   load_cases(yaml) → for each: run BOTH judges (generic output_quality + key_condition) →
#   build_report: generic_accuracy / key_condition_accuracy / key_condition_gain
#   (= cases the generic judge wrongly passes that key_condition correctly fails) +
#   false_positive_rate (acceptable cases key_condition wrongly fails — the over-flag risk)
#   main() gated by RUN_AZURE_INTEGRATION (like benchmark_judge.py)

# fixture key_condition_cases.yaml: two case classes —
#   instruction_violation (generic-blind, key_condition SHOULD catch): "exactly 3" → 5 items,
#     "one word" → paragraph, "ascending" → unsorted, "include unit" → omitted, "JSON" → prose
#   acceptable (BOTH should pass): correct-shape answers + the over-flag traps
#     (a short-but-correct answer; a verbose-but-compliant answer)
```

WHY Option A (single-call template) over Option B (two-phase extract-then-check): the spike's job is to settle whether per-task conditions catch more — a single judge call that reasons "conditions → check → verdict" delivers the mechanism with ZERO code change (rides the existing template wire) and HALF the judge cost of a two-phase call. Option B (a dedicated extraction call feeding a check call, closer to the literal EMNLP2024 pipeline) is a follow-on IF A proves material value — building it before the measurement would repeat the evidence-free risk 57.136/137's discipline avoided. The existing `chat_verification_judge_template` setting (DEFAULT `output_quality`) = zero-risk rollback: nothing changes unless an operator selects `key_condition`.

### Ground truth (recon head-start — code read on `main` HEAD `57423a80`; ALL re-verified §checklist 0.1)

- `verification/templates/output_quality.txt:1-30` — the generic template the key_condition template's floor section mirrors (so key_condition strictly dominates on the floor categories).
- `verification/llm_judge.py:123-139` — `_build_prompt` substitutes `{output}` + `{trace}`; the new template uses the SAME two placeholders (no judge code change).
- `verification/templates/__init__.py:35-64` — `load_template` + `list_templates`; confirm Day-0 whether `list_templates()` globs `*.txt` (zero code) or is a hardcoded frozenset (+1 line).
- `core/config/__init__.py:127` + `api/v1/chat/handler.py:659-679` — the existing selection lever the spike rides (verify the handler resolves an arbitrary shipped-template name, not a hardcoded allow-list).
- `scripts/benchmark_judge.py:73-349` + `tests/fixtures/verification/judge_benchmark.yaml` + `tests/unit/scripts/test_benchmark_judge.py` — the measurement scaffold + golden-fixture + CI-safe-unit pattern to mirror.

**Baselines (57.137 closeout)**: pytest 2786+5skip · wire 25 · Vitest 915 · mockup 51 · mypy 0/374 · run_all 10/10. Re-verify Day-0.

### STALE / drift findings (Day-0; full detail → progress.md — placeholder, filled in §checklist 0.1)

- **D-list-templates** — read `templates/__init__.py:35-64`: does `list_templates()` glob `*.txt` (→ `key_condition` auto-selectable, zero code) or return a hardcoded frozenset (→ add `"key_condition"`, +1 line)? Shifts §3.1 / §4.
- **D-handler-resolve** — read `handler.py:659-679`: does it resolve the setting value against `list_templates()` dynamically (any shipped template selectable) or hardcode an allow-list? If hardcoded, the lever needs the name added (+1 line).
- **D-placeholder-shape** — confirm `_build_prompt` (`llm_judge.py:132-139`) substitutes BOTH `{output}` and `{trace}` so the new template composes with A3 trace-awareness (no judge code change).
- **D-json-contract** — confirm `_parse_response` (`llm_judge.py:141-187`) needs only `passed` (+ optional score/reason/suggested_correction) → the key_condition template can carry its per-condition detail inside `reason` with NO contract change.
- **D-template-test** — confirm `test_judge_templates.py` enumerates/loads templates so the new one gets a load + list assertion (the regression guard).
- **D-benchmark-shadow** — confirm the `tests.unit.scripts` importlib-shadow idiom (`test_benchmark_judge.py`) so the new CI-safe test loads cleanly.

## 1. Sprint Goal

Settle, with real numbers, whether a per-task key-condition judge catches instruction-following failures (count / format / ordering / unit / inclusion) that the generic 5-failure-mode judge is structurally blind to — and whether it does so WITHOUT over-flagging acceptable answers — then ship the mechanism as a selectable judge template (the existing `chat_verification_judge_template` lever) so an operator can opt in, default unchanged. PROVEN by: the full gate set + a real-Azure A/B report (`benchmark_key_condition`: generic_accuracy / key_condition_accuracy / key_condition_gain / false_positive_rate) + a MANDATORY chat-v2 drive-through (the `key_condition` template selectable + running on the main flow + the generic default byte-unchanged). Produces **CHANGE-105** + a **design note (42)** carrying the measured numbers + the per-task-condition reframe.

## 2. User Stories

- **US-1** (key-condition template): 作為 verification 維護者，我希望有一個 `key_condition.txt` judge template，能從請求抽取 per-task must-satisfy conditions（count / format / ordering / unit / inclusion）並逐條檢查（且保留 generic usability floor），以便 judge 能抓到 instruction-following 失敗而非只看泛用品質。
- **US-2** (selectable lever): 作為 operator，我希望透過既有的 `chat_verification_judge_template`（env / 57.106 C3 per-tenant）就能選 `key_condition`，DEFAULT 仍是 `output_quality`，以便零風險 opt-in、不改既有行為。
- **US-3** (measurement): 作為決策者，我希望有可重跑的 A/B harness 量測 generic vs key-condition 在 instruction-violation cases 的 accuracy gain 並驗證它不 over-flag acceptable answers，以便用證據（非假設）決定 default 或 opt-in。
- **US-4** (drive-through, MANDATORY): 作為使用者，我希望在 chat-v2 把 judge template 設為 `key_condition` 時，verification gate 仍在主流量正常運作（no-regression with the new template active）；且 generic default 不變，以便驗證 lever 真的可選且不破壞主流量。
- **US-5** (closeout): 設計筆記 42（spike 8-point gate）+ CHANGE-105 + calibration + navigators / next-phase-candidates 更新（CLOSE the AD）。

## 3. Technical Specifications

### 3.0 Architecture (backend-only — NO loop.py / config / handler / migration / wire / frontend)

```
NEW   backend/src/agent_harness/verification/templates/key_condition.txt   — per-task condition judge prompt (superset of output_quality floor; {output}+{trace}, same JSON contract)
NEW   backend/scripts/benchmark_key_condition.py                           — generic-vs-key-condition A/B harness (mirror benchmark_judge.py)
NEW   backend/tests/fixtures/verification/key_condition_cases.yaml          — instruction_violation + acceptable corpus
NEW   backend/tests/unit/scripts/test_benchmark_key_condition.py            — CI-safe (no Azure) load/run/report logic
EDIT  backend/tests/unit/agent_harness/verification/test_judge_templates.py — assert key_condition loads + is listed
EDIT? backend/src/agent_harness/verification/templates/__init__.py          — ONLY IF list_templates() is a hardcoded frozenset (Day-0 D-list-templates); +1 line "key_condition"
UNTOUCHED  llm_judge.py / _abc.py / VerificationResult / loop.py / config / handler / sse / wire schema / output_quality.txt / frontend
```

### 3.1 Key-condition template (US-1, US-2) — `templates/key_condition.txt`

- Same `{trace}` + `{output}` placeholders as `output_quality.txt` (so `_build_prompt` needs NO change + composes with A3 trace-awareness).
- Prompt structure: (1) from the conversation trace, identify the user's request + its must-satisfy conditions (enumerate them: count / format / ordering / required content / unit / explicit constraints); (2) check the output against EACH condition; (3) ALSO apply the generic usability floor (refuses / incoherent / empty / contradicts-trace); (4) `passed = true` IFF every CRITICAL condition is met AND the floor holds. Bias note: only flag conditions the request CLEARLY imposes (avoid inventing constraints — the false-positive guard); a short correct answer that meets all conditions PASSES.
- Same JSON contract: `{"passed": bool, "score": float, "reason": str (name the failed condition), "suggested_correction": str|null}`. The per-condition detail lives in `reason` → NO `VerificationResult` contract change, NO wire change.
- Selectable via the EXISTING `chat_verification_judge_template` setting (DEFAULT `output_quality` — unchanged). If Day-0 D-list-templates shows a hardcoded frozenset, add `"key_condition"` there (+1 line).

### 3.2 Measurement harness (US-3) — `scripts/benchmark_key_condition.py` + fixture

- Mirror `benchmark_judge.py`: `load_cases(path)` (schema-validate) / `run_judge(judge, cases)` (reuse the Verifier ABC; run both the `output_quality` and `key_condition` judges) / `build_report(...)` (pure: `generic_accuracy`, `key_condition_accuracy`, `key_condition_gain` = instruction_violation cases generic wrongly PASSES but key_condition correctly FAILS, `false_positive_rate` = acceptable cases key_condition wrongly FAILS) / `report_to_markdown` / `_amain` (gated by `RUN_AZURE_INTEGRATION`, builds the Azure profile, runs both templates) / `main()`.
- Golden fixture `key_condition_cases.yaml`: two classes — `instruction_violation` (≥6: exactly-N→wrong-count, one-word→paragraph, ascending→unsorted, include-unit→omitted, JSON→prose, cite-source→uncited; each with a trace carrying the constraining request) + `acceptable` (≥4: correct-shape answers + over-flag traps: a terse-but-correct answer, a verbose-but-compliant answer). Each labeled `expected_passed` + `class`.
- pytest unit mirrors `test_benchmark_judge.py` (importlib-load idiom to avoid the `tests.unit.scripts` shadow; covers `load_cases` / `build_report` with a MockChatClient + a stub judge; NO Azure — the real A/B runs only via the gated `main()` / the `@pytest.mark.benchmark` real-LLM path).

### 3.x What is explicitly NOT done

- **Two-phase extract-then-check (Option B)** — a dedicated condition-extraction call feeding a per-condition check call (closer to the literal EMNLP2024 pipeline). OUT — 2× judge cost + new code; a follow-on IF Option A proves material value.
- **Surfacing the structured conditions array** (a `VerificationResult.conditions` field + SSE wire) — OUT (contract + wire change, anti-AP-6); the per-condition detail rides `reason` this sprint.
- **Flipping the default to `key_condition`** — deferred to the measured verdict; default stays `output_quality` unless the A/B shows a material gain with no over-flag.
- **loop.py / config / handler changes** — NONE; the spike rides the existing template-selection wire.

### 3.y Validation (US-1..US-5)

Gates: mypy `src` 0/374 · run_all 10/10 · pytest 2786+ (+ new) · Vitest 915 (unchanged — no FE) · mockup 51 (`diff` empty — no FE) · `npm run lint && npm run build` (NO `--silent`) · black/isort/flake8 clean · LLM-SDK-leak clean. Plus the §3.2 real-Azure A/B report + the MANDATORY §US-4 drive-through.

## 4. File Change List

| # | File | Action |
|---|------|--------|
| 1 | `backend/src/agent_harness/verification/templates/key_condition.txt` | NEW (per-task condition judge prompt) |
| 2 | `backend/scripts/benchmark_key_condition.py` | NEW (generic-vs-key-condition A/B harness) |
| 3 | `backend/tests/fixtures/verification/key_condition_cases.yaml` | NEW (instruction_violation + acceptable corpus) |
| 4 | `backend/tests/unit/scripts/test_benchmark_key_condition.py` | NEW (CI-safe load/run/report) |
| 5 | `backend/tests/unit/agent_harness/verification/test_judge_templates.py` | EDIT (assert key_condition loads + listed) |
| 6 | `backend/src/agent_harness/verification/templates/__init__.py` | EDIT **only if** `list_templates()` is a hardcoded frozenset (Day-0 D-list-templates) |
| 7 | `claudedocs/4-changes/feature-changes/CHANGE-105-verification-key-condition.md` | NEW |
| 8 | `docs/03-implementation/agent-harness-planning/42-verification-key-condition-design.md` | NEW (spike design note) |
| — | `llm_judge.py` / `_abc.py` / `VerificationResult` / `loop.py` / `config` / `handler.py` / `sse.py` / wire schema / `output_quality.txt` | **UNTOUCHED** |
| — | any frontend / migration / new DB table | **UNTOUCHED** |

## 5. Acceptance Criteria

1. `key_condition.txt` template loads via `load_template("key_condition")` + is enumerated by `list_templates()`; unit asserts both. It uses `{output}` + `{trace}` and returns the same JSON contract (no judge code change).
2. `key_condition` is selectable via `chat_verification_judge_template` (env / per-tenant) — the handler resolves it; DEFAULT stays `output_quality` (byte-unchanged); unit/integration asserts the default path is unchanged.
3. `benchmark_key_condition.py` produces a real-Azure A/B report with `generic_accuracy` + `key_condition_accuracy` + `key_condition_gain` (> 0 expected on instruction_violation — proves the catch) + `false_positive_rate` (low expected on acceptable — proves no over-flag); CI-safe unit covers the pure logic with a stub judge + the fixture (no Azure).
4. The key-condition template strictly includes the generic usability floor (refuses/incoherent/empty/contradicts-trace) so it does not regress the floor categories.
5. **Drive-through PASS (MANDATORY, real UI + backend + LLM)** — chat-v2 with `CHAT_VERIFICATION_JUDGE_TEMPLATE=key_condition`: the verification gate runs on the main flow end-to-end (no-regression with the new template active) + the generic default (unset) path is unchanged; screenshot + observed-vs-intended in progress.md. (NOT gate-only; the deterministic catch is the A/B harness — same honest "兩者結合" as 57.136 since a real LLM rarely violates a precise instruction on demand.)
6. `AD-Verification-KeyCondition-PerTask` CLOSED; CHANGE-105 + design note 42 (8-point gate); calibration recorded; navigators + next-phase-candidates updated.

## 6. Deliverables

- [ ] US-1 `key_condition.txt` template (per-task conditions + generic floor; `{output}`+`{trace}`; same JSON contract)
- [ ] US-2 selectable via the existing `chat_verification_judge_template` lever (DEFAULT unchanged; +1 line iff hardcoded list)
- [ ] US-3 `benchmark_key_condition.py` + corpus fixture + CI-safe unit test + real-Azure A/B report
- [ ] US-4 chat-v2 drive-through (key_condition active no-regression + generic default unchanged) (MANDATORY)
- [ ] US-5 design note 42 + CHANGE-105 + closeout

## 7. Workload Calibration

- Scope class **`verification-keycondition-spike` 0.60** (NEW class, 1st data point; analogous to `verification-context-hygiene-spike` 0.60 (57.136) + `verification-trace-and-benchmark-spike` 0.60 (57.111) + `verification-in-loop-spike` 0.60 (57.98) — a Cat 10 verification spike paired with a measurement harness + drive-through; cite `.claude/rules/sprint-workflow.md` §Scope-class multiplier matrix). NOTE: this spike is LIGHTER on src than 57.136/137 (a template + a harness; NO loop.py/config change), but the harness + fixture + real-Azure A/B + drive-through ceremony is the same fixed cost — the 0.60 family baseline fits; flag at retro if the lighter src pulls the ratio.
- **Agent-delegated: no** (parent-direct; the value is precise judgment of the key-condition prompt design + the A/B evidence + the instruction-following corpus, not mechanical pattern reuse). `agent_factor` 1.0 → 3-segment form.
- Bottom-up est ~11 hr (Day0 三-prong ~1 · key_condition template + selectability verify + template-test ~2 · A/B harness + corpus + CI test + real-Azure run ~4 · drive-through ~1.5 · design note + CHANGE + closeout ~2.5) → class-calibrated commit ~6.6 hr (mult 0.60). Day-4 retro Q2 verifies. NOTE: per the 57.120/136/137 ceremony-not-code-accelerated insight — if the src lands very small (template + harness only) the drive-through + design-note ceremony may pull the ratio up; flag at retro (the harness is the ~3 hr real-code core, so the 0.60 should hold per the 57.137 lesson).

## 8. Dependencies & Risks

| Risk | Mitigation |
|------|------------|
| **Real LLM rarely violates a precise instruction on demand** → can't deterministically drive a key-condition CATCH in the live UI | The A/B harness (deterministic fixture, real Azure) IS the catch evidence; the UI drive-through proves selectability + no-regression with the template active + the generic default unchanged. Same honest "兩者結合" pattern accepted for 57.136/57.137 (never imply the UI drove the catch if it didn't). |
| **Over-flagging acceptable answers** (a stricter judge flags good-enough answers → worse UX) | The fixture includes `acceptable` over-flag traps (terse-but-correct, verbose-but-compliant); `false_positive_rate` is a first-class report metric + a go/no-go gate; the template prompt explicitly says "only flag conditions the request CLEARLY imposes; a short correct answer PASSES". |
| **Selection lever is a hardcoded allow-list** (not a dynamic glob) | Day-0 D-list-templates + D-handler-resolve verify; if hardcoded, add `"key_condition"` (+1 line) — still no loop.py/config change. |
| **Stale `--reload` backend masks the template-selection env** | Risk Class E: clean restart + confirm sole live worker + startup log before the drive-through (the 57.97 spawn-worker trap); set `CHAT_VERIFICATION_JUDGE_TEMPLATE` BEFORE restart (the registry is built at request time from settings, but the singleton/process env is read at startup — verify). |
| **CI-safe test `tests.unit.scripts` import shadow** | Mirror the importlib-load idiom from `test_benchmark_judge.py` (the proven pattern). |
| **Cost of the real-Azure A/B run** | ≥10 cases × 2 templates × [judge] ≈ 20+ Azure calls per run; gated by `RUN_AZURE_INTEGRATION` (on-demand, like benchmark_judge.py) — not in CI. |

## 9. Out of Scope (this sprint; → separate slices / ADs)

- **Two-phase extract-then-check (Option B)** — → `AD-Verification-KeyCondition-TwoPhase-Phase58` (dedicated extraction call + per-condition check; only if Option A proves material value).
- **Structured `conditions` array surfaced to the frontend** (`VerificationResult.conditions` + SSE wire + Inspector render) — → `AD-Verification-Conditions-Surface-Phase58` (contract + wire change; the per-condition detail rides `reason` this sprint).
- **Flipping the default to `key_condition`** — deferred to the measured verdict; if the A/B shows a material gain with no over-flag, a follow-up flips the default (1-line config change).
- **The other research-derived candidates** (#4 layered compaction / #1 task-primitive DAG / #2 pass^k / #5 OTel / #7 tool-lint) — stay registered in `next-phase-candidates.md` per the canonical ranked order; selection-gated.
