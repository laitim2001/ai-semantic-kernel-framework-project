/**
 * File: frontend/src/pages/admin-tenants/index.tsx
 * Purpose: Admin Tenants Console page (filters + table + pagination).
 * Category: Frontend / pages / admin-tenants
 * Scope: Phase 57 / Sprint 57.4 US-4 → 57.8 US-4 (page-level AppShellV2 migration)
 *
 * Description:
 *   Loads on mount + on store query change. URL query string sync deferred
 *   per AP-6 (will land alongside multi-page filter shareability when a
 *   real need surfaces; this sprint ships in-memory filter state only).
 *
 *   Backend enforces require_admin_platform_role; frontend lets 401/403
 *   surface as Error UX.
 *
 * Modification History:
 *   - 2026-05-10: Sprint 57.8 US-4 — page-level AppShellV2 wrap; remove inline
 *     padding (AppShellV2 main provides p-6); error block inline styles
 *     deferred to AD-Cost-Dashboard-ChildrenTailwind batch (Phase 58.2+)
 *
 * Created: 2026-05-07 (Sprint 57.4 Day 3)
 */

import { useEffect } from "react";

import { AppShellV2 } from "../../components/AppShellV2";
import { TenantListFilters } from "../../features/admin-tenants/components/TenantListFilters";
import { TenantListPagination } from "../../features/admin-tenants/components/TenantListPagination";
import { TenantListTable } from "../../features/admin-tenants/components/TenantListTable";
import { useAdminTenantsStore } from "../../features/admin-tenants/store/adminTenantsStore";

export function AdminTenantsPage(): JSX.Element {
  const { error, loadData } = useAdminTenantsStore();

  useEffect(() => {
    void loadData();
  }, [loadData]);

  return (
    <AppShellV2 pageTitle="Admin Tenants Console">
      <p className="mb-4 text-sm text-muted-foreground">
        Browse + filter all tenants. Backend enforces admin-platform role
        (Sprint 57.4 list endpoint). 401/403 surfaces as error below.
      </p>

      <TenantListFilters />

      {error && (
        <div
          style={{
            marginTop: "1rem",
            padding: "1rem",
            border: "1px solid #a00",
            color: "#a00",
          }}
        >
          <p>Error: {error}</p>
          <button onClick={() => void loadData()}>Retry</button>
        </div>
      )}

      <TenantListTable />
      <TenantListPagination />
    </AppShellV2>
  );
}

export default AdminTenantsPage;
