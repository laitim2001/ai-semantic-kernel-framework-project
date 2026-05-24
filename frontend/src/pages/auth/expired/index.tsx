/**
 * File: frontend/src/pages/auth/expired/index.tsx
 * Purpose: Session-expired splash — verbatim re-point per mockup AuthExpired (Sprint 57.35 US-D3).
 * Category: Frontend / pages / auth
 * Scope: Phase 57 / Sprint 57.23 US-D3 (initial NEW route) → Sprint 57.35 US-D3 (Phase-2 verbatim-CSS re-point)
 *
 * Description:
 *   Sprint 57.35 US-D3 verbatim re-point per `reference/design-mockups/page-auth-extras.jsx:373-416`:
 *     - Drop shadcn Card/CardContent/Button/Badge + lucide-react Clock/ArrowRight
 *     - Use mockup-ui Card + Button + Badge + Icon (clock/arrow_right)
 *     - Verbatim .col + .row + .muted + .subtle + .mono + .spread classes
 *     - 56×56 warning-alpha clock avatar inline-style verbatim per mockup L378-384
 *     - 3-row metadata grid inline-style verbatim per mockup L390-403
 *     - Badge tone="warning" for reason (was generic Badge in Sprint 57.23)
 *
 *   Query param contract preserved:
 *     - ?session_id=<id> → metadata grid (fallback FIXTURE_SESSION_ID)
 *     - ?reason=<reason> → Badge (fallback FIXTURE_REASON)
 *     - ?next=<path> → forwarded to /auth/callback?next= on "Resume session"
 *
 *   No backend fetch (client-side splash; previous request already returned 401).
 *
 * Created: 2026-05-18 (Sprint 57.23 US-D3)
 * Last Modified: 2026-05-24
 *
 * Modification History:
 *   - 2026-05-24: Sprint 57.35 US-D3 — verbatim re-point per page-auth-extras.jsx:373-416 (closes Sprint 57.23 vintage HSL-translation drift); Badge tone='warning' for reason matches mockup L401
 *   - 2026-05-18: Initial creation (Sprint 57.23 US-D3) — mockup-direct port of AuthExpired
 *
 * Related:
 *   - frontend/src/components/AuthShell.tsx (Sprint 57.35 verbatim re-point)
 *   - frontend/src/components/mockup-ui.tsx (Card/Button/Badge/Icon)
 *   - frontend/src/i18n/locales/{en,zh-TW}/auth.json (auth.expired.* namespace)
 *   - reference/design-mockups/page-auth-extras.jsx:373-416 (AuthExpired canonical visual source)
 */

/* eslint-disable no-restricted-syntax -- verbatim re-point: inline-style literals (avatar + metadata grid + buttons row + container) copied byte-for-byte from mockup page-auth-extras.jsx:373-416 (STYLE.md §1 escape hatch + frontend-mockup-fidelity.md verbatim-CSS rule) */

import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";

import { AuthShell } from "@/components/AuthShell";
import { Badge, Button, Card, Icon } from "@/components/mockup-ui";

const FIXTURE_LAST_ACTIVITY = "14h 02m ago";
const FIXTURE_SESSION_ID = "sess_8a2f1c3";
const FIXTURE_REASON = "jwt_expired · 24h max";

export default function ExpiredPage(): JSX.Element {
  const { t } = useTranslation("auth");
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const sessionId = searchParams.get("session_id") ?? FIXTURE_SESSION_ID;
  const reason = searchParams.get("reason") ?? FIXTURE_REASON;
  const next = searchParams.get("next");

  const signInAgain = (): void => navigate("/auth/login");
  const resume = (): void => {
    const target = next ? `/auth/callback?next=${encodeURIComponent(next)}` : "/auth/callback";
    navigate(target);
  };

  return (
    <AuthShell>
      <Card>
        <div
          className="col"
          style={{ gap: 16, alignItems: "center", textAlign: "center", padding: 8 }}
        >
          {/* Icon — verbatim mockup L378-384 */}
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: "50%",
              background: "oklch(from var(--warning) l c h / 0.14)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--warning)",
            }}
            aria-hidden
          >
            <Icon name="clock" size={26} />
          </div>

          {/* Title + subtitle — verbatim mockup L385-388 */}
          <div>
            <div style={{ fontSize: 17, fontWeight: 600, marginBottom: 6 }}>
              {t("expired.title")}
            </div>
            <div
              className="muted"
              style={{ fontSize: 13, maxWidth: 320, lineHeight: 1.5 }}
            >
              {t("expired.subtitle")}
            </div>
          </div>

          {/* Metadata grid — verbatim mockup L390-403 */}
          <div
            className="col"
            style={{
              gap: 0,
              alignSelf: "stretch",
              background: "var(--bg-1)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-sm)",
            }}
          >
            <div
              className="spread"
              style={{
                padding: "8px 12px",
                borderBottom: "1px solid var(--border)",
                fontSize: 11.5,
              }}
            >
              <span className="muted">{t("expired.lastActivity")}</span>
              <span className="mono">{FIXTURE_LAST_ACTIVITY}</span>
            </div>
            <div
              className="spread"
              style={{
                padding: "8px 12px",
                borderBottom: "1px solid var(--border)",
                fontSize: 11.5,
              }}
            >
              <span className="muted">{t("expired.sessionId")}</span>
              <span className="mono subtle">{sessionId}</span>
            </div>
            <div className="spread" style={{ padding: "8px 12px", fontSize: 11.5 }}>
              <span className="muted">{t("expired.reason")}</span>
              <Badge tone="warning">{reason}</Badge>
            </div>
          </div>

          {/* Buttons row — verbatim mockup L405-408 */}
          <div
            className="row"
            style={{ gap: 8, alignSelf: "stretch", marginTop: 4 }}
          >
            <Button variant="outline" onClick={signInAgain}>
              {t("expired.signInAgain")}
            </Button>
            <Button
              variant="primary"
              iconRight="arrow_right"
              onClick={resume}
            >
              {t("expired.resume")}
            </Button>
          </div>

          {/* Data hint — verbatim mockup L410-412 */}
          <div
            className="muted"
            style={{ fontSize: 11, marginTop: 2, maxWidth: 320, lineHeight: 1.5 }}
          >
            {t("expired.dataHint")}
          </div>
        </div>
      </Card>
    </AuthShell>
  );
}
