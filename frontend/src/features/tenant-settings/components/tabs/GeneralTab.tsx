/**
 * File: frontend/src/features/tenant-settings/components/tabs/GeneralTab.tsx
 * Purpose: General tab — General Card (display_name + region/locale/retention real) + Identity Card.
 * Category: Frontend / tenant-settings / components / tabs
 * Scope: Phase 57 / Sprint 57.50 Day 1 (Identity fixture → real backend wire)
 *
 * Description:
 *   Sprint 57.50 wires Identity & SSO Card to real backend via `useTenantIdentity`
 *   hook (fixture-projection Option A). 4 Identity rows (Provider type / SCIM /
 *   Allowed domains / MFA) now read from `GET /admin/tenants/{id}/identity`
 *   response; `IDENTITY_FIXTURE` dropped. `data.sso_enabled` remains the SSO
 *   Provider badge source (Sprint 57.46 baseline).
 *
 *   Save button continues to wire display_name + region + locale + retention_days
 *   (all 4 are patch-able via Sprint 57.46 TenantUpdateRequest extension).
 *
 * Created: 2026-05-26 (Sprint 57.44 Day 1) — original fixture port
 * Last Modified: 2026-05-26
 *
 * Modification History (newest-first):
 *   - 2026-05-26: Sprint 57.50 — Identity Card wires useTenantIdentity (closes IdentityFixture-Cleanup)
 *   - 2026-05-26: Sprint 57.49 — drop GENERAL_FIXTURE; consume Sprint 57.46 real fields
 *   - 2026-05-26: Initial creation (Sprint 57.44 Day 1)
 *
 * Related:
 *   - reference/design-mockups/page-admin.jsx L440-465
 *   - ../../hooks/useTenantSettingsSave.ts (display_name + new fields PATCH)
 *   - ../../hooks/useTenantIdentity.ts (Identity & SSO Card data source)
 */

import { useEffect, useState } from "react";

import { Badge, Button, Card, Field } from "../../../../components/mockup-ui";
import { BackendGapBanner } from "../../../../components/ui/BackendGapBanner";
import { useTenantIdentity } from "../../hooks/useTenantIdentity";
import { useTenantSettingsSave } from "../../hooks/useTenantSettingsSave";
import type { TenantSettingsResponse } from "../../types";

export interface GeneralTabProps {
  data: TenantSettingsResponse;
}

export function GeneralTab({ data }: GeneralTabProps): JSX.Element {
  const [displayName, setDisplayName] = useState<string>(data.display_name);
  const { mutate: save, isPending, error } = useTenantSettingsSave();
  const { data: identity, isLoading: identityLoading, error: identityError } = useTenantIdentity(data.id);

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
        <BackendGapBanner reason="SCIM / Allowed-domains / MFA values are tenant-effective via fixture-projection backend (Sprint 57.50); full SSO admin write endpoint deferred to Phase 58.x" />
        {/* eslint-disable-next-line no-restricted-syntax -- verbatim port: mockup uses inline style for col gap + fontSize */}
        <div className="col" style={{ gap: 10, fontSize: 12, marginTop: 8 }}>
          <div className="spread">
            <span className="muted">SSO Provider</span>
            <Badge tone={data.sso_enabled ? "success" : ""} dot={data.sso_enabled}>
              {data.sso_enabled ? "enabled" : "disabled"}
            </Badge>
          </div>
          {identityLoading && (
            // eslint-disable-next-line no-restricted-syntax -- inline-style loading hint mirrors save-error pattern
            <div className="muted" style={{ fontSize: 11.5 }}>Loading identity configuration…</div>
          )}
          {identityError && (
            // eslint-disable-next-line no-restricted-syntax -- inline-style error hint mirrors save-error pattern L86
            <div style={{ color: "var(--danger)", fontSize: 11.5 }}>
              Identity load failed: {identityError.message}
            </div>
          )}
          {identity && (
            <>
              <div className="spread">
                <span className="muted">Provider type</span>
                <Badge>{identity.provider}</Badge>
              </div>
              <div className="spread">
                <span className="muted">SCIM</span>
                <Badge tone={identity.scim_enabled ? "success" : ""} dot={identity.scim_enabled}>
                  {identity.scim_enabled ? "enabled" : "disabled"}
                </Badge>
              </div>
              <div className="spread">
                <span className="muted">Allowed domains</span>
                <span className="mono">{identity.allowed_domains.join(", ")}</span>
              </div>
              <div className="spread">
                <span className="muted">MFA</span>
                <Badge tone={identity.mfa_required ? "success" : ""} dot={identity.mfa_required}>
                  {identity.mfa_required ? "required" : "optional"}
                </Badge>
              </div>
            </>
          )}
          <Button variant="outline" size="sm" icon="settings" onClick={handleConfigureSso}>
            Configure
          </Button>
        </div>
      </Card>
    </div>
  );
}
