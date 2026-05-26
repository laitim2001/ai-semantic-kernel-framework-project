/**
 * File: frontend/src/features/tenant-settings/components/tabs/QuotasTab.tsx
 * Purpose: Quotas tab — Usage quotas + Rate limits (real backend via useQuotas + useRateLimits).
 * Category: Frontend / tenant-settings / components / tabs
 * Scope: Phase 57 / Sprint 57.49 Day 1 (Track A 1.1.3 — fixture → real backend migration)
 *
 * Description:
 *   Sprint 57.49 migration: previously consumed `QUOTAS` + `RATE_LIMITS` from
 *   `_fixtures.ts`; now fetches via `useQuotas(tenantId)` + `useRateLimits(tenantId)`
 *   hooks (Sprint 57.48 Track C + D endpoints).
 *
 *   Backend QuotaItem shape: `{resource, limit, unit, period, current_usage}`.
 *   `current_usage` is `null` at admin layer (Sprint 57.48 doc-string: Redis
 *   gating Phase 58+). Bar-track percentage falls back to 0% until real usage
 *   wired; `used / max` display uses `current_usage ?? 0` / `limit`.
 *
 *   RateLimitItem `{label, value}` matches fixture exactly — direct render.
 *
 *   Loading/Empty/Error states added per resource.
 *
 * Created: 2026-05-26 (Sprint 57.44 Day 1) — original fixture port
 * Last Modified: 2026-05-26
 *
 * Modification History (newest-first):
 *   - 2026-05-26: Sprint 57.49 — fixture → useQuotas + useRateLimits real backend (Sprint 57.48 Track C+D)
 *   - 2026-05-26: Initial creation (Sprint 57.44 Day 1)
 *
 * Related:
 *   - backend/src/api/v1/admin/tenants.py L886-1030 (Quota + RateLimit endpoints)
 *   - ../../hooks/useQuotas.ts + ../../hooks/useRateLimits.ts
 */

import { Button, Card } from "../../../../components/mockup-ui";
import { BackendGapBanner } from "../../../../components/ui/BackendGapBanner";
import { useQuotas } from "../../hooks/useQuotas";
import { useRateLimits } from "../../hooks/useRateLimits";

export interface QuotasTabProps {
  tenantId: string;
}

function formatLimit(limit: number, unit: string): string {
  // Tokens are usually large numbers; format M / k for readability
  if (unit === "tokens" && limit >= 1_000_000) {
    return `${(limit / 1_000_000).toFixed(1)}M`;
  }
  if (limit >= 1_000) {
    return limit.toLocaleString();
  }
  return String(limit);
}

export function QuotasTab({ tenantId }: QuotasTabProps): JSX.Element {
  const quotas = useQuotas(tenantId);
  const rateLimits = useRateLimits(tenantId);

  const handleRequestIncrease = (): void => {
    window.alert("Request increase: backend gap (Phase 58+) — rate limit increase request endpoint pending");
  };

  return (
    <div className="grid-main">
      <Card title="Usage quotas">
        <BackendGapBanner reason="Live usage tracking (current_usage): backend extension Phase 58+ — limits shown are tenant-effective from PlanQuota" />
        {quotas.isLoading ? (
          <p className="muted">Loading quotas…</p>
        ) : quotas.error ? (
          // eslint-disable-next-line no-restricted-syntax -- inline-style error hint
          <p style={{ color: "var(--danger)", fontSize: 12 }}>
            Error loading quotas: {quotas.error.message}
          </p>
        ) : (quotas.data?.items ?? []).length === 0 ? (
          <p className="muted">No quotas configured for this tenant plan.</p>
        ) : (
          // eslint-disable-next-line no-restricted-syntax -- verbatim port: col gap
          <div className="col" style={{ gap: 14, marginTop: 8 }}>
            {(quotas.data?.items ?? []).map((q) => {
              const used = q.current_usage ?? 0;
              const pct = q.limit > 0 ? Math.round((used / q.limit) * 100) : 0;
              return (
                <div key={q.resource}>
                  {/* eslint-disable-next-line no-restricted-syntax -- verbatim port: spread marginBottom */}
                  <div className="spread" style={{ marginBottom: 4 }}>
                    {/* eslint-disable-next-line no-restricted-syntax -- verbatim port: fontSize */}
                    <span style={{ fontSize: 12.5 }}>{q.resource}</span>
                    {/* eslint-disable-next-line no-restricted-syntax -- verbatim port: mono fontSize */}
                    <span className="mono tnum" style={{ fontSize: 11.5 }}>
                      {/* eslint-disable-next-line no-restricted-syntax -- verbatim port: fg color */}
                      <span style={{ color: "var(--fg)" }}>{formatLimit(used, q.unit)}</span>{q.unit ? ` ${q.unit}` : ""}
                      <span className="subtle"> / {formatLimit(q.limit, q.unit)}{q.unit ? ` ${q.unit}` : ""}</span>
                    </span>
                  </div>
                  <div className="bar-track">
                    {/* eslint-disable-next-line no-restricted-syntax -- verbatim port: width pct */}
                    <span style={{ width: pct + "%" }} />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>
      <Card title="Rate limits">
        {rateLimits.isLoading ? (
          <p className="muted">Loading rate limits…</p>
        ) : rateLimits.error ? (
          // eslint-disable-next-line no-restricted-syntax -- inline-style error hint
          <p style={{ color: "var(--danger)", fontSize: 12 }}>
            Error loading rate limits: {rateLimits.error.message}
          </p>
        ) : (
          // eslint-disable-next-line no-restricted-syntax -- verbatim port: col gap + fontSize
          <div className="col" style={{ gap: 10, fontSize: 12 }}>
            {(rateLimits.data?.items ?? []).map((r) => (
              <div key={r.label} className="spread">
                <span className="muted">{r.label}</span>
                <span className="mono">{r.value}</span>
              </div>
            ))}
            <Button variant="outline" size="sm" onClick={handleRequestIncrease}>
              Request increase
            </Button>
          </div>
        )}
      </Card>
    </div>
  );
}
