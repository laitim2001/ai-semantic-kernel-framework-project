# Sprint 57.105 — Checklist (RBAC DB→JWT wiring: `get_user_role_codes` + DB-sourced roles claims at OIDC callback + password-login → founding admin drives admin endpoints without dev-login — closes `AD-RBAC-DB-To-JWT-Wiring-Phase58`)

[Plan](./sprint-57-105-plan.md)

**Status**: 🚧 Day 0 ✅ GO — Day 1 in progress
**Branch**: `feature/sprint-57-105-rbac-jwt-wiring`

---

## Day 0 — Plan-vs-Repo Verify + Branch ✅

### 0.1 Three-prong Day-0 verify (against `main` HEAD `ed52d435`) — DONE, catalogued in progress.md D1-D10
- [x] **Prong 1 — path verify**: `rbac.py` / `auth.py` / `jwt.py` confirmed; suites pinned: `test_jwt_auth.py` / `test_auth_me.py` / `test_password_login.py` / `test_tenant_register.py` / `test_dev_login.py` / `test_admin_tenants_rbac.py` / `unit/.../test_rbac.py`; note 23 §5 Open Invariants at L55
- [x] **Prong 2 — content verify**: 3 issue sites exact (`:299-304` / `:429-434` / `:493-498` — grep sweep proves no 4th); kw `roles=` shape; `_PASSWORD_LOGIN_ROLES` refs only `:458/:491`; JOIN liftable (`rbac.py:114-137`); both handlers `Depends(get_db_session)` request-scoped; password-login tenant key = `user.tenant_id` == JWT's (D7); **CONVERT list EMPTY** (D5 — extend-only); dev-login `_is_production()` 404 gate (D6); `AuthMeResponse{user,tenant,roles}` (`:132-135`); roles also in login response BODY (D2); 3 stale "per-request RBAC" comments to fix (D3)
- [x] **Prong 2.5 — FE tree audit**: `authStore.roles` ← `/auth/me` + login payload only (`authStore.ts:76`); zero FE code holds (D10)
- [x] **Prong 3 — schema verify**: N/A change; `Role` unique `(tenant_id, code)` + `UserRole` PK `(user_id, role_id)` confirmed read-only
- [x] **Catalog drift** in progress.md Day 0 (D1-D10 + implications; D5 shrinks Day 2 convert→extend)
- [x] **Go/no-go**: GO — scope shift ≈ 0

### 0.2 Branch
- [x] `git checkout -b feature/sprint-57-105-rbac-jwt-wiring` (from `main` HEAD `ed52d435` post-#279-merge — created at kickoff)

---

## Day 1 — Backend: role-codes query + the two issue-site rewires (US-1..US-3) ✅

### 1.1 Role-codes query (US-1)
- [x] **`RBACManager.get_user_role_codes(*, user_id, tenant_id, session) -> list[str]`** (`platform_layer/identity/rbac.py`)
  - `select(Role.code).join(UserRole).where(user_id, Role.tenant_id == tenant_id)` → sorted deduped; REQUIRES the caller's session (no self-opened factory); `has_role_code` untouched
  - DoD: mypy green ✓; unit tests (1.3) green ✓

### 1.2 Issue-site rewires (US-2/US-3)
- [x] **OIDC callback** (`api/v1/auth.py:296-310`): `roles=sorted({"user", *role_codes})` → encode; `roles=["user"]` literal retired; stale "per-request RBAC" comment fixed (D3)
  - DoD: role-less user claim byte-identical `["user"]` ✓ (existing success test green unchanged); mypy green ✓
- [x] **password-login**: same pattern into claim AND response body (D2); `_PASSWORD_LOGIN_ROLES` deleted (refs grep-confirmed `:458/:491` only); dev-login untouched
  - DoD: existing password-login tests green WITHOUT conversion (D5) ✓; `registration.py` honest-boundary docstring resolved

### 1.3 Unit tests (US-1)
- [x] **`get_user_role_codes`**: no grants → `[]`; dedup + sort (`["user","admin","admin"]` → `["admin","user"]`); cross-tenant isolation moved to integration (mock-style unit can't prove SQL filter — real-Postgres test in 2.1 does)
  - DoD: `pytest tests/unit/platform_layer/identity/ -q` 9/9 ✓

---

## Day 2 — Integration chain + conversions (US-4) ✅

### 2.1 Integration chain (US-4)
- [x] **Founding-admin chain**: register HTTP (seeds admin) → `set_password` (D11: register collects NO password — drift catalogued) → password-login → decoded claim + body `== ["admin","user"]`
- [x] **Role-less pole**: no-grant user claim exactly `["user"]` (existing success test, unchanged-green) + **cross-tenant pole**: foreign-tenant grant invisible → `["user"]` (multi-tenant 鐵律)
- [x] **`/auth/me`** roles path: claim CONTENT proven by JWT decode; claim→state→/auth/me echo already pinned by `test_auth_me.py` (echo path unchanged) — noted in progress.md; invited-role positive assertion added to the invite e2e (`["member","user"]`)
  - DoD: `test_password_login.py` 12/12 ✓; auth/identity sweep 95/95 ✓
- [x] (gate-level 200/403 poles) claim→gate behavior pinned by existing `test_require_admin_platform_role` + admin suites (Path 1 reads the claim my chain proves); real-UI admin PUT 200 lands in Day 3 drive-through

### 2.2 Hardcode-assertion conversions (Never-Delete → convert)
- [x] D5/D11 outcome: **0 conversions required** (role-less fixtures stay `["user"]`); EXTEND-only (+3 tests + 1 assertion); 0 test deletions
  - DoD: full `pytest` **2384 passed + 4 skipped** (+5, 0 deletions) ✓

---

## Day 3 — Full regression + drive-through (US-5) + CHANGE-072 + 17.md + note-23 edit

### 3.1 Full gate sweep ✅
- [x] `black . && isort . && flake8 .` (src tests) clean (1 reformat applied to the new test block)
- [x] `mypy src` 0 errors (0/357)
- [x] `python scripts/lint/run_all.py` 10/10 (event count UNCHANGED; `check_llm_sdk_leak` 0; `check_cross_category_import` green)
- [x] full `pytest` green — 2384 + 4 skipped (+5, 0 deletions)
- [x] frontend untouched: `git status` shows backend-only (5 files)
- [x] `loop.py` / DB / migration / generated wire schema diff = 0 (no such paths touched)

### 3.2 Drive-through (US-5 — founding admin drives admin endpoints with NO dev-login) — must PASS
- [ ] Clean restart (Risk Class E): kill stale uvicorn reloader + spawn-workers (`Win32_Process` PID/PPID/StartTime sweep); fresh PID sole :8000 owner; frontend node :3007 untouched
- [ ] Real UI: `/auth/register` wizard → fresh tenant + founding admin (password set) → **201**
- [ ] `/auth/password-login` as the founding admin → lands in app; **role renders admin** (ISSUE-6 "every page renders role=user" observably closed)
- [ ] tenant-settings → Model Policy tab (C1) → edit + Save → **PUT 200** (not 403) — first admin write ever driven without dev-login
- [ ] Negative probe: a role-less session (or curl with a role-less JWT) → admin PUT **403**
- [ ] Screenshots (`artifacts/dt57105-*.png`) + observed-vs-intended into progress.md Day 3
- [ ] (cleanup) revert any drive-through policy edit; note the throwaway tenant

### 3.3 CHANGE-072 + docs
- [ ] `CHANGE-072-rbac-db-to-jwt-wiring.md` (problem / design Option A / verification / open invariants: staleness + OIDC-linkage + dev-login divergence)
- [ ] design note `23-iam-registration-spike.md` §Open Invariants — RBAC-wiring invariant RESOLVED (OIDC-linkage stays open); NO new design note (gap-fix continuation)
- [ ] 17.md — JWT roles-claim sourcing semantics row updated

---

## Day 4 — Closeout

### 4.1 Closeout
- [ ] progress.md Day 0-3 complete (incl. drift catalog + drive-through observed-vs-intended)
- [ ] retrospective.md Q1-Q7 (Q2: `iam-backend-spike` 0.65 2nd-validation ratio → 3-sprint window)
- [ ] CLAUDE.md Current Sprint + Last Updated (lean, per §Sprint Closeout policy)
- [ ] MEMORY.md pointer + `project_phase57_105_rbac_jwt_wiring.md` subfile
- [ ] next-phase-candidates.md: `AD-RBAC-DB-To-JWT-Wiring-Phase58` ✅ CLOSED (+ drive-through-audit ISSUE-6 closed); next per interleave decision: C3
- [ ] sprint-workflow.md calibration row (`iam-backend-spike` 0.65 — 2nd data point)
- [ ] all checklist items `[x]` or annotated 🚧 (never delete unchecked)
