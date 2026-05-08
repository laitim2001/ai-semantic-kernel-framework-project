/**
 * File: frontend/src/features/auth/services/authService.ts
 * Purpose: V2 JWT helpers + auth fetch wrapper for OIDC PKCE flow.
 * Category: Frontend / auth / services
 * Scope: Phase 57 / Sprint 57.7 US-A2
 *
 * Description:
 *   Foundational auth service consumed by ALL feature services. Provides:
 *
 *   1. getJwt() — read JWT cookie value (set by /api/v1/auth/callback)
 *   2. setJwt(token) — write JWT to localStorage (Day 2 cookie-based; Day 3
 *      may swap to httpOnly cookie when SameSite/CSRF model finalized)
 *   3. clearJwt() — remove JWT for logout
 *   4. isAuthenticated() — boolean check for guard logic
 *   5. fetchWithAuth(url, init) — wrapper adding Authorization: Bearer header
 *
 *   Day 2 skeleton uses localStorage for simplicity (matches backend cookie
 *   placement in /callback; both readable/writable from JS). Day 3 may
 *   harden via httpOnly secure cookie + CSRF token + SameSite=Lax once
 *   security model finalized in 20-iam-deep-dive.md design note §2.5.
 *
 * Created: 2026-05-09 (Sprint 57.7 Day 2 PM)
 * Last Modified: 2026-05-09
 *
 * Modification History:
 *   - 2026-05-09: Initial creation (Sprint 57.7 US-A2 Day 2)
 *
 * Related:
 *   - backend/src/api/v1/auth.py (login + callback + logout endpoints)
 *   - backend/src/platform_layer/identity/jwt.py (JWTManager.encode HS256)
 *   - frontend/src/pages/auth/{login,callback}/index.tsx (consumers)
 */

const JWT_STORAGE_KEY = "v2_jwt";
const REDIRECT_KEY = "v2_post_login_redirect";

export function getJwt(): string | null {
  return localStorage.getItem(JWT_STORAGE_KEY);
}

export function setJwt(token: string): void {
  localStorage.setItem(JWT_STORAGE_KEY, token);
}

export function clearJwt(): void {
  localStorage.removeItem(JWT_STORAGE_KEY);
}

export function isAuthenticated(): boolean {
  const token = getJwt();
  if (!token) return false;
  // Day 3 may add expiry parsing via jose / jwt-decode; for skeleton
  // presence-of-token is sufficient.
  return token.length > 0;
}

export function setPostLoginRedirect(path: string): void {
  sessionStorage.setItem(REDIRECT_KEY, path);
}

export function consumePostLoginRedirect(): string {
  const path = sessionStorage.getItem(REDIRECT_KEY);
  sessionStorage.removeItem(REDIRECT_KEY);
  return path || "/cost-dashboard";
}

/**
 * Wrapper around fetch() that adds Authorization: Bearer header when
 * JWT is present. Use this in all feature services instead of raw fetch.
 *
 * 401 responses surface as Error so feature components can redirect to
 * /auth/login (Day 3 may add automatic redirect via QueryClient onError).
 */
export async function fetchWithAuth(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  const token = getJwt();
  const headers = new Headers(init?.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  return fetch(input, {
    ...init,
    headers,
    credentials: "include",
  });
}

export async function logout(): Promise<void> {
  // Call backend /auth/logout to get vendor signout URL
  const response = await fetchWithAuth("/api/v1/auth/logout", { method: "POST" });
  clearJwt();
  if (response.ok) {
    const body = (await response.json()) as { redirect_to: string };
    window.location.href = body.redirect_to;
  } else {
    // Even on backend error clear local JWT; redirect to login
    window.location.href = "/auth/login";
  }
}
