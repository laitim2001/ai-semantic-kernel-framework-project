# 22 — IAM Block B/C: local credentials + password-login vertical spike (design note extract)

**Purpose**: Design note extracted from the Sprint 57.86 local-credentials vertical spike (C-12 IAM Block B/C). Documents the verified password-store + password-login path (bcrypt hash on `users`, `POST /auth/password-login`, the anti-enumeration contract, the new mockup-faithful login page), the decisions that shaped it, and the explicit deferred boundary. Per `.claude/rules/sprint-workflow.md` §Step 5.5 (spike → retrospective → extract design note); per CLAUDE.md §"V2 不是『先寫一批新規劃文件』" this was extracted from a shipped spike, NOT pre-written.
**Category / Scope**: Platform / Identity (IAM) — C-12 Block B/C / Sprint 57.86
**Created**: 2026-06-06
**Status**: Active (verified against shipped code on `feature/sprint-57-86-credentials-password-login`)

> **Modification History**
> - 2026-06-06: Initial extract from Sprint 57.86 (credentials + password-login spike)

**Related**:
- `21-iam-invites-spike.md` (Sprint 57.85 — the invites slice this credentials leg completes)
- `20-iam-deep-dive.md` (Block A — JWT / OIDC / DB-RBAC reused here)
- `09-db-schema-design.md` §Group 1 Identity & Tenancy
- `c12-iam-block-bc-analysis-20260601.md` §4-§5 (thin-spike discipline)

---

## 1. Spike Summary (US-1..US-5)

An invited user who sets a password at invite-accept (57.85's `password` was accepted-not-stored) now has it **bcrypt-hashed onto `users.password_hash`**, and can **sign back in without SSO** via `POST /api/v1/auth/password-login` (tenant_code + email + password → V2 JWT cookie + `AuthMeResponse`), through a NEW mockup-faithful `/auth/password-login` page. The OIDC/dev-login path is untouched.

**Verified scope**: bcrypt hash/verify (offloaded), invite-accept password storage, `(tenant_code, email)` authentication, single generic-401 for every failure mode (anti-enumeration), 2-tenant isolation, full-stack invite-accept→password-login, the new page (POST→bootstrap→navigate). **Deferred** (see §5): brute-force lockout, password-strength policy, self-service registration, MFA, password recovery, a discoverability link from the OIDC login page.

---

## 2. Decision Matrix

### 2.1 Hash algorithm (US-1) — **bcrypt direct** chosen

| Option | Maintained | passlib layer | Tuning | Verdict |
|--------|-----------|---------------|--------|---------|
| **bcrypt direct** (chosen) | ✅ (active) | none | cost only | **CHOSEN** — simplest; no passlib bcrypt-4.x compat noise |
| argon2-cffi | ✅ | none | time+memory+parallelism | rejected — stronger but extra tuning for a spike |
| passlib[bcrypt] | ⚠️ (passlib stale) | yes | cost | rejected — passlib has known bcrypt-4.x warnings; needs pin |

bcrypt cost=12 (`passwords.py:_BCRYPT_ROUNDS`). hash/verify are sync/CPU-bound so both offload via `anyio.to_thread.run_sync` (`passwords.py:hash_password` / `verify_password`). bcrypt only hashes the first 72 bytes → both encode + **truncate to 72 bytes** (`passwords.py:_to_bcrypt_bytes` / `_BCRYPT_MAX_BYTES`) so behaviour is deterministic + version-independent (bcrypt 4.x may raise on >72 bytes); `verify` swallows a malformed-hash `ValueError` → `False` (never raises). API password fields are capped `max_length=72` (`api/v1/invites.py:InviteAcceptRequest`, `api/v1/auth.py:PasswordLoginRequest`).

### 2.2 Credential storage (US-1) — **nullable `users.password_hash` column** chosen

| Option | Schema cost | RLS | Fits repo | Verdict |
|--------|-------------|-----|-----------|---------|
| **`users.password_hash` nullable** (chosen) | 1 ALTER | inherits `users` RLS (no new policy) | ✅ lean monolithic identity | **CHOSEN** |
| separate `user_credentials` table | 1 table + 2 RLS policies | new policies | ✗ over-structured for one credential type | rejected (YAGNI) |

`User.password_hash: Mapped[str | None]` (`infrastructure/db/models/identity.py`), `VARCHAR(255)`, nullable (OIDC-only users have none). Migration `0027_user_password_hash` (`down_revision=0026_invites`) is a plain `add_column` — **no new RLS policy** (the column inherits the existing row-level `users` RLS; `check_rls_policies` stays green).

### 2.3 Password-login UI scope — **full slice + new mockup-faithful page** chosen

Day-0 found password-login has **no UI consumer in the mockup** (login mockup is OIDC-only; no password-login screen). Storing a password with no verifier, a verifier with no UI, or inventing a fidelity-absent page each violates a hard constraint (約束 2 主流量驗證 / AP-4 Potemkin / Mockup-Fidelity). Decision (user, AskUserQuestion): build the full slice **and** extend the canonical mockup (`page-auth-extras.jsx:AuthPasswordLogin` + `i18n.jsx`) so the production page has a real mockup parent — a deliberate, user-approved source-of-truth extension, NOT a drift.

### 2.4 Tenant resolution (US-2) — **tenant-code field** chosen

Email is per-tenant unique (`uq_users_tenant_email`) → the same email can exist in multiple tenants. The login form carries a **tenant code**; the endpoint resolves the tenant by `Tenant.code` (the RLS-free root, `identity.py:116`) then the user by `(tenant_id, email)`. Global-email-unique was rejected (breaks the multi-tenant schema); invite-only-context was rejected (no true return login).

---

## 3. Verified Invariants (file:line + verification)

| Invariant | Evidence | Verification |
|-----------|----------|--------------|
| bcrypt round-trip; hash ≠ raw; `$2b$12$` format | `passwords.py:hash_password`/`verify_password` (cost=12, anyio offload) | `test_passwords.py` (6) |
| 72-byte truncation deterministic; malformed hash → False (no raise) | `passwords.py:_to_bcrypt_bytes` + `_verify_sync` try/except | `test_passwords.py::test_72_char_password_verifies` / `::test_verify_malformed_hash_returns_false` |
| invite-accept stores the password (closes 57.85 gap); `password=None` keeps OIDC-only | `invites.py:accept(..., password=None)` → `CredentialsService().set_password` | `test_invites_service.py::test_accept_stores_password_hash` / `::test_accept_without_password_leaves_hash_none` |
| authenticate resolves tenant-by-code → user-by-(tenant,email) → bcrypt verify | `credentials.py:authenticate` | `test_credentials_service.py::test_authenticate_success_returns_user` |
| **Every** miss mode raises ONE `InvalidCredentialsError` (anti-enumeration) | `credentials.py:authenticate` (unknown tenant / email / no-hash / wrong-pw all → same error) | `test_credentials_service.py` (4 miss tests) + `test_password_login.py` (generic-401 ×4) |
| Constant-time miss (no timing enumeration) | `credentials.py:authenticate` runs `verify_password(raw, DUMMY_HASH)` on the user-absent/no-hash path; `passwords.py:DUMMY_HASH` | (design invariant; exercised by the generic-401 tests) |
| password-login → V2 JWT cookie + AuthMeResponse (mirrors dev-login) | `auth.py:password_login` (`JWTManager().encode` + `set_cookie(_JWT_COOKIE)` + `AuthMeResponse`) | `test_password_login.py::test_password_login_success` (cookie `JWTManager().verify`) |
| Single generic 401 (identical status+body) across all failures | `auth.py:password_login` maps `CredentialsError`→`HTTPException(401, "Invalid credentials")` | `test_password_login.py` `_assert_generic_401` across 4 modes |
| 2-tenant isolation (same email, own tenant_code+password only) | `credentials.py:authenticate` `(tenant_id, email)` scope | `test_password_login.py::test_two_tenant_isolation` |
| Full-stack: invite-accept(password) → password-login succeeds | end-to-end through both routers | `test_password_login.py::test_invite_accept_then_password_login` |
| password-login exempt (pre-JWT); `/auth/me` NOT | `tenant_context.py:EXEMPT_PATH_PREFIXES` += `/api/v1/auth/password-login` | `test_password_login.py::test_exempt_path_contract` |
| Login audit on success | `auth.py:password_login` `append_audit("password_login")` | `test_password_login.py::test_audit_row_on_success` |
| Frontend: 401 shows form error, no SSO bounce | `password-login/index.tsx` `fetchWithAuth(..., {redirectOn401:false})` | `password-login.test.tsx::submit 401 …` |

**Verification command**:
```
cd backend && python -m pytest tests/unit/platform_layer/identity/test_passwords.py tests/unit/platform_layer/identity/test_credentials_service.py tests/integration/api/test_password_login.py -q
cd frontend && npx vitest run tests/unit/pages/auth/password-login.test.tsx
```
**Test fixtures**: `tests/conftest.py` (`db_session`, `seed_tenant`, `seed_user`); integration `_build_app` (X-Test headers + override `get_db_session`/`require_admin_platform_role`) mirrors `test_invites.py`. Gates: mypy 0/342, full backend pytest 2202, run_all 10/10, Vitest 761, check:mockup-fidelity (HEX_OKLCH_BASELINE 50→53).

---

## 4. Cross-Category Contracts (17.md assessment)

**17.md = N/A** (assessed, same call as 57.84 / 57.85). `17-cross-category-interfaces.md` registers the 11+1 **category** contracts; `platform_layer.identity` is not a registered category surface there (sibling `auth.py` / `jwt.py` / `invites.py` are absent too). The contracts live in this design note + the module docstrings + CHANGE-053. The endpoint→frontend contract is `AuthMeResponse {user{id,email,display_name}, tenant{id,name,code}, roles}` (`api/v1/auth.py:AuthMeResponse` ↔ `authStore.bootstrap` via GET `/auth/me`); the request contract is `{tenant_code, email, password}` (`PasswordLoginRequest` ↔ `password-login/index.tsx`).

---

## 5. Open Invariants (deferred — NOT verified here)

- **Brute-force / lockout throttle** — `AD-Auth-PasswordLogin-Lockout-Phase58` (NEW). No per-tenant login-attempt counter; bcrypt cost=12 + the generic-401 raise the per-guess cost but there is no rate limit. The Redis rate-limit-counter infra (57.48/57.58) is a candidate substrate.
- **Password-strength policy** — invite-accept keeps `min_length=1`; password fields gain only `max_length=72` (bcrypt safety). Min length / complexity / breach-check are a follow-up.
- **Self-service tenant registration** — `AD-Auth-Register-Backend-IAM-Block-B-Phase58` (POST /tenants/register + first admin + password).
- **MFA TOTP + WebAuthn** — `AD-Auth-MFA-Backend-IAM-Block-C-Phase58`; password-login lands the user via `consumePostLoginRedirect()` (MFA step-up is separate).
- **Password reset / recovery** — `AD-Auth-Recovery-Page-Phase58`; `/auth/recovery` does not exist.
- **Login-page discoverability link** — the OIDC `/auth/login` page does NOT link to `/auth/password-login` (kept pristine per mockup); `/auth/password-login` is reachable by direct route + is its own real consumer. A mockup-gated link is a follow-up.
- **DB-level RLS enforcement is NOT exercised in tests** — the `ipa_v2` test DB role is a superuser (bypasses RLS); `password_hash` inherits the `users` RLS which enforces in production under a non-superuser role. Isolation is asserted at the application layer here (per the codebase convention).
- **Per-verifier timing constancy is not measured** — the constant-time-miss design (DUMMY_HASH) is asserted structurally (one verify on every path), not via a timing benchmark (flaky).

---

## 6. Rollback

- **Backend**: revert the 2 NEW files (`passwords.py`, `credentials.py`) + `0027_user_password_hash.py` + the `auth.py` endpoint + the `invites.py`/`api/v1/invites.py` password wiring + the `tenant_context.py` exempt entry + the `User.password_hash` column. DB: `alembic downgrade -1` drops the column (nullable; no data to migrate; SSO users unaffected). Drop `bcrypt` from requirements. Est. < 30 min.
- **Frontend**: revert `password-login/index.tsx` + `App.tsx` route + the i18n keys + the mockup `AuthPasswordLogin` + the `HEX_OKLCH_BASELINE` bump (53→50). The invite-accept page still stores the password (backend) — only the standalone login page disappears.
- **Safety**: the password-login path is additive (new column nullable, new endpoint, new page); the OIDC/dev-login path is untouched, so a rollback degrades to "invited users set a password that only the (now-reverted) endpoint could check" — no data loss, no OIDC regression.

---

## 7. References

- Code: `backend/src/platform_layer/identity/passwords.py`, `backend/src/platform_layer/identity/credentials.py`, `backend/src/infrastructure/db/models/identity.py` (User.password_hash), `migrations/versions/0027_user_password_hash.py`, `backend/src/platform_layer/identity/invites.py` (accept wiring), `backend/src/api/v1/invites.py`, `backend/src/api/v1/auth.py` (password_login), `backend/src/platform_layer/middleware/tenant_context.py`, `frontend/src/pages/auth/password-login/index.tsx`, `frontend/src/App.tsx`, `reference/design-mockups/page-auth-extras.jsx` (AuthPasswordLogin)
- Tests: `backend/tests/unit/platform_layer/identity/test_passwords.py`, `test_credentials_service.py`, `backend/tests/integration/api/test_password_login.py`, `frontend/tests/unit/pages/auth/password-login.test.tsx`
- Change record: `claudedocs/4-changes/feature-changes/CHANGE-053-iam-credentials-password-login.md`
- Plan / checklist / progress / retrospective: `phase-57-frontend-saas/sprint-57-86-{plan,checklist}.md` + `agent-harness-execution/phase-57/sprint-57-86/{progress,retrospective}.md`
