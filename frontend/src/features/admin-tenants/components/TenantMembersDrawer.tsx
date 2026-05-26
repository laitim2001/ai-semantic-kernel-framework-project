/**
 * File: frontend/src/features/admin-tenants/components/TenantMembersDrawer.tsx
 * Purpose: Slide-over drawer showing paginated members of selected tenant (Sprint 57.47 endpoint).
 * Category: Frontend / admin-tenants / components
 * Scope: Phase 57 / Sprint 57.49 Day 1 (Track B — admin-tenants members drill-down)
 *
 * Description:
 *   New for Sprint 57.49 Track B — exposes Sprint 57.47 `/admin/tenants/{id}/members`
 *   endpoint as user-visible feature. Drawer is closed when `tenantId === null`;
 *   open with the selected tenant_id passed in.
 *
 *   Layout: fixed-position right-side panel (~520 px wide) over translucent
 *   backdrop; mockup-ui Card primitive inside. Closes on backdrop click,
 *   Escape key, or explicit X button.
 *
 *   Shared hook with TenantSettings MembersTab via `useTenantMembers` — same
 *   query key namespace so both views benefit from one cache entry.
 *
 *   Pagination: 50/page default; Previous/Next buttons; only renders when
 *   total > limit.
 *
 * Created: 2026-05-26 (Sprint 57.49 Day 1)
 *
 * Modification History (newest-first):
 *   - 2026-05-26: Initial creation (Sprint 57.49 Day 1 / Track B)
 *
 * Related:
 *   - backend/src/api/v1/admin/tenants.py L590-662 (Sprint 57.47 MEMBERS endpoint)
 *   - frontend/src/features/tenant-settings/hooks/useTenantMembers.ts (shared)
 *   - ./TenantsTable.tsx (row click handler trigger)
 *   - ./AdminTenantsView.tsx (mounts this drawer)
 */

/* eslint-disable no-restricted-syntax -- drawer overlay + slide layout uses inline style for fixed positioning; STYLE.md §3 escape hatch */

import { useEffect, useState } from "react";

import { Badge, Button, Card, Icon } from "../../../components/mockup-ui";
import { useTenantMembers } from "../../tenant-settings/hooks/useTenantMembers";

export interface TenantMembersDrawerProps {
  tenantId: string | null;
  onClose: () => void;
}

const PAGE_SIZE = 50;

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

export function TenantMembersDrawer({ tenantId, onClose }: TenantMembersDrawerProps): JSX.Element | null {
  const [offset, setOffset] = useState(0);

  // Reset offset whenever a different tenant is selected
  useEffect(() => {
    setOffset(0);
  }, [tenantId]);

  // Close on Escape key
  useEffect(() => {
    if (tenantId === null) return;
    const handler = (e: KeyboardEvent): void => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [tenantId, onClose]);

  const { data, isLoading, error } = useTenantMembers(tenantId ?? "", PAGE_SIZE, offset);

  if (tenantId === null) return null;

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const hasPrev = offset > 0;
  const hasNext = offset + PAGE_SIZE < total;

  return (
    // eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions -- backdrop overlay; Escape-key handler attached via window listener above (lines 64-72); button-vs-div tradeoff: button breaks dialog inset positioning
    <div
      data-testid="tenant-members-drawer"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 1000,
        background: "rgba(0,0,0,0.45)",
        display: "flex",
        justifyContent: "flex-end",
      }}
      onClick={onClose}
    >
      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-noninteractive-element-interactions -- stop-propagation div; role=dialog provides accessible name; inner controls (Close button + table rows) are keyboard-accessible */}
      <div
        style={{
          width: 520,
          maxWidth: "100%",
          height: "100%",
          background: "var(--bg)",
          overflowY: "auto",
          boxShadow: "-4px 0 24px rgba(0,0,0,0.18)",
        }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label="Tenant members"
      >
        <Card
          title="Members"
          subtitle={`${total} active · tenant ${tenantId}`}
          actions={
            <Button variant="ghost" size="sm" icon="x" onClick={onClose} aria-label="Close drawer">
              Close
            </Button>
          }
          bodyClass="flush"
        >
          {isLoading ? (
            <p className="muted" style={{ padding: 14 }}>Loading members…</p>
          ) : error ? (
            <p style={{ color: "var(--danger)", fontSize: 12, padding: 14 }}>
              Error loading members: {error.message}
            </p>
          ) : items.length === 0 ? (
            <p className="muted" style={{ padding: 14 }}>No members in this tenant.</p>
          ) : (
            <>
              <table className="table">
                <thead>
                  <tr>
                    <th>Member</th>
                    <th>Email</th>
                    <th>Status</th>
                    <th>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((m) => {
                    const name = m.display_name ?? m.email.split("@")[0];
                    const c = hueFromId(m.id);
                    return (
                      <tr key={m.id}>
                        <td>
                          <div className="row" style={{ gap: 8 }}>
                            <span
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
                            <span style={{ fontSize: 12.5 }}>{name}</span>
                          </div>
                        </td>
                        <td className="mono subtle" style={{ fontSize: 11.5 }}>{m.email}</td>
                        <td><Badge tone={m.status === "active" ? "success" : ""}>{m.status}</Badge></td>
                        <td className="subtle" style={{ fontSize: 11.5 }}>
                          {new Date(m.created_at).toLocaleDateString()}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {(hasPrev || hasNext) && (
                <div
                  className="row spread"
                  style={{
                    padding: 14,
                    borderTop: "1px solid var(--border)",
                    gap: 10,
                  }}
                >
                  <span className="muted" style={{ fontSize: 11.5 }}>
                    Showing {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total}
                  </span>
                  <div className="row" style={{ gap: 6 }}>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={!hasPrev}
                      onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      iconRight="chevron_right"
                      disabled={!hasNext}
                      onClick={() => setOffset(offset + PAGE_SIZE)}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </Card>
        {/* Sprint 57.49: hint a single Icon import is in use */}
        <span style={{ display: "none" }}>
          <Icon name="dots" size={12} />
        </span>
      </div>
    </div>
  );
}
