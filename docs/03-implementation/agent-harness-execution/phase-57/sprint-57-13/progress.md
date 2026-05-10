# Sprint 57.13 Progress — Frontend Foundation 1/N Completion + Frontend↔Backend Wiring 全打通

> Branch: `feature/sprint-57-13-frontend-foundation-completion` (from main `75c74d32`)
> Calibration: `frontend-foundation-spike` HYBRID 0.50 (1st application) — bottom-up ~49-65 hr → committed ~25-32 hr / Day 0-9
> ⚠️ Large Foundation sprint (~2x normal). Per user 2026-05-10 directive — 完全集中、不簡化、不切分.
> 15 USs: A1-A5 (auth wiring 打通) + B1-B9 (frontend architecture 基建) + C1 (closeout).

---

## Day 0 Accomplishments (2026-05-10) — Setup + 三-prong + Calibration

### Branch + Baselines
- Branch `feature/sprint-57-13-frontend-foundation-completion` from main `75c74d32`
- pytest **1658 collected** (1654 pass + 4 skip) / mypy --strict **0/305** / 9 V2 lints **9/9** / Vitest **168/45 files** / Playwright **37/14 files** / Vite build main **296.58 kB (gzip 93.48)** / LLM SDK leak **0**

### Plan + Checklist
- `sprint-57-13-plan.md` (NEW, ~9 sections, ~700+ lines — mirrors 57.12 structure; 15 USs)
- `sprint-57-13-checklist.md` (NEW, Day 0-9, ~10 days)
- this `progress.md` (NEW)

### User decision points (pre-confirmed via AskUserQuestion 2026-05-10)
- 全做（不只連通）— 完整 Foundation 1/N + frontend↔backend wiring，不簡化、不切分
- US-A1 auth fix = **cookie-only + GET /auth/me**（推薦案）
- Branch name confirmed

### Day 0 三-prong verify — Drift Catalog (10 D-PRE findings; 1 🔴 / 4 🟡 / 5 🟢)

| ID | Severity | Finding | Resolution |
|----|----------|---------|------------|
| **D-PRE-1** | 🟢 GREEN | Frontend dev port = **3007** (not 3005 — CLAUDE.md "3005" is V1; vite.config.ts L18 `port: 3007` since Sprint 57.5 D-21 port drift fix) | Plan/checklist updated — use 3007; dev setup doc note 3007 |
| **D-PRE-2** | 🟢 GREEN | Playwright `E2E_PORT` default **5173**, baseURL `http://localhost:5173`; webServer auto-starts `npm run dev --port 5173` (local) / `npm run preview` (CI); vite proxy `/api` → :8000 works from 5173 too | connectivity/a11y/visual specs run against 5173 dev server + need backend on :8000 for real-backend tests (opt-in via env) — plan §US-A5/B6/B8 already accounts |
| **D-PRE-3** | 🟡 YELLOW | `Settings.env` default = `"development"` (not `"dev"`) — plan said `env != "prod"` / `env == "prod"` | dev-login gate = `Settings.env.lower() not in ("production", "prod")` → allow; else 404. Adjust US-A4 impl |
| **D-PRE-4** | 🟡 YELLOW | `Settings.cookie_secure` does NOT exist | US-A1 adds `cookie_secure: bool = False` to Settings (註解 prod True) |
| **D-PRE-5** | 🟡 YELLOW | `Settings.oidc_redirect_uri` default = `http://localhost:3005/auth/callback` — **doubly wrong**: (a) port 3005 is V1, (b) `/auth/callback` is frontend path but OIDC code-exchange needs backend (client secret) | US-A1 changes to `http://localhost:8000/api/v1/auth/callback` (註解: prod via reverse proxy `/api/v1/auth/callback`) |
| **D-PRE-6** | 🟢 GREEN | `class-variance-authority@^0.7.1` is **already installed** (+ `sonner@^1.7.4` + `@radix-ui/react-dialog@^1.1.15` + `@radix-ui/react-slot@^1.2.4` + `tailwind-merge@^3.5.0`) | US-B2/B3 skip `npm i class-variance-authority` — one less install |
| **D-PRE-7** | 🟢 GREEN | NEW paths confirmed don't exist: `api/v1/telemetry.py`, `api/_deps.py`, `features/auth/store/authStore.ts`, `lib/toast.ts`, `lighthouserc.js`; not-installed confirmed: `@radix-ui/react-dropdown-menu`, `@sentry/react`, `web-vitals`, `i18next`, `react-i18next`, `eslint-plugin-jsx-a11y`, `@axe-core/playwright`, `@lhci/cli` | Plan §File Change List correct |
| **D-PRE-8** | 🔴 RED (scope-confirming, not abort) | `tenant_context.py` `EXEMPT_PATH_PREFIXES = ("/api/v1/health",)` — **ONLY `/health` is exempt**. So `/api/v1/auth/login` + `/callback` currently hit middleware → no Bearer → 401 → **the OIDC flow has never worked end-to-end** (confirms user observation). | US-A1 adds to `EXEMPT_PATH_PREFIXES`: `/api/v1/auth/login`, `/api/v1/auth/callback`, `/api/v1/auth/dev-login`, `/api/v1/auth/logout`, `/api/v1/telemetry`. NOT `/api/v1/auth/me` (needs JWT; 401 is correct). Folded into US-A1 (was US-A5 allowlist note — promote to US-A1 since it's part of "make auth flow work"). |
| **D-PRE-9** | 🟢 GREEN | `JWTManager.encode(*, sub: str, tenant_id: UUID, roles, extra)` → HS256; `decode()` → `JWTClaims` dataclass (`sub`/`tenant_id`/`roles`/`iat`/`exp`/`extra`) — matches plan §Tech Spec | No change |
| **D-PRE-10** | 🟢 GREEN | admin `{tenant_id}` path endpoints use `Depends(require_admin_platform_role)` from `platform_layer/identity/auth.py` — `require_tenant_match_or_platform_admin` is NEW (doesn't exist) | Plan §US-A3 correct |

**Scope impact**: 0 abort-level findings. D-PRE-8 confirms the auth flow is genuinely broken (matches user report) — US-A1 already covers the fix; just promote the `EXEMPT_PATH_PREFIXES` change from US-A5-note to US-A1-core. Net scope shift < 5%.

**Open content-verify items to confirm at Day 1 start** (Prong 2 not exhaustively done — these are low-risk impl details): exact `JWTManager.encode` kwarg names beyond `sub`/`tenant_id`; whether `RBACManager` is class or fn; `App.tsx` exact route wrapping (Explore report says auth routes rendered bare, AuthShell exists but unused by login/callback — confirm); the 4 ungated pages' exact tenant_id sourcing line. None gate Day 1.

### Calibration
- Class `frontend-foundation-spike` HYBRID 0.50 (1st application; 1-data-point opens) — bottom-up ~49-65 hr → committed ~25-32 hr; Day 0-9 (10 days)
- Weighted blend: Group A (auth/dev-login/smoke) `backend-auth × 0.65` ~30% + Group B (Toast/design-system/Radix) `frontend-arch-greenfield × 0.50` ~30% + Group B (Sentry/i18n/a11y/Lighthouse/visual) `frontend-infra-new × 0.45` ~25% + Group B (AuthShell/inline) `frontend-pattern-reuse × 0.35` ~10% + Group C closeout `× 0.80` ~5% → ~0.50
- Day 4 retrospective Q2 mid-sprint ratio check; |delta| > 30% → log AD-Sprint-Plan-N

---

## Remaining for Day 1-9

- [ ] Day 1: US-A1 — cookie fallback middleware + `EXEMPT_PATH_PREFIXES` fix (D-PRE-8) + GET /auth/me + config oidc_redirect_uri+cookie_secure + authStore + authService + App bootstrap + callback rewire + 5-page gate + tests
- [ ] Day 2: US-A2 (4-page gate + tenant-from-authStore) + US-A3 (cross-tenant hardening) + US-A4 (dev-login)
- [ ] Day 3: US-A5 (connectivity smoke + .env.example) + US-B1 (Toast)
- [ ] Day 4: US-B2 (design-system component layer + refactor 6 feature areas) + mid-sprint ratio check
- [ ] Day 5: US-B3 (Radix Dialog+DropdownMenu + DecisionModal+UserMenu refactor)
- [ ] Day 6: US-B4 (Sentry + Web Vitals + telemetry endpoint)
- [ ] Day 7: US-B5 (i18n)
- [ ] Day 8: US-B6 (a11y) + US-B7 (Lighthouse CI)
- [ ] Day 9: US-B8 (visual regression) + US-B9 (AuthShell + login/callback + inline cleanup) + US-C1 (closeout)

---

## Notes / Risks

- **D-PRE-8 is the key finding**: the auth flow being broken at the middleware-allowlist level confirms why the user couldn't log in. US-A1 fixes it (cookie fallback + EXEMPT_PATH_PREFIXES). Combined with the cookie↔localStorage fix (authStore + /auth/me), login → callback → authenticated → navigate becomes end-to-end functional.
- **Bundle size watch**: adding @radix-ui/react-dropdown-menu + @sentry/react + web-vitals + i18next + react-i18next will grow main bundle (~50-70 KB est). Sentry + i18n dynamic-import as mitigation; track vs 296.58 kB; retrospective Q3 + AD-Bundle-Size-285kB-Carryover continuation.
- **Large sprint scope control**: per checklist 重要備註 — if a US超估, go minimal-viable within that US (don't delete US; mark 🚧 + reason → carryover AD). cookie-only fallback path (Bearer + localStorage dev-login) if cookie cross-port fails in dev.
- **Day 1 三-prong完成**: a few content-verify items deferred to Day 1 start (low-risk impl details, none gate Day 1).
