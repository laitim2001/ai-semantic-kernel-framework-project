# Sprint 57.138 Progress — verification key-condition judge (per-task condition template + A/B accuracy spike)

[Plan](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-138-plan.md) · [Checklist](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-138-checklist.md)

---

## Day 0 — 2026-06-24 — Plan-vs-Repo Verify (三-prong) + Branch

**Base**: `main` HEAD `57423a80` (post-#328 flip of 57.137 → MERGED + canonical-order restore; backend code identical to 57.137 close `f47964ad` — #328 was docs-only). Branch `feature/sprint-57-138-verification-key-condition`.

### Drift findings (三-prong)

| ID | Prong | Finding | Implication |
|----|-------|---------|-------------|
| Prong 1 (paths) | 1 | 4 NEW free (`templates/key_condition.txt`, `scripts/benchmark_key_condition.py`, `tests/fixtures/verification/key_condition_cases.yaml`, `tests/unit/scripts/test_benchmark_key_condition.py`); EDIT target `test_judge_templates.py` present; `CHANGE-105` free (max=104); design note `42-*` free (max=41). | ✅ all confirmed. |
| D-list-templates | 2 | `templates/__init__.py:47-53` `load_template` reads `<name>.txt`; `:56-64` `list_templates()` returns `frozenset(p.stem for p in ...glob("*.txt"))` — **globbed, NOT a hardcoded frozenset**. | ✅ **SCOPE REDUCTION**: adding `key_condition.txt` auto-makes it loadable + listed → `templates/__init__.py` **NOT edited** (plan file #6 dropped). |
| D-handler-resolve | 2 | `handler.py:658-665` — base `judge_template = settings.chat_verification_judge_template` (`:660`, used directly); per-tenant override `:661-665` validated `in list_templates()` (dynamic glob). `:679 make_chat_verifier_registry(profile.cheap, judge_template)`. | ✅ env `CHAT_VERIFICATION_JUDGE_TEMPLATE=key_condition` selects with ZERO code; per-tenant path also works (dynamic). |
| D-placeholder-shape | 2 | `llm_judge.py:132-139` `_build_prompt` substitutes BOTH `{output}` + `{trace}` (`build_trace_block` when state present). | ✅ new template composes with A3 trace-awareness; NO judge code change. |
| D-json-contract | 2 | `llm_judge.py:141-187` `_parse_response` requires only `passed`; optional `score`/`reason`/`suggested_correction`; fail-closed on parse error. | ✅ per-condition detail rides `reason` → NO `VerificationResult` contract change, NO wire change. |
| D-template-test | 2 | `test_judge_templates.py:42-55` parametrizes 5 templates asserting `{output}` + `JSON`; `:28-39` load/missing tests. | ✅ extend the parametrize list + add a `key_condition`-specific test (per-task-condition language + `{trace}` + floor criteria + FP guard). The new template MUST contain `{output}` + "JSON". |
| D-benchmark-shadow | 2 | `test_benchmark_judge.py` exists (importlib-load idiom to dodge the `tests.unit.scripts` shadow) — confirmed via Explore map. | ✅ mirror the idiom in the new CI-safe test. |
| Prong 3 (schema) | 3 | N/A — no new DB table / migration / ORM column (template + harness only). | — |

### Baselines (57.137 closeout; `57423a80` backend == `f47964ad`, #328 docs-only)

pytest **2786 + 5 skip** · mypy `src` **0/374** · run_all **10/10** · wire **25** / Vitest **915** / mockup **51** = unchanged sentinels (backend-only sprint, no FE/wire). Re-confirm at Day-2 full gate.

### Go/no-go

All prongs **GREEN**; **zero drift** from the plan's recon (every file:line anchor confirmed). The only "shift" is a SCOPE REDUCTION: `templates/__init__.py` needs NO edit (`list_templates()` globs), so the file change list drops to 4 NEW backend + 1 test EDIT + 2 docs — even more surgical than planned (zero src code edit; the new template is a data file, the harness is a new script). Scope-shift ~−10% (reduction, well under the 20% revise threshold). **PROCEED to Day 1.** The spike rides existing machinery end-to-end: the glob-based template loader + the existing `chat_verification_judge_template` wire + the `benchmark_judge.py` measurement scaffold. No new primitive, no schema, no frontend, no wire event, no loop.py/config/handler change.

**Design decisions locked (Day 0)**: (a) single-call key_condition template (Option A) — extract conditions → check each → verdict in ONE judge call; (b) superset of the generic usability floor (keeps refuses/incoherent/empty/contradicts-trace + adds per-task conditions) so it strictly dominates on the floor; (c) per-condition detail rides `reason` (NO contract/wire change); (d) DEFAULT stays `output_quality` (the existing setting selects `key_condition`); (e) the A/B harness is the deterministic CATCH evidence, the UI drive-through proves selectability + no-regression ("兩者結合" honesty per 57.136/137).

---

## Day 1 — 2026-06-24 — key_condition template + selectability (US-1, US-2)

- **`templates/key_condition.txt`** (Cat 10, NEW): a per-task condition judge prompt — Step 1 EXTRACT the request's must-satisfy conditions from `{trace}` (count / format / ordering / inclusion / explicit constraints; "do not invent conditions the request does not clearly state" = the false-positive guard); Step 2 CHECK `{output}` against each; Step 3 ALSO apply the generic usability floor (refuses / incoherent / empty / off-topic / contradicts-trace); verdict `passed=true` IFF every CRITICAL condition met AND floor holds. Same JSON contract `{passed, score, reason (the violated condition), suggested_correction}`; "Default to passed=true / When in doubt, pass" bias kept. Uses `{output}` + `{trace}` → composes with the A3 trace-aware judge with NO `llm_judge.py` change.
- **Selectability (US-2)**: confirmed auto-selectable — `load_template`/`list_templates` glob `*.txt` (Day-0 D-list-templates), so `key_condition` loads + lists with ZERO `templates/__init__.py` edit; the handler's `chat_verification_judge_template` (env `CHAT_VERIFICATION_JUDGE_TEMPLATE`) + the per-tenant `in list_templates()` path both resolve it. DEFAULT stays `output_quality`.
- **`test_judge_templates.py`** (EDIT): added `key_condition` to the parametrized load+placeholder test + a dedicated `test_key_condition_template_extracts_per_task_conditions` (asserts condition-extraction language + the 3 condition axes + the retained floor criteria + the false-positive guard + default-pass bias). → 10 passed (was 8; +2).
- **Partial gate**: `pytest test_judge_templates.py` 10 passed · black/isort/flake8 clean on the edited test · mypy `src` 0/374 (no src code change — template is a data file).

---

## Day 2 — 2026-06-24 — A/B measurement harness + real-Azure run (US-3)

### 2.1 + 2.2 — Harness + corpus + CI-safe test

- **`scripts/benchmark_key_condition.py`** (Cat 10 eval, NEW): mirrors `benchmark_judge.py`'s scaffold (`load_cases` / `run_judge` / `build_report` / `report_to_markdown` / `_amain` / `main` + frozen `KeyCondCase`/`JudgeRun`/`KeyCondReport` dataclasses + lazy Azure import). Runs BOTH templates (`output_quality` + `key_condition`) over the same corpus (trace-aware) and computes: `generic_accuracy` / `key_condition_accuracy` / `key_condition_gain` (key_cond − generic accuracy on the `instruction_violation` class) / `false_positive_rate` (acceptable cases key_condition WRONGLY fails) / `key_condition_recommended` (gain ≥ `GAIN_FLOOR` 0.30 AND fp ≤ `FP_CEILING` 0.20).
- **`tests/fixtures/verification/key_condition_cases.yaml`** (NEW): 11 cases — 6 `instruction_violation` (exactly-3→5 items / one-word→paragraph / ascending→unsorted / unit→omitted / JSON→prose / two-with-capitals→names-only; each w/ a constraining-request trace) + 5 `acceptable` (count-met / terse-but-correct / JSON-met / verbose-but-compliant / no-condition-imposed — the over-flag traps).
- **`tests/unit/scripts/test_benchmark_key_condition.py`** (NEW, +9): importlib-load idiom (avoids the `tests.unit.scripts` shadow). Covers load_cases (schema/dup/class + the fixture's label-consistency invariant) · run_judge (trace-state build + token accumulation) · build_report (gain + zero-FP RECOMMENDED / over-flag blocks recommendation / per-class + tokens / gain-below-floor blocks). 9 passed.

### 2.3 — Real-Azure A/B run (US-3) — the spike's core evidence

Ran `RUN_AZURE_INTEGRATION=1 python scripts/benchmark_key_condition.py` against real Azure (cheap-tier judge, temp 0.0), 11 cases × 2 templates. Report → `artifacts/key_condition_report.{md,json}`.

| metric | value |
|--------|-------|
| generic accuracy (all) | 90.91% (10/11) |
| key_condition accuracy (all) | **90.91%** (tie) |
| **key_condition gain** (instruction_violation: key_cond − generic) | **+16.67%** |
| generic acc on instruction_violation | 83.33% (5/6) |
| key_condition acc on instruction_violation | **100.00% (6/6)** |
| **false_positive_rate** (acceptable wrongly failed) | **20.00% (1/5)** |
| thresholds (gain ≥ 30% AND fp ≤ 20%) | **NOT recommended** |
| generic tokens / key_condition tokens | 4090 / 7493 |

**Verdict: directionally better at instruction-following catching, but NOT a default flip.** The key_condition judge caught **all 6** instruction violations (100%) vs the generic judge's 5/6 (+16.67pp on that class) — but it **over-flagged 1 acceptable answer** (20% FP), so overall accuracy is a **tie** (90.91% each) and it does NOT clear the recommendation thresholds (gain 16.67% < 30% floor; fp 20% AT the ceiling). It also costs ~1.8× the tokens (7493 vs 4090 — the condition-extraction reasoning).

**Honest nuance**: the generic judge is LESS blind than the theory predicted (83% on instruction_violation, not ~0%) — because A3 trace-awareness lets it reason "the user asked for exactly 3 and got 5 → contradicts the trace". So explicit per-task condition extraction adds a real-but-marginal catch (the 6th) at a false-positive + token cost. This matches the reconciliation assessment ("#8 partially done / refinable; priority low").

**Decision**: keep `output_quality` as DEFAULT; ship `key_condition` as a SELECTABLE env / per-tenant opt-in (the existing `chat_verification_judge_template` lever) for instruction-adherence-strict tenants who accept the higher FP + token cost. The mechanism works + is measured; the default does not change (zero risk). Harness is permanent + re-runnable on a larger / harder corpus.

### 2.x — Full gate

- **v2 lints** (`python scripts/lint/run_all.py`, cwd=root): **10/10 green** (incl. check_llm_sdk_leak — the harness uses the Verifier ABC; the Azure profile is built only in `main()`, mirroring `benchmark_judge.py`).
- **mypy src**: **0/374** (no src code change — template is a data file; harness is a script).
- **pytest full suite**: **2797 passed + 5 skip** (baseline 2786 + 11 new: 2 Day-1 template tests + 9 Day-2 harness tests). No regressions.
- Frontend (Vitest 915 / mockup 51 / npm): unchanged sentinels — backend-only sprint.

---

## Day 3 — 2026-06-24 — Drive-through (US-4): chat-v2 real UI + real backend + real LLM ("兩者結合")

### Clean restart (Risk Class E)

Backend was NOT running (no python.exe, port 8000 free, no orphan spawn-worker — the 57.97 trap clear). For each arm a FRESH single-process uvicorn (`api.main:app --app-dir src`, NO `--reload` → no orphan; root `.env` loaded for Azure). Frontend already up on :3007 (PID 31616, node — not touched). The judge registry is built at request time from `get_settings()` (lru_cached, read once at first request), so `CHAT_VERIFICATION_JUDGE_TEMPLATE` was set BEFORE each restart.

### Drive-through (real chat-v2 + real Azure gpt-5.2, jamie@acme.com·operator·acme-prod) — PASS

| arm | config | prompt | result |
|-----|--------|--------|--------|
| **A key_condition active** | `CHAT_VERIFICATION_JUDGE_TEMPLATE=key_condition` (restart) | "List exactly 3 primary colors." | answer **"Red, blue, yellow"** (compliant — exactly 3) → **verification_passed (llm_judge score=0.99)** → loop_end stop=end_turn. The key_condition judge ran on the main flow, extracted the "exactly 3" condition, found it met → PASSED (no over-flag of a compliant answer). |
| **B default unchanged** | env UNSET (default `output_quality`, restart) | "What is the capital of France?" | answer **"Paris"** → **verification_passed (llm_judge score=0.99)** → loop_end stop=end_turn. The default path is byte-unchanged (no-regression). |

Both arms: Inspector "Verification (1) ✅ llm_judge Score: 0.99" + Loop visualizer `verification_passed` event + the answer rendered in the thread. Screenshots: `artifacts/dt-57138-keycond-active-verification-passed.jpeg` (A) + `artifacts/dt-57138-default-template-no-regression.jpeg` (B).

### Observed vs intended

- **Intended**: (a) the `key_condition` template is selectable + runs on the chat-v2 main flow without breaking it (no-regression with it active); (b) the generic default path is unchanged.
- **Observed**: exactly that — ARM A ran the key_condition judge end-to-end and correctly passed a compliant answer (verification_passed 0.99); ARM B with the default ran verification as before (verification_passed 0.99). The selectability lever (the existing `chat_verification_judge_template` setting) works with the new template; no code change to the judge/loop/handler.

### Drive-through verdict ("兩者結合" honesty)

- **Selectability + no-regression**: UI PASS (both arms, real chat-v2 + real Azure). The new template is selectable via the existing env lever and runs on the main flow; the default is unchanged.
- **The deterministic CATCH** (key_condition catching an instruction violation the generic judge misses): the **A/B harness** (Day 2, real Azure, +16.67pp on instruction_violation) — NOT the UI. A real LLM complies with a simple instruction on demand, so a clean instruction-violation-then-catch can't be forced in a live UI (same honest limit as 57.136's "real fail can't be forced cleanly"). We do NOT claim the UI drove the catch.
- Backend stopped + port 8000 confirmed free at Day-3 close (no orphan python). Frontend (:3007 node) left running.
