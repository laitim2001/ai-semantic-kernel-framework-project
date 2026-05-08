/**
 * File: frontend/src/pages/auth/login/index.tsx
 * Purpose: OIDC login entry — "Login with Microsoft Entra" button + 302 redirect to backend.
 * Category: Frontend / pages / auth (Sprint 57.7 US-A2)
 * Scope: Phase 57 / Sprint 57.7
 *
 * Description:
 *   Skeleton login page (basic React, NOT yet wrapped in AppShell — US-B2
 *   Day 3 will wrap). On click, sets post-login redirect target in
 *   sessionStorage then navigates browser to /api/v1/auth/login which
 *   returns 302 to vendor authorize URL. Backend handles all OIDC PKCE
 *   handshake; frontend only kicks off + receives JWT cookie at /callback.
 *
 *   Display error message if URL has ?error=... query param (callback
 *   failure surfaced via redirect with error payload).
 *
 * Created: 2026-05-09 (Sprint 57.7 Day 2 PM)
 * Last Modified: 2026-05-09
 *
 * Modification History:
 *   - 2026-05-09: Initial skeleton (Sprint 57.7 US-A2 Day 2)
 *
 * Related:
 *   - backend/src/api/v1/auth.py:login (302 redirect target)
 *   - frontend/src/features/auth/services/authService.ts:setPostLoginRedirect
 */

import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { setPostLoginRedirect } from "../../../features/auth/services/authService";

export default function LoginPage() {
  const [params] = useSearchParams();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const error = params.get("error");
    if (error) {
      setErrorMessage(decodeURIComponent(error));
    }
  }, [params]);

  const handleLogin = () => {
    // Day 3 may pull intended page from referer or query param ?redirect_to=...
    const redirectTo = params.get("redirect_to") || "/cost-dashboard";
    setPostLoginRedirect(redirectTo);
    // Navigate to backend; backend redirects to vendor → IdP → callback
    window.location.href = `/api/v1/auth/login?redirect_to=${encodeURIComponent(redirectTo)}`;
  };

  return (
    <div
      style={{
        padding: "4rem 2rem",
        fontFamily: "system-ui, sans-serif",
        maxWidth: "480px",
        margin: "0 auto",
      }}
    >
      <h1 style={{ marginBottom: "1rem" }}>IPA Platform V2 — Sign In</h1>
      <p style={{ color: "#666", marginBottom: "2rem" }}>
        Sprint 57.7 spike — IAM Foundation Tier 0. Click below to sign in via Microsoft Entra ID.
      </p>

      {errorMessage ? (
        <div
          role="alert"
          style={{
            padding: "0.75rem 1rem",
            marginBottom: "1.5rem",
            backgroundColor: "#fee",
            border: "1px solid #fcc",
            borderRadius: "4px",
            color: "#900",
          }}
        >
          <strong>Sign-in failed:</strong> {errorMessage}
        </div>
      ) : null}

      <button
        type="button"
        onClick={handleLogin}
        style={{
          padding: "0.75rem 1.5rem",
          fontSize: "1rem",
          fontWeight: 600,
          backgroundColor: "#0078d4",
          color: "white",
          border: "none",
          borderRadius: "4px",
          cursor: "pointer",
        }}
      >
        Login with Microsoft Entra
      </button>

      <p style={{ marginTop: "2rem", fontSize: "0.875rem", color: "#999" }}>
        Vendor: WorkOS (chosen per Sprint 57.7 US-A1 vendor matrix)
      </p>
    </div>
  );
}
