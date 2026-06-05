# Sprint 57.83 — Checklist (B-8 leg-2: general judge template + real-LLM e2e + data-gated flip)

**Plan**: `sprint-57-83-plan.md`
**Branch**: `feature/sprint-57-83-verification-enable` (from `main` `ee8d4cc9`)
**Closes**: B-8 **blocker B + C + flip** (final leg; flip is data-gated per Q2). Closes `AD-Cat10-Wire-1-Production` IF flipped.

---

## Day 0 — Plan-vs-Repo Verify + Branch + Decisions

### 0.1 Day-0 verify (parent grep + code read, main `ee8d4cc9`)
- [x] **Prong 1 (path)** — confirm: `verification/templates/*.txt` (4 existing), `verification/llm_judge.py` (_build_prompt load_template), `core/config/__init__.py` (both defaults), `_category_factories.py` (make_chat_verifier_registry), `tests/unit/core/test_config_verification.py`, `tests/unit/agent_harness/verification/test_judge_templates.py`.
- [x] **Prong 2 (content)** — 4 templates all special-purpose (safety/factual/format/pii) → NO general quality judge; `chat_verification_judge_template`="safety_review", `chat_verification_mode`="disabled"; real_llm is a chat MODE not a pytest marker (real-LLM e2e = manual local backend + real Azure); `test_config_verification.py:37` asserts mode=disabled (must update iff flip); echo_demo unaffected (no registry regardless of mode); leg-1 judge→ledger wiring means enabled run writes `_verification` entries (cost measurement free).
- [x] **Prong 3 (schema)** — N/A (no DB / migration / ORM change).
- [x] **Design locked** (AskUserQuestion 2026-06-05): Q1 = general quality judge (helpful/complete/accurate/on-topic, fail on any); Q2 = data-driven gate (flip only if FP rate / latency / cost acceptable).
- [x] **go/no-go** — GO; leg 2 = blocker B + C + (gated) flip.

### 0.2 Branch + decisions
- [x] **Branch created** `feature/sprint-57-83-verification-enable`
- [x] **Decisions locked**: NEW `output_quality.txt` general judge (single judge, NOT combine-with-safety, NOT factual-rework); default template swap → output_quality; real-LLM measurement = manual local-backend run with real Azure (user-authorized Q2); flip is conditional on measured data (FP ≤ ~15%, p95 < 5s); parent-direct.
- [x] **Day-0 commit** plan + checklist + progress.md Day 0 (`6d82af71`)

---

## Day 1 — Blocker B: general quality judge template (US-1/US-2)

### 1.1 output_quality template
- [x] **NEW `verification/templates/output_quality.txt`** — general quality judge (helpful/complete/accurate/on-topic, fail on any dimension); JSON shape `passed`/`score`/`reason`/`suggested_correction`; contains literal `{output}`; "normal answer should pass / lean pass when uncertain" (low-FP intent)
  - DoD: loads via `load_template("output_quality")` (auto-read by glob, no registration); not a safety-lean phrasing ✅

### 1.2 default judge template swap
- [x] **`core/config/__init__.py`** — `chat_verification_judge_template` default `"safety_review"` → `"output_quality"` + update docstring example (+ templates/__init__.py docstring list)
  - DoD: mypy clean; mode stays `disabled` (flip is Day 3) ✅

### 1.3 unit tests + gate
- [x] **`test_judge_templates.py`** (extend) — output_quality in parametrize (5 templates) + dedicated test (4 dimensions + `{output}` + lean-pass guard)
- [x] **`test_config_verification.py`** — `TestChatVerificationJudgeTemplate` default == output_quality (mode default test unchanged — flip is Day 3)
- [x] **black + isort + flake8 + mypy src/** — clean (4 files unchanged / flake8 0 / mypy 0 in 332 / pytest 12 passed)

---

## Day 2 — Blocker C: real-LLM e2e measurement (US-3) — real Azure, user-authorized

### 2.1 measurement setup
- [x] **Confirm `.env` Azure secrets** live (5 keys SET) + user authorized full-stack run (AskUserQuestion)
- [x] **Clean local backend** (Risk Class E): Docker (postgres Healthy + redis) + no-reload backend `CHAT_VERIFICATION_MODE=enabled` + output_quality; 3 wiring lines confirmed

### 2.2 run measurement
- [x] **K=8 normal + 2 nonsense prompts** (mode=real_llm) → pass 1 (fail-on-any) FP ~75% → re-tune lightweight → pass 2 FP 0%; bad always caught
- [x] **Compute**: pass 2 FP 0% / normal ~5s (0 corrections) / judge ~$0.0047/chat
- [x] **Record** in `claudedocs/5-status/cat10-verification-real-llm-measurement-20260605.md` (both passes + verdict)

---

## Day 3 — Data-gated flip decision (US-4) + tests

### 3.1 flip decision
- [x] **Evaluate** — FP 0% << 15% (pass 2 lightweight) + bad caught → gate PASS → flip
- [x] **IF acceptable** (TAKEN): config mode default → `enabled`; grep confirmed only `test_config_verification` depended on the default; updated `test_default_is_enabled`; B-8 fully closed
- [x] **ELSE** (N/A — gate PASSED on pass 2; the disabled-keep branch was effectively exercised in pass 1 then re-tuned in-sprint, not deferred)

### 3.2 regression
- [x] **full pytest 2150 passed** — flip broke nothing (all mode-dependent tests setenv explicitly)

---

## Day 4 — Sweep + Closeout

### 4.1 Full sweep
- [x] **Backend gates** — black/isort/flake8 0 + `mypy src/` 0 (332) + `pytest` 2150 passed/4 skipped + `run_all.py` 10/10 (check_llm_sdk_leak + check_event_schema_sync green)
- [x] **No frontend** — backend + docs only
- [x] **Read all changed code** — final pass

### 4.2 Closeout docs
- [x] **CHANGE-050** in `claudedocs/4-changes/feature-changes/`
- [x] **progress.md** Day 0-4 + **retrospective.md** Q1-Q7 (flip decision + 2-pass measurement data)
- [x] **Checklist** all `[x]` (no 🚧 carryover)
- [x] **Calibration** record (medium-backend 0.80; agent_factor 1.0 parent-direct; ratio ~1.14; real-LLM measurement wall-clock variance noted)
- [x] **AD status**: B-8 blocker B+C + flip CLOSED; `AD-Cat10-Wire-1-Production` CLOSED (flipped); 完整 B-8 epic COMPLETE; next-phase-candidates.md updated
- [x] **MEMORY subfile + pointer** + **CLAUDE.md lean** (Current Sprint + Last Updated)
- [x] **Design note?** — NO (template + config + measurement artifact; no new contract)

### 4.3 Ship
- [x] **Commit mapping** Day-0 (`6d82af71`) / Day-1 template+default (`d27401e2`) / Day2-3-4 measurement+flip+closeout (pending)
- [ ] **Push + PR** (user-gated — explicit authorization required)
