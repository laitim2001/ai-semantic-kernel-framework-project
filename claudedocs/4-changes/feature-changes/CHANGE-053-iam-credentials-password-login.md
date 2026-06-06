# CHANGE-053: IAM local credentials + password-login (C-12 Block B/C)

**Date**: 2026-06-06
**Sprint**: 57.86
**Scope**: platform_layer.identity (cross-cutting auth) + infrastructure/db + api/v1 + frontend/auth + mockup
**Closes**: `AD-Auth-Credentials-PasswordLogin-Phase58`

## Problem

57.85 invite-accept accepts `{full_name, password}` but **discarded** the password — there was no local-credential store (auth was OIDC/WorkOS + dev-login only) and no way to sign in with a password. The invite-accept "set a password" input was therefore non-functional (a soft-Potemkin). The credential leg was split to 57.86.

## Root Cause

By design (Phase-58 gap): the platform shipped OIDC-first; the `users` table had no `password_hash`, no hashing dependency, and no password-login endpoint or UI. The login mockup is OIDC-only (no password field), so a password-login UI had no mockup home.

## Solution

A full vertical slice (user-approved over backend-only/defer, to avoid a Potemkin):

- **Schema**: `bcrypt` dependency + `users.password_hash` nullable column + migration `0027_user_password_hash` (no new RLS policy — inherits `users` RLS).
- **Hashing**: `platform_layer/identity/passwords.py` — `hash_password`/`verify_password` (bcrypt cost=12, offloaded via `anyio.to_thread.run_sync`, 72-byte deterministic truncation, malformed-hash→False) + `DUMMY_HASH` (constant-time miss).
- **Service**: `platform_layer/identity/credentials.py` — `CredentialsService.set_password` + `authenticate(tenant_code, email, password)`; **every** miss mode raises one `InvalidCredentialsError` (generic 401) with a constant-time `verify_password(raw, DUMMY_HASH)` on absent paths (anti-enumeration).
- **Wiring**: `InvitesService.accept(..., password=None)` now bcrypt-hashes the password onto the new user (closes the 57.85 gap; `password=None` keeps the OIDC-only path); `api/v1/invites.py` passes `body.password` (`max_length=72`).
- **Endpoint**: `POST /api/v1/auth/password-login` (`api/v1/auth.py`) — JSON body, generic 401, V2 JWT cookie + `AuthMeResponse` (mirrors dev-login), `roles=["user"]`, `append_audit("password_login")`, NOT prod-gated; EXEMPT in `tenant_context.py`.
- **Frontend**: NEW `/auth/password-login` page (AuthShell + 3 fields + generic error; `fetchWithAuth(..., {redirectOn401:false})` so a wrong-pw 401 shows the form error rather than bouncing to SSO) + `App.tsx` route + i18n en/zh-TW + mockup `AuthPasswordLogin` (canonical source extended honestly).

PR: (pending) — branch `feature/sprint-57-86-credentials-password-login`.

## Verification

- Unit `test_passwords.py` (6) + `test_credentials_service.py` (6) + `test_invites_service.py` (+2 accept-stores-hash / regression).
- Integration `test_password_login.py` (9): success+cookie+AuthMeResponse; wrong-pw / SSO-only / unknown-tenant / unknown-email all generic 401 (identical status+body); 2-tenant isolation; **full-stack invite-accept(password)→password-login**; audit; exempt-path.
- Frontend `password-login.test.tsx` (4): renders / 200→bootstrap+navigate / 401→error no-navigate / empty-field disable.
- Gates: mypy 0/342, backend pytest **2202 passed** (+23), run_all 10/10, Vitest **761 passed** (+4), check:mockup-fidelity ✓ (`HEX_OKLCH_BASELINE` 50→53; styles-mockup.css byte-identical). Migration `0027` applied both directions.

## Impact

Backend + frontend + mockup + 1 DB column (nullable, additive). The OIDC/dev-login path is untouched. An invited user can now set a password and sign back in via `/auth/password-login`. No data migration to reverse (nullable column). Deferred (→ next-phase-candidates): brute-force lockout (`AD-Auth-PasswordLogin-Lockout-Phase58`, NEW), password-strength policy, self-service registration, MFA, recovery, a login-page discoverability link.
