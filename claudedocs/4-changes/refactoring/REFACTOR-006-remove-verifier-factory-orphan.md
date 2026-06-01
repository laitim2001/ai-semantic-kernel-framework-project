# REFACTOR-006: Remove production-orphan `_verifier_factory.py` (B-10)

**Date**: 2026-05-31
**Sprint**: B 區優化分析 / B-10 (non-sprint chore)
**Scope**: 範疇 10 (Verification Loops) wiring — `api/v1/chat`
**AD**: `AD-Cat10-VerifierFactory-Disposition` (closed)

## Problem

`backend/src/api/v1/chat/_verifier_factory.py` (Sprint 55.5) became production-orphan
after Sprint 57.63 approach A moved verifier-registry construction into
`build_real_llm_handler` (`make_chat_verifier_registry`, builds a real
`LLMJudgeVerifier` sharing the loop's adapter). The factory's two functions
(`build_default_verifier_registry` / `select_verifier_registry`) had **zero
production callers** — only tests referenced them. This is an AP-2 (Side-Track Code
Pollution) instance, and the no-op `RulesBasedVerifier(rules=[])` default it returned
was a latent Potemkin (emits `VerificationPassed` without verifying).

## Root Cause

Sprint 57.63 approach A superseded the factory but deferred its disposition (kept
intact under Never-Delete-Tests pending user decision — `AD-Cat10-VerifierFactory-Disposition`).
The orphan is a 57.63-produced dead reference (Karpathy §3: "your change's orphan is
yours to clean").

## Solution

User-confirmed disposition (a) delete + bounded test migration (2026-05-31):

1. **Deleted** `backend/src/api/v1/chat/_verifier_factory.py`.
2. **Retired** `backend/tests/unit/api/v1/chat/test_verification_wire.py` factory tests
   (`TestBuildDefaultVerifierRegistry` + `TestSelectVerifierRegistry`) — they tested the
   removed code; retiring tests of deleted functionality does NOT violate Never-Delete-Tests.
3. **Migrated** (not deleted) `test_invalid_mode_raises` → new
   `backend/tests/unit/core/test_config_verification.py` — it tests
   `Settings.chat_verification_mode` pydantic Literal validation, which is independent of
   the factory and has standalone value (preserved + 2 sibling tests added for coverage).
4. **Inlined** the no-op registry helper in `test_chat_verification_smoke.py:154`
   (`VerifierRegistry()` + `RulesBasedVerifier(rules=[])` direct from `agent_harness.verification`).
5. **Cleaned** 2 stale comments that referenced the removed symbols
   (`_category_factories.py` docstring + `router.py` inline comment) — Karpathy §3 orphan cleanup.

## Verification

- `pytest tests/unit/core/test_config_verification.py tests/integration/api/test_chat_verification_smoke.py tests/unit/api/v1/chat/` → **49 passed**
- `black --check` / `isort --check-only` / `flake8` on touched files → **0**
- `mypy src/api/v1/chat/router.py src/api/v1/chat/_category_factories.py` → **Success: no issues found in 2 source files**
- `python scripts/lint/run_all.py` → **9/9 PASS** (incl. `check_ap2_side_track` — confirms the side-track is eliminated)
- `git grep "_verifier_factory|build_default_verifier_registry|select_verifier_registry" -- backend/src backend/tests` → **0 hits**

## Impact

Backend-only. No production behavior change (the factory was already unused on the
production path since Sprint 57.63). Net: −2 files, +1 migrated test file, −2 stale comments.
Closes `AD-Cat10-VerifierFactory-Disposition`.
