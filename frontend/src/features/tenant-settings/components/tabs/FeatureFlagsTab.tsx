/**
 * File: frontend/src/features/tenant-settings/components/tabs/FeatureFlagsTab.tsx
 * Purpose: Feature flags tab — table of tenant-scoped flag overrides (real backend via useFeatureFlags).
 * Category: Frontend / tenant-settings / components / tabs
 * Scope: Phase 57 / Sprint 57.49 Day 1 (Track A 1.1.2 — fixture → real backend migration)
 *
 * Description:
 *   Sprint 57.49 migration: previously consumed `FEATURE_FLAGS` from `_fixtures.ts`;
 *   now fetches via `useFeatureFlags(tenantId)` hook (Sprint 57.48 Track B endpoint).
 *
 *   Backend FeatureFlagItem shape: `{name, value, default_enabled, overridden,
 *   description, updated_at}`. Numeric override (mockup fixture `ctl: "num"`)
 *   not in backend yet — all rows render as boolean Switch. `def` derived from
 *   `default_enabled` (bool → "on"/"off" label).
 *
 *   Loading/Empty/Error states added; BackendGapBanner kept for honesty (numeric
 *   override Phase 58+).
 *
 * Created: 2026-05-26 (Sprint 57.44 Day 1) — original fixture port
 * Last Modified: 2026-05-26
 *
 * Modification History (newest-first):
 *   - 2026-05-26: Sprint 57.49 — fixture → useFeatureFlags real backend (Sprint 57.48 Track B)
 *   - 2026-05-26: Initial creation (Sprint 57.44 Day 1)
 *
 * Related:
 *   - backend/src/api/v1/admin/tenants.py L803-871 (FeatureFlagItem / list_tenant_feature_flags)
 *   - ../../hooks/useFeatureFlags.ts (TanStack consumer)
 */

import { Badge, Card, Switch } from "../../../../components/mockup-ui";
import { BackendGapBanner } from "../../../../components/ui/BackendGapBanner";
import { useFeatureFlags } from "../../hooks/useFeatureFlags";

export interface FeatureFlagsTabProps {
  tenantId: string;
}

export function FeatureFlagsTab({ tenantId }: FeatureFlagsTabProps): JSX.Element {
  const { data, isLoading, error } = useFeatureFlags(tenantId);

  if (isLoading) {
    return (
      <Card title="Feature flags" subtitle="Tenant-scoped overrides">
        <p className="muted">Loading feature flags…</p>
      </Card>
    );
  }

  if (error) {
    return (
      <Card title="Feature flags" subtitle="Tenant-scoped overrides">
        {/* eslint-disable-next-line no-restricted-syntax -- inline-style error hint */}
        <p style={{ color: "var(--danger)", fontSize: 12 }}>
          Error loading feature flags: {error.message}
        </p>
      </Card>
    );
  }

  const items = data?.items ?? [];

  return (
    <Card title="Feature flags" subtitle="Tenant-scoped overrides">
      <BackendGapBanner reason="Numeric flag overrides + per-tenant override write API: backend extension Phase 58+ — booleans shown are tenant-effective" />
      {items.length === 0 ? (
        <p className="muted">No feature flags registered for this tenant.</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Flag</th>
              <th>Description</th>
              <th>Default</th>
              <th>Tenant override</th>
            </tr>
          </thead>
          <tbody>
            {items.map((f) => (
              <tr key={f.name}>
                {/* eslint-disable-next-line no-restricted-syntax -- verbatim port: mono fontSize */}
                <td className="mono" style={{ fontSize: 12 }}>{f.name}</td>
                {/* eslint-disable-next-line no-restricted-syntax -- verbatim port: subtle fontSize */}
                <td className="subtle" style={{ fontSize: 12 }}>{f.description ?? "—"}</td>
                <td><Badge>{f.default_enabled ? "on" : "off"}</Badge></td>
                <td>
                  <Switch on={f.value} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}
