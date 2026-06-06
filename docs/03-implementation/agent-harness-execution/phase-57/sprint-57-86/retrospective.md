# Sprint 57.86 Retrospective — C-12 IAM Block B/C: local credentials + password-login spike

**Closed**: 2026-06-06
**Closes**: `AD-Auth-Credentials-PasswordLogin-Phase58` (local-password leg of C-12)
**Branch**: `feature/sprint-57-86-credentials-password-login` (from `main` `f61df966`)

---

## Q1 — What was delivered?

The local-credentials vertical slice: `bcrypt` dep + `users.password_hash` (migration `0027`) + `passwords.py` (hash/verify, anyio offload, 72-byte guard, DUMMY_HASH) + `CredentialsService` (set_password/authenticate, generic-401 anti-enumeration + constant-time miss) + invite-accept password storage (closes 57.85's accepted-not-stored gap) + `POST /auth/password-login` (JSON body, generic 401, JWT/cookie/AuthMeResponse mirror dev-login, exempt) + a NEW mockup-faithful `/auth/password-login` page (+ route + i18n + mockup `AuthPasswordLogin`). 23 backend tests + 4 frontend tests. Design note `22-iam-credentials-spike.md`.

## Q2 — Calibration (estimate accuracy)

- **Scope class**: `medium-backend` 0.80. **Agent-delegated: no** (parent-direct; `agent_factor` 1.0 → 3-segment).
- Bottom-up est ~10.5 hr → class-calibrated commit ~8.4 hr (×0.80).
- **Actual ≈ 9.5-10 hr** → `actual/committed ≈ 1.15-1.2` (greenfield-IAM over-run, as the plan flagged).
- **2nd consecutive greenfield-IAM over-run** (57.85 ~1.25 + 57.86 ~1.15-1.2 at `medium-backend` 0.80). Per the plan's flag → **PROPOSE a new `iam-backend-spike` scope class (~0.65)** for the next IAM backend spike (register / MFA). Do NOT pre-create — log as `AD-Sprint-Plan-IAM-Backend-Spike-Class` for the next IAM sprint to adopt. The over-run source is genuine greenfield judgment (token/RLS in 57.85; bcrypt offload + anti-enumeration + the no-mockup-UI fork here), not estimation noise.

## Q3 — What went well?

- **Day-0 fork surfaced + resolved upfront** (AskUserQuestion ×2): the no-mockup-UI Potemkin/fidelity tension was the make-or-break; resolving it before code (full-slice + mockup extension) prevented a mid-sprint scope crisis.
- **SAFE CUT-LINE held**: Day-2-end (passwords + credentials + storage + 25 service tests) was a real, provable partial-ship line before any HTTP/UI wiring.
- **Two real bugs caught by tests, not prod**: (1) the `fetchWithAuth` 401 → "session expired" bounce (would have made a wrong password kick the user to SSO with a misleading toast) — fixed with `{redirectOn401:false}`; (2) the oklch silent-delta (Day-0 Prong-2 lesson) — bumped `HEX_OKLCH_BASELINE` in-sprint, not a post-merge CI hotfix.
- **Full-stack e2e test** (invite-accept(password)→password-login) proves the stored hash round-trips through the whole stack — the strongest non-Potemkin evidence.

## Q4 — What to improve / lessons?

- **`fetchWithAuth` 401 semantics**: a login form must opt out of the auto-"session expired" redirect (`{redirectOn401:false}`). Worth noting for the future register/recovery login forms — they'll hit the same trap.
- **bcrypt 72-byte limit** is a quiet footgun; the deterministic-truncate + `max_length=72` pattern in `passwords.py` should be the reference for any future credential code.
- The new-page oklch bump was predictable from Day-0 (the page reuses the sibling auth pages' DangerNote/avatar tints); next time pre-state the expected `+N` in the plan §mockup-fidelity to avoid the mid-Day-3 surprise (it was caught, but the plan said "delta 0" which was wrong — the reuse-without-new-literals assumption only holds when importing a shared component, not when rebuilding the alert inline).

## Q5 — Anti-pattern audit (04)

- AP-2 (side-track): ✅ password-login reachable from `api/v1/auth.py` main router; the page is a real route + tested consumer.
- AP-4 (Potemkin): ✅ the central risk — resolved by the full slice + the full-stack e2e + the new UI consumer (not backend-only).
- AP-6 (YAGNI bridge): ✅ chose the `users` column over a `user_credentials` table; dropped the unused `db` param from `set_password`.
- AP-10 (mock vs real): ✅ the credential path is real Postgres in tests; the frontend mocks only `fetch`/`bootstrap`/`navigate`.
- AP-11 (version suffix): ✅ none.

## Q6 — Carryover (→ `next-phase-candidates.md`)

- `AD-Auth-PasswordLogin-Lockout-Phase58` (NEW) — brute-force/lockout throttle.
- Password-strength policy (min-length/complexity/breach-check).
- `AD-Auth-Register-Backend-IAM-Block-B-Phase58` — self-service registration.
- `AD-Auth-MFA-Backend-IAM-Block-C-Phase58` — MFA TOTP/WebAuthn.
- `AD-Auth-Recovery-Page-Phase58` — password reset.
- Login-page discoverability link to `/auth/password-login` (mockup-gated).
- `AD-Sprint-Plan-IAM-Backend-Spike-Class` (NEW) — propose `iam-backend-spike` 0.65 (2 greenfield-IAM over-runs).

## Q7 — Gates (final)

mypy **0/342** · backend pytest **2202 passed** / 4 skipped (+23) · `run_all.py` **10/10** · frontend lint(no `--silent`)+build green · Vitest **761 passed** (+4) · `check:mockup-fidelity` ✓ (HEX_OKLCH_BASELINE 50→53; styles-mockup.css byte-identical) · migration `0027` both directions.

---

## Design Note Extract (spike sprint)

**File**: `docs/03-implementation/agent-harness-planning/22-iam-credentials-spike.md`
**Verified ratio (estimated)**: ~96% (every §3 invariant carries a file:line symbol + a named test; the deferred §5 items are clearly fenced)
**8-Point Quality Gate**:
- [x] 1. Section header maps to spike US (§1 US-1..US-5; §2 per-decision; §3 invariants)
- [x] 2. file:line / symbol per technical claim (§3 table — passwords.py / credentials.py / auth.py / invites.py symbols)
- [x] 3. Decision rationale has comparison matrix (§2.1 hash algo / §2.2 storage / §2.3 UI scope / §2.4 tenant resolution)
- [x] 4. Verification command reproducible (§3 pytest + vitest commands)
- [x] 5. Test fixture reference (§3 conftest + `_build_app`)
- [x] 6. Open invariant boundary explicit (§5 deferred, NOT verified — lockout / strength / register / MFA / recovery / RLS-under-superuser / timing)
- [x] 7. Rollback path (§6 — additive; nullable column; OIDC untouched)
- [x] 8. 17.md cross-ref (§4 — N/A assessment, same call as 57.84/57.85; contracts in design note + docstrings + CHANGE-053)

**Reviewer pass**: self-review (parent).
