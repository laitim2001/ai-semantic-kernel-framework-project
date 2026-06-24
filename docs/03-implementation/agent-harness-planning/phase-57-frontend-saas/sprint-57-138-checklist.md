# Sprint 57.138 — Checklist (verification key-condition judge: per-task condition template + A/B accuracy spike)

[Plan](./sprint-57-138-plan.md)

---

## Day 0 — Plan-vs-Repo Verify (三-prong) + Branch

### 0.1 Three-prong Day-0 verify (against `main` HEAD `57423a80`)
- [x] **Prong 1 — path verify**: ✅ 4 NEW free; EDIT target `test_judge_templates.py` present; `CHANGE-105` free (max 104); design note `42-*` free (max 41)
- [x] **Prong 2 — content verify** (drift → progress.md):
  - [x] **D-list-templates** — ✅ `list_templates()` + `load_template` GLOB `*.txt` (`__init__.py:47,51,64`) → `key_condition.txt` auto-loadable + listed → **`templates/__init__.py` NOT edited** (SCOPE REDUCTION, plan file #6 dropped)
  - [x] **D-handler-resolve** — ✅ DYNAMIC: base `judge_template = settings.chat_verification_judge_template` (`handler.py:660`, used directly); per-tenant override validated `in list_templates()` (`:663`) → env selects with ZERO code
  - [x] **D-placeholder-shape** — ✅ `_build_prompt` substitutes BOTH `{output}` + `{trace}` (`llm_judge.py:132-139`) → composes, no judge code change
  - [x] **D-json-contract** — ✅ `_parse_response` needs only `passed` (+ optional) (`llm_judge.py:141-187`) → per-condition detail rides `reason`, no contract change
  - [x] **D-template-test** — ✅ `test_judge_templates.py:42-55` parametrizes 5 templates (assert `{output}` + `JSON`) → extend + add key_condition-specific test
  - [x] **D-benchmark-shadow** — ✅ `test_benchmark_judge.py` importlib-shadow idiom confirmed → mirror it
- [x] **Prong 3 — schema verify**: N/A (no new DB table / migration / ORM column)
- [x] **D-baselines** — pytest 2786+5skip · wire 25 · Vitest 915 · mockup 51 · mypy 0/374 · run_all 10/10 → recorded (57.137 closeout)
- [x] **Catalog drift** — ✅ progress.md Day-0 table (8 rows + implication)
- [x] **Go/no-go** — ✅ all GREEN, zero drift, scope-shift ~−10% (reduction) → PROCEED to Day 1

### 0.2 Branch
- [x] `git checkout -b feature/sprint-57-138-verification-key-condition` (from `main` `57423a80`) → ✅ on branch

---

## Day 1 — Key-condition template + selectability (US-1, US-2)

### 1.1 `key_condition.txt` template
- [x] **per-task condition judge prompt (superset of generic floor)**
  - DoD: `templates/key_condition.txt` instructs extract-conditions (count/format/ordering/unit/inclusion from `{trace}`) → check each against `{output}` → ALSO apply the generic usability floor → `passed=true` IFF every critical condition met AND floor holds; same JSON contract `{passed, score, reason, suggested_correction}`; explicit false-positive guard ("only flag conditions the request CLEARLY imposes; a short correct answer PASSES")
  - ✅ done: 3-step prompt (extract → check → floor); `{output}`+`{trace}`; same JSON contract; "do not invent conditions" FP guard + "When in doubt, pass" bias

### 1.2 Selectability via the existing lever
- [x] **`key_condition` selectable; DEFAULT unchanged**
  - DoD: `list_templates()` includes `key_condition` (zero code if globbed; +1 line in `templates/__init__.py` if hardcoded per D-list-templates); the handler resolves `CHAT_VERIFICATION_JUDGE_TEMPLATE=key_condition`; DEFAULT stays `output_quality`
  - ✅ done: `list_templates()`/`load_template` GLOB → ZERO `__init__.py` edit; verified `'key_condition' in list_templates()` → True

### 1.3 Template test
- [x] **`test_judge_templates.py` asserts load + listed**
  - DoD: new test (or extend existing) asserts `load_template('key_condition')` returns a non-empty string with `{output}`+`{trace}` and `'key_condition' in list_templates()`
  - ✅ done: added to the parametrized test + a dedicated key_condition test → 10 passed (+2)

### 1.x Partial gate
- [x] `cd backend && mypy src && black . && isort . && flake8 .` clean + the FULL test surface of every edited src file (`test_judge_templates.py`) — 57.136 process lesson
  - ✅ done: test_judge_templates.py 10 passed · black/isort/flake8 clean · mypy src 0/374 (no src code change — template is a data file)

---

## Day 2 — A/B measurement harness + real-Azure run (US-3)

### 2.1 `benchmark_key_condition.py` + corpus fixture
- [x] **mirror benchmark_judge.py — generic vs key-condition A/B**
  - DoD: `load_cases / run_judge (both output_quality + key_condition judges) / build_report (generic_accuracy, key_condition_accuracy, key_condition_gain, false_positive_rate) / report_to_markdown / _amain (RUN_AZURE_INTEGRATION-gated) / main()`; `key_condition_cases.yaml` = `instruction_violation` (≥6) + `acceptable` (≥4 incl. over-flag traps); each labeled `expected_passed` + `class`
  - ✅ done: full scaffold; fixture = 6 instruction_violation + 5 acceptable (11 total); `key_condition_recommended` = gain≥0.30 AND fp≤0.20

### 2.2 CI-safe unit test
- [x] **stub-judge load/run/report test (no Azure)**
  - DoD: `test_benchmark_key_condition.py` (importlib-load idiom; D-benchmark-shadow) covers load_cases (schema/dup/class) · run_judge with a stub judge · build_report (gain / false_positive_rate); NO Azure; fixture label-consistency invariant
  - ✅ done: +9 tests incl. fixture label-consistency invariant + gain/FP/recommendation matrix. 9 passed

### 2.3 Real-Azure A/B run
- [x] **A/B report (generic vs key-condition)**
  - DoD: `RUN_AZURE_INTEGRATION=1 python scripts/benchmark_key_condition.py` → report; gain + false_positive_rate recorded in progress.md Day 2 + copied to `artifacts/`
  - ✅ done: real Azure 11 cases × 2 templates → **gain +16.67% (instruction_violation: key_cond 100% vs generic 83%)** · **fp 20%** · overall tie 90.91% → **NOT recommended** (gain < 30% floor) → keep output_quality default, key_condition = env opt-in. Report → `artifacts/key_condition_report.{md,json}` + progress.md Day 2

### 2.x Full gate
- [x] mypy `src` 0/374 · run_all 10/10 · backend pytest 2786+ + new · Vitest 915 (unchanged) · mockup 51 (`diff` empty) · black/isort/flake8 clean · LLM-SDK-leak clean
  - ✅ mypy src 0/374 · run_all 10/10 (incl. check_llm_sdk_leak) · black/isort/flake8 clean · pytest (recording — running) · Vitest 915 / mockup 51 unchanged sentinels (backend-only, no FE touched)

---

## Day 3 — Drive-through (US-4) — real UI + real backend + real LLM

### 3.1 Clean restart (Risk Class E)
- [x] kill stale `--reload` + orphan spawn-workers; confirm fresh SOLE port owner + startup log; set `CHAT_VERIFICATION_JUDGE_TEMPLATE=key_condition` BEFORE restart for the key-condition arm
  - ✅ done: no python/orphan pre-start (port free); fresh single-process uvicorn per arm (no `--reload`); env set before each restart; frontend :3007 (node) untouched

### 3.2 Drive-through (MANDATORY — NOT gate-only)
- [x] **(a) key_condition active no-regression** — chat-v2 + real Azure with `CHAT_VERIFICATION_JUDGE_TEMPLATE=key_condition`
  - ✅ "List exactly 3 primary colors." → "Red, blue, yellow" → verification_passed (llm_judge 0.99) → end_turn; key_condition judge ran on main flow, passed the compliant answer (no over-flag)
- [x] **(b) generic default unchanged** — restart with env UNSET (default `output_quality`)
  - ✅ "What is the capital of France?" → "Paris" → verification_passed (0.99) → end_turn; default path byte-unchanged
- [x] **THE walk (real UI)**: verification event visible in Inspector / answer renders / labels real
  - ✅ Inspector "Verification (1) ✅ llm_judge Score: 0.99" + Loop visualizer `verification_passed` + answer in thread (both arms)
- [x] Screenshot + observed-vs-intended → progress.md Day 3
  - ✅ `dt-57138-keycond-active-verification-passed.jpeg` (A) + `dt-57138-default-template-no-regression.jpeg` (B) + progress.md Day 3 (兩者結合 honesty: UI = selectability + no-regression; the CATCH = the A/B harness, NOT the UI)

---

## Day 4 — CHANGE-105 + design note 42 + closeout

### 4.1 CHANGE-105 + design note (spike)
- [x] **`CHANGE-105-verification-key-condition.md`** (gap + fix + A/B numbers + drive-through PASS + AD closed) → ✅ done
- [x] **`42-verification-key-condition-design.md`** (spike design note — 8-point gate) → ✅ done (8/8 gate; NO new 17.md contract — template-only N/A justified §3)

### 4.2 Closeout
- [x] retrospective.md Q1-Q7 + calibration (`verification-keycondition-spike` 0.60, 1st data point) → ✅ done (ratio ~0.98 IN band → KEEP 0.60)
- [x] Final gate sweep: mypy · run_all · pytest · Vitest · mockup · build · lint · LLM-SDK-leak → ✅ mypy 0/374 · run_all 10/10 · pytest 2797+5skip · black/isort/flake8 clean · LLM-SDK-leak clean · Vitest 915 / mockup 51 unchanged sentinels (backend-only, no FE touched)
- [x] Navigators: CLAUDE.md Current-Sprint + Last-Updated · MEMORY.md pointer + subfile · next-phase-candidates (CLOSE `AD-Verification-KeyCondition-PerTask`; advance → #4 next) · sprint-workflow matrix (`verification-keycondition-spike` row) → ✅ all done
- [x] Anti-pattern self-check (retro Q5): AP-2/3/4/6/8/11 → violations; v2 lints 10/10 → ✅ no violations; v2 lints 10/10
- [ ] **Commit** → ⏳ PR push + open → CI → merge: PENDING USER CONFIRMATION (push is outward-facing per Developer Preferences) → post-merge status flip after gh-verified MERGED
