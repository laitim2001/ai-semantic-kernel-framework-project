/**
 * File: frontend/src/features/tenant-settings/components/tabs/MembersTab.tsx
 * Purpose: Members tab — table of active members w/ avatar gradient (real backend via useTenantMembers).
 * Category: Frontend / tenant-settings / components / tabs
 * Scope: Phase 57 / Sprint 57.49 Day 1 (Track A 1.1.5 — fixture → real backend migration)
 *
 * Description:
 *   Sprint 57.49 migration: previously consumed `MEMBERS` from `_fixtures.ts`;
 *   now fetches via `useTenantMembers(tenantId)` hook (Sprint 57.47 endpoint).
 *
 *   Backend TenantMemberItem shape: `{id, email, display_name, status, created_at}`.
 *   Fields missing vs mockup fixture: `role` / `last_active` / `capacity_pct`
 *   (Sprint 57.47 doc-string: NOT in User ORM; Phase 58+ wire). Adapter:
 *   - `r` (role) = "operator" (placeholder until ORM extension)
 *   - `a` (last active) = "—" (status field shown instead)
 *   - `c` (capacity / hue) = derived from `id.charCodeAt(0) % 360` to preserve
 *     gradient variety
 *
 *   Loading/Empty/Error states added.
 *
 * Created: 2026-05-26 (Sprint 57.44 Day 1) — original fixture port
 * Last Modified: 2026-05-26
 *
 * Modification History (newest-first):
 *   - 2026-05-26: Sprint 57.49 — fixture → useTenantMembers real backend (Sprint 57.47)
 *   - 2026-05-26: Initial creation (Sprint 57.44 Day 1)
 *
 * Related:
 *   - backend/src/api/v1/admin/tenants.py L590-662 (TenantMemberItem / list_tenant_members)
 *   - ../../hooks/useTenantMembers.ts (TanStack consumer — shared with admin-tenants drawer)
 */

import { Badge, Button, Card, Icon } from "../../../../components/mockup-ui";
import { BackendGapBanner } from "../../../../components/ui/BackendGapBanner";
import { useTenantMembers } from "../../hooks/useTenantMembers";

export interface MembersTabProps {
  tenantId: string;
}

function initials(name: string): string {
  return name
    .split(" ")
    .map((x) => x[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function hueFromId(id: string): number {
  if (!id) return 200;
  return id.charCodeAt(0) * 17 + (id.charCodeAt(1) ?? 0) * 7;
}

export function MembersTab({ tenantId }: MembersTabProps): JSX.Element {
  const { data, isLoading, error } = useTenantMembers(tenantId);

  const handleInvite = (): void => {
    window.alert("Invite member: backend gap (Phase 58+) — member invitation endpoint pending");
  };

  if (isLoading) {
    return (
      <Card title="Members" subtitle="Loading…">
        <p className="muted">Loading members…</p>
      </Card>
    );
  }

  if (error) {
    return (
      <Card title="Members" subtitle="Error">
        {/* eslint-disable-next-line no-restricted-syntax -- inline-style error hint */}
        <p style={{ color: "var(--danger)", fontSize: 12 }}>
          Error loading members: {error.message}
        </p>
      </Card>
    );
  }

  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  return (
    <Card
      title="Members"
      subtitle={`${total} active · 0 invitations`}
      actions={
        <Button variant="primary" size="sm" icon="plus" onClick={handleInvite}>
          Invite
        </Button>
      }
      bodyClass="flush"
    >
      <BackendGapBanner reason="Role / last-active / capacity per-member: backend extension Phase 58+ — email + display_name shown are tenant-effective" />
      {items.length === 0 ? (
        // eslint-disable-next-line no-restricted-syntax -- inline padding for empty state
        <p className="muted" style={{ padding: 14 }}>No members in this tenant.</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Member</th>
              <th>Email</th>
              <th>Status</th>
              <th>Created</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((m) => {
              const name = m.display_name ?? m.email.split("@")[0];
              const c = hueFromId(m.id);
              return (
                <tr key={m.id}>
                  <td>
                    {/* eslint-disable-next-line no-restricted-syntax -- verbatim port: row gap */}
                    <div className="row" style={{ gap: 8 }}>
                      <span
                        // eslint-disable-next-line no-restricted-syntax -- verbatim port: oklch avatar gradient + dimensions
                        style={{
                          width: 24,
                          height: 24,
                          borderRadius: "50%",
                          background: `linear-gradient(135deg, oklch(0.65 0.15 ${c % 360}), oklch(0.5 0.16 ${(c + 60) % 360}))`,
                          color: "white",
                          display: "inline-flex",
                          alignItems: "center",
                          justifyContent: "center",
                          fontSize: 10,
                          fontWeight: 600,
                        }}
                      >
                        {initials(name)}
                      </span>
                      {/* eslint-disable-next-line no-restricted-syntax -- verbatim port: fontSize */}
                      <span style={{ fontSize: 12.5 }}>{name}</span>
                    </div>
                  </td>
                  {/* eslint-disable-next-line no-restricted-syntax -- verbatim port: mono subtle fontSize */}
                  <td className="mono subtle" style={{ fontSize: 11.5 }}>{m.email}</td>
                  <td><Badge tone={m.status === "active" ? "success" : ""}>{m.status}</Badge></td>
                  {/* eslint-disable-next-line no-restricted-syntax -- verbatim port: subtle fontSize */}
                  <td className="subtle" style={{ fontSize: 11.5 }}>
                    {new Date(m.created_at).toLocaleDateString()}
                  </td>
                  <td><Icon name="dots" size={14} className="subtle" /></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </Card>
  );
}
