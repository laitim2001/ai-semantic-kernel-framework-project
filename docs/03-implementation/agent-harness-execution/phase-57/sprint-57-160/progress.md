# Sprint 57.160 Progress — tool-anchored observation masking + reduction/retention A/B

**Plan**: [sprint-57-160-plan.md](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-160-plan.md) · **Checklist**: [sprint-57-160-checklist.md](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-160-checklist.md)
**Branch**: `feature/sprint-57-160-compaction-tool-anchored-masking` from `main` `29da11e8`
**Scope class**: NEW `compaction-tool-anchored-masking-spike` 0.60 · parent-direct agent_factor 1.0

---

## Day 0 — Plan-vs-Repo Verify (三-prong) + Branch — 2026-07-07

### Three-prong Day-0 verify (against `main` HEAD `29da11e8`) — ALL GREEN

**Prong 1 — path verify** ✅
- NEW absent: `benchmark_tool_anchored_masking.py` · `tool_anchored_masking_cases.yaml` · `test_benchmark_tool_anchored_masking.py` — all absent
- EDIT present: `observation_masker.py` · `_category_factories.py` · `test_observation_masker.py` — all present
- `CHANGE-127` free (highest = CHANGE-126) · design note `62` free (highest = 61)
- 57.139 harness test present (`test_benchmark_layered_compaction.py`) — guards to mirror

**Prong 2 — content verify** ✅ (Drift findings table below)

**Prong 3 — schema verify** N/A — no DB tables / migrations / ORM columns

**Baselines** (re-verified): pytest **3180** · wire **26** · Vitest **927** · mockup **51** · mypy `src` **400** · run_all **11/11**

### Drift findings

| ID | Finding | Implication |
|----|---------|-------------|
| D-masker-ctor-absent | `DefaultObservationMasker` has NO existing `__init__` (stateless today; `observation_masker.py:47` class, no ctor) | Adding keyword-only `__init__(tool_anchor_keep=None)` is additive-safe — no collision |
| D-abc-signature | `ObservationMasker` ABC (`_abc.py:57-80`) declares ONLY `mask_old_results(messages, *, keep_recent=5)`; no `__init__` | Impl `__init__` is impl-detail → NO ABC change needed |
| D-factory-masker-inject | Both `StructuralCompactor` (`structural.py:115`) and `PreClearCompactor` (`preclear.py:90`) accept `masker: ObservationMasker \| None = None` | Factory can inject the configured masker into both → both become effective when lever ON |
| D-tool-msg-shape | Tool results are `role=="tool"` with `name` + `tool_call_id` (`chat.py:76-93`); masker already reads `msg.name` (`observation_masker.py:71`) | Tool-anchored path can identify tool results by `role=="tool"` and reuse the tombstone format |
| D-harness-import-shadow | 57.139 `benchmark_layered_compaction.py` notes `tests.unit.scripts` importlib-shadow + cp950 `sys.stdout.reconfigure` guards | Mirror the same guards in the new harness + its test (Day 2) |

### Go/no-go
**PROCEED** — 0 drift, all recon confirmed, scope shift ~0% (all changes additive; recon reads matched reality exactly).

### Notes
- Backend (:8000) was left running with non-default `CHAT_COMPACTION_KEEP_RECENT_TURNS=1` (57.159 drive-through leftover). Day 1-2 work is fully offline (unit tests + deterministic harness) so no restart needed yet; the Day 3 clean-restart (Risk Class E) will set the DEFAULTS + only the 57.160 lever.

---

## Day 1 — Tool-anchored masking mode + env lever (US-1, US-2) — 2026-07-07

### Accomplishments
- **US-1** `observation_masker.py`: extracted module-level `_tombstone(msg)`; added `__init__(*, tool_anchor_keep: int | None = None)`; split `mask_old_results` into `_mask_user_anchored` (verbatim original path, byte-identical when `tool_anchor_keep is None`) + `_mask_tool_anchored` (keep last N `role=="tool"` results intact, tombstone older; defensive `keep < 1` passthrough guards the `tool_indices[-0]` footgun). MHist updated.
- **US-2** `_category_factories.py`: added `_compaction_tool_anchored_keep()` env reader (`CHAT_COMPACTION_TOOL_ANCHORED_MASKING`; `>=1` → N, else None) mirroring `_compaction_preclear_ratio`; `make_chat_compactor` builds `DefaultObservationMasker(tool_anchor_keep=N)` when set and injects `masker=` into BOTH `StructuralCompactor` and `PreClearCompactor`; None → `masker=None` → compactors default to user-anchored (byte-identical). Import + MHist added.
- **Tests**: +5 masker mode tests (single-user-turn fixture: reduces / default-None no-op regression guard / `<=N` passthrough / provenance+non-tool preserved / keep=0 passthrough); +6 factory tests (env-reader parametrized set/unset/0/neg/garbage + default-user-anchored + inject-into-structural + inject-into-preclear). Existing 6 masker tests UNCHANGED.

### Gate (partial, touched files)
- `test_observation_masker.py` 11 passed (6 existing + 5 new) · `test_category_factories.py` 32 passed (incl. 6 new) — combined 43 passed
- black/isort ✅ · flake8 ✅ (fixed 2 E501 docstring/comment) · mypy `src` (2 files) Success 0 issues

### Notes
- Chose instance-config (`tool_anchor_keep` on the masker) over a call-kwarg so the factory injects one configured masker into both compactors with zero compactor-signature / call-site threading change (plan §3.1 WHY).

## Day 2 — A/B reduction/retention harness (US-3) — 2026-07-07

### Accomplishments
- **`scripts/benchmark_tool_anchored_masking.py`** (NEW, mirrors 57.139 `benchmark_layered_compaction.py`): `load_cases`/`build_transcript` (ONE user turn + K×(assistant tool_call, tool result))/`measure_case` (OFF user-anchored vs ON tool-anchored + `_mechanical_retention_ok`)/`build_report` (means + `retention_ok_rate` + `recommend_default_on`)/`report_to_markdown`/`main` (cp950 `sys.stdout.reconfigure` guard). Fully deterministic (masking is a pure LLM-free transform) → NO Azure arm; behavioural retention deferred to the Day 3 drive-through (stronger than a synthetic probe — documented Day-2 scope decision).
- **`tests/fixtures/context_mgmt/tool_anchored_masking_cases.yaml`** (NEW): 8 single-user-turn cases (deep-tool-run / mid / many-small / few-large / prose-balanced / long-single-send 20-round / keep-1-aggressive / keep-covers-all boundary).
- **`tests/unit/scripts/test_benchmark_tool_anchored_masking.py`** (NEW): 13 CI-safe tests (importlib-shadow load mirror; real TiktokenCounter; OFF-noop / ON-reduces / keep-covers-all passthrough / keep-1-most-aggressive / fixture-verdict / build_report recommend logic incl. retention-veto + off-not-noop + below-materiality).

### A/B verdict (real TiktokenCounter, deterministic) — `recommend_default_on: True`
| metric | value |
|--------|-------|
| mean off_reduction (user-anchored, DEFAULT) | **0.00%** — confirms the single-user-turn no-op the fix targets |
| mean on_reduction (tool-anchored) | **60.83%** |
| retention_ok_rate | **100.00%** |
| **recommend_default_on** | **True** |

Per-case ON reduction 55.4%–86.6% (except `keep-covers-all` boundary 0% by design); OFF 0% on ALL cases. Report archived: `artifacts/tool_anchored_masking_report.{md,json}`.

### Gate (full, Day 2.x)
- pytest **3202 passed + 6 skipped** (baseline 3180 → +28: 5 masker + 10 factory incl. 6-param env test + 13 harness; NO regression)
- mypy `src` **400** (unchanged; scripts/ not in `mypy src` scope, mirrors 57.139 harness) · run_all **11/11** · flake8/black/isort clean (fixed 4 harness docstring E501) · LLM-SDK-leak clean (no openai/anthropic import)
- FE untouched → Vitest 927 / mockup 51 unchanged; `npm run build` N/A (0 frontend files changed)

## Day 3 — Drive-through (US-4, MANDATORY) — (pending)

## Day 4 — CHANGE-127 + closeout — (pending)
