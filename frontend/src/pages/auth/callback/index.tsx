/**
 * File: frontend/src/pages/auth/callback/index.tsx
 * Purpose: OIDC callback landing — extract V2 JWT cookie + redirect to original page.
 * Category: Frontend / pages / auth (Sprint 57.7 US-A2)
 * Scope: Phase 57 / Sprint 57.7
 *
 * Description:
 *   Skeleton callback page. Backend /api/v1/auth/callback handles all OIDC
 *   exchange + V2 JWT issue + sets v2_jwt cookie + 302 redirects browser
 *   to the original requested page (oidc_redirect_to cookie). This page
 *   only handles the edge case where browser lands here directly (e.g.
 *   user refreshes after redirect) — extract JWT from cookie/document,
 *   stash in localStorage, then navigate to consumePostLoginRedirect().
 *
 *   Day 3 may swap to httpOnly cookie-only flow (then this page becomes
 *   pure loading spinner + nav delegate to backend redirect chain).
 *
 *   For Day 2 skeleton: simple loading UI + delegate to backend redirect
 *   (page should NEVER actually render content because backend 302 fires
 *   before React mounts).
 *
 * Created: 2026-05-09 (Sprint 57.7 Day 2 PM)
 * Last Modified: 2026-05-09
 *
 * Modification History:
 *   - 2026-05-09: Initial skeleton (Sprint 57.7 US-A2 Day 2)
 *
 * Related:
 *   - backend/src/api/v1/auth.py:callback (302 redirect with v2_jwt cookie)
 *   - frontend/src/features/auth/services/authService.ts
 */

import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  consumePostLoginRedirect,
  setJwt,
} from "../../../features/auth/services/authService";

export default function CallbackPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    // Path 1: backend already 302'd here with v2_jwt cookie set + URL param
    // Path 2: ?error=... query param surfaces vendor failure
    const error = params.get("error");
    if (error) {
      setErrorMessage(decodeURIComponent(error));
      return;
    }

    // Day 2 skeleton: read JWT from URL query (?token=...). Day 3 swap to
    // cookie-based flow once secure attribute decided.
    const token = params.get("token");
    if (token) {
      setJwt(token);
    }

    const target = consumePostLoginRedirect();
    // Use replace so back button doesn't return to /callback
    navigate(target, { replace: true });
  }, [navigate, params]);

  if (errorMessage) {
    return (
      <div
        style={{
          padding: "4rem 2rem",
          fontFamily: "system-ui, sans-serif",
          maxWidth: "480px",
          margin: "0 auto",
        }}
      >
        <h1>Sign-in failed</h1>
        <div
          role="alert"
          style={{
            padding: "0.75rem 1rem",
            marginTop: "1rem",
            backgroundColor: "#fee",
            border: "1px solid #fcc",
            borderRadius: "4px",
            color: "#900",
          }}
        >
          {errorMessage}
        </div>
        <p style={{ marginTop: "2rem" }}>
          <a href="/auth/login">← Back to login</a>
        </p>
      </div>
    );
  }

  return (
    <div
      style={{
        padding: "4rem 2rem",
        fontFamily: "system-ui, sans-serif",
        textAlign: "center",
      }}
    >
      <p>Completing sign-in…</p>
    </div>
  );
}
