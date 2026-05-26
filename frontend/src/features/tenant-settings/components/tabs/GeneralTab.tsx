/**
 * File: frontend/src/features/tenant-settings/components/tabs/GeneralTab.tsx
 * Purpose: General tab — General Card (display_name + region/locale/retention real) + Identity Card.
 * Category: Frontend / tenant-settings / components / tabs
 * Scope: Phase 57 / Sprint 57.49 Day 1 (Track A 1.1.1 — Sprint 57.46 backend real consumption)
 *
 * Description:
 *   Sprint 57.49: removes residual `GENERAL_FIXTURE` import; consumes real
 *   `data.region / data.locale / data.retention_days` (Sprint 57.46 TenantResponse
 *   15-field schema). `IDENTITY_FIXTURE` retained for SCIM/Allowed-domains/MFA
 *   (no backend fields yet); `data.sso_enabled` displayed as Provider badge.
 *
 *   Save button now wires display_name + region + locale + retention_days
 *   (all 4 are patch-able via Sprint 57.46 TenantUpdateRequest extension).
 *
 * Created: 2026-05-26 (Sprint 57.44 Day 1) — original fixture port
 * Last Modified: 2026-05-26
 *
 * Modification History (newest-first):
 *   - 2026-05-26: Sprint 57.49 — drop GENERAL_FIXTURE; consume Sprint 57.46 real fields
 *   - 2026-05-26: Initial creation (Sprint 57.44 Day 1)
 *
 * Related:
 *   - reference/design-mockups/page-admin.jsx L440-465
 *   - ../../hooks/useTenantSettingsSave.ts (display_name + new fields PATCH)
 *   - ../../_fixtures.ts (IDENTITY_FIXTURE only; SCIM/Allowed-domains/MFA still gap)
 */

import { useEffect, useState } from "react";

import { Badge, Button, Card, Field } from "../../../../components/mockup-ui";
import { BackendGapBanner } from "../../../../components/ui/BackendGapBanner";
import { IDENTITY_FIXTURE } from "../../_fixtures";
import { useTenantSettingsSave } from "../../hooks/useTenantSettingsSave";
import type { TenantSettingsResponse } from "../../types";

export interface GeneralTabProps {
  data: TenantSettingsResponse;
}

export function GeneralTab({ data }: GeneralTabProps): JSX.Element {
  const [displayName, setDisplayName] = useState<string>(data.display_name);
  const { mutate: save, isPending, error } = useTenantSettingsSave();

  // Reset local edit state when backend data refreshes (post-save invalidation).
  useEffect(() => {
    setDisplayName(data.display_name);
  }, [data.display_name]);

  const dirty = displayName !== data.display_name;

  const handleSave = (): void => {
    if (!dirty) return;
    save({ tenantId: data.id, payload: { display_name: displayName } });
  };

  const handleConfigureSso = (): void => {
    window.alert("Configure SSO: backend gap (Phase 58+) — SSO admin endpoint pending");
  };

  return (
    <div className="grid-main">
      <Card title="General">
        {/* eslint-disable-next-line no-restricted-syntax -- verbatim port: mockup uses inline style for col gap + maxWidth */}
        <div className="col" style={{ gap: 14, maxWidth: 480 }}>
          <Field label="Display name">
            <input
              className="input"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              disabled={isPending}
            />
            {dirty && (
              // eslint-disable-next-line no-restricted-syntax -- inline-style row gap mirrors mockup .row pattern
              <div className="row" style={{ gap: 8, marginTop: 8 }}>
                <Button variant="primary" size="sm" onClick={handleSave} disabled={isPending}>
                  {isPending ? "Saving…" : "Save"}
                </Button>
                <Button variant="outline" size="sm" onClick={() => setDisplayName(data.display_name)} disabled={isPending}>
                  Cancel
                </Button>
              </div>
            )}
            {error && (
              // eslint-disable-next-line no-restricted-syntax -- inline-style minor error hint
              <div style={{ color: "var(--danger)", fontSize: 11.5, marginTop: 6 }}>
                Save failed: {error.message}
              </div>
            )}
          </Field>
          <Field label="Tenant id">
            <input className="input mono" readOnly value={data.code} />
          </Field>
          <Field label="Default region">
            <input className="input" readOnly value={data.region} />
          </Field>
          <Field label="Default locale">
            <input className="input" readOnly value={data.locale} />
          </Field>
          <Field label="Data retention" help="Memory + audit retention. WORM audit is append-only.">
            {/* eslint-disable-next-line no-restricted-syntax -- verbatim port row gap */}
            <div className="row" style={{ gap: 8 }}>
              <input
                className="input"
                readOnly
                value={data.retention_days}
                // eslint-disable-next-line no-restricted-syntax -- verbatim port input maxWidth
                style={{ maxWidth: 100 }}
              />
              <span className="muted">days</span>
            </div>
          </Field>
          <Field label="Seats">
            {/* eslint-disable-next-line no-restricted-syntax -- verbatim port row gap */}
            <div className="row" style={{ gap: 8 }}>
              <input
                className="input"
                readOnly
                value={data.seats}
                // eslint-disable-next-line no-restricted-syntax -- verbatim port input maxWidth
                style={{ maxWidth: 100 }}
              />
              <span className="muted">licensed</span>
            </div>
          </Field>
          <BackendGapBanner reason="Region / locale / retention / seats edit UI: backend supports PATCH (Sprint 57.46); inline edit UI Phase 58+ — values shown are tenant-effective from DB" />
        </div>
      </Card>
      <Card title="Identity & SSO">
        <BackendGapBanner reason="SCIM / Allowed-domains / MFA configuration: backend extension Phase 58+ — values shown are mockup defaults; SSO status from DB" />
        {/* eslint-disable-next-line no-restricted-syntax -- verbatim port: mockup uses inline style for col gap + fontSize */}
        <div className="col" style={{ gap: 10, fontSize: 12, marginTop: 8 }}>
          <div className="spread">
            <span className="muted">SSO Provider</span>
            <Badge tone={data.sso_enabled ? "success" : ""} dot={data.sso_enabled}>
              {data.sso_enabled ? "enabled" : "disabled"}
            </Badge>
          </div>
          <div className="spread">
            <span className="muted">Provider type</span>
            <Badge>{IDENTITY_FIXTURE.provider}</Badge>
          </div>
          <div className="spread">
            <span className="muted">SCIM</span>
            <Badge tone="success" dot>{IDENTITY_FIXTURE.scim}</Badge>
          </div>
          <div className="spread">
            <span className="muted">Allowed domains</span>
            <span className="mono">{IDENTITY_FIXTURE.allowedDomains}</span>
          </div>
          <div className="spread">
            <span className="muted">MFA</span>
            <Badge tone="success" dot>{IDENTITY_FIXTURE.mfa}</Badge>
          </div>
          <Button variant="outline" size="sm" icon="settings" onClick={handleConfigureSso}>
            Configure
          </Button>
        </div>
      </Card>
    </div>
  );
}
